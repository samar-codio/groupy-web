"""Hand-written migration (PLAN §5.6: read and hand-edit each migration).

Creates the Postgres extensions the schema depends on:
- citext  -> case-insensitive, unique email (PLAN §5.1)
- pg_trgm -> trigram GIN index for file-name search (PLAN §5.4)

CREATE EXTENSION runs in its own transaction (not part of a multi-statement
tx), so each gets its own RunSQL. IF NOT EXISTS keeps it idempotent.
"""

from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies: list = []

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS citext",
            reverse_sql="DROP EXTENSION IF EXISTS citext",
        ),
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm",
        ),
    ]
