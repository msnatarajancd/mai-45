"""Policy regressions: a missed present threat or global negation breaks these."""
import pytest
from pydantic import ValidationError

from domain.contracts import IncidentType, RouteResult
from emergency.models import SituationInput
from emergency.service import evaluate_situation, screen_report
from services.emergency import route_situation


@pytest.mark.parametrize('text,types', [
    ('My father is trapped and water is rising', {'trapped', 'flood'}),
    ('We are stuck in the house as floodwater comes in', {'trapped', 'flood'}),
    ('My child is not breathing', {'medical'}),
    ('She cannot breathe', {'medical'}),
    ('He is unconscious', {'medical'}),
    ('Someone is drowning', {'medical', 'flood'}),
    ('I need an ambulance', {'medical'}),
    ('There is a strong gas smell', {'utility_hazard'}),
    ('The house is on fire', {'unknown'}),
    ('A power line is down in the street', {'utility_hazard'}),
    ('We are not trapped, but my child is not breathing', {'medical'}),
    ('We may need transport next week, but the water is rising now', {'flood'}),
    ('Yesterday I was safe; now I smell gas', {'utility_hazard'}),
    ('How do I open Recover? My mother is unconscious', {'medical'}),
    ('No immediate danger was reported earlier, but we are trapped now', {'trapped'}),
    ('I am trapped now and need transport next week', {'trapped', 'evacuation_support'}),
    ('My child is barely breathing', {'medical'}),
    ('My mom will not wake up', {'medical'}),
    ('The water is rapidly rising', {'flood'}),
    ('Floodwater is coming through the door', {'flood'}),
    ('We cannot leave the house because of flooding', {'trapped', 'flood'}),
])
def test_present_threats_interrupt_and_queue_report(text, types):
    result = evaluate_situation(SituationInput(text=text))
    assert result.route == 'emergency'
    assert result.urgency == 'immediate'
    assert types <= set(result.incident_types)
    assert result.interrupt_routine and result.persist_danger
    assert result.reason_codes and result.policy_version


@pytest.mark.parametrize('text', [
    'How can I plan in case floodwater traps us?',
    'What should I prepare if I am trapped next week?',
    'We were trapped yesterday and everyone is safe now',
    'We are not trapped',
    'There is no gas leak',
    'No one is unconscious',
    'The water is not rising',
    'My child is breathing normally, not unconscious',
    'What do I do if someone is not breathing?',
    'How can I prepare in case someone stops breathing?',
    'I am not in immediate danger',
    'If the water is rising and my father is trapped, what should I do?',
    'What if I cannot call 911 and I am trapped?',
])
def test_clear_negation_history_and_hypothetical_do_not_persist(text):
    result = evaluate_situation(SituationInput(text=text))
    assert result.urgency == 'ordinary'
    assert not result.interrupt_routine and not result.persist_danger


def test_future_accessible_transport_is_planning_not_dispatch():
    result = route_situation('We may need accessible evacuation transport next week')
    assert result.urgency == 'ordinary' and result.route == 'resources'
    assert result.incident_types == [IncidentType.EVACUATION_SUPPORT]
    assert 'transportation' in result.resource_categories
    assert not result.persist_danger


def test_today_transport_needs_urgent_assistance_without_claiming_immediate_danger():
    result = route_situation('We need accessible evacuation transport today; no immediate danger reported')
    assert result.urgency == 'urgent' and result.route == 'resources'
    assert not result.interrupt_routine and not result.persist_danger


def test_water_near_electricity_keeps_uncertainty_without_persisting_unresolved_report():
    result = route_situation("Water is near the electrical panel; I don't know if it's dangerous")
    assert result.urgency == 'uncertain' and result.route == 'emergency'
    assert {'flood', 'utility_hazard'} <= set(result.incident_types)
    assert result.interrupt_routine and not result.persist_danger


@pytest.mark.parametrize('text', ['', 'help', 'something is wrong', None, {'bad': 'shape'}])
def test_malformed_or_unclear_help_stays_available_without_inventing_incident(text):
    result = route_situation(text)
    assert result.urgency == 'uncertain' and result.route == 'emergency'
    assert result.incident_types == [IncidentType.UNKNOWN]
    assert result.interrupt_routine and not result.persist_danger


def test_explicit_danger_overrides_selected_category():
    result = evaluate_situation(SituationInput(category='evacuation_support', immediate_danger=True))
    assert result.urgency == 'immediate' and result.persist_danger


def test_current_threat_overrides_future_selected_category():
    result = evaluate_situation(SituationInput(category='evacuation_support', text='For next week I need a ride. My child cannot breathe'))
    assert result.urgency == 'immediate' and result.persist_danger
    assert 'medical' in result.incident_types


def test_current_threat_retains_future_assistance_type_but_excludes_negated_threat():
    result = route_situation('We are not trapped. We need transport next week, but water is rising now')
    assert set(result.incident_types) == {'evacuation_support', 'flood'}
    assert result.urgency == 'immediate'


@pytest.mark.parametrize('text', ['open Recover', 'How do I update my household?', 'How does the immediate danger button work?', 'hello', 'What sources are reviewed?'])
def test_product_support_does_not_create_a_danger_report(text):
    assert screen_report(text, entrypoint='assistant') is None


def test_unclear_help_in_report_screen_is_not_a_safety_clearance():
    assert screen_report('help', entrypoint='respond').interrupt_routine


def test_unsupported_language_is_explicit_and_never_assumed_safe():
    result = evaluate_situation(SituationInput(text='Necesito ayuda', language='es'))
    assert result.urgency == 'uncertain' and result.interrupt_routine
    assert 'unsupported_language' in result.reason_codes
    assert not result.persist_danger


@pytest.mark.parametrize('text', [
    'He might be unconscious',
    'I am not sure if my child is breathing',
    "I don't know whether my father is breathing",
    'I am not sure whether there is a gas leak',
])
def test_potential_current_life_threat_is_uncertain_not_ordinary(text):
    result = screen_report(text, entrypoint='assistant')
    assert result is not None and result.interrupt_routine
    assert result.urgency == 'uncertain' and not result.persist_danger


def test_uncertainty_in_another_clause_does_not_downgrade_definite_danger():
    result = route_situation('I am unsure about transport, but my child is not breathing')
    assert result.urgency == 'immediate' and result.persist_danger


@pytest.mark.parametrize('separator', ['\n', '\r\n', ': ', '; ', '. '])
@pytest.mark.parametrize('danger,expected_type', [
    ('My child is not breathing', 'medical'),
    ('The water is rising', 'flood'),
    ('My father is trapped', 'trapped'),
])
def test_report_boundaries_prevent_future_transport_from_qualifying_present_threat(separator, danger, expected_type):
    result = route_situation(danger + separator + 'We need accessible transportation next week')
    assert result.route == 'emergency' and result.urgency == 'immediate'
    assert result.interrupt_routine and result.persist_danger
    assert expected_type in result.incident_types


@pytest.mark.parametrize('text', [
    'Planning transport but water is near the electrical panel',
    'Water is near the electrical panel; we are planning transport',
    'We need evacuation transport next week, but I have a medical concern now',
    'I have a medical concern now. We need evacuation transport next week',
    'We need transport next week\nWater is near the electrical panel',
    'I have a medical concern now: please give transport information for next week',
    'How do I plan for transport? Water is near the electrical panel',
])
def test_current_ambiguous_hazard_wins_over_planning_in_another_clause(text):
    result = screen_report(text, entrypoint='assistant')
    assert result is not None
    assert result.route == 'emergency' and result.urgency == 'uncertain'
    assert result.interrupt_routine and not result.persist_danger


@pytest.mark.parametrize('text', [
    'How can I plan for water near electrical equipment? We need transport next week',
    'We need transport next week. How can I prepare for a medical emergency?',
    'We have no medical concern now; we need transport next week',
])
def test_clause_scoping_retains_explicit_planning_and_negation_without_current_danger(text):
    result = route_situation(text)
    assert result.route == 'resources' and result.urgency == 'ordinary'
    assert not result.interrupt_routine and not result.persist_danger


def test_contracts_reject_unknown_enum_and_extra_operational_fields():
    with pytest.raises(ValidationError):
        SituationInput(category='dispatch', responders_dispatched=True)
    with pytest.raises(ValidationError):
        RouteResult(route='dispatch', urgency='low', message='sent')
