"""Semantic contracts for the curated synthetic demo, including non-success paths."""
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

import pytest

from recovery.progress.fixtures import list_scenarios, load_scenario
from recovery.progress.housing import check_housing
from recovery.progress.insurance import assess_funding, check_insurance_and_funding
from recovery.progress.mcp_server import evaluate
from recovery.progress.models import ExecutionState, SignalState
from recovery.progress.orchestrator import _failed_result, start_run
from recovery.progress.priorities import select_next_actions
from recovery.progress.rebuild import check_rebuild
from recovery.progress.utilities import check_utilities

DATA = Path(__file__).parents[1] / 'recovery' / 'progress' / 'data'
NOTES = json.loads((DATA / 'demo_scenarios.json').read_text())
SPECIALISTS = ('housing', 'utilities', 'insurance', 'rebuild')
CHECKS = (check_housing, check_utilities, check_insurance_and_funding, check_rebuild)
CHECKPOINTS = [(story['id'], checkpoint) for story in NOTES for checkpoint in story['checkpoints']]


def _results(inputs):
    """Use real domain functions and the graph's failure representation, not live services."""
    assert inputs.immediate_danger is False, 'Do not evaluate ordinary specialists at paused checkpoints'
    return tuple(_failed_result(name, inputs) if name in inputs.specialist_failures else check(inputs, now=inputs.as_of)
                 for name, check in zip(SPECIALISTS, CHECKS))


def _items(result):
    return {item.id: item for item in result.items}


def test_curated_catalog_preserves_original_six_and_has_complete_presenter_notes():
    rows = json.loads((DATA / 'scenarios.json').read_text())
    canonical = json.dumps(rows[:6], sort_keys=True, separators=(',', ':')).encode()
    assert sha256(canonical).hexdigest() == 'ea2744042c352bafc3c5df71affeefe752e8b1fa3513d2548b2eccb4cc926798'
    assert [story['id'] for story in NOTES] == [story.id for story in list_scenarios()]
    assert len({story['theme'] for story in NOTES}) == 24
    assert len(CHECKPOINTS) == 72
    for story in NOTES:
        assert story['presenter_goal'] and story['key_lesson']
        assert story['recommended_tool'] in {
            'find_temporary_housing', 'check_utility_health', 'assess_insurance_readiness',
            'assess_funding_gap', 'search_repair_providers',
        }
        assert [checkpoint['id'] for checkpoint in story['checkpoints']] == ['initial', 'update', 'later']
        assert all(checkpoint['talk_track'] for checkpoint in story['checkpoints'])
    assert all(not story['featured'] for story in rows[6:])


@pytest.mark.parametrize('story_id,notes', CHECKPOINTS, ids=[f'{story}-{notes["id"]}' for story, notes in CHECKPOINTS])
def test_presenter_expectations_match_existing_rules_and_pause_gate(story_id, notes):
    inputs = load_scenario(story_id, notes['id'])
    if inputs.immediate_danger is not False:
        assert notes['expected_signals'] == dict.fromkeys(SPECIALISTS, None)
        assert notes['expected_execution'] == dict.fromkeys(SPECIALISTS, 'paused')
        assert notes['expected_primary_action'] is None
        with pytest.raises(ValueError, match='Safety assessment'):
            start_run(inputs)
        for name in SPECIALISTS:
            with pytest.raises(ValueError, match='paused'):
                evaluate(name, inputs)
        return
    results = _results(inputs)
    assert {result.specialist: result.state.value for result in results} == notes['expected_signals']
    assert {result.specialist: result.execution_state.value for result in results} == notes['expected_execution']
    actions = select_next_actions(inputs, results)
    assert (actions[0].key if actions else None) == notes['expected_primary_action']
    assert len(actions) <= 3


def test_new_stories_are_isolated_fictional_records_with_a_fixed_clock_and_valid_links():
    old_clock = datetime(2000, 1, 1, tzinfo=timezone.utc)
    future_clock = datetime(2040, 1, 1, tzinfo=timezone.utc)
    addresses = set()
    for story in list_scenarios()[6:]:
        previous = None
        for checkpoint in story.checkpoints:
            inputs = load_scenario(story.id, checkpoint)
            assert inputs.context_key == f'synthetic:{story.id}'
            assert inputs.source_mode.value == 'synthetic'
            assert inputs.household.county == 'Miami-Dade'
            assert '(fictional)' in inputs.household.address
            assert inputs.household.adults + inputs.household.children == inputs.household.total
            assert previous is None or previous < inputs.as_of
            previous = inputs.as_of
            assert all(observation.provenance.source_mode.value == 'synthetic' for observation in inputs.utilities)
            assert all(record.provenance.source_mode.value == 'synthetic' for record in [*inputs.housing_sites, *inputs.providers])
            assert {interaction.provider_id for interaction in inputs.interactions} <= {provider.id for provider in inputs.providers}
            if inputs.checklist:
                assert {requirement for record in inputs.evidence for requirement in record.requirement_ids} <= {requirement.id for requirement in inputs.checklist.requirements}
            if inputs.immediate_danger is False:
                assert check_utilities(inputs, now=old_clock) == check_utilities(inputs, now=future_clock)
        addresses.add(inputs.household.address)
    assert len(addresses) == 18
    inputs = load_scenario('rodriguez', 'update')
    inputs.housing_sites[0].available_units = 999
    assert all(site.available_units == 0 for site in load_scenario('rodriguez').housing_sites)


def test_eight_person_household_requires_two_rooms_or_eight_spaces_and_stays_unarranged():
    initial = load_scenario('santos')
    assert check_housing(initial, now=initial.as_of).items == []
    update = load_scenario('santos', 'update')
    result = check_housing(update, now=update.as_of)
    items = _items(result)
    assert items['hotel-6'].fields['Units required'] == '2 rooms'
    assert items['hotel-6'].fields['Nightly household cost'] == 'USD 90.00'
    assert items['school-6'].fields['Units required'] == '8 spaces'
    assert 'church-11' not in items  # Plenty of space does not override staying together.
    assert result.state is SignalState.RED
    assert all(item.state is SignalState.GREEN for item in result.items)


def test_pets_transport_budget_accessibility_and_capacity_are_real_filters():
    for story in ['patel', 'rodriguez']:
        initial = load_scenario(story)
        update = load_scenario(story, 'update')
        assert check_housing(initial, now=initial.as_of).items == []
        result = check_housing(update, now=update.as_of)
        assert result.items and result.state is SignalState.RED
        later = load_scenario(story, 'later')
        assert check_housing(later, now=later.as_of).state is SignalState.GREEN
    initial = load_scenario('okafor')
    housing = _items(check_housing(initial, now=initial.as_of))
    assert set(housing) == {'school-5'} and housing['school-5'].state is SignalState.UNKNOWN
    providers = _items(check_rebuild(initial, now=initial.as_of))
    assert set(providers) == {'contractor-5'} and providers['contractor-5'].state is SignalState.UNKNOWN


def test_area_reports_potability_applicability_and_conflicts_remain_separate():
    cases = [
        ('thompson', 'initial', 'electricity', SignalState.UNKNOWN),
        ('thompson', 'update', 'electricity', SignalState.YELLOW),
        ('garcia', 'update', 'water', SignalState.YELLOW),
        ('lopez', 'update', 'gas', SignalState.UNKNOWN),
        ('lopez', 'later', 'gas', SignalState.NOT_APPLICABLE),
        ('nguyen', 'initial', 'electricity', SignalState.UNKNOWN),
        ('nguyen', 'update', 'electricity', SignalState.GREEN),
        ('nguyen', 'update', 'water', SignalState.UNKNOWN),
    ]
    for story, checkpoint, service, expected in cases:
        inputs = load_scenario(story, checkpoint)
        item = _items(check_utilities(inputs, now=inputs.as_of))[service]
        assert item.state is expected
    inputs = load_scenario('garcia', 'update')
    assert _items(check_utilities(inputs, now=inputs.as_of))['water'].fields['Potability'] == 'Not confirmed'


def test_freshness_changes_candidate_signals_without_reserving_accommodation():
    initial = load_scenario('johnson')
    update = load_scenario('johnson', 'update')
    initial_housing = check_housing(initial, now=initial.as_of)
    update_housing = check_housing(update, now=update.as_of)
    assert all(item.state is SignalState.UNKNOWN for item in initial_housing.items)
    assert all(item.state is SignalState.GREEN for item in update_housing.items)
    assert initial_housing.state is update_housing.state is SignalState.RED
    assert check_rebuild(initial, now=initial.as_of).state is SignalState.UNKNOWN
    assert check_rebuild(update, now=update.as_of).state is SignalState.YELLOW


def test_received_payment_is_never_implicitly_allocated_and_uninsured_funding_still_applies():
    singh = [load_scenario('singh', checkpoint) for checkpoint in ['initial', 'update', 'later']]
    assessments = [assess_funding(inputs, now=inputs.as_of) for inputs in singh]
    assert [assessment.available_allocation for assessment in assessments] == [Decimal(1000), Decimal(1000), Decimal(5000)]
    assert [assessment.exact_gap for assessment in assessments] == [Decimal(4000), Decimal(4000), Decimal(0)]
    payment_states = [_items(check_insurance_and_funding(inputs, now=inputs.as_of))['insurance-payment'].state for inputs in singh]
    assert payment_states == [SignalState.YELLOW, SignalState.GREEN, SignalState.GREEN]
    martinez = load_scenario('martinez')
    items = _items(check_insurance_and_funding(martinez, now=martinez.as_of))
    assert items['preparation'].state is items['insurance-payment'].state is SignalState.NOT_APPLICABLE
    assert items['funding'].state is SignalState.RED
    assert items['funding'].fields['Exact stage gap'] == 'USD 3000.00'


def test_currency_stage_and_spending_contracts_are_demonstrated_without_guessing():
    for story in ['robinson', 'lewis']:
        inputs = load_scenario(story)
        assert assess_funding(inputs, now=inputs.as_of).state is SignalState.UNKNOWN
    mixed_spend = load_scenario('robinson', 'update')
    assert assess_funding(mixed_spend, now=mixed_spend.as_of).state is SignalState.UNKNOWN
    lewis = load_scenario('lewis', 'later')
    assessment = assess_funding(lewis, now=lewis.as_of)
    assert (assessment.remaining_cost, assessment.available_allocation, assessment.exact_gap) == (Decimal(1800), Decimal(1800), Decimal(0))
    brown = load_scenario('brown', 'later')
    assert assess_funding(brown, now=brown.as_of).exact_gap == Decimal(3000)
    assert brown.reviewed_tasks[0].completed
    assert not any(action.task_id == 'brown-cleanup' for action in select_next_actions(brown, _results(brown)))


def test_saved_photo_needs_a_link_and_reported_available_is_not_saved():
    states = []
    for checkpoint in ['initial', 'update', 'later']:
        inputs = load_scenario('wilson', checkpoint)
        states.append(_items(check_insurance_and_funding(inputs, now=inputs.as_of))['requirement:photos'].state)
    assert states == [SignalState.RED, SignalState.YELLOW, SignalState.GREEN]
    initial = load_scenario('wilson')
    photo = next(record for record in initial.evidence if record.id == 'photos-record')
    assert photo.status == 'saved' and photo.requirement_ids == []


def test_decline_quotes_and_commitments_do_not_claim_repair_completion():
    initial = load_scenario('davis')
    result = check_rebuild(initial, now=initial.as_of)
    assert _items(result)['contractor-8'].state is SignalState.NOT_APPLICABLE
    assert all(action.key != 'rebuild:contractor-8' for action in result.actions)
    update = load_scenario('davis', 'update')
    assert check_rebuild(update, now=update.as_of).state is SignalState.YELLOW
    later = load_scenario('davis', 'later')
    assert check_rebuild(later, now=later.as_of).state is SignalState.GREEN
    assert later.repairs_complete is False


def test_new_danger_pauses_without_erasing_completed_repairs_and_retry_is_explicit():
    inputs = [load_scenario('fernandez', checkpoint) for checkpoint in ['initial', 'update', 'later']]
    assert [row.immediate_danger for row in inputs] == [False, True, False]
    assert all(row.repairs_complete and row.reviewed_tasks[0].completed for row in inputs)
    with pytest.raises(ValueError, match='paused'):
        evaluate('utilities', inputs[1])
    assert _items(check_utilities(inputs[2], now=inputs[2].as_of))['electricity'].state is SignalState.YELLOW


def test_partial_failure_has_no_current_utility_actions_and_remaining_action_discloses_it():
    inputs = load_scenario('campbell', 'update')
    with pytest.raises(ValueError, match='unavailable'):
        evaluate('utilities', inputs)
    results = _results(inputs)
    failed = next(result for result in results if result.specialist == 'utilities')
    assert failed.execution_state is ExecutionState.FAILED
    assert failed.observed_at is None and failed.actions == [] and failed.items == []
    actions = select_next_actions(inputs, results)
    assert actions and all('Partial check: utilities' in action.reason for action in actions)
    assert not any(action.key.startswith('utilities:') for action in actions)
    restored = load_scenario('campbell', 'later')
    result = evaluate('utilities', restored)['result']
    assert result['execution_state'] == 'complete' and result['state'] == 'green'
