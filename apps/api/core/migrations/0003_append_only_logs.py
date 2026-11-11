"""Append-only enforcement for the log tables (PLAN §5.5 / §6.5).

Two layers, exactly as the PLAN freezes:
1. Privilege revocation — REVOKE UPDATE/DELETE so the app role cannot modify
   rows once inserted. PUBLIC carries the default table grants, so revoking
   from PUBLIC strips them from every non-owner role (infra creates the app
   role as a plain non-owner role). The table owner (migration role) keeps
   rights for ops/purge jobs.
2. Trigger backstop — even a table owner's UPDATE/DELETE raises an exception.
   Purge after 12 months (PLAN §5.5) is therefore done by an ops job that
   drops/recreates partitions or TRUNCATEs under the owner role with the
   trigger temporarily disabled — never by the app.

Hand-written migration (PLAN §5.6: read and hand-edit each migration).
"""

from django.db import migrations


FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION groupy_log_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'table % is append-only (PLAN 5.5): UPDATE and DELETE are forbidden',
        TG_TABLE_NAME
        USING ERRCODE = '0A000';  -- feature_not_supported: maps cleanly, not a 5xx
END;
$$;
"""

TRIGGER_UP_SQL = """
CREATE TRIGGER activity_log_append_only
BEFORE UPDATE OR DELETE ON activity_log
FOR EACH ROW EXECUTE FUNCTION groupy_log_immutable();
"""

TRIGGER_AU_SQL = """
CREATE TRIGGER audit_log_append_only
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION groupy_log_immutable();
"""

REVOKE_SQL = """
REVOKE UPDATE, DELETE ON activity_log, audit_log FROM PUBLIC;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(
            FUNCTION_SQL,
            reverse_sql="DROP FUNCTION IF EXISTS groupy_log_immutable()",
        ),
        migrations.RunSQL(
            TRIGGER_UP_SQL,
            reverse_sql="DROP TRIGGER IF EXISTS activity_log_append_only ON activity_log",
        ),
        migrations.RunSQL(
            TRIGGER_AU_SQL,
            reverse_sql="DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log",
        ),
        migrations.RunSQL(
            REVOKE_SQL,
            reverse_sql="GRANT UPDATE, DELETE ON activity_log, audit_log TO PUBLIC",
        ),
    ]
