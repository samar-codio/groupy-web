"""UUIDv7 contract tests (ADR-002): version 7, RFC 4122 variant, per-process
monotonicity, and B-tree-friendly time sortability — the properties keyset
pagination depends on.
"""

import pytest

from core.fields import uuid7


def test_version_7():
    u = uuid7()
    assert str(u)[14] == "7"  # the version nibble


def test_rfc4122_variant():
    u = uuid7()
    assert str(u)[19] in "89ab"


def test_16_bytes():
    assert len(uuid7().bytes) == 16


def test_unique_under_burst():
    seen = {uuid7() for _ in range(20_000)}
    assert len(seen) == 20_000


def test_monotonic_prefix_within_process():
    """The 48-bit ms + 12-bit counter prefix must never decrease within one
    process — this is what makes (created_at, id) keyset pagination stable."""
    ids = [uuid7() for _ in range(10_000)]
    prefixes = [u.int >> 68 for u in ids]
    assert all(b >= a for a, b in zip(prefixes, prefixes[1:]))


def test_counter_rollover_spins_to_next_ms():
    """More than 4096 ids in the same millisecond must roll into the next ms
    instead of producing duplicates (the spin loop in core/fields.py)."""
    ids = [uuid7() for _ in range(4100)]
    assert len({u.int >> 68 for u in ids}) > 1  # crossed at least one ms
    assert len(ids) == len(set(ids))  # and never a duplicate


@pytest.mark.django_db
def test_database_pk_is_uuid7():
    """A freshly saved row's PK must be a time-sortable UUIDv7."""
    from accounts.models import User

    user = User.objects.create_user(email="uuid7@example.test", name="UUIDv7")
    assert str(user.id)[14] == "7"


@pytest.mark.django_db
def test_bulk_created_ids_strictly_increasing():
    """30k bulk-inserted ids must be strictly time-ordered in the same
    process — the seed command relies on this (PLAN §5.6, 100k rows)."""
    from accounts.models import User

    users = [User(email=f"bulk{i}@example.test", name="B") for i in range(30_000)]
    User.objects.bulk_create(users, batch_size=2_000)
    ids = [u.id.int for u in users]
    assert all(b > a for a, b in zip(ids, ids[1:]))
