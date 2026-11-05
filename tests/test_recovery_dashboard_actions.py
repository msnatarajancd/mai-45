"""Dashboard controls must expose the persisted work and review actual intake."""
from uuid import UUID

import pytest

from recovery.database import SQLiteRecoveryRepository
from recovery.models import TaskStatus
from recovery.task_view import current_task_views
from test_recovery_landing import app, button


def _load_checkpoint(app, scenario_id, day):
    next(widget for widget in app.selectbox if widget.label == 'Fictional household').select(scenario_id).run()
    next(widget for widget in app.selectbox if widget.label == 'Story checkpoint').select(day)
    button(app, 'Load fictional checkpoint').click().run()
    assert not app.exception
    return (SQLiteRecoveryRepository(app.session_state['rr_demo_database_path']),
            UUID(app.session_state['rr_case_id']))


@pytest.mark.parametrize('label,status', [
    ('Not started', TaskStatus.NOT_STARTED), ('In progress', TaskStatus.IN_PROGRESS),
])
def test_dashboard_status_filter_exposes_matching_saved_tasks_without_writes(app, label, status):
    repo, case_id = _load_checkpoint(app, 'bennett', 3)
    plan = repo.get_active_plan(case_id)
    expected = ['Status · '+view.task.title for view in current_task_views(plan)
                if view.applicable and view.task.status is status]
    assert expected  # This fixture actually exercises both multiword filter labels.
    events_before = repo.list_journey_events(case_id)

    next(widget for widget in app.selectbox if widget.label == 'Show tasks').select(label).run()

    assert not app.exception
    controls = [widget for widget in app.selectbox if widget.label.startswith('Status · ')]
    assert [widget.label for widget in controls] == expected
    assert all(widget.value == status for widget in controls)
    assert len([widget for widget in app.button if widget.label == 'Save progress']) == len(expected)
    assert repo.get_active_plan(case_id) == plan
    assert repo.list_journey_events(case_id) == events_before


def test_review_edit_situation_edits_authoritative_intake_only_after_approval(app):
    repo, case_id = _load_checkpoint(app, 'rivera', 7)
    case_before = repo.get_case(case_id)
    plan_before = repo.get_active_plan(case_id)
    events_before = repo.list_journey_events(case_id)
    assert case_before.intake.utility_availability['electricity'] is True
    assert 'transportation' in case_before.intake.household_recovery_needs

    button(app, 'Review or edit your situation').click().run()

    assert not app.exception
    labels = {widget.label for widget in app.selectbox}
    assert {'Housing condition', 'Temporary accommodation', 'Electricity availability',
            'Water availability', 'Updated immediate danger assessment'} <= labels
    needs = next(widget for widget in app.multiselect if widget.label == 'Household recovery needs')
    assert 'transportation' in needs.value
    next(widget for widget in app.selectbox if widget.label == 'Updated immediate danger assessment').select(
        'No immediate danger reported').run()
    next(widget for widget in app.selectbox if widget.label == 'Electricity availability').select('Unavailable')
    next(widget for widget in app.multiselect if widget.label == 'Household recovery needs').set_value(
        [need for need in case_before.intake.household_recovery_needs if need != 'transportation'])
    button(app, 'Preview proposed changes').click().run()

    assert not app.exception
    assert repo.get_case(case_id) == case_before
    assert repo.get_active_plan(case_id) == plan_before
    assert repo.list_journey_events(case_id) == events_before
    button(app, 'Approve this revision').click().run()

    assert not app.exception
    saved = repo.get_case(case_id)
    assert saved.intake.utility_availability['electricity'] is False
    assert 'transportation' not in saved.intake.household_recovery_needs
    plan_after = repo.get_active_plan(case_id)
    assert plan_after.plan_id != plan_before.plan_id
    after_statuses = {task.task_id: task.status for task in plan_after.proposed_tasks}
    assert all(after_statuses[task.task_id] == task.status for task in plan_before.proposed_tasks)
    transport = next(view for view in current_task_views(plan_after) if view.task.planning_key == 'transport')
    assert not transport.applicable
    assert transport.task.status is TaskStatus.BLOCKED
    assert repo.list_journey_events(case_id)[-1]['kind'] == 'revision_approved'
