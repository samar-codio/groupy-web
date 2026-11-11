"""Files module (PLAN §5.4): files, folders (folders reserved for later).

Upload flow (PLAN §10.3, implemented S11): intent → presigned PUT (private
bucket) → confirm (HEAD + magic-byte sniff) → status=ready. storage_key is
always SERVER-GENERATED (uuid), never the user's filename. Serve as
`Content-Disposition: attachment` + nosniff from the storage domain.
"""

from django.db import models
from django.db.models import CheckConstraint, Q
from django.db.models.functions import Lower
from django.contrib.postgres.indexes import GinIndex, OpClass

from core.fields import UUIDv7Field


class FilePurpose(models.TextChoices):
    GROUP_FILE = "group_file"
    AVATAR = "avatar"
    FEEDBACK = "feedback"


class FileStatus(models.TextChoices):
    PENDING_UPLOAD = "pending_upload"
    READY = "ready"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


class Folder(models.Model):
    """Nested folders (later feature; table reserved). Depth limit 5 is
    enforced app-side when the feature ships."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey("groups.Group", on_delete=models.CASCADE, related_name="folders")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, related_name="children"
    )
    name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "folders"
        constraints = [
            CheckConstraint(
                check=Q(name__length__gte=1) & Q(name__length__lte=120),
                name="folders_name_length",
            )
        ]


class File(models.Model):
    """One stored file. purpose disambiguates group_file/avatar/feedback.
    status: pending_upload → ready / quarantined; deleted = soft delete
    (job removes the R2 object — PLAN 5.5)."""

    id = UUIDv7Field(primary_key=True)
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, null=True, related_name="files"
    )
    uploaded_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="uploads"
    )
    post = models.ForeignKey(
        "groups.Post", on_delete=models.SET_NULL, null=True, related_name="files"
    )
    task = models.ForeignKey(
        "tasks.Task", on_delete=models.SET_NULL, null=True, related_name="files"
    )
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, null=True, related_name="files"
    )
    purpose = models.TextField(choices=FilePurpose.choices)
    # SECURITY: server-generated key like groups/{groupId}/{uuidv7} — never a
    # user filename (path traversal is impossible by construction, PLAN 10.2).
    storage_key = models.TextField(unique=True)
    filename = models.TextField()  # display only — data, not markup
    mime_declared = models.TextField()  # what the client claimed
    mime_detected = models.TextField(null=True)  # what magic bytes said
    size_bytes = models.BigIntegerField()
    sha256 = models.TextField(null=True)
    status = models.TextField(choices=FileStatus.choices, default=FileStatus.PENDING_UPLOAD)
    scan_status = models.TextField(null=True)  # ClamAV worker (post-MVP)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "files"
        constraints = [
            CheckConstraint(check=Q(purpose__in=FilePurpose.values), name="files_purpose_valid"),
            CheckConstraint(check=Q(status__in=FileStatus.values), name="files_status_valid"),
            CheckConstraint(check=Q(size_bytes__gte=0), name="files_size_nonnegative"),
            CheckConstraint(
                check=Q(filename__length__gte=1) & Q(filename__length__lte=255),
                name="files_filename_length",
            ),
        ]
        indexes = [
            models.Index(fields=["group", "-created_at"], name="files_group_created"),
            # Search across my groups' files: trigram GIN on lower(filename)
            # accelerates LIKE '%query%' (PLAN §5.4 "Other indexes").
            GinIndex(
                OpClass(Lower("filename"), name="gin_trgm_ops"),
                name="files_filename_trgm",
            ),
        ]
