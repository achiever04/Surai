"""
Timezone-safe UTC datetime helper.

All database columns use `TIMESTAMP WITHOUT TIME ZONE`, so every datetime
that touches the DB **must** be a naive (no tzinfo) UTC datetime.

Using `datetime.utcnow()` works but is deprecated since Python 3.12.
This module provides `utc_now()` as a drop-in replacement that is both
non-deprecated AND produces naive UTC datetimes compatible with asyncpg.
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime.

    Equivalent to the deprecated `datetime.utcnow()` but uses the
    recommended `datetime.now(timezone.utc)` internally.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
