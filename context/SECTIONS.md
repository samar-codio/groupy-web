# Groupy: Build Sections (SECTIONS.md)

> Companion to PLAN.md. PLAN.md = the *why* (architecture, rules, references). This file = the *order* (what you read, then code, section by section). Backend decision: **Python — Django + DRF** (see PLAN.md A5). All TS snippets in PLAN.md map to Python via the table below.

---

## 0. How this works (your loop, per section)

1. **READ** — open the PLAN.md sections listed under "Read" above the section. Slowly. Once.
2. **NOTE** — write in your notebook: goal in one sentence · the rules · what could break.
3. **CODE** — tell the AI: *"Implement section S only. Read SECTIONS.md section S and these PLAN.md sections: … Do not touch frozen items."*
4. **ATTACK** — review the code against the section's "Attack checklist" + PLAN.md Section 15. Ask the AI *why* for every line you can't explain. Run the tests.
5. **FREEZE** — CI green (this section's tests + ALL previous sections' tests). Mark the section `done` in the table below. From now on its "Frozen" list is contract; changing it needs a written change request (new ADR in `docs/decisions/`) approved by you.

**Why errors can't cascade:** each section is *additive* (new files, new tests) and only consumes frozen interfaces from earlier sections. Earlier tests stay in CI forever — if a later section breaks an earlier one, CI goes red at the moment of breakage, not weeks later.

**Size rule:** every section ≤ \~1–2 coding sessions for the AI, ≤ \~4–6 pages of PLAN.md reading for you.

### Progress tracker

| S | Title | Status |
| --- | --- | --- |
| S0 | Walking skeleton (repo, compose, health, CI) | ☐ |
| S1 | Data model (Django models + migrations) | ☐ |
| S2 | API conventions & error contract | ☐ |
| S3 | Authorization policy (pure) + RLS | ☐ |
| S4 | Auth core (pure: password/OTP/session/email) | ☐ |
| S5 | Auth routes (signup → OTP → login → /me) | ☐ |
| S6 | Groups (create/join/members + policy wiring) | ☐ |
| S7 | Task requests + the approve transaction | ☐ |
| S8 | Calendar + notifications read | ☐ |
| S9 | Frontend wiring (screen by screen: S9a–S9f) | ☐ |
| S10 | E2E + staging/prod deploy + ops | ☐ |
| S11+ | Post-MVP queue (posts/files, recurrence, push…) | ☐ |

### TS (PLAN.md) → Python (what we build)

| PLAN.md says | We use |
| --- | --- |
| Zod schema | Pydantic / DRF serializer (`.strict` = `extra='forbid'`) |
| Fastify route | DRF viewset/APIView + `urls.py` |
| Drizzle ORM + drizzle-kit | Django ORM + `makemigrations` (read + hand-edit each migration) |
| pg-boss outbox | `django-tasks` (or a real `outbox` table + management command) |
| pino | stdlib `logging` with JSON formatter + redaction filter |
| Vitest / Supertest / `app.inject` | pytest / `pytest-django` / DRF test client |
| Testcontainers Postgres | CI service container Postgres (gh actions `postgres:`) |
| fastify-type-provider-zod → openapi.json | `drf-spectacular` → `openapi.json` (committed, CI staleness check) |
| `crypto.randomInt` | `secrets.randbelow` (NEVER `random`) |
| Argon2id | `argon2-cffi` via Django `PBKDF2…→Argon2` PASSWORD_HASHERS\[0\] |
| web-push | `pywebpush` |
| shared Zod packages/contract | OpenAPI → `openapi-typescript` codegen for the React app |
| rrule / luxon | `python-dateutil` rrule (backend); frontend keeps its JS libs |
| sharp (avatar re-encode) | `Pillow` |

Frontend repo stays TypeScript/React untouched (PLAN rule 2: wiring only).

---

## S0 — Walking skeleton

**Read:** PLAN.md §0, §1, §2 (all), §4, §17. **Learn:** docker compose · 12-factor env · WSGI/ASGI in one paragraph · GitHub Actions caching · conventional commits. **Build:**

- Monorepo: `apps/web/` (move existing React app **byte-for-byte unchanged**), `apps/api/` (Django project, one deployable, app-per-module: `accounts`, `groups`, `tasks`, `notifications`, `files`, `core`).
- `docker-compose.yml`: postgres 16, mailpit, minio.
- `GET /v1/healthz` (static ok) + `/v1/readyz` (DB `SELECT 1`).
- Env validation with pydantic-settings — app **refuses to boot** on missing/invalid env; `.env.example` committed.
- CI (`ci.yml`): ruff + mypy + pytest (empty suite runs) + web build; gitleaks; branch protection on `main`.
- Vite proxy `/api/*` → api (same-origin now, real deploy later). Web shows "API: ok, DB: ok".
- `AGENTS.md` copied from PLAN §0 rules + this file's loop. **Tests:** healthz/readyz integration test (readyz fails when DB down). **Attack checklist:** `.env` in `.gitignore`? frontend has NO hardcoded API URL? CI actually runs on PR? did the UI change at all (it must not)? **Freeze:** repo layout, env var names, `/v1` prefix + health contract, CI pipeline, python version + dependency pins (`uv`/`requirements.txt`). **Done when:** push to `main` → CI green → staging shows "API: ok, DB: ok" from your phone.

---

## S1 — Data model

**Read:** PLAN.md §5 (all, slowly — this is the P0 section). DDIA ch. 2–3, 7. **Learn:** 3NF · ON DELETE semantics · CHECK constraints · partial indexes · EXPLAIN ANALYZE · `timestamptz` vs `date` · citext · UUIDv7 · SELECT FOR UPDATE. **Build:**

- Django models for: `users, otp_challenges, sessions, groups, memberships, member_prefs, task_requests, tasks, task_exceptions, task_completions, posts, files, notifications, notification_prefs, push_subscriptions, activity_log, audit_log, idempotency_keys, outbox, data_export_requests` (+ reserved `institutions`, `folders`, `join_requests`).
- `Meta.constraints` = every CHECK from PLAN 5.4; `Meta.indexes` = every listed index; `db.Collation`/citext via migration SQL; UUIDv7 generated in app layer.
- Append-only protection for the two logs: `REVOKE UPDATE/DELETE` + trigger (raw SQL migration).
- `version`/`updated_at` on editable tables.
- Seed script (100k tasks, fake users/groups) — dev only, guarded against prod.
- ADRs 001–003 in `docs/decisions/`. **Tests:** migration applies to empty DB in CI; model-level constraint tests (illegal states raise); the 6 core queries exist as pytest fixtures with timing assertions on seed. **Attack checklist:** every FK indexed? every status column has a CHECK? can you explain each partial index by the query it serves? any `null=True` on something that should be required? does rejoin reuse the membership row? **Freeze:** entire schema (tables/columns/constraints/indexes). Later sections add expand/contract migrations ONLY with a change request. **Done when:** 6 core queries &lt; 50 ms on the seed and you can walk `EXPLAIN ANALYZE` for each.

---

## S2 — API conventions & error contract

**Read:** PLAN.md §7.1–7.3, §10.4, §10.7 (implementation note only). **Learn:** REST resources · RFC 9457 · keyset vs offset pagination · idempotency keys · ETag/If-Match · OpenAPI. **Build:**

- DRF configured for **deny by default** (default permission = authenticated; nothing public except auth + health).
- Problem-json exception handler: stable `code`s exactly from PLAN §7.3, `requestId`, no stack/SQL leakage, 422 validation shape from serializer errors.
- Keyset pagination class (`(created_at,id)` cursor, limit cap 100); calendar window params validated (max 62 days).
- Idempotency middleware reading `Idempotency-Key` against the frozen `idempotency_keys` table.
- Versioning `/v1`; `GET /v1/version`; security headers middleware (CSP report-only, HSTS, nosniff, `Cache-Control: no-store` on API JSON).
- `drf-spectacular` → generate `openapi.json`, committed; CI fails on drift; Spectral lint.
- TS client codegen script for the web app (openapi-typescript) — wired but unused so far. **Tests:** every error path returns the exact problem shape; pagination stability test; idempotent replay + mismatched-body 422; spec diff check. **Attack checklist:** does a 500 ever leak a traceback? do validation errors list field paths? is `limit` capped? does the spec generation exclude internal endpoints? **Freeze:** error envelope, status-code meanings, pagination format, cookie name `__Host-sid`, `/v1` URL scheme, OpenAPI generation pipeline. **Done when:** one throwaway demo endpoint uses ALL conventions and its tests pass; frontend compiles against generated types.

---

## S3 — Authorization policy (pure) + RLS

**Read:** PLAN.md §6 (all). PortSwigger access-control labs (do them yourself, this week). **Learn:** AuthN vs AuthZ · IDOR/BOLA · BFLA · BOPLA · deny-by-default · RLS. **Build:**

- `core/policy.py`: `can(actor, action, resource) -> Decision` pure function, deny by default, membership includes `status='active'`.
- Table-driven pytest covering **every cell** of the PLAN 6.3 matrix (including owner⊂admin, last-admin, banned, removed).
- `authorize()` DRF permission + a test that **walks the URLconf and fails if any route lacks it**.
- RLS migration for `tasks, posts, files, notifications` (PLAN 6.5 SQL verbatim); API DB role is not owner, no BYPASSRLS; per-request `set_config('app.user_id', …, true)` via middleware/transaction hook.
- STRIDE threat model draft for auth + join in `docs/threat-models/`; ADR 004. **Tests:** matrix cells; RLS negative test (raw SQL as app role, wrong user → 0 rows even if policy is bypassed). **Attack checklist:** any `role`/`group_id`/`user_id` read from the request body? non-member → 404 (not 403)? does demote/leave check the last-admin rule in the same transaction design? **Freeze:** policy function signature + matrix semantics. (Routes will *call* it from S5 on; they may not re-implement checks.) **Done when:** matrix is 100% green and you can defend any cell verbally.

---

## S4 — Auth core (pure logic, zero HTTP)

**Read:** PLAN.md §10.1, §8.1 step 4, §5.4 rows for `otp_challenges`/`sessions`. OWASP: Password Storage, Session Management, Authentication cheat sheets. **Learn:** Argon2id parameters · HMAC vs hash for low-entropy codes · opaque tokens · timing-safe compare · device trust. **Build:** (module, no views)

- `passwords.py`: Argon2id hasher config + strength check + HIBP k-anonymity pre-password check (offline-safe, with timeout).
- `otp.py`: 6 digits via `secrets.randbelow(10**6)`; store `HMAC-SHA256(code, OTP_PEPPER ‖ challenge_id)`; 10-min expiry; 5 attempts → dead; single-use; new challenge invalidates old; resend cooldowns; `hmac.compare_digest`.
- `sessions.py`: 256-bit `secrets.token_urlsafe`; store SHA-256 only; idle 30d / absolute 90d; rotate on privilege change; revoke-all on password change.
- `email_port.py`: `EmailPort` protocol + Console/Mailpit-smtp/Resend adapters (ports & adapters; DI via env).
- **Injectable** `clock` everywhere (expiry tests never sleep). **Tests:** 100% of OTP rules unit-tested; property test: codes never logged; token/hash round-trip. **Attack checklist:** `random` module anywhere? (must be `secrets`) · any place the raw code is stored/logged · constant-time compare used · pepper rotation plan written in ADR. **Freeze:** function signatures of otp/sessions/email ports. **Done when:** unit tests green and you can explain why HMAC and not SHA-256 for OTP storage (1M-value space).

---

## S5 — Auth routes

**Read:** PLAN.md §8.1 step 5, §7.4 Auth table, §10.1 login/lockout/CSRF bullets, §10.7 rows for auth. **Build:** `signup`, `otp/verify`, `otp/resend`, `login`, `logout`, `GET/PATCH /me` — calling S4 core only (routes contain NO crypto logic). `__Host-sid` cookie flags exact; Origin/Sec-Fetch check on mutations; DB-backed rate limits + progressive delay; anti-enumeration identical responses; audit_log events (login_ok/fail, otp_fail…). **Tests:** integration on real Postgres: enumeration resistance (timing + identical bodies), lockout after 5 bad codes, expired code, cookie flags asserted, logout revokes, resend invalidates old. **Attack checklist:** generic error wording · no OTP in response · routes pass the S3 "every route authorized" walker (auth routes explicitly public-listed) · rate limits per IP *and* per email. **Freeze:** auth endpoint URLs + request/response bodies (they're in the OpenAPI spec now). **Done when:** abuse suite green; manual run through Mailpit signup → OTP → login works from the generated API docs page.

---

## S6 — Groups

**Read:** PLAN.md §7.4 Groups table, §6.4 R1–R5. **Build:** create (group + owner membership + join code in ONE transaction; code collision retry), list (+memberCount/unreadCount/role — 1–2 queries, no N+1), join-by-code (rate limited, banned refused, idempotent R4), detail (join_code only for admins), members list, rotate code, leave/last-admin block (SELECT FOR UPDATE + trigger backstop). All handlers go through `authorize()`. DTOs only. **Tests:** policy matrix applied over HTTP; IDOR suite: user C hits every group endpoint with A's/B's IDs → 404 everywhere; join race (two users, capacity limits R17); leave blocks last admin under concurrency. **Attack checklist:** does `GET /groups/:id` leak `join_code` to members? does membership check include `status='active'`? is `group_id` derived from the object, not the body? **Freeze:** group endpoints + DTOs. **Done when:** C-gets-404 suite green and `GET /groups` query count verified = constant.

---

## S7 — Task requests + the approve transaction

**Read:** PLAN.md §8.2 (study the transaction line by line), §6.4 R6–R9, §7.4 Tasks&requests table, outbox note in §10.1/§8.1 step 7. **Build:** `POST task-requests` (member; ≤5 pending), list (own vs all for admin), detail, PATCH/DELETE while pending, approve/decline. Approve = ONE transaction exactly like PLAN 8.2: `SELECT FOR UPDATE` → policy → insert task → mark request → fan-out notifications (dedupe_key) → activity_log → **outbox row** (delivery after commit — never email/push inside the tx). **Tests:** state machine (decided immutable; decline with reason; cancel); **concurrency: two admins approve simultaneously → exactly one task, second gets 409** `already_decided`; idempotency-key replay; notification dedupe. **Attack checklist:** anything outside the transaction that must be inside? are recipients the *active* members? does approve re-check admin status at approve time (not at request time)? **Freeze:** request/task endpoints + approve semantics. **Done when:** race test green and you can explain why each of the 6 steps inside the transaction must be there.

---

## S8 — Calendar + notifications read

**Read:** PLAN.md §5.4 "Calendar query shape" + "Time rules", §7.4 calendar/notifications rows, §12 pagination/perf bullets. **Build:** `GET /calendar?scope&from&to&groupIds` (non-recurring only; `rrule` present → `422 recurrence_not_supported_yet`), all-day vs timed rendering rules server-side (dates in group/viewer tz per PLAN time rules), `GET /todo` buckets (user tz, "due soon" = 7 days, not completed by me), `GET /notifications`, unread count (indexed partial), mark-read. Personal tasks CRUD (R15: last-write-wins). **Tests:** timezone edge cases (Karachi/UTC/New York across a DST boundary, all-day stays same date for everyone); N+1 guard on calendar; completed-occurrence excluded from due-soon. **Attack checklist:** does calendar respect group membership via policy *and* RLS? is `to-from` ≤ 62 days enforced? any `SELECT *`? **Freeze:** calendar/todo/notification read contracts. **Done when:** timezone tests green; p95 on seed &lt; 300 ms.

---

## S9 — Frontend wiring (screen by screen — UI is FROZEN)

**Parent rules for all sub-sections:** PLAN.md §8.1 step 9. Never touch JSX structure/CSS — only data source swap + loading/error/empty states using existing components. Delete localStorage auth + the client-side SHA-256/OTP display **in S9a**. One sub-section = one PR = one demo on the running app. **Each sub-section keeps all previously wired screens working** (that's the stability test: after S9c, sign-up AND groups still work).

### S9a — API client + Auth screens

`src/api/client.ts` (typed fetch from generated types, `credentials: 'include'`, problem-json → typed errors), TanStack Query provider. Wire sign-up → OTP → login → logout → /me against the real API. **Done when:** real signup through Mailpit works in the dev browser; zero localStorage auth left.

### S9b — Groups: dashboard, create, join

Wire dashboard list, create group, join by code. Badges come from API.

### S9c — Group detail: People, Requests, Tasks tabs

Member list, request form, requests list w/ admin all-vs-own, pending-request cancel.

### S9d — Approve/decline UI

Admin approve/decline with `Idempotency-Key`, optimistic-off (server wins), badges clear correctly.

### S9e — Calendar/Day + To-do

Wire to /calendar, /todo; group toggle; colour keys → existing palette classes.

### S9f — Alerts + Feedback + Profile

Notifications list, mark read, unread counts, feedback form, /me edit + avatar intent/confirm. **Attack checklist (each):** any hardcoded mock data left? does an error ever show a raw `detail` from server? do screens 404-to-login correctly when session dies? cache wiped on logout?

---

## S10 — E2E, deploy, ops

**Read:** PLAN.md §8 acceptance script, §9 (all), §16 MVP DoD. **Build:** Playwright two-context acceptance run (A/B + C-locked-out), axe checks on key screens; deploy pipeline staging (migrate→deploy→smoke) + prod (tag + manual approval); Sentry (web+api, PII scrub); uptime on /readyz; nightly `pg_dump` → encrypt → R2; **one restore drill**; runbooks (deploy/rollback/restore/incident); ADR 011. **Done when:** PLAN §16 MVP Definition of Done is checked end-to-end (slice scope) and you shipped a trivial change to prod &lt; 15 min, rolled back &lt; 5 min.

---

## S11+ — Post-slice queue (each becomes its own S when you reach it)

Order chosen so each is additive to the frozen API/schema:

1. Posts/announcements + file upload/download (presigned, PLAN §10.3) — v1.0
2. Forgot/reset password (revokes all sessions)
3. Recurrence: RRULE storage is already frozen in S1; add expansion + `task_exceptions`
4. Remove member / promote / transfer ownership UI (endpoints exist from S6)
5. Web Push + notification prefs (outbox table exists from S7)
6. Account deletion + data export (jobs over frozen tables)
7. PWA offline write queue + install polish; a11y/WCAG pass; hardening (ASVS L1) + beta

---

## AI briefing template (paste before each coding request)

> Implement **section S** only. Read first: SECTIONS.md S + S Frozen list, and PLAN.md §&lt;list from "Read"&gt;. Rules: PLAN.md §0 rules 1–14 apply (backend is Django+DRF — translate TS examples per SECTIONS.md §0 table). You may create new files and tests. You may NOT modify frozen items from S0…S — if you need to, stop and propose a change request instead. Exit = every item in this section's Tests + Attack checklist passes; previous sections' tests still pass; openapi.json regenerated if routes changed.