"""Accounts module (PLAN §5.4): users, otp_challenges, sessions, feedback,
data_export_requests.

Schema notes:
- email is citext (case-insensitive, unique) — extension created in
  core/0001_extensions.py.
- users never hard-deleted: deleted_at + 14-day grace then anonymize (PLAN 5.5).
- otp_challenges stores HMAC-SHA256(code, pepper ‖ challenge_id) — never the
  raw code (a 6-digit code is brute-forceable from a plain hash; PLAN §5.4).
- sessions store SHA-256 of the 256-bit token — the raw token lives only in
  the HttpOnly cookie (PLAN §10.1).
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import CheckConstraint, F, Q

from core.fields import CITextField, UUIDv7Field


class UserStatus(models.TextChoices):
    """Product state machine; is_active mirrors it for Django plumbing."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_DELETION = "pending_deletion"


class OtpPurpose(models.TextChoices):
    SIGNUP = "signup"
    LOGIN = "login"
    RESET = "reset"


class ExportStatus(models.TextChoices):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra) -> "User":
        if not email:
            raise ValueError("email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        if password is not None:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra) -> "User":
        extra.setdefault("status", UserStatus.ACTIVE)
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser):
    """Groupy account. `status` is the product state machine;
    `is_active` is the Django auth-framework switch (kept in sync by S5)."""

    id = UUIDv7Field(primary_key=True)
    email = CITextField(unique=True)  # SECURITY: never SELECT * (password col)
    name = models.TextField()  # derived from email at signup; editable in Profile
    avatar_key = models.TextField(null=True)  # storage key; never exposed raw
    tz = models.TextField(default="Asia/Karachi")  # IANA zone (PLAN A2/A5)
    status = models.TextField(choices=UserStatus.choices, default=UserStatus.ACTIVE)
    terms_accepted_at = models.DateTimeField(null=True)  # consent logging (10.8)
    terms_version = models.TextField(null=True)
    email_verified_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)  # soft delete (PLAN 5.5)
    is_active = models.BooleanField(default=True)  # Django auth plumbing only

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "users"
        constraints = [
            CheckConstraint(check=Q(status__in=UserStatus.values), name="users_status_valid"),
            CheckConstraint(check=Q(name__length__gt=0), name="users_name_not_empty"),
        ]

    def __str__(self) -> str:
        return str(self.email)


class OtpChallenge(models.Model):
    """One OTP challenge (signup/login/reset). Expires in 10 min, max 5
    attempts, single use; a new challenge invalidates the old one (PLAN 10.1)."""

    id = UUIDv7Field(primary_key=True)
    email = CITextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="+")
    purpose = models.TextField(choices=OtpPurpose.choices)
    # SECURITY: HMAC-SHA256(code, OTP_PEPPER ‖ challenge_id) — not a bare hash.
    code_hmac = models.TextField()
    expires_at = models.DateTimeField()  # now + 10 min
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    consumed_at = models.DateTimeField(null=True)
    resend_count = models.PositiveSmallIntegerField(default=0)
    ip_hash = models.TextField(null=True)  # daily-salted, never raw (10.6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_challenges"
        constraints = [
            CheckConstraint(check=Q(purpose__in=OtpPurpose.values), name="otp_purpose_valid"),
            CheckConstraint(check=Q(attempts__lte=F("max_attempts")), name="otp_attempts_within_max"),
        ]
        indexes = [
            models.Index(fields=["email", "purpose", "-created_at"], name="otp_email_purpose_created")
        ]


class Session(models.Model):
    """Server-side session (PLAN §10.1). Token: 256-bit random; only its
    SHA-256 hash is stored. Idle 30 d / absolute 90 d; revoked on logout,
    password change, or privilege change."""

    id = UUIDv7Field(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    token_hash = models.TextField(unique=True)  # SECURITY: SHA-256(token)
    device_label = models.TextField(null=True)
    ip_hash = models.TextField(null=True)
    user_agent = models.TextField(null=True)
    trusted_device = models.BooleanField(default=False)  # A8: OTP on new device
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True)
    idle_expires_at = models.DateTimeField()
    absolute_expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "sessions"
        indexes = [models.Index(fields=["user"], name="sessions_user")]


class Feedback(models.Model):
    """User feedback (PLAN §7.4: POST /feedback, 5/day limit)."""

    id = UUIDv7Field(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    message = models.TextField()
    file = models.ForeignKey(
        "files.File", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    app_version = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feedback"
        constraints = [
            CheckConstraint(
                check=Q(message__length__gte=1) & Q(message__length__lte=2000),
                name="feedback_message_length",
            )
        ]


class DataExportRequest(models.Model):
    """Async export job (PLAN R13): JSON zip emailed via link, 24 h expiry."""

    id = UUIDv7Field(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    status = models.TextField(choices=ExportStatus.choices, default=ExportStatus.PENDING)
    file = models.ForeignKey(
        "files.File", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    expires_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_export_requests"
        constraints = [
            CheckConstraint(check=Q(status__in=ExportStatus.values), name="export_status_valid")
        ]
