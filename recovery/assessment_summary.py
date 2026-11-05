"""Plain reported facts for assessment review and the continuing dashboard."""
from domain.contracts import Household
from recovery.models import RecoveryIntake, RecoveryRecords


def summary_items(intake: RecoveryIntake, records: RecoveryRecords) -> list[tuple[str, str]]:
    h = records.household
    return [
        ('Current danger', {False: 'No immediate danger reported', True: 'Immediate danger reported', None: 'Not assessed'}[intake.immediate_danger]),
        ('Incident', intake.disaster_type), ('Reported housing condition', intake.housing_condition),
        ('Accommodation', intake.temporary_accommodation_status), ('Housing type', h.housing_type or 'Unknown'),
        ('Utilities', ', '.join(f'{name.capitalize()}: '+{None: 'Unknown', True: 'Reported available', False: 'Reported unavailable'}[value]
                              for name, value in intake.utility_availability.items()) or 'Unknown'),
        ('Needs you reported', ', '.join(intake.household_recovery_needs) or 'None selected'),
        ('Accessibility needs', ', '.join(h.accessibility_needs) or 'Not reported'),
        ('Children', str(h.children) if h.children is not None else 'Unknown'),
        ('Adults', str(h.adults) if h.adults is not None else 'Unknown'),
        ('Reported property damage', h.reported_property_damage or 'Not reported'),
        ('Insurance preparation requested', {None: 'Unknown', True: 'Yes', False: 'No'}[h.wants_insurance_help]),
        ('Insurer contact', h.insurer_contact_status),
        ('County', records.reported_county or 'Unknown'),
        ('Reported incident date', records.incident_date.isoformat() if records.incident_date else 'Unknown'),
        ('Your next check-in target', records.next_check_in_date.isoformat() if records.next_check_in_date else 'Not chosen'),
        ('Confirmed damage records', str(len(records.damage_records))),
    ] + [(f'Damage item {i}', f'{item.item_description}: {item.damage_description}'
          + (f' · Incident date: {item.incident_date}' if item.incident_date else '')
          + (f' · Notes: {item.notes}' if item.notes else ''))
         for i, item in enumerate(records.damage_records, 1)]


def profile_suggestions(profile: Household) -> dict[str, list[str]]:
    """Optional suggestions only; total profile size cannot establish current adults."""
    return {'accessibility_needs': ['Mobility assistance'] if profile.mobility_support else [],
            'recovery_needs': ['Transportation'] if not profile.has_vehicle else []}
