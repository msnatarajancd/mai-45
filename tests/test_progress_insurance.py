def test_preparation_requires_explicit_requirement_links_and_is_not_approval():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.insurance import check_insurance_and_funding
    inputs = load_scenario('rivera', 'later')
    result = check_insurance_and_funding(inputs, now=inputs.as_of)
    assert next(i for i in result.items if i.id == 'preparation').state.value == 'green'
    assert inputs.funding.decision == 'pending'
    for evidence in inputs.evidence:
        evidence.requirement_ids = []
    result = check_insurance_and_funding(inputs, now=inputs.as_of)
    assert next(i for i in result.items if i.id == 'preparation').state.value != 'green'


def test_no_insurance_has_applicable_funding_and_saved_checklist_is_unknown():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.insurance import check_insurance_and_funding
    from recovery.progress.models import SourceMode
    inputs = load_scenario('morgan')
    result = check_insurance_and_funding(inputs, now=inputs.as_of)
    assert next(i for i in result.items if i.id == 'preparation').state.value == 'not_applicable'
    assert next(i for i in result.items if i.id == 'funding').state.value != 'not_applicable'
    inputs = load_scenario('rivera', 'later')
    inputs.source_mode = SourceMode.SAVED_CASE
    result = check_insurance_and_funding(inputs, now=inputs.as_of)
    assert next(i for i in result.items if i.id == 'preparation').state.value == 'unknown'


def test_reported_available_evidence_is_not_saved_or_approved():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.insurance import check_insurance_and_funding
    inputs = load_scenario('chen', 'later')
    for evidence in inputs.evidence:
        evidence.status = 'reported_available'
    result = check_insurance_and_funding(inputs, now=inputs.as_of)
    assert next(i for i in result.items if i.id == 'preparation').state.value == 'yellow'
    assert next(i for i in result.items if i.id == 'insurance-payment').state.value == 'yellow'
