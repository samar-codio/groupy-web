"""Groups module (PLAN §5.4): institutions (reserved), groups, memberships,
member_prefs, join_requests (v1.1), posts.

Key invariants (PLAN §6.4):
- memberships: UNIQUE(group_id, user_id) — rejoin re-activates the SAME row
  (R3), status carries the history (active/left/removed/banned); `banned`
  blocks code re-entry.
- member_prefs: composite PK (group_id, user_id), user-editable, kept separate
  from the authz-critical memberships table.
- join_requests: partial unique index blocks duplicate pending requests.
- posts: plain-text announcements, soft delete (edited_at/deleted_at).
"""

from django.db import models
from django.db.models import CheckConstraint, CompositePrimaryKey, Q

from core.fields import UUIDv7Field


class GroupJoinMode(models.TextChoices):
    OPEN = "open"
    APPROVAL = "approval"


class MembershipRole(models.TextChoices):
    ADMIN = "admin"
    MEMBER = "member"


class MembershipStatus(models.TextChoices):
    ACTIVE = "active"
    LEFT = "left"
    REMOVED = "removed"
    BANNED = "banned"


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class Institution(models.Model):
    """Reserved for future multi-institution tenancy (PLAN A6). NO logic in MVP."""

    id = UUIDv7Field(primary_key=True)
    name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "institutions"
        constraints = [
            CheckConstraint(check=Q(name__length__gt=0), name="institutions_name_not_empty")
        ]


class Group(models.Model):
    """A class/section group. Exactly one owner (⊂ admin), many admins allowed.

    SECURITY (R5): join_code = 6 chars from a 32-symbol alphabet (A–Z minus
    I/O, digits 2–9), generated with secrets; shown only to admins (S6 DTOs)."""

    id = UUIDv7Field(primary_key=True)
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="owned_groups"
    )
    name = models.TextField()
    subtitle = models.TextField(null=True)
    join_code = models.TextField(unique=True)
    join_code_expires_at = models.DateTimeField(null=True)
    join_mode = models.TextField(choices=GroupJoinMode.choices, default=GroupJoinMode.OPEN)
    tz = models.TextField(default="Asia/Karachi")  # default tz for its events
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    archived_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "groups"
        constraints = [
            CheckConstraint(
                check=Q(name__length__gte=1) & Q(name__length__lte=120),
                name="groups_name_length",
            ),
            CheckConstraint(
                check=Q(subtitle__isnull=True) | Q(subtitle__length__lte=200),
                name="groups_subtitle_length",
            ),
            CheckConstraint(
                check=Q(join_mode__in=GroupJoinMode.values), name="groups_join_mode_valid"
            ),
            CheckConstraint(check=Q(join_code__length=6), name="groups_join_code_length"),
        ]


class Membership(models.Model):
    """(group, user) pair — the authz core (PLAN §6). Never deleted: status
    transitions active → left/removed/banned keep history and FK targets."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.TextField(choices=MembershipRole.choices, default=MembershipRole.MEMBER)
    status = models.TextField(choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True)
    removed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        db_table = "memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"], name="memberships_group_user_uniq"
            ),
            CheckConstraint(check=Q(role__in=MembershipRole.values), name="memberships_role_valid"),
            CheckConstraint(check=Q(status__in=MembershipStatus.values), name="memberships_status_valid"),
        ]
        indexes = [
            # Partial indexes keep the "my groups" / "group members" lookups small.
            models.Index(
                fields=["user"],
                condition=Q(status=MembershipStatus.ACTIVE),
                name="memberships_user_active",
            ),
            models.Index(
                fields=["group"],
                condition=Q(status=MembershipStatus.ACTIVE),
                name="memberships_group_active",
            ),
        ]


class MemberPref(models.Model):
    """User-editable per-group preferences (colour, hide, mute). Composite PK
    (PLAN §5.4): separate table from memberships because the USER writes here
    frequently while memberships is authz-critical."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="member_prefs")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="member_prefs"
    )
    colour_key = models.TextField(null=True)  # palette key c1..c8, never raw CSS
    hidden_in_calendar = models.BooleanField(default=False)
    muted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    pk = CompositePrimaryKey("group", "user")

    class Meta:
        db_table = "member_prefs"
        constraints = [
            CheckConstraint(
                check=Q(colour_key__isnull=True) | Q(colour_key__regex=r"^c[1-8]$"),
                name="member_prefs_colour_key_format",
            )
        ]


class JoinRequest(models.Model):
    """v1.1: per-group approval mode (PLAN A6: not in MVP, table reserved)."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")
    status = models.TextField(choices=JoinRequestStatus.choices, default=JoinRequestStatus.PENDING)
    message = models.TextField(null=True)
    decided_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "join_requests"
        constraints = [
            CheckConstraint(check=Q(status__in=JoinRequestStatus.values), name="join_requests_status_valid"),
            # "one pending request per (group, user)" — the race-proof way.
            models.UniqueConstraint(
                fields=["group", "user"],
                condition=Q(status=JoinRequestStatus.PENDING),
                name="join_requests_pending_uniq",
            ),
        ]


class Post(models.Model):
    """Announcement (History tab feed). Plain text only — no HTML (PLAN 10.2)."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="+"
    )
    body = models.TextField()
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True)
    deleted_at = models.DateTimeField(null=True)  # soft delete, purge after 30 d

    class Meta:
        db_table = "posts"
        constraints = [
            CheckConstraint(
                check=Q(body__length__gte=1) & Q(body__length__lte=4000),
                name="posts_body_length",
            )
        ]
        indexes = [
            # Keyset pagination (created_at, id) for the feed query.
            models.Index(
                fields=["group", "-created_at", "-id"], name="posts_group_created_id"
            )
        ]
