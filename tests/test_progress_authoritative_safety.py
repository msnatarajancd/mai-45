"""Selected saved safety is authoritative even while viewing a fictional story."""
from pathlib import Path
import sqlite3

import pytest
from streamlit.testing.v1 import AppTest
from recovery.database import SQLiteRecoveryRepository
from recovery.models import RecoveryCase, RecoveryIntake


def case(repo, danger=False):
    value = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Flooded',
        utility_availability={'electricity': False}, temporary_accommodation_status='Needed',
        immediate_danger=danger, household_recovery_needs=['Temporary housing']))
    repo.create_case(value)
    return value


@pytest.fixture
def selected(tmp_path, monkeypatch):
    path = tmp_path / 'case.sqlite3'
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    monkeypatch.setenv('READYRELIEF_PROGRESS_DB_PATH', str(tmp_path / 'progress.sqlite3'))
    repo = SQLiteRecoveryRepository(path)
    return repo, case(repo)


def app_for(case_id):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['rr_case_id'] = str(case_id)
    app.session_state['rr_emergency'] = False
    app.session_state['rr_pending_danger'] = []
    app.session_state['page'] = 'Recovery Progress'
    return app.run()


def blocked(app):
    assert not app.exception
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I Can't Call 911" in [w.label for w in app.button]
    assert not any(w.key == 'rp_refresh' and not w.disabled for w in app.button)
    assert not any(w.key == 'rp_next_action' or str(w.key).startswith('rp_secondary_') for w in app.button)


@pytest.mark.parametrize('mode', ['Synthetic stories', 'Saved recovery case'])
@pytest.mark.parametrize('danger', [True, None])
def test_selected_persisted_safety_blocks_both_modes(selected, mode, danger):
    repo, saved = selected
    if danger is True:
        repo.report_immediate_danger(saved.case_id)
    else:
        # Independent fictional unassessed case, never danger clearance.
        saved = case(repo, None)
    app = app_for(saved.case_id)
    app.session_state['rp_source_mode'] = mode
    app.run()
    blocked(app)
    assert repo.get_case(saved.case_id).intake.immediate_danger is danger
    assert not app.success


def test_selected_safety_lookup_failure_suppresses_story_and_recommendations(selected, monkeypatch):
    repo, saved = selected
    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError('Synthetic safety lookup failure')
    monkeypatch.setattr(SQLiteRecoveryRepository, 'get_progress_revision', unavailable)
    app = app_for(saved.case_id)
    blocked(app)
    assert any('could not be verified' in w.value for w in app.warning)
    assert repo.get_case(saved.case_id).intake.immediate_danger is False


@pytest.mark.parametrize('persistence_fails', [False, True])
def test_pending_danger_never_allows_synthetic_recommendations(selected, monkeypatch, persistence_fails):
    repo, saved = selected
    app = app_for(saved.case_id)
    if persistence_fails:
        def unavailable(*args, **kwargs):
            raise sqlite3.OperationalError('Synthetic danger persistence failure')
        monkeypatch.setattr(SQLiteRecoveryRepository, 'report_immediate_danger', unavailable)
    app.session_state['rr_pending_danger'] = [str(saved.case_id)]
    app.run()
    blocked(app)
    assert repo.get_case(saved.case_id).intake.immediate_danger is (not persistence_fails)
    if persistence_fails:
        assert app.session_state['rr_pending_danger'] == [str(saved.case_id)]


def test_case_switch_and_new_persisted_danger_are_not_cached(selected):
    repo, safe = selected
    danger = case(repo)
    repo.report_immediate_danger(danger.case_id)
    app = app_for(safe.case_id)
    assert not app.button(key='rp_refresh').disabled
    app.session_state['rr_case_id'] = str(danger.case_id)
    app.run()
    blocked(app)
    app.session_state['rr_case_id'] = str(safe.case_id)
    app.run()
    assert not app.button(key='rp_refresh').disabled
    repo.report_immediate_danger(safe.case_id)
    app.run()
    blocked(app)


def test_input_loader_rechecks_safety_even_without_page_render(selected, monkeypatch):
    repo, saved = selected
    from ui import recovery_progress_page as page
    state = {'rr_case_id': str(saved.case_id), 'rp_source_mode': 'Synthetic stories'}
    monkeypatch.setattr(page.st, 'session_state', state)
    from types import SimpleNamespace
    store = SimpleNamespace(interactions=lambda *args: {})
    assert page._load_current_inputs(store).source_mode.value == 'synthetic'
    repo.report_immediate_danger(saved.case_id)
    with pytest.raises(ValueError, match='safety'):
        page._load_current_inputs(store)
