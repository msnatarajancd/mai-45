"""Missing UI regressions only; no live provider calls in pytest."""
import json
import sqlite3
from pathlib import Path
from urllib.error import URLError

import pytest
from streamlit.testing.v1 import AppTest

from recovery.ai_planner import CATALOGUE, REASON
from recovery.database import SQLiteRecoveryRepository
from recovery.llm_client import NebiusClient
from recovery.models import RecoveryCase, RecoveryIntake


def valid_response():
    return json.dumps({'tasks': [dict(title=t, description=d, priority='HIGH',
        reason_for_recommendation=REASON, source_reference=None) for t, d in CATALOGUE[:3]]})


@pytest.fixture
def planning(tmp_path, monkeypatch):
    path = tmp_path / 'ui.db'
    repo = SQLiteRecoveryRepository(path)
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Fictional hurricane',
        housing_condition='Minor reported damage', utility_availability={'water': None},
        temporary_accommodation_status='Fictional stay with others', immediate_danger=False,
        household_recovery_needs=['Supplies']))
    repo.create_case(case)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10)
    app.session_state['case_id'] = str(case.case_id)
    app.session_state['recovery_page'] = 'planning'
    app.run()
    next(r for r in app.radio if r.label == 'Initial planner').set_value('AI-assisted (experimental)').run()
    return app, repo, case, path


@pytest.mark.parametrize('failure', ['missing_key', 'timeout', 'wrapped_timeout', 'invalid', 'configuration'])
def test_ui_provider_failures_are_clear_safe_and_not_saved(planning, monkeypatch, failure):
    app, repo, case, path = planning
    monkeypatch.setenv('NEBIUS_API_KEY', 'fictional-never-display-key')
    if failure == 'missing_key':
        monkeypatch.delenv('NEBIUS_API_KEY')
    elif failure == 'configuration':
        monkeypatch.setenv('NEBIUS_MODEL', ' ')
    elif failure in ('timeout', 'wrapped_timeout'):
        class Opener:
            def open(self, *args, **kwargs):
                if failure == 'wrapped_timeout':
                    raise URLError(TimeoutError('fictional-never-display-key'))
                raise TimeoutError('fictional-never-display-key')
        monkeypatch.setattr('recovery.llm_client.build_opener', lambda *args: Opener())
    else:
        monkeypatch.setattr(NebiusClient, 'complete', lambda *args: '{bad json')
    next(b for b in app.button if b.label == 'Generate AI Draft Plan').click().run()
    assert not app.exception
    errors = ' '.join(e.value for e in app.error)
    expected = {'missing_key': 'NEBIUS_API_KEY is not configured', 'timeout': 'timed out',
                'wrapped_timeout': 'timed out', 'invalid': 'rejected', 'configuration': 'configuration is invalid'}
    assert expected[failure] in errors
    assert 'fictional-never-display-key' not in errors
    assert repo.get_active_plan(case.case_id) is None
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT count(*) FROM recovery_plans').fetchone()[0] == 0
    assert 'Approve Recovery Plan' not in [b.label for b in app.button]
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert "I Can't Call 911" in [b.label for b in app.button]
    assert next(r for r in app.radio if r.label == 'Initial planner').value == 'AI-assisted (experimental)'


def test_danger_during_provider_call_discards_result(planning, monkeypatch):
    app, repo, case, path = planning
    def complete(*args):
        SQLiteRecoveryRepository(path).report_immediate_danger(case.case_id)
        return valid_response()
    monkeypatch.setattr(NebiusClient, 'complete', complete)
    next(b for b in app.button if b.label == 'Generate AI Draft Plan').click().run()
    assert not app.exception
    assert any('Emergency handoff' in e.value for e in app.error)
    assert 'Approve Recovery Plan' not in [b.label for b in app.button]
    with pytest.raises(KeyError):
        app.session_state[f'draft_plan_json:{case.case_id}:AI-assisted (experimental)']
    assert repo.get_active_plan(case.case_id) is None


def test_new_danger_prevents_even_cached_ai_draft_display(planning, monkeypatch):
    app, repo, case, path = planning
    calls = []
    def complete(*args):
        calls.append(True)
        return valid_response()
    monkeypatch.setattr(NebiusClient, 'complete', complete)
    next(b for b in app.button if b.label == 'Generate AI Draft Plan').click().run()
    assert len(calls) == 1
    next(b for b in app.button if b.label == 'Report immediate danger').click().run()
    assert any('Emergency handoff' in e.value for e in app.error)
    next(b for b in app.button if b.label == 'Return to recovery demo').click().run()
    assert any('Emergency handoff' in e.value for e in app.error)
    assert 'Approve Recovery Plan' not in [b.label for b in app.button]
    assert len(calls) == 1


def test_intake_change_during_generation_discards_draft(planning, monkeypatch):
    app, repo, case, path = planning
    def complete(*args):
        changed = case.model_copy(deep=True)
        changed.intake.housing_condition = 'Major reported damage'
        with sqlite3.connect(path) as connection:
            connection.execute('UPDATE recovery_cases SET case_json = ? WHERE case_id = ?',
                               (changed.model_dump_json(), str(case.case_id)))
        return valid_response()
    monkeypatch.setattr(NebiusClient, 'complete', complete)
    next(b for b in app.button if b.label == 'Generate AI Draft Plan').click().run()
    assert any('circumstances changed during generation' in e.value for e in app.error)
    assert 'Approve Recovery Plan' not in [b.label for b in app.button]


def test_emergency_controls_without_database_or_llm(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs): raise sqlite3.OperationalError('fictional unavailable database')
    monkeypatch.setattr('recovery.ui.SQLiteRecoveryRepository', unavailable)
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'unavailable.db'))
    app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10).run()
    assert any('database is unavailable' in e.value for e in app.error)
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    next(b for b in app.button if b.label == "I Can't Call 911").click().run()
    assert any('cannot contact responders' in w.value for w in app.warning)
    next(b for b in app.button if b.label == 'Report immediate danger').click().run()
    assert any('Emergency handoff' in e.value for e in app.error)
    assert not app.exception


def test_complete_hurricane_ai_ui_journey_with_fake_model(monkeypatch):
    from smoke_nebius import run_ui_smoke
    monkeypatch.setattr(NebiusClient, 'complete', lambda *args: valid_response())
    report = run_ui_smoke()
    assert report['generation_plan_rows'] == 0
    assert report['active_before_approval'] is False
    assert report['resumed_completed_status'] == 'COMPLETED'
    assert report['provider_calls'] == 1
    assert report['task_evidence_status_visible']
