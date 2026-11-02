import sqlite3

import pytest

from recovery.assessment import RecoveryAssessmentOutcome, start_recovery_case
from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import PlanStatus, RecoveryCase, RecoveryIntake, TaskStatus
from recovery.reassessment import preview_reassessment


@pytest.fixture
def saved(tmp_path):
    path = tmp_path / 'recovery.db'
    repo = SQLiteRecoveryRepository(path)
    intake = RecoveryIntake(
        disaster_type='Flood', housing_condition='Major reported damage',
        utility_availability={'electricity': False, 'water': True},
        temporary_accommodation_status='No lodging arranged',
        immediate_danger=False,
        household_recovery_needs=['Temporary housing', 'Transportation'],
    )
    case = start_recovery_case(intake, repo)
    draft = create_demo_draft_plan(case)
    repo.save_draft_plan(draft)
    plan = repo.approve_plan(draft.plan_id)
    repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED)
    repo.update_task_status(plan.plan_id, plan.proposed_tasks[1].task_id, TaskStatus.BLOCKED)
    return path, repo, case, repo.get_active_plan(case.case_id)


def updated(case, **changes):
    return RecoveryIntake.model_validate({**case.intake.model_dump(), **changes})


def test_utility_change_and_explanation(saved):
    _, _, case, plan = saved
    result = preview_reassessment(case, plan, updated(case, utility_availability={'electricity': True, 'water': True}))
    change = next(c for c in result.changed_circumstances if c.field == 'utility_availability.electricity')
    assert change.previous is False and change.updated is True
    assert 'available' in change.explanation
    assert 'does not establish household safety' in change.explanation
    assert any('utility' in r.task.title for r in result.potentially_irrelevant_tasks)


def test_housing_change_adds_specific_review(saved):
    _, _, case, plan = saved
    result = preview_reassessment(case, plan, updated(case, temporary_accommodation_status='Staying with others'))
    assert any(c.field == 'temporary_accommodation_status' for c in result.changed_circumstances)
    assert any(r.task.title == 'Review changed housing arrangements' for r in result.new_tasks)
    assert all(r.explanation for r in result.new_tasks)


def test_progress_and_original_approved_plan_preserved(saved):
    _, _, case, plan = saved
    before = plan.model_dump_json()
    result = preview_reassessment(case, plan, updated(case, household_recovery_needs=['Food']))
    assert plan.model_dump_json() == before
    assert result.completed_tasks[0].task == plan.proposed_tasks[0]
    assert result.proposed_revision.proposed_tasks[:len(plan.proposed_tasks)] == plan.proposed_tasks
    assert result.proposed_revision.plan_id != plan.plan_id
    assert result.proposed_revision.approval_status is PlanStatus.DRAFT
    assert all(r.task.status is TaskStatus.NOT_STARTED for r in result.new_tasks)
    result.proposed_revision.proposed_tasks[0].title = 'mutated preview'
    assert plan.model_dump_json() == before


def test_no_duplicate_or_unnecessary_tasks(saved):
    _, _, case, plan = saved
    same = preview_reassessment(case, plan, case.intake)
    assert not same.changed_circumstances and not same.new_tasks
    result = preview_reassessment(case, plan, updated(case, household_recovery_needs=['Transportation', 'Food', ' food ']))
    titles = [t.title.casefold() for t in result.proposed_revision.proposed_tasks]
    assert len(titles) == len(set(titles))
    assert len(result.new_tasks) == 1


def test_removed_need_is_only_flagged(saved):
    _, _, case, plan = saved
    result = preview_reassessment(case, plan, updated(case, household_recovery_needs=[]))
    assert any('transportation' in r.task.title for r in result.potentially_irrelevant_tasks)
    assert all(t in result.proposed_revision.proposed_tasks for t in plan.proposed_tasks)


@pytest.mark.parametrize('danger,outcome', [
    (True, RecoveryAssessmentOutcome.EMERGENCY_HANDOFF),
    (None, RecoveryAssessmentOutcome.DANGER_NOT_ASSESSED),
])
def test_safety_blocks_preview(saved, danger, outcome):
    path, repo, case, plan = saved
    before = path.read_bytes()
    result = preview_reassessment(case, plan, updated(case, immediate_danger=danger))
    assert result.outcome is outcome
    assert result.proposed_revision is None
    assert not result.new_tasks and not result.changed_circumstances
    assert path.read_bytes() == before
    assert repo.get_active_plan(case.case_id) == plan


def test_preview_does_not_modify_any_persisted_state(saved):
    path, repo, case, plan = saved
    before = path.read_bytes()
    case_before = case.model_dump_json()
    result = preview_reassessment(case, plan, updated(case, housing_condition='Minor reported damage', household_recovery_needs=['Food']))
    assert path.read_bytes() == before
    assert case.model_dump_json() == case_before
    assert repo.get_case(case.case_id) == case
    assert repo.get_plan(plan.plan_id) == plan
    assert repo.get_active_plan(case.case_id) == plan
    assert repo.get_plan(result.proposed_revision.plan_id) is None
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT count(*) FROM recovery_plans').fetchone()[0] == 1


@pytest.mark.parametrize('value', [False, None])
def test_new_utility_gap_has_targeted_task(saved, value):
    _, _, case, plan = saved
    result = preview_reassessment(case, plan, updated(case, utility_availability={'electricity': False, 'water': value}))
    assert [r.task.title for r in result.new_tasks] == ['Review water availability gap']


def test_invalid_plan_rejected(saved):
    _, _, case, plan = saved
    with pytest.raises(ValueError, match='approved'):
        preview_reassessment(case, plan.model_copy(update={'approval_status': PlanStatus.DRAFT}), case.intake)
    with pytest.raises(ValueError, match='belong'):
        preview_reassessment(RecoveryCase(intake=case.intake), plan, case.intake)


def make_revision(case, plan):
    return preview_reassessment(case, plan, updated(case,
        housing_condition='Minor reported damage', household_recovery_needs=['Food']))


def test_accept_requires_explicit_action(saved):
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    before = path.read_bytes()
    with pytest.raises(ValueError, match='explicit'):
        repo.approve_reassessment(preview)
    assert path.read_bytes() == before
    assert repo.get_active_plan(case.case_id) == plan


def test_accept_persists_revision_assessment_and_history(saved):
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    accepted = repo.approve_reassessment(preview, explicitly_approved=True)
    reopened = SQLiteRecoveryRepository(path)
    assert accepted.approval_status is PlanStatus.APPROVED
    assert reopened.get_active_plan(case.case_id) == accepted
    assert reopened.get_plan(plan.plan_id) == plan
    assert accepted.proposed_tasks[:len(plan.proposed_tasks)] == plan.proposed_tasks
    assert accepted.proposed_tasks[0].status is TaskStatus.COMPLETED
    assert accepted.proposed_tasks[1].status is TaskStatus.BLOCKED
    new_tasks = accepted.proposed_tasks[len(plan.proposed_tasks):]
    assert new_tasks and all(t.status is TaskStatus.NOT_STARTED for t in new_tasks)
    assert not {t.task_id for t in new_tasks} & {t.task_id for t in plan.proposed_tasks}
    assert len({t.title for t in accepted.proposed_tasks}) == len(accepted.proposed_tasks)
    latest = reopened.get_case(case.case_id)
    assert latest.intake == preview.updated_intake
    assert latest.updated_at > case.updated_at
    assert latest.created_at == case.created_at
    assert reopened.list_approved_plans(case.case_id) == [plan, accepted]
    following = preview_reassessment(latest, accepted, latest.intake)
    assert not following.changed_circumstances and not following.new_tasks
    with sqlite3.connect(path) as connection:
        evidence = connection.execute('SELECT preview_json FROM recovery_reassessments').fetchone()[0]
    from recovery.reassessment import ReassessmentPreview
    assert ReassessmentPreview.model_validate_json(evidence) == preview


@pytest.mark.parametrize('revert', [False, True])
def test_stale_task_progress_rejected(saved, revert):
    _, repo, case, plan = saved
    preview = make_revision(case, plan)
    task = plan.proposed_tasks[1]
    repo.update_task_status(plan.plan_id, task.task_id, TaskStatus.IN_PROGRESS)
    if revert:
        repo.update_task_status(plan.plan_id, task.task_id, task.status)
    latest = repo.get_active_plan(case.case_id)
    with pytest.raises(ValueError, match='stale'):
        repo.approve_reassessment(preview, explicitly_approved=True)
    assert repo.get_active_plan(case.case_id) == latest
    assert repo.get_case(case.case_id) == case
    assert repo.get_plan(preview.proposed_revision.plan_id) is None


def test_changed_active_plan_rejected(saved):
    _, repo, case, plan = saved
    preview = make_revision(case, plan)
    accepted = repo.approve_reassessment(make_revision(case, plan), explicitly_approved=True)
    with pytest.raises(ValueError, match='stale'):
        repo.approve_reassessment(preview, explicitly_approved=True)
    assert repo.get_active_plan(case.case_id) == accepted


@pytest.mark.parametrize('danger', [True, None])
def test_approval_reevaluates_danger(saved, danger):
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    preview.updated_intake.immediate_danger = danger
    before = path.read_bytes()
    from recovery.assessment import RecoveryIntakeNotPermitted
    with pytest.raises(RecoveryIntakeNotPermitted):
        repo.approve_reassessment(preview, explicitly_approved=True)
    assert path.read_bytes() == before


@pytest.mark.parametrize('target', ['recovery_reassessments', 'recovery_cases'])
def test_approval_failure_rolls_back_entire_transaction(saved, target):
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    operation = 'INSERT' if target == 'recovery_reassessments' else 'UPDATE'
    with sqlite3.connect(path) as connection:
        connection.execute(f"CREATE TRIGGER fail_accept BEFORE {operation} ON {target} BEGIN SELECT RAISE(ABORT, 'fictional failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match='fictional failure'):
        repo.approve_reassessment(preview, explicitly_approved=True)
    assert repo.get_plan(preview.proposed_revision.plan_id) is None
    assert repo.get_active_plan(case.case_id) == plan
    assert repo.get_case(case.case_id) == case
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT count(*) FROM recovery_reassessments').fetchone()[0] == 0


def test_missing_case_rejected(saved):
    _, repo, case, plan = saved
    preview = make_revision(case, plan)
    from uuid import uuid4
    preview.case_id = uuid4()
    with pytest.raises(ValueError, match='does not exist'):
        repo.approve_reassessment(preview, explicitly_approved=True)


@pytest.mark.parametrize('mutation', ['status', 'duplicate', 'new_status'])
def test_altered_proposal_rejected(saved, mutation):
    _, repo, case, plan = saved
    preview = make_revision(case, plan)
    tasks = preview.proposed_revision.proposed_tasks
    if mutation == 'status':
        tasks[0].status = TaskStatus.NOT_STARTED
    elif mutation == 'duplicate':
        tasks[-1].task_id = tasks[0].task_id
    else:
        tasks[-1].status = TaskStatus.COMPLETED
    with pytest.raises(ValueError):
        repo.approve_reassessment(preview, explicitly_approved=True)
    assert repo.get_active_plan(case.case_id) == plan


@pytest.mark.parametrize('action', ['approve', 'keep', 'danger', 'unknown'])
def test_reassessment_dashboard_actions(saved, monkeypatch, action):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    path, repo, case, plan = saved
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10)
    app.session_state['case_id'] = str(case.case_id)
    app.session_state['recovery_page'] = 'dashboard'
    app.run()
    assert not app.exception
    def button(label):
        return next(b for b in app.button if b.label == label)
    def danger():
        return next(s for s in app.selectbox if s.label == 'Current immediate danger assessment')
    danger().select('No immediate danger reported').run()
    next(t for t in app.text_input if t.label == 'Updated housing condition').set_value('Minor reported damage')
    button('Preview proposed revision').click().run()
    assert repo.get_active_plan(case.case_id) == plan
    assert any('Previous reported circumstances' in m.value for m in app.markdown)
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert "I Can't Call 911" in [b.label for b in app.button]
    if action == 'approve':
        button('Approve Revised Recovery Plan').click().run()
        assert repo.get_active_plan(case.case_id).plan_id != plan.plan_id
        assert any('saved and approved' in s.value for s in app.success)
        assert any(str(plan.plan_id) in m.value for m in app.markdown)
    elif action == 'keep':
        button('Keep Current Plan').click().run()
        assert repo.get_active_plan(case.case_id) == plan
        assert any('Current plan kept' in s.value for s in app.success)
    elif action == 'danger':
        danger().select('Immediate danger reported').run()
        assert any('Emergency handoff' in e.value for e in app.error)
        assert repo.get_active_plan(case.case_id) == plan
        assert 'Approve Revised Recovery Plan' not in [b.label for b in app.button]
    else:
        danger().select('Choose an assessment').run()
        button('Approve Revised Recovery Plan').click().run()
        assert any('Explicitly assess' in e.value for e in app.error)
        assert repo.get_active_plan(case.case_id) == plan
    assert not app.exception


def test_changed_case_snapshot_rejected(saved):
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    changed = case.model_copy(deep=True)
    changed.intake.temporary_accommodation_status = 'Fictional lodging update'
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE recovery_cases SET case_json = ? WHERE case_id = ?',
                           (changed.model_dump_json(), str(case.case_id)))
    with pytest.raises(ValueError, match='stale'):
        repo.approve_reassessment(preview, explicitly_approved=True)
    assert repo.get_case(case.case_id) == changed
    assert repo.get_active_plan(case.case_id) == plan


def test_duplicate_revision_approval_is_rejected(saved):
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    accepted = repo.approve_reassessment(preview, explicitly_approved=True)
    with pytest.raises(ValueError, match='stale'):
        SQLiteRecoveryRepository(path).approve_reassessment(preview, explicitly_approved=True)
    assert repo.list_approved_plans(case.case_id) == [plan, accepted]


def test_two_sessions_cannot_overwrite_same_task(saved):
    path, repo, case, plan = saved
    other = SQLiteRecoveryRepository(path)
    version = plan.progress_version
    task = plan.proposed_tasks[1]
    repo.update_task_status(plan.plan_id, task.task_id, TaskStatus.COMPLETED,
                            expected_progress_version=version)
    with pytest.raises(ValueError, match='stale task update'):
        other.update_task_status(plan.plan_id, task.task_id, TaskStatus.NOT_STARTED,
                                 expected_progress_version=version)
    assert other.get_active_plan(case.case_id).proposed_tasks[1].status is TaskStatus.COMPLETED


@pytest.mark.parametrize('danger', [True, None])
def test_persisted_danger_blocks_task_writes(saved, danger):
    path, repo, case, plan = saved
    changed = case.model_copy(deep=True)
    changed.intake.immediate_danger = danger
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE recovery_cases SET case_json = ? WHERE case_id = ?',
                           (changed.model_dump_json(), str(case.case_id)))
    with pytest.raises(ValueError, match='no-immediate-danger'):
        repo.update_task_status(plan.plan_id, plan.proposed_tasks[1].task_id, TaskStatus.COMPLETED)
    assert repo.get_active_plan(case.case_id) == plan


def test_emergency_report_invalidates_other_session_preview(saved):
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    other = SQLiteRecoveryRepository(path)
    repo.report_immediate_danger(case.case_id)
    with pytest.raises(ValueError, match='stale'):
        other.approve_reassessment(preview, explicitly_approved=True)
    with pytest.raises(ValueError, match='no-immediate-danger'):
        other.update_task_status(plan.plan_id, plan.proposed_tasks[1].task_id, TaskStatus.COMPLETED)
    assert other.get_active_plan(case.case_id) == plan


def test_foreign_task_id_cannot_be_used_for_new_revision_task(saved):
    _, repo, case, plan = saved
    other_case = RecoveryCase(intake=case.intake.model_copy(deep=True))
    repo.create_case(other_case)
    foreign = create_demo_draft_plan(other_case)
    repo.save_draft_plan(foreign)
    preview = make_revision(case, plan)
    preview.proposed_revision.proposed_tasks[-1].task_id = foreign.proposed_tasks[0].task_id
    with pytest.raises(ValueError, match='new task IDs'):
        repo.approve_reassessment(preview, explicitly_approved=True)
    with pytest.raises(ValueError, match='does not belong'):
        repo.update_task_status(plan.plan_id, foreign.proposed_tasks[0].task_id, TaskStatus.COMPLETED)
    borrowed = create_demo_draft_plan(other_case)
    borrowed.proposed_tasks[0].task_id = plan.proposed_tasks[0].task_id
    with pytest.raises(ValueError, match='cross recovery cases'):
        repo.save_draft_plan(borrowed)


def test_altered_explanations_cannot_be_saved_as_approval_evidence(saved):
    _, repo, case, plan = saved
    preview = make_revision(case, plan)
    preview.changed_circumstances[0].explanation = 'Fictional altered evidence'
    with pytest.raises(ValueError, match='review evidence'):
        repo.approve_reassessment(preview, explicitly_approved=True)


def test_approval_evidence_records_explicit_action(saved):
    path, repo, case, plan = saved
    accepted = repo.approve_reassessment(make_revision(case, plan), explicitly_approved=True)
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT approval_action FROM recovery_reassessments WHERE plan_id = ?',
                                  (str(accepted.plan_id),)).fetchone()[0] == 'explicit_user_approval'


def test_concurrent_approvals_have_exactly_one_winner(saved):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    path, repo, case, plan = saved
    preview = make_revision(case, plan)
    repositories = [SQLiteRecoveryRepository(path), SQLiteRecoveryRepository(path)]
    barrier = Barrier(2)
    def accept(repository):
        barrier.wait(timeout=5)
        try:
            repository.approve_reassessment(preview, explicitly_approved=True)
            return 'approved'
        except ValueError as error:
            assert 'stale' in str(error)
            return 'stale'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(accept, repositories))
    assert sorted(results) == ['approved', 'stale']
    assert len(repo.list_approved_plans(case.case_id)) == 2


def test_version_reads_are_inside_acceptance_transaction(saved, monkeypatch):
    from contextlib import contextmanager
    _, repo, case, plan = saved
    statements = []
    original = repo._connection
    @contextmanager
    def traced():
        with original() as connection:
            connection.set_trace_callback(statements.append)
            yield connection
    monkeypatch.setattr(repo, '_connection', traced)
    repo.approve_reassessment(make_revision(case, plan), explicitly_approved=True)
    begin = next(i for i, sql in enumerate(statements) if sql == 'BEGIN IMMEDIATE')
    read = next(i for i, sql in enumerate(statements) if sql.startswith('SELECT plan_json FROM recovery_plans WHERE plan_id'))
    write = next(i for i, sql in enumerate(statements) if sql.startswith('INSERT INTO recovery_plans'))
    commit = statements.index('COMMIT')
    assert begin < read < write < commit


def test_failure_at_transaction_exit_rolls_back(saved, monkeypatch):
    from contextlib import contextmanager
    _, repo, case, plan = saved
    original = repo._connection
    preview = make_revision(case, plan)
    @contextmanager
    def fail_before_commit():
        with original() as connection:
            yield connection
            raise sqlite3.OperationalError('fictional commit failure')
    with monkeypatch.context() as patch:
        patch.setattr(repo, '_connection', fail_before_commit)
        with pytest.raises(sqlite3.OperationalError, match='commit failure'):
            repo.approve_reassessment(preview, explicitly_approved=True)
    assert repo.get_plan(preview.proposed_revision.plan_id) is None
    assert repo.get_active_plan(case.case_id) == plan
    assert repo.get_case(case.case_id) == case


def test_ui_failed_revision_never_reports_success(saved, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    path, repo, case, plan = saved
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10)
    app.session_state['case_id'] = str(case.case_id)
    app.session_state['recovery_page'] = 'dashboard'
    app.run()
    next(s for s in app.selectbox if s.label == 'Current immediate danger assessment').select('No immediate danger reported').run()
    next(b for b in app.button if b.label == 'Preview proposed revision').click().run()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_ui BEFORE UPDATE ON recovery_cases BEGIN SELECT RAISE(ABORT, 'fictional write failure'); END")
    next(b for b in app.button if b.label == 'Approve Revised Recovery Plan').click().run()
    assert any('Revision was not saved' in e.value for e in app.error)
    assert not app.success
    assert repo.get_active_plan(case.case_id) == plan
    assert len(repo.list_approved_plans(case.case_id)) == 1


def test_two_dashboard_sessions_reject_stale_status_submission(saved, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    path, repo, case, plan = saved
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    apps = []
    for _ in range(2):
        app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10)
        app.session_state['case_id'] = str(case.case_id)
        app.session_state['recovery_page'] = 'dashboard'
        app.run()
        apps.append(app)
    for app, status in zip(apps, [TaskStatus.IN_PROGRESS, TaskStatus.NOT_STARTED]):
        next(s for s in app.selectbox if s.label == 'Task status').select(status)
        next(b for b in app.button if b.label == 'Save task status').click().run()
    assert any('stale task update' in e.value for e in apps[1].error)
    assert not apps[1].success
    assert repo.get_active_plan(case.case_id).proposed_tasks[0].status is TaskStatus.IN_PROGRESS


def test_dashboard_refresh_resets_stale_status_widget(saved, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    path, repo, case, plan = saved
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10)
    app.session_state['case_id'] = str(case.case_id)
    app.session_state['recovery_page'] = 'dashboard'
    app.run()
    repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.IN_PROGRESS,
                            expected_progress_version=plan.progress_version)
    app.run()
    assert next(s for s in app.selectbox if s.label == 'Task status').value == TaskStatus.IN_PROGRESS


def test_emergency_controls_survive_danger_persistence_failure(saved, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    path, repo, case, plan = saved
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10)
    app.session_state['case_id'] = str(case.case_id)
    app.session_state['recovery_page'] = 'dashboard'
    app.run()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_danger BEFORE UPDATE ON recovery_cases BEGIN SELECT RAISE(ABORT, 'fictional failure'); END")
    next(b for b in app.button if b.label == 'Report immediate danger').click().run()
    assert any('Emergency handoff' in e.value for e in app.error)
    assert any('could not be saved across sessions' in w.value for w in app.warning)
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert "I Can't Call 911" in [b.label for b in app.button]
    assert 'Save task status' not in [b.label for b in app.button]
    assert not app.success
    assert repo.get_active_plan(case.case_id) == plan
