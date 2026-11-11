"""The six frozen core queries (PLAN §5.4) — the S1 "done when" bar.

Every query below is written against the indexes frozen in the schema, and
each one's expected index is stated in its docstring. RULES.md §1.2: a query
shape change that loses the index path is a change request, not a refactor.

The S1 acceptance test (PLAN §5.6) runs these against a 100k-row seed and
captures EXPLAIN ANALYZE for each — see docs/decisions/ and the seed command.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from django.db import connection, models
from django.db.models import Count, F, Q
from django.db.models.functions import Cast, Lower

from accounts.models import User
from files.models import File, FileStatus
from groups.models import Group, Membership, MembershipStatus, Post
from notifications.models import Notification
from tasks.models import Task, TaskRequest, TaskRequestStatus


# --------------------------------------------------------------------------
# Q1 — "My groups" + unread counts
# --------------------------------------------------------------------------

def unread_counts(user: User) -> models.QuerySet:
    """Unread count per group for `user` — index: notifications_unread
    (user, group, partial: read_at IS NULL). GROUP BY rides the index's
    (user, group) prefix; no full-table scan, ever."""
    return (
        Notification.objects.filter(
            user=user,
            read_at__isnull=True,
            group__isnull=False,
        )
        .values_list("group")
        .annotate(c=Count("id"))
    )


def my_groups_with_unread(user: User) -> list[tuple[Group, int]]:
    """Groups where `user` is an ACTIVE member, each with its unread count.

    Indexes:
    - memberships_user_active (user, partial: status=active)  → my groups
    - notifications_unread    (user, group, partial: read_at IS NULL) → counts

    Two small, independent, index-only lookups — no GROUP BY over all rows.
    """
    groups = list(
        Group.objects.filter(
            memberships__user=user,
            memberships__status=MembershipStatus.ACTIVE,
        ).order_by("created_at")
    )
    unread = dict(unread_counts(user))
    return [(g, unread.get(g.id, 0)) for g in groups]


# --------------------------------------------------------------------------
# Q2 — A group's tasks in one month (the calendar query)
# --------------------------------------------------------------------------

def group_tasks_timed(group: Group, from_dt: datetime, to_dt: datetime) -> models.QuerySet:
    """Timed branch — tasks_group_start (group, start_at, partial)."""
    return (
        Task.objects.filter(
            deleted_at__isnull=True, group=group, rrule__isnull=True, all_day=False
        )
        .filter(Q(start_at__lt=to_dt) & (Q(end_at__gte=from_dt) | Q(end_at__isnull=True)))
        .annotate(start_key=F("start_at"))
        .values("id", "start_key")
    )


def group_tasks_allday(group: Group, from_dt: datetime, to_dt: datetime) -> models.QuerySet:
    """All-day branch — tasks_group_sdate (group, start_date, partial).

    All-day rows compare in DATE space, never cast date→timestamptz
    (ADR-002); the cast here is only for the common union sort key, which is
    legal in queries — only index EXPRESSIONS must be IMMUTABLE."""
    from_date = from_dt.date()
    to_date = (to_dt - timedelta(days=1)).date()
    return (
        Task.objects.filter(
            deleted_at__isnull=True, group=group, rrule__isnull=True, all_day=True
        )
        .filter(
            Q(start_date__lt=to_date) & (Q(end_date__gte=from_date) | Q(end_date__isnull=True))
        )
        .annotate(start_key=Cast(F("start_date"), output_field=models.DateTimeField()))
        .values("id", "start_key")
    )


def group_tasks_recurring(group: Group, from_dt: datetime) -> models.QuerySet:
    """Recurring branch — tasks_group_recur (group, partial: rrule IS NOT NULL)."""
    return (
        Task.objects.filter(deleted_at__isnull=True, group=group, rrule__isnull=False)
        .filter(Q(recur_until__isnull=True) | Q(recur_until__gte=from_dt))
        .annotate(start_key=F("created_at"))
        .values("id", "start_key")
    )


def group_tasks_in_month(
    group: Group, from_dt: datetime, to_dt: datetime
) -> models.QuerySet:
    """All live tasks of `group` overlapping [from_dt, to_dt), as a UNION of
    the three disjoint frozen branches above — the calendar query shape
    (ADR-002). Branches are disjoint by construction (all_day XOR timed XOR
    recurring), so UNION ALL is correct and skips dedup work."""
    return group_tasks_timed(group, from_dt, to_dt).union(
        group_tasks_allday(group, from_dt, to_dt),
        group_tasks_recurring(group, from_dt),
        all=True,
    ).order_by("start_key")


# --------------------------------------------------------------------------
# Q3 — "Due soon" (deadlines in the next N days, my active groups)
# --------------------------------------------------------------------------

def tasks_due_soon(user: User, horizon: timedelta, now: datetime) -> models.QuerySet:
    """Live tasks of my ACTIVE groups with deadline_at in [now, now+horizon].

    Indexes:
    - memberships_user_active → my groups (subquery)
    - tasks_group_deadline (group, deadline_at) WHERE deleted_at IS NULL
      AND deadline_at IS NOT NULL → the range scan per group.

    SHAPE (frozen): two steps, mirroring Q1 — (1) fetch my active group ids
    via memberships_user_active, then (2) filter tasks with a LITERAL IN list
    of those ids, so the planner knows the exact groups at plan time and does
    one tight range scan on tasks_group_deadline PER GROUP. Passing the ids
    as a subquery instead lets the planner flatten it into a merge join over
    the generic group_id index, which degrades badly once many rows fall
    inside the deadline window (observed on the 100k seed: 65k rows filtered,
    70+ ms).

    Returns a values() projection of the due-soon list columns (id, title,
    deadline_at, group_id, group_name) — the list view never needs full rows,
    and hydrating hundreds of full Task instances would dominate the wall
    clock while the DB itself answers in a few ms.

    Personal tasks are intentionally NOT included: the frozen index set only
    covers group scoping, and "due soon" is a group feature (PLAN §8).
    """
    my_group_ids = list(
        Membership.objects.filter(user=user, status=MembershipStatus.ACTIVE).values_list(
            "group_id", flat=True
        )
    )
    return (
        Task.objects.filter(
            deleted_at__isnull=True,
            deadline_at__isnull=False,
            deadline_at__gte=now,
            deadline_at__lte=now + horizon,
            group_id__in=my_group_ids,
        )
        .values(
            "id",
            "title",
            "deadline_at",
            "group_id",
            group_name=F("group__name"),
        )
        .order_by("deadline_at")
    )


# --------------------------------------------------------------------------
# Q4 — Group feed page (keyset pagination)
# --------------------------------------------------------------------------

def feed_page(
    group: Group,
    limit: int = 20,
    cursor: tuple[datetime, uuid.UUID] | None = None,
) -> tuple[list[Post], tuple[datetime, uuid.UUID] | None]:
    """One page of the History-tab feed, keyset-paginated on (created_at, id).

    Index: posts_group_created_id (group, -created_at, -id).
    The keyset predicate (created_at, id) < (c, i) is exactly the index order,
    so page N is a bounded index read — OFFSET is never used.
    """
    qs = Post.objects.filter(group=group, deleted_at__isnull=True)
    if cursor is not None:
        c_created, c_id = cursor
        qs = qs.filter(Q(created_at__lt=c_created) | Q(created_at=c_created, id__lt=c_id))

    page = list(qs.order_by("-created_at", "-id")[: limit + 1])
    has_more = len(page) > limit
    page = page[:limit]
    next_cursor = None
    if has_more and page:
        next_cursor = (page[-1].created_at, page[-1].id)
    return page, next_cursor


# --------------------------------------------------------------------------
# Q5 — File search across my groups (trigram)
# --------------------------------------------------------------------------

def files_search(user: User, query: str, limit: int = 20) -> models.QuerySet:
    """Substring search over file names in my ACTIVE groups.

    Index: files_filename_trgm — GIN (gin_trgm_ops) on lower(filename).

    CRITICAL (frozen): the predicate must be an exact match of the INDEX
    EXPRESSION, i.e. `Lower("filename")__contains=q`. Django's `icontains`
    compiles to `UPPER(col) LIKE UPPER(q)` on Postgres, whose trigram set
    does NOT match the `lower(col)` index — it would silently fall back to a
    seq scan. We annotate Lower() explicitly and filter on it.
    """
    return (
        File.objects.filter(
            group__memberships__user=user,
            group__memberships__status=MembershipStatus.ACTIVE,
            status=FileStatus.READY,
            deleted_at__isnull=True,
        )
        .annotate(fn=Lower("filename"))
        .filter(fn__contains=query.lower())
        .order_by("-created_at")[:limit]
    )


# --------------------------------------------------------------------------
# Q6 — Pending task requests (moderation queue)
# --------------------------------------------------------------------------

def pending_requests(group: Group) -> models.QuerySet:
    """The admin moderation queue: pending requests, oldest first.

    Index: task_requests_group_pending (group) WHERE status='pending'.
    Decided rows never enter this scan (ADR-003: pending data can't leak).
    """
    return (
        TaskRequest.objects.filter(group=group, status=TaskRequestStatus.PENDING)
        .select_related("requested_by")
        .order_by("created_at")
    )


# --------------------------------------------------------------------------
# Explain helpers (S1 acceptance: capture EXPLAIN ANALYZE per query)
# --------------------------------------------------------------------------

def explain(qs: models.QuerySet, analyze: bool = True) -> str:
    """EXPLAIN (ANALYZE) text for a queryset — used by the acceptance run to
    prove each frozen query uses its frozen index."""
    return qs.explain(analyze=analyze, format="text")


def force_index_plan(qs: models.QuerySet) -> str:
    """EXPLAIN for `qs` with seq scans disabled in this transaction, so the
    plan demonstrates the frozen index path even on tiny test datasets.

    SET LOCAL applies only inside the current transaction; callers run inside
    an atomic block (pytest-django does this per test). ANALYZE is omitted
    (tiny tables prove nothing about timing). For plans that also compete
    with Django's auto-named FK indexes, tests drop those first (see
    tests/test_queries.py::_drop_fk_indexes) — DDL is transactional, so the
    rollback restores them."""
    with connection.cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = off")
        return qs.explain(analyze=False, format="text")


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """UTC [start, end) of a calendar month — helper for Q2 callers/tests."""
    from_dt = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        to_dt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        to_dt = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return from_dt, to_dt


# Export the frozen six for discoverability (S1 acceptance script iterates).
CORE_QUERIES = [
    my_groups_with_unread,
    group_tasks_in_month,
    tasks_due_soon,
    feed_page,
    files_search,
    pending_requests,
]
