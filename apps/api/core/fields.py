"""UUIDv7 primary keys (RFC 9562).

Why UUIDv7 (PLAN §5.1 / ADR-002):
- 48-bit unix-millisecond prefix -> time-sortable -> B-tree-friendly inserts
  (vs UUIDv4's random scatter), and keyset pagination on (created_at, id)
  works without a separate sequence.
- 12-bit per-millisecond monotonic counter (rand_a) keeps ordering strict even
  for rows created in the same millisecond (bulk inserts).
- IDs are generated in the app layer (not gen_random_uuid()) so the same id
  can be reused offline for idempotent writes (PLAN §7.3).

SECURITY note (RULES.md §4.27): UUIDs are NOT secrets — guessing resistance is
a bonus, authorization is still mandatory.
"""

import secrets
import time
import uuid
from threading import Lock

from django.contrib.postgres.fields import CITextField as DjangoCITextField
from django.db import models
from django.db.models.functions import Length

# Django 5.2 no longer registers the `length` transform on text fields by
# default (and removed expression comparison operators), so `name__length__gt`
# is rejected. The frozen PLAN §5.4 DDL is written as CHECK (length(x) ...),
# so we re-register the maintained transform — this restores the idiomatic
# `Q(name__length__gte=1)` syntax in constraints and queries.
models.CharField.register_lookup(Length)
models.TextField.register_lookup(Length)

_MS_MASK = (1 << 48) - 1
_COUNTER_MASK = 0xFFF  # 12-bit rand_a

# Per-process state; uuid7() may be called concurrently (threads/async).
_lock = Lock()
_state = {"ms": -1, "counter": 0}


def uuid7() -> uuid.UUID:
    """Return a new, strictly increasing (per process) UUIDv7."""
    while True:
        with _lock:
            now_ms = int(time.time() * 1000) & _MS_MASK
            if now_ms == _state["ms"]:
                if _state["counter"] == _COUNTER_MASK:
                    # Overflow: more than 4096 ids in this millisecond.
                    # Spin until the clock advances (real UUIDv7 impls do this).
                    continue
                _state["counter"] += 1
            else:
                _state["ms"] = now_ms
                # Random seed per millisecond: ids within a ms are monotonic
                # but not predictable. secrets module per RULES.md §3.1.16.
                _state["counter"] = secrets.randbelow(0x1000)
            ms, rand_a = _state["ms"], _state["counter"]
            break

    rand_b = secrets.randbits(62)
    # UUID field layout: time_low | time_mid | ver+rand_a | var+rand_b[61:48]
    # | rand_b[47:0]. version=7, RFC 4122 variant=10.
    clock_seq = (0b10 << 14) | ((rand_b >> 48) & 0x3FFF)
    return uuid.UUID(
        fields=(
            (ms >> 16) & 0xFFFFFFFF,
            ms & 0xFFFF,
            0x7000 | rand_a,
            (clock_seq >> 8) & 0xFF,
            clock_seq & 0xFF,
            rand_b & ((1 << 48) - 1),
        )
    )


class UUIDv7Field(models.UUIDField):
    """UUIDField whose default is uuid7() and which never appears in forms."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", uuid7)
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)


class CITextField(DjangoCITextField):
    """citext column — deliberate choice (PLAN §5.1, ADR-001).

    Django 5.2 deprecates its built-in CITextField (fields.E907) in favour of
    ICU collations and the remnant class emits a plain `text` column. We
    intentionally keep citext: the frozen PLAN schema says `citext UK` for
    email, the citext extension is created in migration core/0001_extensions,
    and citext remains fully supported by PostgreSQL. The deprecation
    system-check is therefore disabled here on purpose — do not change this
    without a change request (RULES.md §1.2)."""

    system_check_removed_details = None  # disables fields.E907 on purpose

    def db_type(self, connection) -> str:
        return "citext"
