"""Deterministic discussion notes from confirmed records; no insurance decisions."""
from .models import RecoveryCase, RecoveryRecords


def insurance_discussion_summary(case: RecoveryCase, records: RecoveryRecords) -> str:
    if records.case_id != case.case_id:
        raise ValueError('records do not belong to this case')
    if case.intake.immediate_danger is not False:
        raise ValueError('routine preparation is paused pending the safety assessment')
    known = lambda value: 'Unknown' if value is None or value == '' else str(value)
    household = records.household
    intake = case.intake
    lines = [
        'READYRELIEF - DRAFT INSURANCE DISCUSSION SUMMARY',
        "Prepared for the user's review from confirmed saved reports, not independent verification.",
        'Insurance coverage has not been determined. No insurance claim has been submitted.',
        f'Fictional case ID: {case.case_id}',
        f'Record version: {records.version}',
        '', 'REPORTED INCIDENT AND CIRCUMSTANCES',
        f'Incident type reported: {intake.disaster_type}',
        'Incident cause: Unknown unless explicitly described in the reports below.',
        f'Housing condition reported: {intake.housing_condition}',
        f'Temporary accommodation reported: {intake.temporary_accommodation_status}',
        f'Children: {known(household.children)}', f'Adults: {known(household.adults)}',
        f'Property damage reported: {known(household.reported_property_damage)}',
        'Insurance preparation requested: ' + {True: 'Yes', False: 'No', None: 'Unknown'}[household.wants_insurance_help],
        'Recovery needs reported: ' + (', '.join(intake.household_recovery_needs) or 'Unknown'),
        '', 'USER-REPORTED UTILITIES',
    ]
    for name, available in sorted(intake.utility_availability.items()):
        lines.append(f'{name}: ' + {True: 'Reported available', False: 'Reported unavailable', None: 'Unknown'}[available])
    if not intake.utility_availability:
        lines.append('Utility status: Unknown')
    lines.extend(['Utility restoration does not establish household safety.', '', 'CONFIRMED DAMAGE REPORTS'])
    if not records.damage_records:
        lines.append('No damaged items recorded; damage details are unknown.')
    for item in records.damage_records:
        lines.extend([f'Item / area: {item.item_description}', f'Damage reported: {item.damage_description}',
                      f'Incident date: {known(item.incident_date)}', f'Notes: {known(item.notes)}'])
    lines.extend(['', 'MISSING INSURANCE INFORMATION',
                  'Insurer, policy number, coverage, deductible, repair costs and replacement values: Unknown.',
                  'No photographs are attached through this feature.', '', 'QUESTIONS FOR THE INSURANCE PROVIDER',
                  '- What policy information and documentation should I provide?',
                  '- What deadlines or procedures apply to discussing this reported damage?',
                  '- How does my policy address the reported circumstances and any deductible?',
                  '- What records should I keep before arranging repairs or replacing items?',
                  '', 'This draft does not determine eligibility, coverage, structural safety or damage value.',
                  'ReadyRelief has not contacted an insurer or taken any external action.'])
    return '\n'.join(lines)
