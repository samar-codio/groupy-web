# ADR-002: Identifiers (UUIDv7) and time semantics

- **Status:** accepted (S1 implemented)
- **Decided:** S1 (data model phase), per PLAN §5.1 time rules and PLAN §7.3 idempotency
- **Applies to:** every phase after S1

## Context

Two cross-cutting schema decisions shape every query:

1. **Primary keys.** Plain `bigserial` leaks size/order, breaks idempotent
   offline writes, and makes multi-writer id generation a coordination problem.
   Random UUIDv4 fixes those but destroys B-tree insert locality and keyset
   pagination (`created_at, id` ordering works only when ids are time-sortable).
2. **Time.** A class app must show "09:00 weekly" correctly across DST,
   all-day events as the same date for everyone, and deadlines in the group's
   local 23:59.

## Decision

**IDs: UUIDv7 (RFC 9562), generated in the app layer.**

Layout: 48-bit unix-ms prefix + 12-bit monotonic counter (rand_a) + 62-bit
random (rand_b); version=7, RFC 4122 variant. Implementation:
`core.fields.uuid7()`, used as the default of `UUIDv7Field` (every PK).

- **Time-sortable** → B-tree-friendly inserts, and keyset pagination on
  `(created_at, id)` works like a sequence without a sequence.
- **Monotonic per process**: the counter increments within a millisecond;
  on overflow (>4096 ids in one ms) the generator spins to the next ms — bulk
  inserts keep strict ordering (verified: 30k ids monotonic).
- **App-generated, not `gen_random_uuid()`**: the same id can be reused for
  idempotent offline writes (PLAN §7.3) and client-side retries.
- **SECURITY**: UUIDs are NOT secrets — guessing resistance is a bonus,
  authorization is still mandatory (RULES.md §4.27). IDs never appear in
  activity-log metadata as a substitute for PII (RULES.md §3.1.14).

**Time (PLAN §5.4 rules, frozen):**

| Aspect | Storage | Rationale |
| --- | --- | --- |
| Timed events | `timestamptz` (`start_at`/`end_at`), UTC in DB | Unambiguous instants; DST-safe arithmetic |
| All-day events | `date` (`start_date`/`end_date`) | "That date for everyone" — no zone conversion, ever |
| Recurring events | `rrule` + authoring `tz` (IANA) + `recur_until` | "09:00 weekly" authored in local time survives DST |
| Deadlines | `timestamptz`; default 23:59 group tz (app-level, S6) | Predictable end-of-day semantics |
| Sessions/OTP expiry | `timestamptz` with `expires_at` | Comparison-only, no wall-clock parsing |

`django` is configured `TIME_ZONE="UTC"`, `USE_TZ=True`; all columns are
timestamptz; the codebase bans naive datetimes.

## Deviations from the frozen DDL (recorded per RULES.md §1.2)

**Personal-calendar index.** The frozen DDL freezes

```sql
create index tasks_owner_start on tasks (owner_id, coalesce(start_at, start_date::timestamptz)) where deleted_at is null;
```

Postgres rejects this outright: casting `date → timestamptz` depends on the
session `TimeZone` (STABLE, not IMMUTABLE), and index expressions must be
IMMUTABLE. The frozen expression is therefore physically unimplementable.

Replacement: two partial indexes, mirroring the frozen **group** calendar
indexes:

- `tasks_owner_start (owner_id, start_at) WHERE deleted_at IS NULL AND rrule IS NULL AND NOT all_day`
- `tasks_owner_sdate (owner_id, start_date) WHERE deleted_at IS NULL AND rrule IS NULL AND all_day`

This is semantically *better* than the frozen coalesce: all-day rows stay in
date space (an all-day task must not shift days when the viewer's zone differs),
and the two query branches are exactly the PLAN's own group-calendar pattern
("calendar query shape", PLAN §5.4).

## Consequences

- Every FK target is a UUIDv7; join/keyset code must never rely on insertion
  order alone — `(created_at, id)` is the frozen pagination pair.
- UUIDv7 ids are 16 bytes: slightly larger indexes than bigserial; accepted for
  the offline-idempotency and multi-writer benefits.
- The counter makes ids within one process strictly monotonic, but two
  processes can interleave — "total order" must never be assumed across
  servers.
- `date` vs `timestamptz` is a hard boundary: queries mixing them without an
  explicit zone conversion are bugs by definition (frozen in the two-index
  split above).
