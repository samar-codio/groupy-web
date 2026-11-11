"""Constraint tests (PLAN §5.6): the DB — not the app — rejects invalid rows.

Every case here must fail with the DB-side constraint name in the error, proving
the frozen CHECKs/UNIQUEs are real and named as frozen (RULES.md §6: the DB is
the security layer, the API is the friendly layer).
"""

from datetime import timedelta

import pytest
from django.db import IntegrityError

from accounts.models import OtpChallenge, OtpPurpose, User
from core.models import AuditLog, Outbox
from files.models import File, FilePurpose
from groups.models import (
    Group,
    JoinRequest,
    MemberPref,
    Membership,
    Post,
)
from notifications.models import Notification
from tasks.models import Task, TaskRequest


def _group(owner, **kw):
    defaults = dict(owner=owner, name="G", join_code="ABCD23")
    defaults.update(kw)
    return Group.objects.create(**defaults)


def _timed_task(group, me, **kw):
    defaults = dict(
        group=group,
        title="T",
        tz="Asia/Karachi",
        created_by=me,
        start_at=None,
    )
    defaults.update(kw)
    return Task.objects.create(**defaults)


@pytest.mark.django_db
def test_user_name_cannot_be_empty(me):
    with pytest.raises(IntegrityError, match="users_name_not_empty"):
        User.objects.create(email="x@example.test", name="")


@pytest.mark.django_db
def test_email_unique_is_case_insensitive(me):
    User.objects.create(email="dup@example.test", name="Dup")
    with pytest.raises(IntegrityError):
        User.objects.create(email="DUP@example.test", name="Dup 2")


@pytest.mark.django_db
def test_group_name_max_120(me):
    with pytest.raises(IntegrityError, match="groups_name_length"):
        _group(me, name="x" * 121)


@pytest.mark.django_db
def test_group_subtitle_max_200(me):
    with pytest.raises(IntegrityError, match="groups_subtitle_length"):
        _group(me, subtitle="x" * 201)


@pytest.mark.django_db
def test_join_code_must_be_6_chars(me):
    with pytest.raises(IntegrityError, match="groups_join_code_length"):
        _group(me, join_code="ABC")


@pytest.mark.django_db
def test_join_mode_enum(me):
    with pytest.raises(IntegrityError, match="groups_join_mode_valid"):
        _group(me, join_mode="weird")


@pytest.mark.django_db
def test_membership_pair_unique(group, other):
    Membership.objects.create(group=group, user=other)
    with pytest.raises(IntegrityError, match="memberships_group_user_uniq"):
        Membership.objects.create(group=group, user=other)


@pytest.mark.django_db
def test_member_pref_colour_palette_only(group, other):
    with pytest.raises(IntegrityError, match="member_prefs_colour_key_format"):
        MemberPref.objects.create(group=group, user=other, colour_key="red")


@pytest.mark.django_db
def test_one_pending_join_request_per_pair(group, other):
    JoinRequest.objects.create(group=group, user=other)
    with pytest.raises(IntegrityError, match="join_requests_pending_uniq"):
        JoinRequest.objects.create(group=group, user=other)


@pytest.mark.django_db
def test_post_body_nonempty(group, me):
    with pytest.raises(IntegrityError, match="posts_body_length"):
        Post.objects.create(group=group, author=me, body="")


@pytest.mark.django_db
def test_post_body_max_4000(group, me):
    with pytest.raises(IntegrityError, match="posts_body_length"):
        Post.objects.create(group=group, author=me, body="x" * 4001)


@pytest.mark.django_db
def test_task_group_xor_owner(group, me):
    with pytest.raises(IntegrityError, match="tasks_group_xor_owner"):
        _timed_task(group, me, owner=me)


@pytest.mark.django_db
def test_task_timed_must_not_carry_dates(group, me):
    from datetime import date

    with pytest.raises(IntegrityError, match="tasks_timing_fields_match"):
        Task.objects.create(
            group=group,
            title="T",
            tz="Asia/Karachi",
            created_by=me,
            start_at=None,
            start_date=date(2026, 11, 1),
        )


@pytest.mark.django_db
def test_task_end_after_start(group, me):
    from datetime import datetime, timezone

    t0 = datetime(2026, 11, 1, 10, tzinfo=timezone.utc)
    t1 = datetime(2026, 11, 1, 9, tzinfo=timezone.utc)
    with pytest.raises(IntegrityError, match="tasks_end_after_start"):
        _timed_task(group, me, start_at=t0, end_at=t1)


@pytest.mark.django_db
def test_task_deadline_single_form(group, me):
    from datetime import datetime, timezone

    with pytest.raises(IntegrityError, match="tasks_deadline_single"):
        _timed_task(
            group,
            me,
            start_at=datetime(2026, 11, 1, 10, tzinfo=timezone.utc),
            deadline_at=datetime(2026, 12, 1, tzinfo=timezone.utc),
            deadline_offset=timedelta(days=1),
        )


@pytest.mark.django_db
def test_task_title_length(group, me):
    from datetime import datetime, timezone

    with pytest.raises(IntegrityError, match="tasks_title_length"):
        _timed_task(
            group, me, title="x" * 121, start_at=datetime(2026, 11, 1, 10, tzinfo=timezone.utc)
        )


@pytest.mark.django_db
def test_task_request_decline_reason_max_200(group, me, other):
    from datetime import datetime, timezone

    with pytest.raises(IntegrityError, match="task_requests_decline_reason_length"):
        TaskRequest.objects.create(
            group=group,
            requested_by=other,
            title="R",
            tz="Asia/Karachi",
            start_at=datetime(2026, 11, 1, 10, tzinfo=timezone.utc),
            status="declined",
            decline_reason="x" * 201,
        )


@pytest.mark.django_db
def test_notification_type_enum(group, me):
    with pytest.raises(IntegrityError, match="notifications_type_valid"):
        Notification.objects.create(user=me, group=group, type="spam")


@pytest.mark.django_db
def test_audit_event_enum(me):
    with pytest.raises(IntegrityError, match="audit_log_event_valid"):
        AuditLog.objects.create(user=me, event="banana")


@pytest.mark.django_db
def test_outbox_dedupe_uniq():
    Outbox.objects.create(topic="push", dedupe_key="k")
    with pytest.raises(IntegrityError, match="outbox_topic_dedupe_uniq"):
        Outbox.objects.create(topic="push", dedupe_key="k")


@pytest.mark.django_db
def test_file_size_nonnegative(group, me):
    with pytest.raises(IntegrityError, match="files_size_nonnegative"):
        File.objects.create(
            group=group,
            uploaded_by=me,
            purpose=FilePurpose.GROUP_FILE,
            storage_key="groups/x/bad",
            filename="f.txt",
            mime_declared="text/plain",
            size_bytes=-1,
        )


@pytest.mark.django_db
def test_otp_attempts_capped(me):
    from datetime import datetime, timezone

    with pytest.raises(IntegrityError, match="otp_attempts_within_max"):
        OtpChallenge.objects.create(
            email="me@example.test",
            purpose=OtpPurpose.LOGIN,
            code_hmac="deadbeef",
            expires_at=datetime(2026, 11, 11, 12, 10, tzinfo=timezone.utc),
            attempts=6,
            max_attempts=5,
        )
