import pytest

from domain.contracts import AppMode, Household
from services.nws_alerts import get_alerts
from services.emergency import route_situation
from services.knowledge import retrieve_guidance
from ui.state import change_context


def test_live_never_returns_simulated_warning():
    result = get_alerts('miami', AppMode.LIVE)
    assert result.status == 'unavailable'
    assert not result.alerts
    assert not result.simulated


def test_demo_warning_has_explicit_provenance():
    result = get_alerts('miami', AppMode.DEMO)
    assert result.simulated
    assert result.status == 'alerts'
    assert all('SIMULATED' in a.headline for a in result.alerts)
    assert result.checked_at is None


def test_unknown_location_does_not_get_miami_fixture():
    assert get_alerts('unknown', AppMode.DEMO).status == 'unavailable'


@pytest.mark.parametrize('text', ["water is rising; we're trapped", 'cannot breathe', 'gas smell', 'help', ''])
def test_unclassified_or_danger_text_keeps_emergency_route(text):
    assert route_situation(text).route == 'emergency'


def test_explicit_resource_category_is_bounded():
    assert route_situation('Transportation').route == 'resources'


def test_knowledge_abstains_without_connected_corpus():
    result = retrieve_guidance('Is my home safe?', 'recover', Household())
    assert result.insufficient_evidence
    assert not result.sources


def test_context_change_clears_stale_results_but_keeps_case():
    state = {'location_id': 'miami', 'mode': AppMode.DEMO, 'alerts': object(), 'guidance': object(), 'case_id': 'saved'}
    change_context(state, 'homestead', AppMode.LIVE)
    assert 'alerts' not in state and 'guidance' not in state
    assert state['case_id'] == 'saved'


def test_same_context_preserves_results():
    state = {'location_id': 'miami', 'mode': AppMode.DEMO, 'alerts': 'cached'}
    change_context(state, 'miami', AppMode.DEMO)
    assert state['alerts'] == 'cached'
