from pathlib import Path
from uuid import UUID

import pytest

from recovery.assessment import (
    RecoveryAssessmentOutcome,
    RecoveryIntakeNotPermitted,
    evaluate_recovery_intake,
    start_recovery_case,
)
from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import (
    PlanStatus,
    RecoveryCase,
    RecoveryIntake,
    TaskStatus,
)


def make_hurricane_intake(immediate_danger: bool | None) -> RecoveryIntake:
    return RecoveryIntake(
        disaster_type="fictional hurricane",
        housing_condition="fictional roof and window damage",
        utility_availability={"electricity": False, "water": None},
        temporary_accommodation_status="fictional temporary shelter",
        immediate_danger=immediate_danger,
        household_recovery_needs=[
            "temporary housing",
            "clean water and household supplies",
            "transportation to collect supplies",
            "damage documentation",
        ],
    )


def test_complete_recovery_workflow(tmp_path: Path) -> None:
    database_path = tmp_path / "recovery.db"
    repository = SQLiteRecoveryRepository(database_path)
    intake = make_hurricane_intake(False)

    assessment = evaluate_recovery_intake(intake)
    assert assessment.outcome is RecoveryAssessmentOutcome.CONTINUE_RECOVERY

    case = start_recovery_case(intake, repository)
    assert repository.get_case(case.case_id) == case

    plan = create_demo_draft_plan(case)
    assert plan.approval_status is PlanStatus.DRAFT
    assert 4 <= len(plan.proposed_tasks) <= 6
    assert all(task.status is TaskStatus.NOT_STARTED for task in plan.proposed_tasks)
    assert all(task.source_reference is None for task in plan.proposed_tasks)
    assert len({task.title for task in plan.proposed_tasks}) == len(plan.proposed_tasks)
    assert any("transportation" in task.title.casefold() for task in plan.proposed_tasks)

    repository.save_draft_plan(plan)
    assert repository.get_active_plan(case.case_id) is None

    approved_plan = repository.approve_plan(plan.plan_id)
    assert approved_plan.approval_status is PlanStatus.APPROVED
    assert repository.get_active_plan(case.case_id) == approved_plan

    completed_task = approved_plan.proposed_tasks[0]
    repository.update_task_status(
        plan.plan_id, completed_task.task_id, TaskStatus.COMPLETED
    )

    reopened_repository = SQLiteRecoveryRepository(database_path)
    active_plan = reopened_repository.get_active_plan(case.case_id)

    assert active_plan is not None
    assert active_plan.approval_status is PlanStatus.APPROVED
    task_statuses = {task.task_id: task.status for task in active_plan.proposed_tasks}
    assert task_statuses[completed_task.task_id] is TaskStatus.COMPLETED
    assert all(
        status is TaskStatus.NOT_STARTED
        for task_id, status in task_statuses.items()
        if task_id != completed_task.task_id
    )
    assert reopened_repository.get_case(case.case_id) == case


@pytest.mark.parametrize(
    ("immediate_danger", "expected_outcome"),
    [
        (True, RecoveryAssessmentOutcome.EMERGENCY_HANDOFF),
        (None, RecoveryAssessmentOutcome.DANGER_NOT_ASSESSED),
    ],
)
def test_danger_states_block_demo_plan_generation(
    immediate_danger: bool | None,
    expected_outcome: RecoveryAssessmentOutcome,
) -> None:
    case = RecoveryCase(intake=make_hurricane_intake(immediate_danger))

    with pytest.raises(RecoveryIntakeNotPermitted) as error:
        create_demo_draft_plan(case)

    assert error.value.assessment.outcome is expected_outcome


def test_demo_plan_is_draft_with_inactive_tasks_and_no_citations() -> None:
    case = RecoveryCase(intake=make_hurricane_intake(False))

    plan = create_demo_draft_plan(case)

    assert plan.approval_status is PlanStatus.DRAFT
    assert all(task.status is TaskStatus.NOT_STARTED for task in plan.proposed_tasks)
    assert all(task.source_reference is None for task in plan.proposed_tasks)


def test_demo_plan_generates_unique_tasks() -> None:
    case = RecoveryCase(intake=make_hurricane_intake(False))

    plan = create_demo_draft_plan(case)

    titles = [task.title.casefold() for task in plan.proposed_tasks]
    assert len(titles) >= 4
    assert len(titles) == len(set(titles))