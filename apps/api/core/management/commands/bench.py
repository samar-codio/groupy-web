"""Benchmark the six frozen core queries (PLAN §5.4) against a live seeded
database and save EXPLAIN ANALYZE output — the S1 "done when" acceptance run
(PLAN §5.6): every query must run in <50 ms on the 100k-row seed.

Usage (dev DB only — read-only, no guards needed):
    DATABASE_URL=postgres://groupy@127.0.0.1:5433/groupy_dev \
      python manage.py bench

Output: apps/api/docs/bench/q{1..6}.txt (EXPLAIN ANALYZE per query) and a
printed timing table. Re-runnable; reads whichever user/group it picks.
"""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from accounts.models import User
from core.queries import (
    explain,
    feed_page,
    files_search,
    group_tasks_in_month,
    month_bounds,
    my_groups_with_unread,
    pending_requests,
    tasks_due_soon,
    unread_counts,
)
from groups.models import Group, Membership, MembershipStatus, Post

BUDGET_MS = 50.0
RUNS = 5
DOCS_DIR = Path(__file__).resolve().parents[3] / "docs" / "bench"


def _materialize(result):
    """Force full evaluation: plain querysets are lazy, so timing without
    this would measure query construction, not execution."""
    if hasattr(result, "_fetch_all"):
        list(result)
    return result


class Command(BaseCommand):
    help = "Run the six frozen core queries, time them, save EXPLAIN ANALYZE."

    def handle(self, *args, **options):
        now = timezone.now()
        from_dt, to_dt = month_bounds(now.year, now.month)

        membership = Membership.objects.filter(status=MembershipStatus.ACTIVE).first()
        if membership is None:
            self.stderr.write("No active memberships found — seed first (manage.py seed).")
            return
        user: User = membership.user
        group: Group = membership.group

        # (name, callable, queryset for EXPLAIN ANALYZE)
        entries = [
            (
                "q1_my_groups_with_unread",
                lambda: my_groups_with_unread(user),
                unread_counts(user),
            ),
            (
                "q2_group_tasks_in_month",
                lambda: group_tasks_in_month(group, from_dt, to_dt),
                group_tasks_in_month(group, from_dt, to_dt),
            ),
            (
                "q3_tasks_due_soon",
                lambda: tasks_due_soon(user, timedelta(days=7), now),
                tasks_due_soon(user, timedelta(days=7), now),
            ),
            (
                "q4_feed_page",
                lambda: feed_page(group, 20),
                Post.objects.filter(group=group, deleted_at__isnull=True).order_by(
                    "-created_at", "-id"
                )[:20],
            ),
            (
                "q5_files_search",
                lambda: files_search(user, "week37", 20),
                files_search(user, "week37", 20),
            ),
            (
                "q6_pending_requests",
                lambda: pending_requests(group),
                pending_requests(group),
            ),
        ]

        # Warm caches before timing.
        for _, fn, _qs in entries:
            _materialize(fn())

        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        results = []
        for name, fn, qs in entries:
            timings = []
            for _ in range(RUNS):
                t0 = time.perf_counter()
                _materialize(fn())
                timings.append((time.perf_counter() - t0) * 1000)
            best = min(timings)
            mean = sum(timings) / len(timings)
            results.append((name, best, mean))

            try:
                plan = explain(qs, analyze=True)
            except Exception as exc:
                plan = f"EXPLAIN failed: {exc}"
            out = f"-- {name} on seed: best={best:.2f} ms mean={mean:.2f} ms\n{plan}\n"
            # Q5 extra: the planner switches files_filename_trgm for selective
            # terms — capture both plans as proof the trigram index is live.
            if name == "q5_files_search":
                try:
                    selective = explain(files_search(user, "report_week37", 20), analyze=True)
                except Exception as exc:
                    selective = f"EXPLAIN failed: {exc}"
                out += (
                    "-- selective term (report_week37): planner chooses the"
                    " trigram index\n" + selective + "\n"
                )
            (DOCS_DIR / f"{name}.txt").write_text(out)

        self.stdout.write(
            self.style.SUCCESS(
                f"Benchmark against {connection.settings_dict['NAME']} "
                f"(user={user.email!r}, group={group.name!r}, month={now.year}-{now.month:02d})"
            )
        )
        ok = True
        for name, best, mean in results:
            flag = "OK " if best < BUDGET_MS else "OVER"
            if best >= BUDGET_MS:
                ok = False
            self.stdout.write(f"  {flag} {name:28s} best={best:7.2f} ms  mean={mean:7.2f} ms")
        self.stdout.write(
            f"Budget: < {BUDGET_MS} ms per query. "
            + ("ALL WITHIN BUDGET." if ok else "SOME OVER BUDGET — investigate.")
        )
        self.stdout.write(f"EXPLAIN ANALYZE saved to {DOCS_DIR}/")
