"""CAP-04 user-visible behavior; no real calling or provider requests."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'emergency.sqlite3'))
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    return AppTest.from_file(APP, default_timeout=15).run()


def button(app, label):
    return next(b for b in app.button if b.label == label)


def open_help(app):
    app.session_state['page'] = 'Respond'
    return app.run()


def all_text(app):
    return '\n'.join(str(x.value) for kind in ('markdown', 'caption', 'info', 'warning', 'error')
                     for x in getattr(app, kind))


@pytest.mark.parametrize('page', ['Home', 'Protect', 'Respond', 'Recover', 'Household', 'Evidence', 'Assistant'])
def test_one_action_strip_on_every_page_without_ai(app, page):
    app.session_state['page'] = page
    app.run()
    assert not app.exception
    calls = [b for b in app.get('link_button') if b.label == 'Call 911']
    assert len(calls) == 1
    assert calls[0].proto.url == 'tel:911'
    assert len([b for b in app.button if b.label == "I Can't Call 911"]) == 1
    assert 'use a phone to dial 911' in all_text(app)


def test_help_input_is_optional_and_not_default_transportation(app):
    open_help(app)
    assert next(r for r in app.radio if r.label == 'Situation type (optional)').value is None
    assert next(t for t in app.text_area if t.label == 'Describe the situation (optional)').value == ''
    assert not app.session_state['rr_emergency']


def test_report_trapped_water_interrupts_without_another_question(app):
    open_help(app)
    next(t for t in app.text_area if t.label == 'Describe the situation (optional)').input(
        'My father is trapped and water is rising')
    button(app, 'Show assistance options').click().run()
    assert not app.exception
    assert app.session_state['rr_emergency'] is True
    decision = app.session_state['rr_emergency_decision']
    assert decision['urgency'] == 'immediate'
    assert set(decision['incident_types']) == {'flood', 'trapped'}
    assert not app.chat_input
    assert len([b for b in app.get('link_button') if b.label == 'Call 911']) == 1


def test_future_transport_shows_official_planning_links_not_pickup(app):
    open_help(app)
    next(s for s in app.selectbox if s.label == 'Where is help needed?').select('Miami-Dade County, Florida').run()
    next(t for t in app.text_area if t.label == 'Describe the situation (optional)').input(
        'We may need accessible evacuation transport next week')
    button(app, 'Show assistance options').click().run()
    assert not app.exception
    assert not app.session_state['rr_emergency']
    assert app.session_state['rr_route_result']['urgency'] == 'ordinary'
    links = [x.proto.url for x in app.get('link_button')]
    assert any('faq1598023863344518' in url for url in links)
    assert 'No pickup' in all_text(app)
    assert 'review' in all_text(app).lower()


def test_cannot_call_requires_explicit_incident_geography_for_county_links(app):
    button(app, "I Can't Call 911").click().run()
    assert not app.exception
    assert app.session_state['rr_alternative'] is True
    assert not app.session_state['rr_emergency']
    assert not any('mdso.com/text-911' in x.proto.url for x in app.get('link_button'))
    next(s for s in app.selectbox if s.label == 'Where is help needed?').select('Miami-Dade County, Florida').run()
    assert any('mdso.com/text-911' in x.proto.url for x in app.get('link_button'))
    button(app, "I Can't Call 911").click().run()
    assert app.session_state['rr_alternative'] is True


def test_no_connection_is_not_a_send_or_rescue_action(app):
    button(app, "I Can't Call 911").click().run()
    next(r for r in app.radio if r.label == 'What makes calling difficult? (optional)').set_value(
        'No usable connection').run()
    assert 'cannot restore cellular service' in all_text(app)
    assert not any('sms:' in x.proto.url for x in app.get('link_button'))
    assert not any('Send' in b.label or 'Dispatch' in b.label for b in app.button)
    assert not app.session_state.get('rr_pending_danger', [])


def test_directory_failure_retains_controls_and_honest_status(app, monkeypatch):
    from services import resources
    monkeypatch.setattr(resources, 'lookup_resources', lambda *a, **k: (_ for _ in ()).throw(OSError('unavailable')),
                        raising=False)
    open_help(app)
    next(s for s in app.selectbox if s.label == 'Where is help needed?').select('Miami-Dade County, Florida').run()
    next(t for t in app.text_area if t.label == 'Describe the situation (optional)').input(
        'We may need accessible evacuation transport next week')
    button(app, 'Show assistance options').click().run()
    assert not app.exception
    assert any(b.label == 'Call 911' for b in app.get('link_button'))
    assert 'unavailable' in all_text(app).lower()


def test_live_mode_never_exposes_synthetic_scenario_selector(app):
    from domain.contracts import AppMode
    app.session_state['mode'] = AppMode.LIVE
    open_help(app)
    assert not any(s.label == 'Fictional scenario' for s in app.selectbox)


def test_return_from_report_does_not_claim_safety(app):
    button(app, 'Immediate danger').click().run()
    assert app.session_state['rr_emergency']
    button(app, 'Return to app — this does not confirm safety').click().run()
    assert not app.exception
    assert app.session_state['page'] == 'Respond'
    assert not app.session_state['rr_emergency']
    assert 'connected' not in app.session_state
    assert 'rescued' not in app.session_state


@pytest.mark.parametrize('description', ['We may need accessible evacuation transport next week',
                                        'No flooding. We need transport next week'])
def test_planning_query_matches_directory_contract_and_rechecks_revocation(app, monkeypatch, description):
    from datetime import datetime, timezone
    from domain.resources import ResourceLookupResult, VerifiedResource
    from services import resources
    now = datetime.now(timezone.utc)
    record = VerifiedResource(resource_id='test-only', source_id='test-only',
        official_name='TEST ONLY reviewed transport', provider='TEST ONLY',
        description='Isolated UI test evidence', service_category='transportation',
        service_area='Miami-Dade', official_url='https://www.miamidade.gov/',
        prerequisites=['TEST ONLY eligibility condition'], enrollment_timing='TEST ONLY registration timing',
        limitations=['No pickup guarantee'], retrieved_at=now, source_reviewed_at=now,
        reviewed_at=now, review_due_at=now, supporting_candidate_ids=['test-only'])
    seen = []
    approved = [True]
    def lookup(query, **kwargs):
        seen.append(query)
        return ResourceLookupResult(status='matches' if approved[0] else 'review_required',
                                    records=[record] if approved[0] else [])
    monkeypatch.setattr(resources, 'lookup_resources', lookup)
    open_help(app)
    next(s for s in app.selectbox if s.label == 'Where is help needed?').select('Miami-Dade County, Florida').run()
    next(t for t in app.text_area if t.label == 'Describe the situation (optional)').input(description)
    button(app, 'Show assistance options').click().run()
    assert seen[-1].needs == 'transportation'
    assert seen[-1].phase == 'prepare'
    assert seen[-1].hazard is None
    next(s for s in app.selectbox if s.label == 'Event context (optional)').select('Hurricane').run()
    assert seen[-1].hazard == 'hurricane'
    assert 'TEST ONLY registration timing' in all_text(app)
    approved[0] = False
    app.run()
    assert 'TEST ONLY registration timing' not in all_text(app)
    assert any(b.label == 'Call 911' for b in app.get('link_button'))


def test_demo_communication_context_opens_alternatives(app):
    open_help(app)
    next(s for s in app.selectbox if s.label == 'Fictional scenario').select('demo-cannot-speak')
    button(app, 'Load fictional scenario').click().run()
    assert not app.exception
    assert app.session_state['rr_alternative']
    assert next(r for r in app.radio if r.label == 'What makes calling difficult? (optional)').value == 'Cannot speak safely'
    assert 'SIMULATED DEMO' in all_text(app)


def test_return_from_unsaved_recovery_danger_requires_new_assessment(app):
    app.session_state['page'] = 'Recover'
    app.run()
    next(s for s in app.selectbox if s.label == 'Immediate danger assessment').select('Immediate danger reported').run()
    assert app.session_state['rr_emergency']
    button(app, 'Return to app — this does not confirm safety').click().run()
    app.session_state['page'] = 'Recover'
    app.run()
    assert not app.exception
    assert not app.session_state['rr_emergency']
    assert next(s for s in app.selectbox if s.label == 'Immediate danger assessment').value == 'Choose an assessment'
