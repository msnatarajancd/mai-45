from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def button(app, label):
    return next(b for b in app.button if b.label == label)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'demo.sqlite3'))
    return AppTest.from_file(APP, default_timeout=15).run()


@pytest.mark.parametrize('page', ['Home', 'Protect', 'Respond', 'Recover', 'Household', 'Evidence'])
def test_every_page_renders_with_emergency_access(app, page):
    app.session_state['page'] = page
    app.run()
    assert not app.exception
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert "I can't call 911" in [b.label for b in app.button]


def test_guided_demo_loads_household_and_warning(app):
    button(app, 'Start guided demo').click().run()
    assert app.session_state['household'].mobility_support
    assert app.session_state['page'] == 'Protect'
    button(app, 'Show simulated alert').click().run()
    assert any('SIMULATED' in m.value for m in app.markdown)
    assert app.session_state['alerts'].simulated


def test_emergency_interrupts_recovery(app):
    app.session_state['page'] = 'Recover'
    app.run()
    button(app, 'Immediate danger').click().run()
    assert any('not contacted' in m.value for m in app.error)
    assert 'Create draft plan' not in [b.label for b in app.button]


def test_alternative_contact_is_always_available(app):
    button(app, "I can't call 911").click().run()
    assert any('availability' in m.value.lower() for m in app.info)


def test_recovery_requires_explicit_safety_selection(app):
    app.session_state['page'] = 'Recover'
    app.run()
    button(app, 'Create draft plan').click().run()
    assert any('explicit' in e.value.lower() for e in app.error)
    assert 'rr_case_id' not in app.session_state


def test_full_recovery_approval_progress_and_resume(app):
    app.session_state['page'] = 'Recover'
    app.run()
    next(s for s in app.selectbox if s.label == 'Immediate danger assessment').select('No immediate danger reported')
    button(app, 'Create draft plan').click().run()
    assert not app.exception
    assert app.session_state['rr_draft']
    case_id = app.session_state['rr_case_id']
    button(app, 'Approve my recovery plan').click().run()
    assert any('Review every task' in e.value for e in app.error)
    next(c for c in app.checkbox if c.label == 'I reviewed these tasks and want to accept this plan').check()
    button(app, 'Approve my recovery plan').click().run()
    assert not app.exception
    next(s for s in app.selectbox if s.label.startswith('Status ·')).select_index(2)
    next(b for b in app.button if b.label == 'Save progress').click().run()
    assert not app.exception
    assert any(m.value == '1' for m in app.metric)
    button(app, 'Open a different case').click().run()
    next(t for t in app.text_input if t.label == 'Saved fictional case ID').input(case_id)
    button(app, 'Resume saved case').click().run()
    assert not app.exception
    assert any(m.value == '1' for m in app.metric)



def test_mode_switch_updates_banner_and_discards_fixture(app, monkeypatch):
    from services import nws_alerts
    from m2_guardian.service import GuardianService
    def unavailable(*args): raise TimeoutError('Synthetic outage')
    monkeypatch.setattr(nws_alerts, 'GuardianService', lambda: GuardianService(transport=unavailable))
    app.session_state['page'] = 'Protect'
    app.run()
    button(app, 'Show simulated alert').click().run()
    next(r for r in app.radio if r.label == 'Alert mode').set_value('LIVE CHECK').run()
    assert 'alerts' not in app.session_state
    banner = next(m.value for m in app.markdown if m.value.startswith('<div class=') and 'rr-topline' in m.value)
    assert 'LIVE CHECK' in banner
    button(app, 'Check official alerts').click().run()
    assert app.session_state['alerts'].status == 'unavailable'
    assert not app.session_state['alerts'].simulated


def test_stale_progress_cannot_overwrite_external_update(app):
    from uuid import UUID
    from ui.recovery_page import repository
    from recovery.models import TaskStatus
    app.session_state['page'] = 'Recover'
    app.run()
    next(s for s in app.selectbox if s.label == 'Immediate danger assessment').select(DANGER_SAFE)
    button(app, 'Create draft plan').click().run()
    next(c for c in app.checkbox if c.label == 'I reviewed these tasks and want to accept this plan').check()
    button(app, 'Approve my recovery plan').click().run()
    repo = repository()
    plan = repo.get_active_plan(UUID(app.session_state['rr_case_id']))
    repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED, expected_progress_version=plan.progress_version)
    next(s for s in app.selectbox if s.label.startswith('Status ·')).select_index(1)
    next(b for b in app.button if b.label == 'Save progress').click().run()
    assert any('stale' in e.value.lower() for e in app.error)
    saved = repo.get_active_plan(plan.case_id)
    assert saved.proposed_tasks[0].status == TaskStatus.COMPLETED


DANGER_SAFE = 'No immediate danger reported'


def seed_approved_case(utilities=None):
    from ui.recovery_page import repository
    from recovery.models import RecoveryIntake
    from recovery.assessment import start_recovery_case
    from recovery.demo_planner import create_demo_draft_plan
    repo = repository()
    case = start_recovery_case(RecoveryIntake(disaster_type='Flood', housing_condition='Minor reported damage', utility_availability=utilities or {'electricity': None, 'water': None}, temporary_accommodation_status='Staying with others', immediate_danger=False, household_recovery_needs=['Temporary housing']), repo)
    plan = create_demo_draft_plan(case)
    repo.save_draft_plan(plan)
    repo.approve_plan(plan.plan_id)
    return repo, case, plan


def test_reassessment_requires_current_explicit_danger_answer(app):
    repo, case, plan = seed_approved_case()
    app.session_state['rr_case_id'] = str(case.case_id)
    app.session_state['page'] = 'Recover'
    app.run()
    next(s for s in app.selectbox if s.label == 'Updated immediate danger assessment').select(DANGER_SAFE).run()
    next(s for s in app.selectbox if s.label == 'Electricity availability').select('Unavailable')
    button(app, 'Preview proposed changes').click().run()
    assert 'rr_revision' in app.session_state
    next(s for s in app.selectbox if s.label == 'Updated immediate danger assessment').select('Choose an assessment').run()
    assert 'Approve this revision' not in [b.label for b in app.button]
    assert repo.get_active_plan(case.case_id).plan_id == plan.plan_id


def test_reassessment_preserves_extra_m5_utilities(app):
    repo, case, plan = seed_approved_case({'electricity': None, 'water': None, 'gas': False})
    app.session_state['rr_case_id'] = str(case.case_id)
    app.session_state['page'] = 'Recover'
    app.run()
    assert 'Gas availability' in [s.label for s in app.selectbox]
    next(s for s in app.selectbox if s.label == 'Updated immediate danger assessment').select(DANGER_SAFE).run()
    next(s for s in app.selectbox if s.label == 'Electricity availability').select('Unavailable')
    button(app, 'Preview proposed changes').click().run()
    button(app, 'Approve this revision').click().run()
    assert repo.get_case(case.case_id).intake.utility_availability['gas'] is False


def test_failed_danger_save_is_retried_before_recovery(app, monkeypatch):
    import sqlite3
    import ui.recovery_page as recovery_page
    repo, case, plan = seed_approved_case()
    app.session_state['rr_case_id'] = str(case.case_id)
    original = recovery_page.repository
    def unavailable():
        raise sqlite3.OperationalError('offline')
    monkeypatch.setattr(recovery_page, 'repository', unavailable)
    button(app, 'Immediate danger').click().run()
    button(app, 'Return to app — this does not confirm safety').click().run()
    monkeypatch.setattr(recovery_page, 'repository', original)
    app.session_state['page'] = 'Recover'
    app.run()
    assert repo.get_case(case.case_id).intake.immediate_danger is True
    assert 'Save progress' not in [b.label for b in app.button]


def test_start_guided_demo_resets_live_picker(app):
    app.session_state['page'] = 'Protect'
    app.run()
    next(r for r in app.radio if r.label == 'Alert mode').set_value('LIVE CHECK').run()
    next(s for s in app.selectbox if s.label == 'Check an area').select('homestead').run()
    button(app, 'Start guided demo').click().run()
    assert app.session_state['mode'].value == 'SIMULATED DEMO'
    assert app.session_state['location_id'] == 'miami'
    button(app, 'Show simulated alert').click().run()
    assert app.session_state['alerts'].simulated
