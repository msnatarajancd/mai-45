r"""Manual only: .venv\Scripts\python.exe smoke_nebius.py

Uses synthetic data, prints only validated draft or a sanitized failure, never
credentials. Does not import or instantiate the recovery repository.
"""
from recovery.ai_planner import AIPlanningError, create_ai_draft_plan
from recovery.llm_client import NebiusClient
from recovery.models import RecoveryCase, RecoveryIntake


def main() -> int:
    case = RecoveryCase(intake=RecoveryIntake(
        disaster_type='Fictional flood', housing_condition='Fictional reported roof damage',
        utility_availability={'electricity': False, 'water': None},
        temporary_accommodation_status='Fictional stay with relatives',
        immediate_danger=False, household_recovery_needs=['Household supplies', 'Transportation'],
    ))
    try:
        plan = create_ai_draft_plan(case, [], NebiusClient())
    except AIPlanningError as error:
        print(f'Planning failed: {error}')
        return 1
    print(plan.model_dump_json(indent=2))
    return 0


def run_ui_smoke() -> dict:
    """Exercise the existing UI via AppTest with real Nebius unless explicitly mocked.

    Manual invocation only; temporary SQLite stores synthetic data and is removed
    after completion. No credentials or model/provider error bodies are printed.
    This verifies Streamlit event flow, not rendered browser appearance.
    """
    import os
    import sqlite3
    from contextlib import closing
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from unittest.mock import patch
    from uuid import UUID

    from streamlit.testing.v1 import AppTest
    from recovery.database import SQLiteRecoveryRepository
    from recovery.models import PlanStatus, TaskStatus

    app_path = Path(__file__).resolve().parent / 'dev_recovery_preview.py'
    original_complete = NebiusClient.complete
    calls = []

    def counted_complete(client, messages):
        calls.append(True)
        return original_complete(client, messages)

    def button(app, label):
        return next(b for b in app.button if b.label == label)

    def checked(app):
        if app.exception or app.error:
            raise AIPlanningError('UI smoke test failed; no provider output or household context is included in this report.')
        return app

    with TemporaryDirectory(prefix='readyrelief_ui_smoke_') as directory:
        path = Path(directory) / 'synthetic_recovery.sqlite3'
        with patch.dict(os.environ, {'READYRELIEF_DB_PATH': str(path)}), patch.object(NebiusClient, 'complete', counted_complete):
            app = checked(AppTest.from_file(str(app_path), default_timeout=90).run())
            button(app, 'Start Recovery Assessment').click().run()
            checked(app)
            next(s for s in app.selectbox if s.label == 'Disaster type').select('Hurricane')
            next(s for s in app.selectbox if s.label == 'Housing condition').select('Major reported damage')
            next(s for s in app.selectbox if s.label == 'Electricity availability').select('Unavailable')
            next(s for s in app.selectbox if s.label == 'Immediate danger assessment').select('No immediate danger reported')
            button(app, 'Continue').click().run()
            checked(app)
            case_id = UUID(app.session_state['case_id'])
            repo = SQLiteRecoveryRepository(path)
            if calls:
                raise AIPlanningError('Provider was called before explicit AI generation.')
            next(r for r in app.radio if r.label == 'Initial planner').set_value('AI-assisted (experimental)').run()
            checked(app)
            if calls:
                raise AIPlanningError('Provider was called on planner selection alone.')
            button(app, 'Generate AI Draft Plan').click().run()
            checked(app)
            with closing(sqlite3.connect(path)) as connection:
                plan_rows = connection.execute('SELECT count(*) FROM recovery_plans').fetchone()[0]
            active_before = repo.get_active_plan(case_id) is not None
            if plan_rows or active_before or not calls:
                raise AIPlanningError('Generation unexpectedly persisted state or did not invoke the provider.')
            evidence_visible = any('Evidence: no verified source reference' in item.value for item in app.caption)
            if not evidence_visible or not any('UNGROUNDED EXPERIMENTAL AI OUTPUT' in w.value for w in app.warning):
                raise AIPlanningError('Required experimental/evidence disclosure is missing.')
            button(app, 'Approve Recovery Plan').click().run()
            checked(app)
            plan = repo.get_active_plan(case_id)
            if plan is None or plan.approval_status is not PlanStatus.APPROVED:
                raise AIPlanningError('Explicit approval did not activate the plan.')
            if not all(t.status is TaskStatus.NOT_STARTED for t in plan.proposed_tasks):
                raise AIPlanningError('Unexpected initial task state.')
            first_id = plan.proposed_tasks[0].task_id
            next(s for s in app.selectbox if s.label == 'Task status').select(TaskStatus.COMPLETED)
            button(app, 'Save task status').click().run()
            checked(app)
            resumed = checked(AppTest.from_file(str(app_path), default_timeout=90).run())
            button(resumed, 'Resume Existing Recovery').click().run()
            next(t for t in resumed.text_input if t.label == 'Fictional recovery case ID').set_value(str(case_id))
            button(resumed, 'Resume Recovery').click().run()
            checked(resumed)
            reopened = SQLiteRecoveryRepository(path).get_active_plan(case_id)
            completed = next(t for t in reopened.proposed_tasks if t.task_id == first_id)
            if completed.status is not TaskStatus.COMPLETED or not any('COMPLETED' in e.label for e in resumed.expander):
                raise AIPlanningError('Completed progress did not survive resuming the case.')
            return dict(harness='Streamlit AppTest using existing dev_recovery_preview.py',
                scenario='Fictional hurricane', generation_plan_rows=plan_rows,
                active_before_approval=active_before, validated_task_count=len(plan.proposed_tasks),
                task_evidence_status_visible=evidence_visible, explicit_approval_persisted=True,
                resumed_completed_status=completed.status.value, provider_calls=len(calls),
                database='Temporary synthetic database; removed after test')


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Manual Nebius smoke tests; never run by pytest automatically.')
    parser.add_argument('--ui', action='store_true', help='Run the existing Streamlit UI event journey with real Nebius.')
    args = parser.parse_args()
    if args.ui:
        try:
            print(json.dumps(run_ui_smoke(), indent=2))
        except AIPlanningError as error:
            print(str(error))
            raise SystemExit(1)
    else:
        raise SystemExit(main())