"""Notifications module (PLAN §5.4): notifications, notification_prefs,
push_subscriptions.

R16: notifications are created IN THE SAME DB TRANSACTION as the change they
announce; delivery (push/email) goes through the outbox after commit. The
in-app list is the source of truth. Dedupe: UNIQUE(user_id, dedupe_key) —
replays are impossible even if the fan-out runs twice.
"""

from django.db import models
from django.db.models import CheckConstraint, Q

from core.fields import UUIDv7Field


class NotificationType(models.TextChoices):
    TASK = "task"
    ANNOUNCEMENT = "announcement"
    REQUEST = "request"
    MESSAGE = "message"


class Notification(models.Model):
    """One in-app notification. Hidden (by query) for groups the user left
    (R10); hard-deleted after 90 days (PLAN 5.5)."""

    id = UUIDv7Field(primary_key=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications"
    )
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, null=True, related_name="+"
    )
    type = models.TextField(choices=NotificationType.choices)
    entity_type = models.TextField(null=True)
    entity_id = models.UUIDField(null=True)
    # SECURITY (RULES.md §3.1.14): ids and short title only — never content/PII.
    data = models.JSONField(default=dict, blank=True)
    dedupe_key = models.TextField(null=True)
    read_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"], name="notifications_user_dedupe_uniq"
            ),
            CheckConstraint(check=Q(type__in=NotificationType.values), name="notifications_type_valid"),
        ]
        indexes = [
            # Alerts list: keyset pagination (created_at, id).
            models.Index(
                fields=["user", "-created_at", "-id"], name="notifications_user_created_id"
            ),
            # Unread badge per group: partial index keeps COUNT(*) tiny.
            models.Index(
                fields=["user", "group"],
                condition=Q(read_at__isnull=True),
                name="notifications_unread",
            ),
        ]


class NotificationPref(models.Model):
    """Per-user, per-type delivery prefs (in-app/push/email)."""

    id = UUIDv7Field(primary_key=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notification_prefs"
    )
    type = models.TextField(choices=NotificationType.choices)
    in_app = models.BooleanField(default=True)
    push = models.BooleanField(default=True)
    email = models.BooleanField(default=False)

    class Meta:
        db_table = "notification_prefs"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type"], name="notification_prefs_user_type_uniq"
            ),
            CheckConstraint(check=Q(type__in=NotificationType.values),
                            name="notification_prefs_type_valid"),
        ]


class PushSubscription(models.Model):
    """Web Push VAPID subscription. Delete on 404/410 from the push service
    (PLAN §5.4)."""

    id = UUIDv7Field(primary_key=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True)
    failed_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "push_subscriptions"
