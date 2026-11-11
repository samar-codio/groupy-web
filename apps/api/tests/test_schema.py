"""Schema acceptance tests (PLAN §5.6): the migrated database must match the
frozen 24-table contract — extensions, column types, and index set included.

A schema drift here is a change request, not a test fix (RULES.md §1.2).
"""

import pytest
from django.db import connection

FROZEN_TABLES = {
    # accounts
    "users",
    "otp_challenges",
    "sessions",
    "feedback",
    "data_export_requests",
    # groups
    "institutions",
    "groups",
    "memberships",
    "member_prefs",
    "join_requests",
    "posts",
    # tasks
    "tasks",
    "task_requests",
    "task_exceptions",
    "task_completions",
    # notifications
    "notifications",
    "notification_prefs",
    "push_subscriptions",
    # files
    "files",
    "folders",
    # core
    "activity_log",
    "audit_log",
    "idempotency_keys",
    "outbox",
}

FROZEN_EXTENSIONS = {"citext", "pg_trgm", "plpgsql"}

# Index names the six core queries rely on (PLAN §5.4 key DDL).
FROZEN_QUERY_INDEXES = {
    "memberships_user_active",
    "notifications_unread",
    "tasks_group_start",
    "tasks_group_sdate",
    "tasks_group_recur",
    "tasks_group_deadline",
    "posts_group_created_id",
    "files_filename_trgm",
    "task_requests_group_pending",
}


def _tables() -> set[str]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        return {row[0] for row in cur.fetchall()}


def _indexes() -> set[str]:
    with connection.cursor() as cur:
        cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
        return {row[0] for row in cur.fetchall()}


@pytest.mark.django_db
def test_frozen_tables_only():
    tables = _tables()
    missing = FROZEN_TABLES - tables
    extra = tables - FROZEN_TABLES - {"django_migrations"}
    assert not missing, f"frozen tables missing: {missing}"
    assert not extra, f"non-frozen tables present: {extra}"


@pytest.mark.django_db
def test_extensions_created():
    with connection.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension")
        installed = {row[0] for row in cur.fetchall()}
    assert FROZEN_EXTENSIONS <= installed


@pytest.mark.django_db
def test_users_email_is_citext():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT udt_name FROM information_schema.columns"
            " WHERE table_name = 'users' AND column_name = 'email'"
        )
        assert cur.fetchone()[0] == "citext"


@pytest.mark.django_db
def test_trigram_index_is_gin_on_lower_filename():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT indexdef FROM pg_indexes"
            " WHERE indexname = 'files_filename_trgm'"
        )
        row = cur.fetchone()
    assert row is not None, "files_filename_trgm missing"
    assert "gin" in row[0].lower()
    assert "gin_trgm_ops" in row[0]


@pytest.mark.django_db
def test_core_query_indexes_exist():
    missing = FROZEN_QUERY_INDEXES - _indexes()
    assert not missing, f"frozen query indexes missing: {missing}"
