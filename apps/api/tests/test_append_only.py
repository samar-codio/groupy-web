"""Append-only log tests (PLAN §5.5, migration core/0003_append_only_logs):
activity_log / audit_log accept INSERT only. UPDATE and DELETE are blocked
twice over — REVOKE from PUBLIC plus a trigger backstop raising 0A000.
"""

import pytest
from django.db import DatabaseError, connection

from core.models import ActivityLog, AuditLog


@pytest.mark.django_db
def test_insert_allowed(group, me):
    ActivityLog.objects.create(group=group, actor=me, action="task_created")
    assert ActivityLog.objects.count() == 1


@pytest.mark.django_db
def test_update_blocked_by_trigger(activity_entry):
    activity_entry.action = "tampered"
    with pytest.raises(DatabaseError, match="append-only"):
        activity_entry.save(update_fields=["action"])


@pytest.mark.django_db
def test_delete_blocked_by_trigger(activity_entry):
    with pytest.raises(DatabaseError, match="append-only"):
        activity_entry.delete()


@pytest.mark.django_db
def test_audit_log_also_append_only(me):
    AuditLog.objects.create(user=me, event="login_ok")
    entry = AuditLog.objects.first()
    entry.event = "otp_fail"
    with pytest.raises(DatabaseError, match="append-only"):
        entry.save(update_fields=["event"])


@pytest.mark.django_db
def test_raw_sql_update_raises_0a000(activity_entry):
    """The SQLSTATE must be 0A000 (feature_not_supported) — that is the
    signal API layers can map to a 405, not a 500."""
    from django.db import connections

    raw = connections["default"].connection  # underlying psycopg connection
    try:
        with raw.cursor() as cur:
            with pytest.raises(Exception) as excinfo:
                cur.execute(
                    "UPDATE activity_log SET action = 'x' WHERE id = %s",
                    [activity_entry.id],
                )
        assert getattr(excinfo.value, "sqlstate", None) == "0A000"
    finally:
        raw.rollback()  # leave no aborted transaction for Django


@pytest.mark.django_db
def test_update_delete_revoked_from_public():
    """Defense in depth: even without the trigger, PUBLIC holds no UPDATE/
    DELETE grant on the append-only tables."""
    with connection.cursor() as cur:
        for table in ("activity_log", "audit_log"):
            cur.execute(
                "SELECT has_table_privilege('public', %s, 'UPDATE'),"
                " has_table_privilege('public', %s, 'DELETE')",
                [table, table],
            )
            upd, delete = cur.fetchone()
            assert upd is False, f"PUBLIC can UPDATE {table}"
            assert delete is False, f"PUBLIC can DELETE {table}"
