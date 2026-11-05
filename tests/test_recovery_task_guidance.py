from recovery.models import RecoveryCase, RecoveryIntake, RecoveryRecords, RecoveryTask, TaskPriority


def context():
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Unknown',
        utility_availability={'electricity': None}, temporary_accommodation_status='No lodging arranged',
        immediate_danger=False, household_recovery_needs=['Temporary housing']))
    return case, RecoveryRecords(case_id=case.case_id, reported_county='Miami-Dade')


def test_housing_task_has_actual_reviewed_source_without_eligibility_claim():
    from recovery.task_guidance import guidance_for_task
    case, records = context()
    task = RecoveryTask(title='Review housing', description='Review information', priority=TaskPriority.HIGH,
        reason_for_recommendation='Reported need', planning_key='housing')
    result = guidance_for_task(task, case, records)
    assert result.citations
    assert all(c.source_id == 'usagov-disaster-housing' for c in result.citations)
    assert all(c.candidate_review and c.source_review for c in result.citations)
    assert any('qualif' in text.lower() for c in result.citations for text in c.safety_caveats)


def test_unknown_context_does_not_infer_geography_from_demo_focus():
    from recovery.task_guidance import guidance_for_task
    case, records = context()
    records.reported_county = None
    task = RecoveryTask(title='Safety', description='', priority=TaskPriority.HIGH,
        reason_for_recommendation='Reported situation', planning_key='safety')
    result = guidance_for_task(task, case, records)
    assert not result.citations
    assert result.retrieval_status == 'INSUFFICIENT_EVIDENCE'


def test_unreviewed_damage_material_is_not_promoted_to_task_evidence():
    from recovery.task_guidance import guidance_for_task
    case, records = context()
    task = RecoveryTask(title='Document damage', description='', priority=TaskPriority.MEDIUM,
        reason_for_recommendation='Reported damage', planning_key='damage')
    result = guidance_for_task(task, case, records)
    assert not any(c.source_id == 'nfip-document-flood-damage' for c in result.citations)


def test_foreign_case_records_rejected():
    import pytest
    from uuid import uuid4
    from recovery.task_guidance import guidance_for_task
    case, records = context()
    records.case_id = uuid4()
    task = RecoveryTask(title='Safety', description='', priority=TaskPriority.HIGH,
        reason_for_recommendation='Reported situation', planning_key='safety')
    with pytest.raises(ValueError):
        guidance_for_task(task, case, records)
