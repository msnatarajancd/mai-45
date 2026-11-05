"""Display-only freshness policy; never fetches, mutates or establishes safety.

Matches m2_guardian.explanation's inclusive five-minute snapshot window and
exclusive earliest end/expiry. Preserves the original optional ends_at separately
from required expires_at; no claim about cancellations since the last lookup.
"""
from datetime import datetime, timedelta, timezone


MAX_SNAPSHOT_AGE = timedelta(minutes=5)


def utc_now():
    return datetime.now(timezone.utc)


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError('missing timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('timestamp requires a timezone')
    return parsed


def snapshot_staleness(result):
    """Return a warning reason, or None; None is not a current-safety claim."""
    if result is None or result.simulated or result.status not in {'alerts', 'none'}:
        return None
    now = utc_now()
    try:
        age = now - _timestamp(result.checked_at)
        if age < timedelta(0):
            return 'The lookup timestamp is in the future; freshness cannot be verified.'
        if age > MAX_SNAPSHOT_AGE:
            return 'The lookup is more than five minutes old.'
        if result.status == 'alerts':
            if not result.alerts:
                return 'The saved alert result has no alert records; freshness cannot be verified.'
            for alert in result.alerts:
                expiry = _timestamp(alert.expires_at)
                ends_at = getattr(alert, 'ends_at', None)
                end = _timestamp(ends_at) if ends_at is not None else expiry
                if min(expiry, end) <= now:
                    return 'At least one saved alert has ended or expired.'
    except (ValueError, TypeError, OverflowError):
        return 'Lookup or alert end/expiry metadata is missing or invalid; freshness cannot be verified.'
    return None
