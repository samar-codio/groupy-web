# Groupy — RULES.md

> The single source of truth for **every rule** this project follows. Applies to the human AND the AI. Sources: PLAN.md §0 (AI rules 1–14), PLAN.md §10 (security), PLAN.md §15 (review checklist), SECTIONS.md §0 (freeze workflow). If a rule here conflicts with a newer, explicit user decision, the user decision wins and this file gets updated.
> ****Read before every coding session. A rule violation is a bug, even if tests pass.**

---

## 1. Phase workflow (how we build — the most important rule)

1. **Sections are the unit of work.** Work strictly in order S0 → S1 → … from `context/SECTIONS.md`. One section at a time: READ → NOTE → CODE → ATTACK → FREEZE.
2. **Each phase is individual; earlier phases are permanently OK.** Every section ends with a **Frozen list**. Once frozen:
   - Later sections may **consume** frozen interfaces (call them, import them, build on them).
   - Later sections may **never silently modify** frozen items — no renamed columns, no changed signatures, no re-decided semantics.
   - If a change to a frozen item is needed → stop and write a **formal change request** (a new ADR in `docs/decisions/`), approved by the user, before touching it.
3. **Additive-only.** A new section = new files + new tests. Schema changes beyond S1 happen only via expand/contract migrations with a change request.
4. **All prior tests run forever.** Every previous section's tests stay in CI. If a new section breaks an old one, CI goes red at the moment of breakage — that is the safety net.
5. **Never code ahead of understanding.** The user reads and notes first; the AI implements exactly ONE section and nothing from a later section.

## 2. Architecture & layering rules

 6. **Layering:** `route (HTTP only) → service (business rules, transactions) → repository (SQL only)`. No SQL in routes. No business rules in the front end.
 7. **Backend is Django + DRF + Postgres** (PLAN.md A5 — locked decision). TS snippets in PLAN.md translate per the table in SECTIONS.md §0. Front end stays React/TS.
 8. **Modular monolith.** Apps: `core, accounts, groups, tasks, notifications, files`. Clear boundaries; no microservices.
 9. **Deny by default.** Every read/write of group data goes through the policy module `can(actor, action, resource)`. Non-members get **404, never 403** (don't leak existence).
10. **Validate every input** with strict serializers/Pydantic (equivalent of Zod `.strict()` — unknown fields rejected). Return explicit **DTOs; never return raw DB rows** (prevents leaking `password_hash`, `join_code`, etc.).
11. **Parameterized queries only.** Django ORM or bound parameters. No string-built SQL, ever.
12. **Ports & adapters** for external services (email, storage, push): the core logic talks to a protocol/interface; the adapter is injected by env config.

## 3. Security rules (non-negotiable)

### 3.1 Secrets & config — "never expose important info"

13. **No secrets in git, logs, tests, or the client bundle.** Anything prefixed `VITE_*` is public by definition. `.env.example` documents names only. Real `.env` is gitignored. Prod credentials never live on a laptop.
14. **Never log or return:** passwords, OTP codes, session tokens, cookies, full emails, `password_hash`, internal columns. Hash IPs (daily-salted) in audit tables. Log IDs, not identities.
15. **Errors never leak** stack traces, SQL, or internal paths. Error responses carry a stable `code` + `requestId` (RFC 9457 problem format from S2 on).
16. **Crypto correctness:** `secrets`/`os.urandom` only — never `random`/`Math.random`. Argon2id for passwords; HMAC (not plain hash) for low-entropy OTPs; 256-bit session tokens stored hashed (SHA-256); constant-time compares (`hmac.compare_digest`).
17. **No** `SELECT *` **on users.** No unbounded queries (paginate/window everything). No `ON DELETE CASCADE` on anything that must survive (audit logs).
18. **DB is a security layer:** CHECK constraints encode every enum/state; unique/partial-unique indexes enforce "one pending X" rules; RLS (S3) is the backstop. The API DB role is not the table owner and has no BYPASSRLS.
19. **Generic auth errors** — no user enumeration; identical response shape/timing for "unknown email" and "wrong password".

### 3.2 Review gate

20. Every PR/change is checked against **PLAN.md §15** (review checklist) and the **Red-flag smells** list (§8 below). Security-relevant code must be marked `# SECURITY:` with a one-line reason.
21. Every endpoint ships tests: happy path, validation failure, **cross-group/cross-user access denied (IDOR suite)**, and rate limit if relevant.
22. New dependency → justify it in the PR, pin the version, run the audit. No new dep without a reason.

## 4. Data rules

23. **Time:** store `timestamptz` in UTC; all-day events use `date`; every event carries an IANA zone. Never store local times without a zone.
24. **Schema changes only via migration files** (`makemigrations` then read + hand-edit each one). Expand → migrate → contract; never rename/drop in the same release as the code change.
25. **Append-only logs** (`activity_log`, `audit_log`): UPDATE/DELETE revoked + trigger backstop. Retain 12 months.
26. **Every table has** `created_at`**;** editable tables also have `updated_at` + `version` (optimistic concurrency, `If-Match`).
27. **IDs are UUIDv7** (app-generated, time-sortable). UUIDs are not secrets — authorization is still mandatory.
28. **Seed/load scripts are dev-only** and refuse to run against prod. Never seed or run destructive scripts against prod.

## 5. Front end rules (the UI is FROZEN)

29. **Never change the UI's look or layout.** Front-end work is wiring only: API calls, state, loading/error/empty states. New screens need explicit user approval (PLAN §3.3 list).
30. No business rules duplicated in the UI — UI hides, API enforces.
31. No client-side auth remnants (no localStorage tokens, no client-side OTP/crypto). Cache wiped on logout.
32. **Never just rely on fronend to hide button or retrict user apply proper backend** 

## 6. Process rules

32. Small commits, Conventional Commit messages. CI blocks merge on failure. Branch protection on `main`.
33. **If a requirement is ambiguous or a rule isn't in this file — stop and ask.** Never invent security behaviour.
34. AI-written code is reviewed before merge: you must be able to explain every line, or ask the AI to explain/simplify (PLAN.md §15, §14.1).
35. Do add proper logs to deal with errors properly

## 7. Python-specific conventions (locked S0/S1 choices)

35. Apps per module: `core, accounts, groups, tasks, notifications, files` under `apps/api/`. Project package: `config`.
36. Custom `User` model (`accounts.User`, `AUTH_USER_MODEL`), `USERNAME_FIELD = "email"`. No Django admin in the MVP schema — `is_staff`/admin come later via change request if needed.
37. TextChoices for enums + DB CHECK constraints mirroring them; `CITextField` for email (citext extension); partial indexes for status-filtered lookups.
38. Env config via environment variables; the app validates config at boot (full validation lands in S0). `SEED_ALLOWED=true` is required for the seed command.

## 8. Red-flag smells (auto-fail in review)

- `any`/`# type: ignore` around auth or DB types · swallowing exceptions (`except: pass`)
- `Math.random`/`random` for anything security-related
- `*` CORS with credentials · JWT in localStorage
- `UPDATE`/`DELETE` without a WHERE scoped to the actor/group
- copy-pasted policy checks instead of the shared policy function
- hardcoded URLs/API keys · "TODO: add auth later"
- returning Django model instances from views · `select_related`/`prefetch` missing where query count can grow with data (N+1)

## 9. Frozen decisions log (grows as sections complete)

| Section | Frozen items | Status |
| --- | --- | --- |
| S0 | Repo layout, env var names, `/v1` prefix + health contract, CI pipeline, python version + dependency pins | implemented (carried into S1) |
| S1 | Entire schema: tables/columns/constraints/indexes (expand/contract migrations only, with change request) | **implemented & verified** — 56 tests green, `manage.py check` + `makemigrations --check` clean, all 6 core queries <50 ms on the 100k-row seed (EXPLAIN ANALYZE in `apps/api/docs/bench/`) |

S1 verified deviations from the plan (approved during implementation, captured so later phases consume the real shape, not the doc's):
- `users_name_not_empty` / `groups_name_not_empty` CHECKs needed a re-registered `Length` lookup (`Q(name__length__gt=0)`) because Django only ships it on `CharField` by default.
- PLAN's `coalesce(group_id, owner_id)` index is impossible in Postgres (no expression indexes over two FK columns in one btree); replaced by two frozen partial indexes — `tasks_group_deadline` + `tasks_owner_deadline` (same semantics, covered by tests).
- Q3 ("due soon") is deliberately a **two-step query**: materialize my active group ids (indexed lookup on `memberships_user_active`), then a literal `IN (…)` on `tasks_group_deadline`. A `Subquery`/join shape lets the planner merge-join on the generic FK index and degrade past the 50 ms budget — do not "simplify" this shape in S4 without re-running `manage.py bench`.
| S2 | Error envelope, status codes, pagination format, cookie name `__Host-sid`, OpenAPI pipeline | not started |
| S3+ | (each section appends its own frozen list here when it completes) | — |
