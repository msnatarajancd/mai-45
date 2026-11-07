def test_quote_is_separate_from_accepted_and_committed_work():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.rebuild import check_rebuild, allowed_provider_events
    inputs = load_scenario('chen', 'update')
    result = check_rebuild(inputs, now=inputs.as_of)
    quote = next(i for i in result.items if i.id == 'contractor-1')
    assert quote.state.value == 'yellow'
    assert quote.fields['Interaction'] == 'quote_received'
    assert allowed_provider_events('quote_received') == ['quote_accepted', 'declined']
    assert allowed_provider_events('quote_accepted') == ['work_committed']
    assert allowed_provider_events('work_committed') == []
    inputs.interactions[0].state = 'work_committed'
    committed = next(i for i in check_rebuild(inputs, now=inputs.as_of).items if i.id == 'contractor-1')
    assert committed.state.value == 'green'
    assert inputs.repairs_complete is False


def test_unrated_provider_unknown_availability_and_declined_interaction():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.rebuild import check_rebuild
    from recovery.progress.models import ProviderInteraction
    inputs = load_scenario('chen')
    inputs.household.area = 'Coral demo area'
    inputs.providers = [provider for provider in inputs.providers if provider.id.endswith('-3')]
    result = check_rebuild(inputs, now=inputs.as_of)
    assert result.items
    assert all(i.fields['Rating'] == 'Unrated' for i in result.items)
    assert all(i.state.value == 'unknown' for i in result.items)
    inputs.interactions = [ProviderInteraction(provider_id='contractor-3', state='declined')]
    result = check_rebuild(inputs, now=inputs.as_of)
    declined = next(i for i in result.items if i.id == 'contractor-3')
    assert declined.state.value == 'not_applicable'
    assert not any(a.key.endswith('contractor-3') for a in result.actions)


def test_saved_case_does_not_inherit_fictional_provider_network_and_failures_are_not_green():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.models import SourceMode
    from recovery.progress.rebuild import check_rebuild
    inputs = load_scenario('chen')
    inputs.source_mode = SourceMode.SAVED_CASE
    result = check_rebuild(inputs, now=inputs.as_of)
    assert not result.items and result.state.value == 'unknown'
    inputs = load_scenario('williams', 'update')
    result = check_rebuild(inputs, now=inputs.as_of)
    assert result.execution_state.value == 'failed'
    assert result.state.value == 'unknown'


def test_unknown_catalog_does_not_claim_repairs_are_in_progress():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.rebuild import check_rebuild
    inputs = load_scenario('williams')
    inputs.household.area = 'Coral demo area'
    inputs.providers = [provider for provider in inputs.providers if provider.id.endswith('-3')]
    assert check_rebuild(inputs, now=inputs.as_of).state.value == 'unknown'
