"""Dev-only seed (PLAN §5.6: "Dev seed script (fake users/groups). Never seed
or run destructive scripts against prod.").

Usage (dev only):
    SEED_ALLOWED=true DATABASE_URL=postgres://groupy@127.0.0.1:5433/groupy_dev \\
        python manage.py seed --tasks 100000

Guards (RULES.md §4.28 / §7.38):
- refuses to run unless settings.SEED_ALLOWED is true (env opt-in) AND
  settings.DEBUG is true — two independent switches, both default off;
- refuses to run if the connected database is not explicitly a dev database:
  the database NAME must contain "dev" (groupy_dev, groupy_test_dev, ...).
  Prod runs connect to databases named groupy/prod-* — this blocks them.

Data volume defaults to the PLAN §5.4 "Done when" target: 100k tasks so the 6
core queries can be timed against a realistic row count.

All rows are fake: emails use @example.test (RFC 2606), join codes come from
the same 32-symbol alphabet generation logic as the app (S6), and no real
secrets are involved.
"""

import random
import string
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import User
from core.fields import uuid7
from files.models import File, FilePurpose, FileStatus
from groups.models import Group, Membership, MembershipRole, MembershipStatus, Post
from notifications.models import Notification, NotificationType
from tasks.models import Task, TaskRequest, TaskRequestStatus


# 32-symbol alphabet (R5): A–Z minus I/O, digits 2–9.
JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _join_code() -> str:
    return "".join(random.choices(JOIN_CODE_ALPHABET, k=6))


def _utc_within(days: int) -> timezone.datetime:
    """A random timestamptz in the last `days` days."""
    return timezone.now() - timedelta(
        days=random.random() * days, seconds=random.random() * 86400
    )


class Command(BaseCommand):
    help = "Seed the DEV database with fake users/groups/tasks for query timing."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=200)
        parser.add_argument("--groups", type=int, default=40)
        parser.add_argument("--tasks", type=int, default=100_000)
        parser.add_argument("--requests", type=int, default=2_000)
        parser.add_argument("--posts", type=int, default=10)
        parser.add_argument("--notifications", type=int, default=30)
        parser.add_argument("--files", type=int, default=2_000)
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the interactive confirmation (CI use).",
        )

    def _check_guards(self) -> None:
        if not settings.SEED_ALLOWED:
            raise CommandError(
                "SEED_ALLOWED is not set. Seeding is dev-only (RULES.md §4.28); "
                "export SEED_ALLOWED=true to acknowledge."
            )
        if not settings.DEBUG:
            raise CommandError(
                "Refusing to seed with DEBUG=false — staging/prod must never be "
                "seeded (RULES.md §4.28)."
            )
        db_name = connection.settings_dict["NAME"]
        if "dev" not in db_name:
            raise CommandError(
                f"Refusing to seed database '{db_name}' — the name must contain "
                "'dev' (e.g. groupy_dev). This is a hard guard, not a check "
                "you may skip (RULES.md §7.38)."
            )

    def handle(self, *args, **options):
        self._check_guards()
        self.stdout.write(
            self.style.WARNING(
                f"Target: {connection.settings_dict['NAME']} — this will "
                "DELETE ALL ROWS in every table and insert fake data."
            )
        )
        if not options["yes"] and input("Type 'yes' to continue: ") != "yes":
            raise CommandError("aborted")

        random.seed(42)  # deterministic-ish volume, not reproducible rows
        self._wipe()
        users = self._users(options["users"])
        groups = self._groups(users, options["groups"])
        self._memberships(users, groups)
        tasks = self._tasks(users, groups, options["tasks"])
        self._task_requests(users, groups, options["requests"])
        self._posts(users, groups, options["posts"])
        self._notifications(users, groups, options["notifications"])
        self._files(users, groups, options["files"])
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    @transaction.atomic
    def _wipe(self):
        # Dev-only TRUNCATE; the append-only triggers block DELETE, and
        # TRUNCATE is the ops/purge path those triggers deliberately allow.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE files, folders, notifications, notification_prefs,
                push_subscriptions, task_completions, task_exceptions,
                task_requests, tasks, posts, join_requests, member_prefs,
                memberships, groups, institutions, data_export_requests,
                feedback, sessions, otp_challenges, users, idempotency_keys,
                outbox, activity_log, audit_log CASCADE
                """
            )

    @transaction.atomic
    def _users(self, n: int) -> list[User]:
        now = timezone.now()
        users = [
            User(
                email=f"user{i}@example.test",  # RFC 2606 reserved TLD
                name=f"User {i}",
                tz=random.choice(["Asia/Karachi", "UTC", "Europe/London"]),
                terms_accepted_at=now,
                terms_version="2026-09-01",
                email_verified_at=now,
                is_active=True,  # bulk_create does not apply model defaults
                created_at=_utc_within(180),
                updated_at=now,
            )
            for i in range(n)
        ]
        # bulk_create skips save()/auto_now; values above are explicit.
        User.objects.bulk_create(users, batch_size=5_000)
        return list(User.objects.all())

    @transaction.atomic
    def _groups(self, users: list[User], n: int) -> list[Group]:
        now = timezone.now()
        groups = [
            Group(
                owner=random.choice(users),
                name=f"Group {i} - {random.choice(['CS', 'Math', 'Physics', 'Chem', 'Bio'])}",
                subtitle="Seeded group",
                join_code=_join_code(),
                join_mode="open",
                tz="Asia/Karachi",
                created_at=_utc_within(180),
                updated_at=now,
            )
            for i in range(n)
        ]
        Group.objects.bulk_create(groups, batch_size=5_000)
        return list(Group.objects.all())

    @transaction.atomic
    def _memberships(self, users: list[User], groups: list[Group]):
        now = timezone.now()
        rows = []
        for user in users:
            # Each user joins a random subset: 1..min(6, n_groups) groups.
            k = random.randint(1, min(6, len(groups)))
            for group in random.sample(groups, k=k):
                rows.append(
                    Membership(
                        group=group,
                        user=user,
                        role=random.choices(
                            MembershipRole.values, weights=[1, 9]
                        )[0],
                        status=random.choices(
                            MembershipStatus.values, weights=[90, 3, 3, 4]
                        )[0],
                        joined_at=_utc_within(180),
                        left_at=None,
                    )
                )
        Membership.objects.bulk_create(rows, batch_size=5_000)
        # Guarantee every group has at least its owner as active admin.
        for group in groups:
            Membership.objects.update_or_create(
                group=group,
                user=group.owner,
                defaults={
                    "role": MembershipRole.ADMIN,
                    "status": MembershipStatus.ACTIVE,
                    "joined_at": now,
                },
            )

    @transaction.atomic
    def _tasks(
        self, users: list[User], groups: list[Group], n: int
    ) -> list[Task]:
        now = timezone.now()
        created_by_pool = users[:50]  # keep created_by FK cheap and realistic
        tasks = []
        # 70% group tasks, 30% personal tasks (XOR: one of the two FKs).
        for _ in range(n):
            all_day = random.random() < 0.2
            if random.random() < 0.7:
                group, owner = random.choice(groups), None
            else:
                group, owner = None, random.choice(users)
            start = _utc_within(120)
            if all_day:
                tasks.append(
                    Task(
                        group=group,
                        owner=owner,
                        title=f"Task {_}: {random.choice(['Assignment', 'Quiz', 'Lab', 'Project', 'Reading'])}",
                        all_day=True,
                        start_date=start.date(),
                        end_date=(start + timedelta(days=random.randint(0, 3))).date(),
                        tz=random.choice(["Asia/Karachi", "UTC"]),
                        deadline_at=start + timedelta(days=random.randint(1, 14)),
                        created_by=random.choice(created_by_pool),
                        version=1,  # bulk_create does not apply model defaults
                        created_at=start,
                        updated_at=now,
                    )
                )
            else:
                end = start + timedelta(hours=random.randint(1, 4))
                tasks.append(
                    Task(
                        group=group,
                        owner=owner,
                        title=f"Task {_}: {random.choice(['Assignment', 'Quiz', 'Lab', 'Project', 'Reading'])}",
                        all_day=False,
                        start_at=start,
                        end_at=end,
                        tz=random.choice(["Asia/Karachi", "UTC"]),
                        deadline_at=end + timedelta(days=random.randint(0, 14)),
                        created_by=random.choice(created_by_pool),
                        version=1,  # bulk_create does not apply model defaults
                        created_at=start,
                        updated_at=now,
                    )
                )
        Task.objects.bulk_create(tasks, batch_size=5_000)
        return list(Task.objects.all()[:100])  # caller only needs a sample

    @transaction.atomic
    def _task_requests(self, users: list[User], groups: list[Group], n: int):
        now = timezone.now()
        rows = []
        for _ in range(n):
            start = _utc_within(60)
            rows.append(
                TaskRequest(
                    group=random.choice(groups),
                    requested_by=random.choice(users),
                    title=f"Request: extra session {random.randint(1, 99)}",
                    tz="Asia/Karachi",
                    all_day=False,
                    start_at=start,
                    end_at=start + timedelta(hours=1),
                    status=random.choice(
                        [
                            TaskRequestStatus.PENDING,
                            TaskRequestStatus.APPROVED,
                            TaskRequestStatus.DECLINED,
                        ]
                    ),
                    version=1,
                    created_at=_utc_within(60),
                    updated_at=now,
                )
            )
        TaskRequest.objects.bulk_create(rows, batch_size=5_000)

    @transaction.atomic
    def _posts(self, users: list[User], groups: list[Group], per_group: int):
        now = timezone.now()
        rows = []
        for group in groups:
            admins = list(
                Membership.objects.filter(
                    group=group,
                    status=MembershipStatus.ACTIVE,
                    role=MembershipRole.ADMIN,
                ).values_list("user_id", flat=True)
            ) or [group.owner_id]
            for _ in range(per_group):
                rows.append(
                    Post(
                        group=group,
                        author_id=random.choice(admins),
                        body="Seeded announcement: "
                        + "".join(
                            random.choices(string.ascii_letters + " ", k=80)
                        ),
                        pinned=random.random() < 0.05,
                        created_at=_utc_within(90),
                    )
                )
        Post.objects.bulk_create(rows, batch_size=5_000)

    @transaction.atomic
    def _notifications(
        self, users: list[User], groups: list[Group], per_user: int
    ):
        now = timezone.now()
        rows = []
        for user in users:
            user_groups = random.sample(groups, k=min(4, len(groups)))
            for group in user_groups:
                rows.append(
                    Notification(
                        user=user,
                        group=group,
                        type=random.choice(NotificationType.values),
                        data={"title": "Task updated"},  # ids + short title only
                        created_at=_utc_within(30),
                        read_at=None if random.random() < 0.6 else now,
                    )
                )
        Notification.objects.bulk_create(rows, batch_size=5_000)

    @transaction.atomic
    def _files(self, users: list[User], groups: list[Group], n: int):
        now = timezone.now()
        uploaders = users[:50]  # keep uploaded_by FK cheap and realistic
        words = [
            "assignment", "report", "lab", "notes", "quiz", "slides",
            "project", "draft", "final", "handout",
        ]
        rows = []
        for i in range(n):
            rows.append(
                File(
                    group=random.choice(groups),
                    uploaded_by=random.choice(uploaders),
                    purpose=FilePurpose.GROUP_FILE,
                    # SECURITY (RULES.md §4.27): server-generated storage key,
                    # never the user's filename.
                    storage_key=f"groups/{uuid7()}",
                    filename=(
                        f"{random.choice(words)}_{random.choice(words)}"
                        f"_week{random.randint(1, 40)}_{i}."
                        f"{random.choice(['pdf', 'docx', 'xlsx', 'png'])}"
                    ),
                    mime_declared="application/octet-stream",
                    size_bytes=random.randint(1, 5_000_000),
                    status=FileStatus.READY,  # bulk_create skips model default
                    created_at=_utc_within(90),
                )
            )
        File.objects.bulk_create(rows, batch_size=5_000)
