"""Synthetic data must remain visibly fictional and unavailable to live inputs."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]


def test_demo_loader_returns_only_labeled_input_to_ui():
    from emergency.demo import load_scenario, load_scenarios
    options = load_scenarios()
    assert len(options) == 6
    assert all('SIMULATED' in option.display_label for option in options)
    loaded = load_scenario('demo-rising-water', mode='demo')
    assert loaded.input.text == 'My father is trapped and water is rising'
    assert set(loaded.model_dump()) == {'id', 'display_label', 'input'}
    assert 'expected' not in loaded.model_dump_json()


@pytest.mark.parametrize('loader_name', ['load_scenarios', 'load_households', 'load_failure_states'])
def test_live_mode_cannot_load_synthetic_data(loader_name):
    import emergency.demo as demo
    with pytest.raises(ValueError, match='demo'):
        getattr(demo, loader_name)(mode='live')
    with pytest.raises(ValueError, match='demo'):
        demo.load_scenario('demo-rising-water', mode='live')


def test_fixtures_reject_operational_contacts_and_review_impersonation():
    from emergency.demo import ScenarioFixture
    raw = json.loads((ROOT/'data/emergency_demo/scenarios.json').read_text())['scenarios'][0]
    for mutation in ({'phone': '555-0100'}, {'reviewer': 'Official approval'},
                     {'classification': 'OFFICIAL'}, {'expectation_status': 'APPROVED'}):
        with pytest.raises(ValidationError):
            ScenarioFixture.model_validate({**raw, **mutation})
    with pytest.raises(ValidationError):
        ScenarioFixture.model_validate({**raw, 'input': {**raw['input'], 'dispatch_phone': '555-0100'}})


def test_missing_scenario_does_not_substitute_another_fixture():
    from emergency.demo import load_scenario
    with pytest.raises(ValueError, match='Unknown'):
        load_scenario('not-a-scenario')


def test_demo_uses_same_classifier_as_manual_input():
    from emergency.demo import load_scenario
    from emergency.models import SituationInput
    from emergency.service import evaluate_situation
    scene = load_scenario('demo-rising-water')
    actual = evaluate_situation(scene.input)
    manual = evaluate_situation(SituationInput(text='My father is trapped and water is rising'))
    assert actual.model_dump() == manual.model_dump()
    assert actual.urgency == 'immediate'
    assert set(actual.incident_types) == {'trapped', 'flood'}


def test_profiles_and_failure_states_are_explicitly_synthetic():
    from emergency.demo import load_households, load_failure_states
    profiles = load_households()
    failures = load_failure_states()
    assert len(profiles) == 3
    assert len(failures) == 9
    assert all(p.classification == 'SIMULATED_DEMO' for p in profiles)
    assert all(f.classification == 'SIMULATED_DEMO' for f in failures)
    assert {f.fault for f in failures} == {
        'ai_missing', 'ai_timeout', 'directory_missing', 'stale_source', 'revoked_source',
        'unknown_county', 'database_failure', 'unsupported_dialer', 'no_connection',
    }
