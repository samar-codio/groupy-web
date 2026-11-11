"""Tasks module (PLAN §5.4 + key DDL): tasks, task_requests, task_exceptions,
task_completions.

Why a separate task_requests table (ADR-003): pending request data can never
leak into task queries — there is no `WHERE status='approved'` to forget.

Time rules (PLAN §5.4): UTC timestamptz in DB; timed events carry start_at/
end_at, all-day events carry start_date/end_date (date); recurring events are
authored in their LOCAL time + IANA tz so "09:00 weekly" survives DST.
Completion is per-user AND per-occurrence (task_completions PK), not a
done_at on the task.
"""

from django.db import models
from django.db.models import CheckConstraint, CompositePrimaryKey, F, Q

from core.fields import UUIDv7Field


class TaskRequestStatus(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class TaskExceptionKind(models.TextChoices):
    SKIP = "skip"
    OVERRIDE = "override"

_TIMING_FIELDS = {
    # (all_day, start_date non-null, start_at null, end_at null)
    # or (not all_day, start_at non-null, start_date null, end_date null)
    "all_day_consistency": Q(
        all_day=True, start_date__isnull=False, start_at__isnull=True, end_at__isnull=True
    )
    | Q(
        all_day=False, start_at__isnull=False, start_date__isnull=True, end_date__isnull=True
    )
}

_TITLE_CHECK = Q(title__length__gte=1) & Q(title__length__lte=120)
_DETAILS_CHECK = Q(details__isnull=True) | Q(details__length__lte=4000)
_COLOUR_CHECK = Q(colour_key__isnull=True) | Q(colour_key__regex=r"^c[1-8]$")


class Task(models.Model):
    """One task: group task (group_id) XOR personal task (owner_id) — never both.

    Soft-deleted (deleted_at); partial indexes ignore deleted rows so hot
    paths stay small (PLAN key DDL)."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, null=True, related_name="tasks"
    )
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, related_name="personal_tasks"
    )
    title = models.TextField()
    details = models.TextField(null=True)
    colour_key = models.TextField(null=True)  # palette key c1..c8, never raw CSS
    all_day = models.BooleanField(default=False)
    start_date = models.DateField(null=True)  # all-day
    end_date = models.DateField(null=True)  # all-day
    start_at = models.DateTimeField(null=True)  # timed
    end_at = models.DateTimeField(null=True)  # timed
    tz = models.TextField()  # IANA zone of authoring (R12)
    deadline_at = models.DateTimeField(null=True)  # null = "no deadline"
    deadline_offset = models.DurationField(null=True)  # recurring: relative offset
    rrule = models.TextField(null=True)  # RFC 5545 RRULE (no DTSTART)
    recur_until = models.DateTimeField(null=True)  # derived from rrule
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="+"
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    source_request = models.ForeignKey(
        "TaskRequest", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    version = models.PositiveIntegerField(default=1)  # optimistic concurrency
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "tasks"
        constraints = [
            CheckConstraint(check=Q(group__isnull=True) ^ Q(owner__isnull=True),
                            name="tasks_group_xor_owner"),
            CheckConstraint(check=_TIMING_FIELDS["all_day_consistency"],
                            name="tasks_timing_fields_match"),
            CheckConstraint(
                check=Q(end_at__isnull=True) | Q(end_at__gte=F("start_at")),
                name="tasks_end_after_start",
            ),
            CheckConstraint(
                check=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="tasks_end_date_after_start",
            ),
            CheckConstraint(
                check=Q(deadline_at__isnull=True) | Q(deadline_offset__isnull=True),
                name="tasks_deadline_single",
            ),
            CheckConstraint(check=_TITLE_CHECK, name="tasks_title_length"),
            CheckConstraint(check=_DETAILS_CHECK, name="tasks_details_length"),
            CheckConstraint(check=_COLOUR_CHECK, name="tasks_colour_key_format"),
        ]
        indexes = [
            # Calendar range + due-soon (partial indexes keep them small).
            models.Index(
                fields=["group", "start_at"],
                condition=Q(deleted_at__isnull=True, rrule__isnull=True, all_day=False),
                name="tasks_group_start",
            ),
            models.Index(
                fields=["group", "start_date"],
                condition=Q(deleted_at__isnull=True, rrule__isnull=True, all_day=True),
                name="tasks_group_sdate",
            ),
            models.Index(
                fields=["group"],
                condition=Q(deleted_at__isnull=True, rrule__isnull=False),
                name="tasks_group_recur",
            ),
            models.Index(
                fields=["group", "deadline_at"],
                condition=Q(deleted_at__isnull=True, deadline_at__isnull=False),
                name="tasks_group_deadline",
            ),
            # Personal-task calendar: same timed / all-day split as the group
            # indexes above. DEVIATION from frozen DDL (PLAN §5.4) recorded in
            # ADR-002: the frozen `coalesce(start_at, start_date::timestamptz)`
            # index is rejected by Postgres (date->timestamptz is STABLE, index
            # expressions must be IMMUTABLE). Two partial indexes preserve the
            # intent AND keep all-day comparisons in date space.
            models.Index(
                "owner",
                "start_at",
                condition=Q(deleted_at__isnull=True, rrule__isnull=True, all_day=False),
                name="tasks_owner_start",
            ),
            models.Index(
                "owner",
                "start_date",
                condition=Q(deleted_at__isnull=True, rrule__isnull=True, all_day=True),
                name="tasks_owner_sdate",
            ),
        ]


class TaskRequest(models.Model):
    """A member's "Request task" proposal (PLAN §8.2). Decided requests are
    immutable (R8); approval copies the row into `tasks` in ONE transaction."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, related_name="task_requests"
    )
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="task_requests"
    )
    title = models.TextField()
    details = models.TextField(null=True)
    all_day = models.BooleanField(default=False)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    start_at = models.DateTimeField(null=True)
    end_at = models.DateTimeField(null=True)
    tz = models.TextField()
    rrule = models.TextField(null=True)
    deadline_at = models.DateTimeField(null=True)
    colour_key = models.TextField(null=True)
    status = models.TextField(choices=TaskRequestStatus.choices, default=TaskRequestStatus.PENDING)
    decided_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True)
    decline_reason = models.TextField(null=True)  # R9: ≤ 200 chars
    resulting_task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "task_requests"
        constraints = [
            CheckConstraint(check=Q(status__in=TaskRequestStatus.values), name="task_requests_status_valid"),
            CheckConstraint(check=_TIMING_FIELDS["all_day_consistency"],
                            name="task_requests_timing_fields_match"),
            CheckConstraint(
                check=Q(end_at__isnull=True) | Q(end_at__gte=F("start_at")),
                name="task_requests_end_after_start",
            ),
            CheckConstraint(
                check=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="task_requests_end_date_after_start",
            ),
            CheckConstraint(check=_TITLE_CHECK, name="task_requests_title_length"),
            CheckConstraint(check=_DETAILS_CHECK, name="task_requests_details_length"),
            CheckConstraint(check=_COLOUR_CHECK, name="task_requests_colour_key_format"),
            CheckConstraint(
                check=Q(decline_reason__isnull=True) | Q(decline_reason__length__lte=200),
                name="task_requests_decline_reason_length",
            ),
        ]
        indexes = [
            models.Index(
                fields=["group"],
                condition=Q(status=TaskRequestStatus.PENDING),
                name="task_requests_group_pending",
            ),
            models.Index(
                fields=["requested_by", "status"], name="task_requests_user_status"
            ),
        ]


class TaskException(models.Model):
    """"Edit this occurrence only" for recurring tasks (v1.1, table frozen)."""

    id = UUIDv7Field(primary_key=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="exceptions")
    occurrence_date = models.DateField()
    kind = models.TextField(choices=TaskExceptionKind.choices)
    override_fields = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "task_exceptions"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "occurrence_date"], name="task_exceptions_task_date_uniq"
            ),
            CheckConstraint(check=Q(kind__in=TaskExceptionKind.values), name="task_exceptions_kind_valid"),
        ]


class TaskCompletion(models.Model):
    """"Done" is per user AND per occurrence (PLAN §13.9) — the PK enforces it."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="completions")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="task_completions"
    )
    occurrence_date = models.DateField()
    done_at = models.DateTimeField(auto_now_add=True)

    pk = CompositePrimaryKey("task", "user", "occurrence_date")

    class Meta:
        db_table = "task_completions"
