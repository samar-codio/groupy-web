"""Cross-cutting tables (PLAN §5.4): activity_log, audit_log, idempotency_keys, outbox.

- activity_log / audit_log are APPEND-ONLY: UPDATE/DELETE revoked + trigger
  backstop (migration core/0003_append_only_logs.py). Different audiences:
  activity_log = group History tab (members); audit_log = security events
  (ops only, no API) — PLAN §5.4, ADR-001.
- idempotency_keys: consumed by S2 middleware; schema frozen here.
- outbox: transactional outbox (PLAN §8.2) — rows are enqueued inside the DB
  transaction that created the change; a worker delivers after commit
  (never email/push inside the tx).
"""

from django.db import models
from django.db.models import CheckConstraint, Q

from core.fields import UUIDv7Field


class AuditEvent(models.TextChoices):
    """Security events recorded in audit_log (PLAN §5.4)."""

    LOGIN_OK = "login_ok"
    LOGIN_FAIL = "login_fail"
    OTP_FAIL = "otp_fail"
    ROLE_CHANGE = "role_change"
    REMOVAL = "removal"
    PASSWORD_CHANGE = "password_change"
    SESSION_REVOKED = "session_revoked"
    CODE_ROTATED = "code_rotated"


class OutboxStatus(models.TextChoices):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class ActivityLog(models.Model):
    """Group activity for the History tab (feed). Append-only."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, related_name="+"
    )
    # PROTECT: users are anonymized (soft-deleted), never hard-deleted, so the
    # FK stays valid; PROTECT makes accidental hard deletes fail loudly.
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, related_name="+"
    )
    action = models.TextField()
    entity_type = models.TextField(null=True)
    entity_id = models.UUIDField(null=True)
    # SECURITY (RULES.md §3.1.14): ids only — never content, never PII.
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["group", "-created_at"], name="activity_log_group_created"
            )
        ]


class AuditLog(models.Model):
    """Security events: login_ok/login_fail/otp_fail/role_change/removal/
    password_change/session_revoked/code_rotated (PLAN §5.4). Append-only.
    Retention 12 months; ops-only access (never exposed via API)."""

    id = UUIDv7Field(primary_key=True)
    # SET_NULL: anonymous events (failed login for unknown email) have no user.
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    event = models.TextField(choices=AuditEvent.choices)
    # SECURITY: hashed with a daily salt — never a raw IP (RULES.md §3.1.14).
    ip_hash = models.TextField(null=True)
    user_agent = models.TextField(null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        constraints = [
            CheckConstraint(
                check=Q(event__in=AuditEvent.values), name="audit_log_event_valid"
            )
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="audit_log_user_created"),
            models.Index(fields=["-created_at"], name="audit_log_created"),
        ]


class IdempotencyKey(models.Model):
    """Stripe-style idempotency (PLAN §7.3). S2 middleware reads/writes this;
    the schema is frozen here. TTL 24 h enforced by a cleanup job (S10)."""

    id = UUIDv7Field(primary_key=True)
    key = models.UUIDField(unique=True)  # client-generated Idempotency-Key
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")
    route = models.TextField()
    request_hash = models.TextField()  # SHA-256 of the canonical request body
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "idempotency_keys"
        indexes = [models.Index(fields=["created_at"], name="idempotency_keys_created")]


class Outbox(models.Model):
    """Transactional outbox for post-commit delivery of push/email.

    PLAN §8.2: approve-transaction enqueues here; a worker (S7+) polls
    (status, available_at) and delivers AFTER commit. Deduped per (topic,
    dedupe_key) via a partial unique index. At-least-once + idempotent
    consumers (R16)."""

    id = UUIDv7Field(primary_key=True)
    topic = models.TextField()  # e.g. "push", "email"
    payload = models.JSONField(default=dict, blank=True)  # ids and titles only
    dedupe_key = models.TextField(null=True)
    status = models.TextField(choices=OutboxStatus.choices, default=OutboxStatus.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(auto_now_add=True)  # retry backoff anchor
    locked_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "outbox"
        constraints = [
            CheckConstraint(check=Q(status__in=OutboxStatus.values), name="outbox_status_valid"),
            models.UniqueConstraint(
                fields=["topic", "dedupe_key"],
                condition=Q(dedupe_key__isnull=False),
                name="outbox_topic_dedupe_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "available_at"], name="outbox_status_available")
        ]
