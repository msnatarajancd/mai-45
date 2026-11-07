import pytest


def test_all_authored_stories_have_three_isolated_checkpoints_and_complete_catalogs():
    from recovery.progress.fixtures import list_scenarios, load_scenario, _read
    stories = list_scenarios()
    assert len(stories) == 24 and sum(s.featured for s in stories) == 3
    assert len(_read('housing.json')) == 48
    assert len(_read('providers.json')) == 60
    for story in stories:
        assert story.checkpoints == ['initial', 'update', 'later']
        for checkpoint in story.checkpoints:
            inputs = load_scenario(story.id, checkpoint)
            assert inputs.source_mode.value == 'synthetic'
            assert len(inputs.housing_sites) <= 48
            assert len(inputs.providers) <= 60
            assert {u.service for u in inputs.utilities} == {'electricity', 'water', 'gas'}
    initial = load_scenario('rivera')
    initial.household.label = 'Changed locally'
    assert load_scenario('rivera').household.label == 'Rivera household'
    assert load_scenario('rivera').as_of < load_scenario('rivera', 'later').as_of


def test_incomplete_story_does_not_invent_session_defaults_or_checklist():
    from recovery.progress.fixtures import load_scenario, _load_checklists
    inputs = load_scenario('williams')
    assert inputs.household.total is None
    assert inputs.household.address is None
    assert inputs.household.housing_budget is None
    assert inputs.checklist is None
    assert len(_load_checklists()) == 8
    with pytest.raises(ValueError):
        load_scenario('saved-case')
    with pytest.raises(ValueError):
        load_scenario('rivera', 'tomorrow')


def test_featured_displaced_household_has_known_capacity_and_uncertain_alternatives():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    inputs = load_scenario('rivera')
    result = check_housing(inputs, now=inputs.as_of)
    categories = {'hotel', 'church', 'school', 'official shelter'}
    assert {item.category for item in result.items if item.fields['Available units'] != 'Unknown'} == categories
    assert {item.category for item in result.items if item.fields['Available units'] == 'Unknown'} == categories
    assert result.state.value == 'red'  # Options do not establish accommodation secured.


def test_stories_distinguish_received_money_home_progress_and_pending_payment():
    from recovery.progress.fixtures import load_scenario
    alvarez = load_scenario('alvarez')
    assert alvarez.funding.expected_payment.amount == 6000
    assert alvarez.funding.exact_allocation.amount == 500
    chen = load_scenario('chen', 'later')
    assert chen.home_returned is True and chen.repairs_complete is True
    assert chen.funding.received_payment is None
    morgan = load_scenario('morgan')
    assert morgan.insurance_applicable is False
    baptiste = load_scenario('baptiste', 'update')
    assert baptiste.accommodation_status == 'arranged'
    assert baptiste.household.accessibility is True


def test_alvarez_story_starts_with_accommodation_and_essential_needs_met_so_funding_is_next():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    from recovery.progress.utilities import check_utilities
    from recovery.progress.insurance import check_insurance_and_funding
    from recovery.progress.rebuild import check_rebuild
    from recovery.progress.priorities import select_next_actions
    inputs = load_scenario('alvarez')
    results = tuple(check(inputs, now=inputs.as_of) for check in (check_housing, check_utilities, check_insurance_and_funding, check_rebuild))
    assert select_next_actions(inputs, results)[0].key == 'funding:confirm-next-stage'


def test_chen_initial_paid_costs_lead_to_preparation_while_rivera_needs_housing():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    from recovery.progress.utilities import check_utilities
    from recovery.progress.insurance import check_insurance_and_funding
    from recovery.progress.rebuild import check_rebuild
    from recovery.progress.priorities import select_next_actions
    actions = []
    for story in ['chen', 'rivera']:
        inputs = load_scenario(story)
        results = tuple(check(inputs, now=inputs.as_of) for check in (check_housing, check_utilities, check_insurance_and_funding, check_rebuild))
        actions.append(select_next_actions(inputs, results)[0].key)
    assert actions == ['insurance:prepare-evidence', 'housing:confirm-accommodation']
