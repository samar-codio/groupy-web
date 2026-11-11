"""The six core queries (PLAN §5.4): correctness against fixture data AND
proof that each query's plan uses its frozen index (seq scans disabled
locally so tiny test tables still demonstrate the index path).
"""

from datetime import datetime, timedelta, timezone

import pytest
from django.db import connection

from core.queries import (
    feed_page,
    files_search,
    force_index_plan,
    group_tasks_in_month,
    month_bounds,
    my_groups_with_unread,
    pending_requests,
    tasks_due_soon,
)
from groups.models import Group, Membership, MembershipStatus, Post
from notifications.models import Notification
from tasks.models import Task, TaskRequest, TaskRequestStatus

# Same "today" as the fixture data in conftest.py.
NOW = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
HORIZON = timedelta(days=7)


def _drop_fk_indexes(table: str, extra: tuple[str, ...] = ()) -> list[str]:
    """Drop Django's auto-named FK indexes on `table` (plus any `extra`
    frozen indexes that would compete on tiny data) inside this test's
    transaction — pytest-django rolls back afterwards, restoring them.

    On tiny tables the planner prefers generic (group_id) FK indexes or other
    wider indexes over the frozen composite/partial ones, so this simulates
    the frozen index set for the query under test — where the ONLY usable
    indexes are the frozen ones (PLAN §5.4) — and makes the plan assertion
    deterministic. Django FK index names end in an 8-hex suffix, e.g.
    tasks_group_id_cf815437; frozen names never do."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT indexname FROM pg_indexes"
            " WHERE schemaname = 'public' AND tablename = %s"
            " AND indexname ~ ('^' || %s || '_[a-z_]+_[0-9a-f]{8}$')",
            [table, table],
        )
        names = [row[0] for row in cur.fetchall()]
        for name in names + list(extra):
            cur.execute(f'DROP INDEX "{name}"')
    return names


# ---------------------------------------------------------------------------
# Q1 — my groups + unread counts
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_q1_my_groups_and_unread(me, group, second_group, left_group, unread_notifications):
    result = my_groups_with_unread(me)
    by_name = {g.name: unread for g, unread in result}

    assert set(by_name) == {"Math 101", "CS 210"}  # left_group excluded
    assert by_name["Math 101"] == 2  # 2 unread, the read one not counted
    assert by_name["CS 210"] == 1
    # global notification (group NULL) is not a group unread count
    assert sum(unread for _, unread in result) == 3


@pytest.mark.django_db
def test_q1_uses_frozen_indexes(me, group, unread_notifications):
    groups_qs = Group.objects.filter(
        memberships__user=me, memberships__status=MembershipStatus.ACTIVE
    )
    assert "memberships_user_active" in force_index_plan(groups_qs)

    unread_qs = Notification.objects.filter(
        user=me, read_at__isnull=True, group__isnull=False
    )
    assert "notifications_unread" in force_index_plan(unread_qs)


# ---------------------------------------------------------------------------
# Q2 — group tasks in a month
# ---------------------------------------------------------------------------

EXPECTED_IN_NOV = {
    "timed-spanning-start",
    "timed-spanning-end",
    "timed-no-end",
    "allday-range",
    "allday-single",
    "recurring-active",
}


@pytest.mark.django_db
def test_q2_month_overlap(month_tasks, group):
    from_dt, to_dt = month_bounds(2026, 11)
    ids = [r["id"] for r in group_tasks_in_month(group, from_dt, to_dt)]

    titles = set(Task.objects.filter(id__in=ids).values_list("title", flat=True))
    assert titles == EXPECTED_IN_NOV


@pytest.mark.django_db
def test_q2_excludes_deleted_personal_foreign(month_tasks, group):
    from_dt, to_dt = month_bounds(2026, 11)
    ids = [r["id"] for r in group_tasks_in_month(group, from_dt, to_dt)]

    titles = set(Task.objects.filter(id__in=ids).values_list("title", flat=True))
    # "timed-inside" is soft-deleted in the fixture and must not leak
    assert "timed-inside" not in titles
    assert "personal" not in titles
    assert "foreign-group" not in titles
    assert "allday-outside" not in titles
    assert "recurring-expired" not in titles


@pytest.mark.django_db
def test_q2_ordered_by_start_key(month_tasks, group):
    from_dt, to_dt = month_bounds(2026, 11)
    rows = list(group_tasks_in_month(group, from_dt, to_dt))
    keys = [r["start_key"] for r in rows]
    assert keys == sorted(keys)


@pytest.mark.django_db
def test_q2_uses_frozen_indexes(month_tasks, group):
    # rollback restores everything; owner_* indexes compete for start preds
    _drop_fk_indexes(
        "tasks", extra=("tasks_owner_start", "tasks_owner_sdate")
    )
    from_dt, to_dt = month_bounds(2026, 11)
    plan = force_index_plan(group_tasks_in_month(group, from_dt, to_dt))
    assert "tasks_group_start" in plan
    assert "tasks_group_sdate" in plan
    assert "tasks_group_recur" in plan


# ---------------------------------------------------------------------------
# Q3 — due soon
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_q3_due_soon_scoping(due_tasks, me):
    titles = set(
        tasks_due_soon(me, horizon=HORIZON, now=NOW).values_list("title", flat=True)
    )
    assert "due-soon" in titles
    assert titles == {"due-soon"}  # far/past/foreign/personal/offset excluded


@pytest.mark.django_db
def test_q3_uses_frozen_index(due_tasks, me):
    _drop_fk_indexes("tasks")  # rollback restores them
    plan = force_index_plan(tasks_due_soon(me, horizon=HORIZON, now=NOW))
    assert "tasks_group_deadline" in plan
    # the two-step shape: step 1 (my groups) is a separate indexed lookup
    memberships_qs = Membership.objects.filter(
        user=me, status=MembershipStatus.ACTIVE
    )
    assert "memberships_user_active" in force_index_plan(memberships_qs)


# ---------------------------------------------------------------------------
# Q4 — feed keyset pagination
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_q4_pagination_roundtrip(feed_posts, group):
    seen = []
    cursor = None
    while True:
        page, cursor = feed_page(group, limit=2, cursor=cursor)
        seen.extend(p.body for p in page)
        if cursor is None:
            break
    # 5 live posts, in newest-first order, no dupes, deleted+foreign excluded
    assert seen == [f"Announcement {i}" for i in range(5, 0, -1)]
    assert len(seen) == len(set(seen))


@pytest.mark.django_db
def test_q4_uses_frozen_index(feed_posts, group):
    _drop_fk_indexes("posts")  # rollback restores them
    qs = Post.objects.filter(group=group, deleted_at__isnull=True).order_by(
        "-created_at", "-id"
    )
    assert "posts_group_created_id" in force_index_plan(qs)


# ---------------------------------------------------------------------------
# Q5 — files search (trigram)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_q5_case_insensitive_search(search_files, me):
    titles = set(files_search(me, "RePoRt").values_list("filename", flat=True))
    assert titles == {"lab_report_final.pdf", "REPORT card.xlsx"}


@pytest.mark.django_db
def test_q5_excludes_deleted_pending_foreign(search_files, me):
    titles = set(files_search(me, "lab_report").values_list("filename", flat=True))
    # deleted + pending_upload + foreign-group files must never leak
    assert titles == {"lab_report_final.pdf"}


@pytest.mark.django_db
def test_q5_uses_trigram_index(search_files, me):
    # rollback restores everything; files_group_created competes for the join
    _drop_fk_indexes("files", extra=("files_group_created",))
    plan = force_index_plan(files_search(me, "report"))
    assert "files_filename_trgm" in plan


# ---------------------------------------------------------------------------
# Q6 — pending requests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_q6_pending_only_oldest_first(request_queue, group):
    titles = list(pending_requests(group).values_list("title", flat=True))
    assert titles == ["pending-old", "pending-new"]


@pytest.mark.django_db
def test_q6_uses_frozen_index(request_queue, group):
    qs = TaskRequest.objects.filter(group=group, status=TaskRequestStatus.PENDING)
    assert "task_requests_group_pending" in force_index_plan(qs)
