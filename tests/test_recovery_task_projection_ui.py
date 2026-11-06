"""Secondary screens retain reviewed task priority/order and historical progress."""
import pytest
from streamlit.testing.v1 import AppTest

from recovery.database import SQLiteRecoveryRepository
from recovery.models import (RecoveryCase, RecoveryIntake, RecoveryPlan, RecoveryTask,
                             TaskPriority, TaskReview, TaskStatus)


@pytest.mark.parametrize('screen', ['assistant', 'legacy'])
def test_secondary_screens_order_reviewed_priority_and_keep_historical_work(tmp_path, screen):
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood',
        housing_condition='Minor reported damage', utility_availability={'water': True},
        temporary_accommodation_status='Staying with others', immediate_danger=False,
        household_recovery_needs=[]))
    original = RecoveryTask(title='Originally first', description='Original description',
        priority=TaskPriority.HIGH, reason_for_recommendation='Reported need')
    reviewed = RecoveryTask(title='Reviewed urgent follow-up', description='Earlier description',
        priority=TaskPriority.LOW, reason_for_recommendation='Earlier reported need')
    historical = RecoveryTask(title='Completed historical work', description='Earlier work',
        priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED,
        reason_for_recommendation='Earlier need')
    draft = RecoveryPlan(case_id=case.case_id, proposed_tasks=[original, reviewed, historical], task_reviews={
        str(reviewed.task_id): TaskReview(priority=TaskPriority.URGENT, description='Current reviewed description',
                                         explanation='Current reported need'),
        str(historical.task_id): TaskReview(applicable=False, description='Historical work', explanation='Reported need changed'),
    })
    repo = SQLiteRecoveryRepository(tmp_path / 'secondary.sqlite3')
    repo.create_case(case)
    plan = repo.approve_plan(draft.plan_id, new_draft=draft, explicitly_approved=True)
    before = plan.model_dump_json()
    if screen == 'assistant':
        def render_assistant(raw):
            from ui.assistant_page import show_draft
            show_draft(raw)
        view = AppTest.from_function(render_assistant, args=(plan.model_dump_json(),)).run()
        headings = [widget.value for widget in view.markdown if widget.value.startswith('**') and ' / ' in widget.value]
        assert 'Reviewed urgent follow-up' in headings[0] and 'URGENT' in headings[0]
        assert 'Originally first' in headings[1]
        assert any('Completed historical work' in widget.value and 'COMPLETED' in widget.value for widget in view.caption)
    else:
        def render_legacy(path, case_id):
            import streamlit as st
            from recovery.database import SQLiteRecoveryRepository
            from recovery.ui import _render_dashboard
            st.session_state['case_id'] = case_id
            _render_dashboard(SQLiteRecoveryRepository(path))
        view = AppTest.from_function(render_legacy, args=(str(tmp_path / 'secondary.sqlite3'), str(case.case_id))).run()
        labels = [widget.label for widget in view.expander if widget.label.startswith(('Originally first', 'Reviewed urgent', 'No longer applicable:'))]
        assert labels[0].startswith('Reviewed urgent follow-up')
        assert labels[1].startswith('Originally first')
        assert labels[2] == 'No longer applicable: Completed historical work'
        assert len([widget for widget in view.selectbox if widget.label == 'Task status']) == 2
        assert any('Historical saved status: COMPLETED' in widget.value for widget in view.caption)
    assert not view.exception
    assert any(widget.value == 'Current reviewed description' for widget in view.markdown)
    assert repo.get_active_plan(case.case_id).model_dump_json() == before
