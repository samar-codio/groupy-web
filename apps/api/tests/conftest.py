"""Shared fixtures for the S1 test suite (PLAN §5.6 acceptance tests).

Fixture convention: every fixture creates its data through the ORM so the
DB-side CHECKs/triggers/indexes are exercised for real — no save(force), no
raw SQL inserts in correctness tests.
"""

from datetime import datetime, timedelta, timezone

import pytest

from accounts.models import User
from core.models import ActivityLog
from files.models import File, FilePurpose, FileStatus
from groups.models import (
    Group,
    Membership,
    MembershipRole,
    MembershipStatus,
    Post,
)
from notifications.models import Notification, NotificationType
from tasks.models import Task, TaskRequest, TaskRequestStatus

UTC = timezone.utc
NOW = datetime(2026, 11, 11, 12, 0, 0, tzinfo=UTC)  # "today" for all time tests


@pytest.fixture
def me(db):
    return User.objects.create_user(email="me@example.test", name="Me")


@pytest.fixture
def other(db):
    return User.objects.create_user(email="other@example.test", name="Other")


@pytest.fixture
def outsider(db):
    """A user with NO membership anywhere — used to prove query scoping."""
    return User.objects.create_user(email="outsider@example.test", name="Outsider")


@pytest.fixture
def group(db, me):
    """My group (I am admin)."""
    g = Group.objects.create(
        owner=me, name="Math 101", join_code="ABCD23", tz="Asia/Karachi"
    )
    Membership.objects.create(
        group=g, user=me, role=MembershipRole.ADMIN, status=MembershipStatus.ACTIVE
    )
    return g


@pytest.fixture
def second_group(db, me):
    """Another of my groups (I am a plain member)."""
    g = Group.objects.create(
        owner=me, name="CS 210", join_code="EFGH45", tz="Asia/Karachi"
    )
    Membership.objects.create(
        group=g, user=me, role=MembershipRole.MEMBER, status=MembershipStatus.ACTIVE
    )
    return g


@pytest.fixture
def other_group(db, other):
    """A group I do NOT belong to."""
    g = Group.objects.create(
        owner=other, name="Physics 310", join_code="IJKL67", tz="Asia/Karachi"
    )
    Membership.objects.create(
        group=g, user=other, role=MembershipRole.ADMIN, status=MembershipStatus.ACTIVE
    )
    return g


@pytest.fixture
def left_group(db, me, other):
    """A group I LEFT — must never appear in my-groups queries (R10)."""
    g = Group.objects.create(
        owner=other, name="Bio 120", join_code="MNOP89", tz="Asia/Karachi"
    )
    Membership.objects.create(
        group=g, user=me, role=MembershipRole.MEMBER, status=MembershipStatus.LEFT
    )
    return g


@pytest.fixture
def make_task(me):
    counter = 0

    def _make(group=None, owner=None, title=None, all_day=False, **kwargs):
        nonlocal counter
        counter += 1
        Task.objects.create(
            group=group,
            owner=owner,
            all_day=all_day,
            title=title or f"Task {counter}",
            tz="Asia/Karachi",
            created_by=me,
            **kwargs,
        )

    return _make


@pytest.fixture
def month_tasks(group, other_group, make_task, outsider):
    """Calendar fixture for Q2 (month = Nov 2026)."""
    month = datetime(2026, 11, 1, tzinfo=UTC)
    # timed, inside the month
    make_task(
        group=group,
        title="timed-inside",
        start_at=month + timedelta(days=9, hours=9),
        end_at=month + timedelta(days=9, hours=10),
    )
    # timed, spans the month start (starts in Oct)
    make_task(
        group=group,
        title="timed-spanning-start",
        start_at=month - timedelta(days=2),
        end_at=month + timedelta(days=1),
    )
    # timed, spans the month end
    make_task(
        group=group,
        title="timed-spanning-end",
        start_at=month + timedelta(days=29),
        end_at=month + timedelta(days=32),
    )
    # timed, fully outside (December)
    make_task(
        group=group,
        title="timed-outside",
        start_at=month + timedelta(days=40),
        end_at=month + timedelta(days=41),
    )
    # timed, no end_at (still counts when it starts in the month)
    make_task(
        group=group,
        title="timed-no-end",
        start_at=month + timedelta(days=20, hours=8),
    )
    # all-day with an end date
    make_task(
        group=group,
        title="allday-range",
        all_day=True,
        start_date=month.date() + timedelta(days=15),
        end_date=month.date() + timedelta(days=16),
    )
    # all-day single date (end_date NULL)
    make_task(
        group=group,
        title="allday-single",
        all_day=True,
        start_date=month.date() + timedelta(days=21),
    )
    # all-day outside the month
    make_task(
        group=group,
        title="allday-outside",
        all_day=True,
        start_date=month.date() + timedelta(days=45),
    )
    # recurring, active
    make_task(
        group=group,
        title="recurring-active",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        recur_until=month + timedelta(days=60),
        start_at=month + timedelta(days=2, hours=9),
    )
    # recurring but expired before the month
    make_task(
        group=group,
        title="recurring-expired",
        rrule="FREQ=WEEKLY",
        recur_until=month - timedelta(days=10),
        start_at=month - timedelta(days=30, hours=9),
    )
    # soft-deleted (must never appear)
    Task.objects.filter(title="timed-inside").update(deleted_at=NOW)
    # personal task of mine (must never appear in a GROUP month query)
    make_task(
        owner=outsider,
        title="personal",
        start_at=month + timedelta(days=3),
        end_at=month + timedelta(days=3, hours=1),
    )
    # task in a group I am not in (must never appear)
    make_task(
        group=other_group,
        title="foreign-group",
        start_at=month + timedelta(days=4),
        end_at=month + timedelta(days=4, hours=1),
    )
    return month


@pytest.fixture
def due_tasks(group, other_group, make_task, me):
    """Deadline fixture for Q3."""
    at = NOW + timedelta(days=10)  # any valid timed start, irrelevant to Q3
    make_task(group=group, title="due-soon", start_at=at, deadline_at=NOW + timedelta(days=2))
    make_task(group=group, title="due-far", start_at=at, deadline_at=NOW + timedelta(days=30))
    make_task(group=group, title="due-past", start_at=at, deadline_at=NOW - timedelta(days=1))
    make_task(
        group=other_group,
        title="foreign-due",
        start_at=at,
        deadline_at=NOW + timedelta(days=1),
    )
    make_task(owner=me, title="personal-due", start_at=at, deadline_at=NOW + timedelta(days=1))
    # recurring-style relative deadline (no absolute deadline_at → excluded)
    make_task(group=group, title="offset-only", start_at=at, deadline_offset=timedelta(days=1))


@pytest.fixture
def feed_posts(group, other_group, me):
    """Feed fixture for Q4: 5 live posts, 1 deleted, 1 in a foreign group."""
    for i in range(1, 6):
        Post.objects.create(group=group, author=me, body=f"Announcement {i}")
    Post.objects.create(group=group, author=me, body="Deleted post", deleted_at=NOW)
    Post.objects.create(group=other_group, author=me, body="Foreign post")


@pytest.fixture
def search_files(group, other_group, me):
    """File-search fixture for Q5."""
    File.objects.create(
        group=group,
        uploaded_by=me,
        purpose=FilePurpose.GROUP_FILE,
        storage_key="groups/x/00000000-0000-7000-8000-000000000001",
        filename="lab_report_final.pdf",
        mime_declared="application/pdf",
        size_bytes=100,
        status=FileStatus.READY,
    )
    File.objects.create(
        group=group,
        uploaded_by=me,
        purpose=FilePurpose.GROUP_FILE,
        storage_key="groups/x/00000000-0000-7000-8000-000000000002",
        filename="REPORT card.xlsx",
        mime_declared="application/vnd.ms-excel",
        size_bytes=200,
        status=FileStatus.READY,
    )
    File.objects.create(
        group=group,
        uploaded_by=me,
        purpose=FilePurpose.GROUP_FILE,
        storage_key="groups/x/00000000-0000-7000-8000-000000000003",
        filename="lab_report_old.pdf",
        mime_declared="application/pdf",
        size_bytes=300,
        status=FileStatus.READY,
        deleted_at=NOW,
    )
    File.objects.create(
        group=group,
        uploaded_by=me,
        purpose=FilePurpose.GROUP_FILE,
        storage_key="groups/x/00000000-0000-7000-8000-000000000004",
        filename="lab_report_new.pdf",
        mime_declared="application/pdf",
        size_bytes=400,
        status=FileStatus.PENDING_UPLOAD,
    )
    File.objects.create(
        group=other_group,
        uploaded_by=me,
        purpose=FilePurpose.GROUP_FILE,
        storage_key="groups/x/00000000-0000-7000-8000-000000000005",
        filename="lab_report_physics.pdf",
        mime_declared="application/pdf",
        size_bytes=500,
        status=FileStatus.READY,
    )


@pytest.fixture
def request_queue(group, other_group, me, other):
    """Task-request fixture for Q6."""
    TaskRequest.objects.create(
        group=group,
        requested_by=other,
        title="pending-old",
        start_at=NOW + timedelta(days=1),
        tz="Asia/Karachi",
        status=TaskRequestStatus.PENDING,
    )
    TaskRequest.objects.create(
        group=group,
        requested_by=other,
        title="pending-new",
        start_at=NOW + timedelta(days=2),
        tz="Asia/Karachi",
        status=TaskRequestStatus.PENDING,
    )
    TaskRequest.objects.create(
        group=group,
        requested_by=other,
        title="approved",
        start_at=NOW + timedelta(days=3),
        tz="Asia/Karachi",
        status=TaskRequestStatus.APPROVED,
    )
    TaskRequest.objects.create(
        group=group,
        requested_by=other,
        title="declined",
        start_at=NOW + timedelta(days=4),
        tz="Asia/Karachi",
        status=TaskRequestStatus.DECLINED,
        decline_reason="duplicate",
    )
    TaskRequest.objects.create(
        group=other_group,
        requested_by=other,
        title="foreign-pending",
        start_at=NOW + timedelta(days=5),
        tz="Asia/Karachi",
        status=TaskRequestStatus.PENDING,
    )


@pytest.fixture
def unread_notifications(group, second_group, me, other):
    """Notification fixture for Q1: 2 unread + 1 read in `group`, 1 unread in
    `second_group`, 1 unread notification for `me` with group=NULL."""
    Notification.objects.create(
        user=me, group=group, type=NotificationType.TASK, data={"title": "T1"}
    )
    Notification.objects.create(
        user=me, group=group, type=NotificationType.ANNOUNCEMENT, data={"title": "A1"}
    )
    Notification.objects.create(
        user=me,
        group=group,
        type=NotificationType.MESSAGE,
        data={"title": "M1"},
        read_at=NOW,
    )
    Notification.objects.create(
        user=me, group=second_group, type=NotificationType.TASK, data={"title": "T2"}
    )
    Notification.objects.create(
        user=me, group=None, type=NotificationType.TASK, data={"title": "global"}
    )


@pytest.fixture
def activity_entry(group, me):
    entry = ActivityLog.objects.create(
        group=group, actor=me, action="task_created", metadata={}
    )
    return entry
