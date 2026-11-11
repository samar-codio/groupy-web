# ADR-001: PostgreSQL as the database

- **Status:** accepted (S1 implemented)
- **Decided:** S1 (data model phase), per PLAN §5 and frozen decision A5
- **Applies to:** every phase after S1

## Context

Groupy is a class-organization app whose core reads are group-scoped: a group's
calendar, feed, files, and pending requests. The frozen PLAN §5.4 schema leans
on PostgreSQL features that no other candidate offers together:

- **citext** for case-insensitive, unique email (`users.email`, `otp_challenges.email`)
- **pg_trgm + GIN** for `ILIKE '%query%'` file-name search
- **Partial indexes** (task calendars, unread notifications, active memberships)
- **Partial unique indexes** ("one pending request per (group, user)")
- **Composite primary keys** (Django 5.2 `CompositePrimaryKey` on `member_prefs`,
  `task_completions`)
- **CHECK constraints as the DB-side enforcement layer** (RULES.md §6: the DB is
  the security layer, the API is the friendly layer)
- **Append-only logs** via `REVOKE` + trigger backstop (PLAN §5.5)
- **Row-level security** planned in PLAN §6.5 for group-scoped reads
- Transactional outbox (`outbox`) for post-commit push/email (R16)

## Decision

PostgreSQL 16+ is the only database. The schema uses its features deliberately,
not as an afterthought.

Corollaries:

1. **No `django.contrib.auth`/`contenttypes`/`admin` in the schema.** Installing
   contrib.auth would drag contenttypes/perm/group tables into the frozen
   24-table schema. `AbstractBaseUser` works without the auth app; S4/S5 use our
   own `sessions` model and cookie handling.
2. **citext stays despite Django 5.2 deprecating `CITextField` (fields.E907).**
   The frozen schema says `citext UK` for email. We keep a local
   `core.fields.CITextField` that (a) restores `db_type = "citext"` — Django
   5.2's remnant emits plain `text` — and (b) disables the E907 system check on
   purpose. ICU collations are a valid future swap but would be a change request
   (RULES.md §1.2).
3. **`django.contrib.postgres` stays in `INSTALLED_APPS`.** It defines no
   models/tables; it registers the expression wrapper classes that make
   `GinIndex(OpClass(Lower("filename"), name="gin_trgm_ops"))` render valid SQL
   (without it Django emits a double-parenthesis syntax error).
4. **Extensions live in a hand-written migration** (`core/0001_extensions`),
   and the migrations that need them declare an explicit dependency on it
   (hand-added edges in `accounts/0001` for citext and `files/0001` for
   pg_trgm). The autodetector does not know about extensions.

## Deviations from the frozen DDL (recorded per RULES.md §1.2)

| Frozen | Reality | Why |
| --- | --- | --- |
| `CHECK (length(name) > 0)` written with Django's `__length` lookup | Same SQL via a re-registered `Length` transform in `core/fields.py` | Django 5.2 removed the built-in `length` lookup registration; the maintained `Length` transform is re-registered once, restoring idiomatic `Q(name__length__gt=0)` |
| `coalesce(start_at, start_date::timestamptz)` personal-calendar index | Two partial indexes `tasks_owner_start` (timed) / `tasks_owner_sdate` (all-day) | Postgres rejects the frozen expression: `date → timestamptz` is STABLE (session-TZ dependent), index expressions must be IMMUTABLE. The split mirrors the frozen group-calendar indexes and keeps all-day comparisons in date space (see ADR-002) |

## Consequences

- Single-vendor (Postgres) for the product's lifetime — accepted; every
  feature is chosen because Postgres is assumed (PLAN froze this).
- Migrations must be read and hand-edited (PLAN §5.6): the two hand-added
  dependency edges and the two recorded deviations are the precedent.
- Schema purity is a frozen contract: adding `django.contrib.auth` etc. later
  is a change request, not a refactor.
