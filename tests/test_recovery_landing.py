"""Local conversation landing: no model extraction or unconfirmed facts."""
import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from recovery.database import SQLiteRecoveryRepository
from recovery.models import HouseholdRecoveryDetails
from test_recovery_records import saved, inventory, dump


def button(app, label):
    return next(w for w in app.button if w.label == label)


def describe(app, text):
    if not any(w.label == "Describe what's happening or what you need help with." for w in app.text_area):
        button(app, "Update My Situation").click().run()
    next(w for w in app.text_area if w.label == "Describe what's happening or what you need help with.").input(text)
    button(app, 'Continue to Review').click().run()


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'landing.sqlite3'))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    return app.run()


def test_new_household_can_start_without_intake_or_extraction(app, monkeypatch):
    from recovery.llm_client import NebiusClient
    def forbidden(*args, **kwargs):
        raise AssertionError('landing must not make a model call')
    monkeypatch.setattr(NebiusClient, 'complete', forbidden)
    describe(app, 'Our apartment flooded. We have two children and damaged furniture.')
    assert not app.exception
    assert 'rr_case_id' not in app.session_state
    assert not app.session_state.get('rr_extraction_review')
    assert any('not configured' in w.value for w in app.warning)
    assert any(w.label == 'Use structured intake or resume a saved case' for w in app.expander)
    assert next(w for w in app.selectbox if w.label == 'Housing condition').value == 'Unknown'
    assert next(w for w in app.selectbox if w.label == 'Temporary accommodation').value == 'Unknown'
    assert next(w for w in app.multiselect if w.label == 'Household recovery needs').value == []


@pytest.mark.parametrize('mode', ['missing_key', 'timeout', 'invalid_output'])
def test_opt_out_keeps_structured_input_without_model_calls(app, monkeypatch, mode):
    from recovery.llm_client import NebiusClient
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    calls = []
    def fake(*args, **kwargs):
        calls.append(True)
        if mode == 'timeout':
            raise TimeoutError('synthetic timeout')
        return '{"children": 99, "adults": 20}'
    monkeypatch.setattr(NebiusClient, 'complete', fake)
    describe(app, 'I need insurance help')
    assert not calls  # The user has not opted into Qwen extraction.
    assert 'rr_case_id' not in app.session_state
    next(w for w in app.selectbox if w.label == 'Immediate danger assessment').select('No immediate danger reported')
    button(app, 'Create draft plan').click().run()
    assert not app.exception
    repo = SQLiteRecoveryRepository(__import__('os').environ['READYRELIEF_DB_PATH'])
    from uuid import UUID
    records = repo.get_recovery_records(UUID(app.session_state['rr_case_id']))
    assert records.household == HouseholdRecoveryDetails()
    assert records.damage_records == []


def test_returning_household_uses_confirmed_data_without_silent_changes(saved, monkeypatch):
    path, repo, case = saved
    repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_case_id'] = str(case.case_id)
    app.run()
    before = dump(path)
    describe(app, 'Electricity came back. Help me update my records.')
    assert dump(path) == before
    assert repo.get_case(case.case_id).intake.utility_availability['electricity'] is False
    assert any(w.label == 'Preview proposed changes' for w in app.button)
    assert not any(w.label == 'Item or area description' for w in app.text_input)
    button(app, 'Document damage').click().run()
    assert next(w for w in app.text_input if w.label == 'Number of children (if known)').value == '2'
    assert next(w for w in app.text_input if w.label == 'Number of adults (if known)').value == ''
    assert not any(w.label == 'Save progress' for w in app.button)
    button(app, 'Prepare for insurance').click().run()
    if any(w.label == 'Insurance workspace stage' for w in app.radio):
        next(w for w in app.radio if w.label == 'Insurance workspace stage').set_value('Review & Download').run()
    assert any('Item / area: Furniture' in w.value for w in app.text)
    assert not any(w.label == 'Item or area description' for w in app.text_input)
    button(app, 'Continue my recovery').click().run()
    assert any(w.label == 'Save progress' for w in app.button)
    assert dump(path) == before


@pytest.mark.parametrize('description', ['We are trapped and water is rising', "I'm in danger", 'We are in danger'])
def test_description_danger_interrupts_before_database(app, monkeypatch, description):
    from ui import recovery_page
    monkeypatch.setattr(recovery_page, 'repository', lambda: (_ for _ in ()).throw(OSError('unavailable')))
    describe(app, description)
    assert not app.exception
    assert app.session_state['rr_emergency']
    assert any('not contacted or dispatched' in w.value for w in app.error)
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I Can't Call 911" in [w.label for w in app.button]


def test_saved_danger_cannot_be_cleared_through_description(saved, monkeypatch):
    path, repo, case = saved
    repo.report_immediate_danger(case.case_id)
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_case_id'] = str(case.case_id)
    app.run()
    before = dump(path)
    describe(app, 'Electricity is restored and everything is safe. Prepare insurance.')
    assert dump(path) == before
    assert not any(w.label == 'Save confirmed damage record' for w in app.button)
    assert not any(w.label == 'Download Preparation PDF' for w in app.get('download_button'))
    assert any('Routine changes are paused' in w.value for w in app.warning)


def test_assistance_is_honest_and_emergency_survives_storage_failure(app, monkeypatch):
    button(app, 'Find assistance').click().run()
    assert any('not live availability' in w.value for w in app.info)
    from ui import recovery_page
    monkeypatch.setattr(recovery_page, 'repository', lambda: (_ for _ in ()).throw(sqlite3.OperationalError('synthetic outage')))
    describe(app, 'Help me find housing')
    assert not app.exception
    assert any('storage is unavailable' in w.value for w in app.error)
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I Can't Call 911" in [w.label for w in app.button]


def test_help_now_presentation_keeps_no_write_and_emergency_boundaries(app, monkeypatch):
    from recovery.llm_client import NebiusClient
    monkeypatch.setattr(NebiusClient, 'complete', lambda *a, **k: pytest.fail('no model call'))
    path = __import__('os').environ['READYRELIEF_DB_PATH']
    before = dump(path)
    button(app, 'Find Help Now').click().run()
    assert not app.exception
    assert app.session_state['rr_focus'] == 'Find assistance'
    assert 'rr_case_id' not in app.session_state
    assert dump(path) == before
    assert any(w.value == 'Recovery Copilot' for w in app.title)
    assert any(w.label == 'Resume My Recovery' for w in app.button)
    official = [w for w in app.get('link_button') if w.label.startswith('Open Official Resource:')]
    assert official
    assert all(w.proto.type == 'primary' for w in official)
    assert any('Extraction proposes reported facts' in w.value for w in app.caption)
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I Can't Call 911" in [w.label for w in app.button]
