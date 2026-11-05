from recovery.models import RecoveryCase, RecoveryIntake, RecoveryRecords


def test_summary_distinguishes_reported_safety_and_unknown_details():
    from recovery.assessment_summary import summary_items
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Unknown',
        utility_availability={'electricity': None}, temporary_accommodation_status='Staying with others',
        immediate_danger=False, household_recovery_needs=[]))
    records = RecoveryRecords(case_id=case.case_id)
    rows = dict(summary_items(case.intake, records))
    assert rows['Current danger'] == 'No immediate danger reported'
    assert rows['Accommodation'] == 'Staying with others'
    assert rows['Housing type'] == 'Unknown'
    assert rows['Insurer contact'] == 'Unknown'
    assert 'safe' not in rows['Current danger'].lower()
    assert 'Unknown' in rows['Utilities']
    assert rows['Children'] == rows['Adults'] == 'Unknown'


def test_profile_suggestions_are_not_current_facts_or_inferred_counts():
    from recovery.assessment_summary import profile_suggestions
    from domain.contracts import Household
    profile = Household(members=5, mobility_support=True, has_vehicle=False)
    suggestions = profile_suggestions(profile)
    assert suggestions == {'accessibility_needs': ['Mobility assistance'], 'recovery_needs': ['Transportation']}
    assert profile.members == 5
