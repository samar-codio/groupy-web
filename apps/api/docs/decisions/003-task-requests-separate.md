# ADR-003: Task requests live in a separate table

- **Status:** accepted (S1 implemented)
- **Decided:** S1 (data model phase), per PLAN §8.2 ("Request task" flow)
- **Applies to:** S2+ API design, notifications, group moderation UI

## Context

A member can propose a task ("Request task", PLAN §8.2). Two designs were on
the table:

- **A. One table:** `tasks.status ∈ {pending, approved, declined, …}`. Requests
  are just tasks in a special state.
- **B. Two tables:** `task_requests` (proposals) and `tasks` (approved, real
  tasks). Approval copies the row into `tasks` in one transaction; the request
  row stays as history (R7).

## Decision

**B. Separate `task_requests` table.**

The frozen schema gives `task_requests` its own timing columns (`all_day`,
`start_date`/`end_date`, `start_at`/`end_at`, `tz`, `rrule`, `deadline_at`,
`colour_key`), its own `decline_reason`, `decided_by`/`decided_at`, and a
`resulting_task` FK back to the approved task.

### Why

1. **Pending data can never leak into task queries.** Every calendar, due-soon,
   and recurrence query on `tasks` is *structurally* safe — there is no
   `WHERE status = 'approved'` clause to forget. This is the same
   "make the wrong thing impossible" principle as RULES.md §6.1 (deny by
   default).
2. **Different invariants.** Decided requests are immutable (R8); tasks get
   edited, versioned, soft-deleted. One table would need status-dependent
   constraint logic (e.g. "editable only while pending") — exactly the kind of
   conditional CHECK that rots.
3. **Different hot paths.** The admin moderation queue reads only pending
   requests (`task_requests_group_pending` partial index); calendars read only
   `tasks`. Separate tables keep both index sets small.
4. **Decline data stays local.** `decline_reason` (≤200 chars, R9) exists on
   the request; copying it onto a task would pollute the task model.

### Trade-offs (accepted)

- **Duplicated timing columns.** Mitigated by sharing one module-level
  `_TIMING_FIELDS` CHECK definition between `Task` and `TaskRequest`
  (`apps/api/tasks/models.py`), so the frozen "timing fields match" invariant
  cannot drift between the two.
- **A join to walk request → task.** One column: `resulting_task` FK
  (`SET NULL`). Nothing else is needed; the request row is the history (R7).

## Consequences

- S2's "create task" service must implement approval as a single transaction:
  insert `tasks` row + mark request `approved`/`decided_by`/`decided_at` +
  `resulting_task` + activity_log + notification + outbox row (R16).
- Any future "reject with reason" UI reads/writes `task_requests` only.
- Schema reviewers: adding a `status` column to `tasks` for request-like
  states is a red flag (RULES.md §8) — requests belong in `task_requests`.
