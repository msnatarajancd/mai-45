"""Read-only accepted event views and human descriptions of confirmed changes."""
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from collections.abc import Iterable, Mapping

from .models import RecoveryIntake, RecoveryRecords


@dataclass(frozen=True)
class JourneyEvent:
    event_id: int
    kind: str
    title: str
    detail: str
    occurred_at: str


def normalize_as_of(as_of: date | datetime | None) -> tuple[date, datetime]:
    """Dates include the whole UTC day; aware datetimes preserve their local date."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError('as_of datetime must be timezone-aware')
        return as_of.date(), as_of.astimezone(timezone.utc)
    return as_of, datetime.combine(as_of, time.max, timezone.utc)


def build_timeline(events: Iterable[Mapping | JourneyEvent], *, as_of: date | datetime | None = None) -> tuple[JourneyEvent, ...]:
    """Order actual events by cursor and omit events beyond the supplied instant."""
    _, cutoff = normalize_as_of(as_of)
    accepted = []
    for item in events:
        event = item if isinstance(item, JourneyEvent) else JourneyEvent(**item)
        occurred = datetime.fromisoformat(event.occurred_at)
        if occurred.tzinfo is None or occurred.utcoffset() is None:
            raise ValueError('journey event timestamp must be timezone-aware')
        if occurred <= cutoff:
            accepted.append(event)
    return tuple(sorted(accepted, key=lambda event: event.event_id))


def _reported(value) -> str:
    if value is None or value == [] or value == {}:
        return 'Unknown'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, list):
        return ', '.join(str(item) for item in value)
    if isinstance(value, dict):
        return ', '.join(f'{key}: {_reported(item)}' for key, item in value.items())
    return str(value)


def describe_records_changes(previous: RecoveryRecords, current: RecoveryRecords) -> str:
    changes = []
    for field in ('reported_county',):
        if getattr(previous, field) != getattr(current, field):
            changes.append(f'{field.replace("_", " ").capitalize()}: {_reported(getattr(current, field))}')
    for field in type(current.household).model_fields:
        if getattr(previous.household, field) != getattr(current.household, field):
            changes.append(f'{field.replace("_", " ").capitalize()}: {_reported(getattr(current.household, field))}')
    old_damage = {item.damage_id: item for item in previous.damage_records}
    for item in current.damage_records:
        if old_damage.get(item.damage_id) != item:
            changes.append(f'Damage record confirmed: {item.item_description} — {item.damage_description}')
    return '; '.join(changes) or 'Confirmed reported details updated.'


def describe_intake_changes(previous: RecoveryIntake, current: RecoveryIntake) -> str:
    changes = [f'{field.replace("_", " ").capitalize()}: {_reported(getattr(current, field))}'
               for field in type(current).model_fields if getattr(previous, field) != getattr(current, field)]
    detail = '; '.join(changes) or 'Recovery recommendations reviewed and approved.'
    if previous.utility_availability != current.utility_availability:
        detail += '. Reported availability does not establish household safety or water potability.'
    return detail


def records_change_title(previous: RecoveryRecords, current: RecoveryRecords) -> str:
    if previous.damage_records != current.damage_records:
        return 'Damage information confirmed'
    return 'Household details confirmed'


def intake_change_title(previous: RecoveryIntake, current: RecoveryIntake) -> str:
    if previous.temporary_accommodation_status != current.temporary_accommodation_status:
        return 'Reported accommodation update approved'
    if previous.utility_availability != current.utility_availability:
        return 'Reported utility update approved'
    return 'Situation and plan revision approved'
