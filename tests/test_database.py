import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from recovery import (
    PlanStatus,
    RecoveryCase,
    RecoveryIntake,
    RecoveryPlan,
    RecoveryTask,
    TaskPriority,
    TaskStatus,
)
from recovery.database import SQLiteRecoveryRepository


def make_case(immediate_danger: bool | None = None) -> RecoveryCase:
    return RecoveryCase(
        case_id=UUID("11111111-1111-4111-8111-111111111111"),
        intake=RecoveryIntake(
            disaster_type="fictional flood",
            housing_condition="fictional minor water damage",
            utility_availability={"electricity": False, "water": None},
            temporary_accommodation_status="fictional temporary lodging",
            immediate_danger=immediate_danger,
            household_recovery_needs=["fictional shelter support"],
        ),
        created_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )


def make_task(
    task_id: UUID = UUID("22222222-2222-4222-8222-222222222222"),
) -> RecoveryTask:
    return RecoveryTask(
        task_id=task_id,
        title="Find fictional temporary lodging",
        description="Record a fictional accommodation option for review.",
        priority=TaskPriority.MEDIUM,
        reason_for_recommendation="The fictional household requested shelter support.",
        source_reference="fictional-intake-001",
    )


def make_plan(
    case_id: UUID,
    plan_id: UUID | None = None,
    proposed_tasks: list[RecoveryTask] | None = None,
) -> RecoveryPlan:
    plan_data: dict[str, object] = {
        "case_id": case_id,
        "proposed_tasks": proposed_tasks if proposed_tasks is not None else [make_task()],
    }
    if plan_id is not None:
        plan_data["plan_id"] = plan_id
    return RecoveryPlan.model_validate(plan_data)


def test_recovery_case_is_saved_and_retrieved(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case()

    repository.create_case(case)

    assert repository.get_case(case.case_id) == case


def test_recovery_case_survives_repository_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "recovery.db"
    case = make_case()
    SQLiteRecoveryRepository(database_path).create_case(case)

    reopened_repository = SQLiteRecoveryRepository(database_path)

    assert reopened_repository.get_case(case.case_id) == case


def test_unknown_case_returns_none(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")

    assert repository.get_case(UUID("33333333-3333-4333-8333-333333333333")) is None


def test_duplicate_case_id_is_rejected(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case()
    repository.create_case(case)

    with pytest.raises(sqlite3.IntegrityError):
        repository.create_case(case)


def test_draft_plan_and_tasks_are_saved_and_retrieved(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case()
    repository.create_case(case)
    plan = make_plan(case.case_id)

    repository.save_draft_plan(plan)
    retrieved_plan = repository.get_plan(plan.plan_id)

    assert retrieved_plan is not None
    assert retrieved_plan == plan
    assert retrieved_plan.approval_status is PlanStatus.DRAFT
    assert retrieved_plan.proposed_tasks == [make_task()]
    assert retrieved_plan.proposed_tasks[0].status is TaskStatus.NOT_STARTED


def test_unknown_plan_returns_none(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")

    assert repository.get_plan(UUID("44444444-4444-4444-8444-444444444444")) is None


def test_plan_for_unknown_case_is_rejected(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    plan = make_plan(UUID("55555555-5555-4555-8555-555555555555"))

    with pytest.raises(sqlite3.IntegrityError):
        repository.save_draft_plan(plan)


def test_approved_plan_cannot_be_saved_as_draft(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case()
    repository.create_case(case)
    plan = make_plan(case.case_id).model_copy(
        update={"approval_status": PlanStatus.APPROVED}
    )

    with pytest.raises(ValueError, match="only draft plans can be saved"):
        repository.save_draft_plan(plan)

    assert repository.get_plan(plan.plan_id) is None


def test_duplicate_plan_id_is_rejected(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case()
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)

    with pytest.raises(sqlite3.IntegrityError):
        repository.save_draft_plan(plan)


def test_older_draft_plan_remains_available(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case()
    repository.create_case(case)
    first_plan = make_plan(
        case.case_id, UUID("66666666-6666-4666-8666-666666666666")
    )
    second_plan = make_plan(
        case.case_id, UUID("77777777-7777-4777-8777-777777777777")
    )

    repository.save_draft_plan(first_plan)
    repository.save_draft_plan(second_plan)

    assert repository.get_plan(first_plan.plan_id) == first_plan
    assert repository.get_plan(second_plan.plan_id) == second_plan


def test_draft_plan_approval_succeeds(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id)

    repository.save_draft_plan(plan)
    approved_plan = repository.approve_plan(plan.plan_id)

    assert approved_plan.approval_status is PlanStatus.APPROVED
    assert repository.get_plan(plan.plan_id) == approved_plan


def test_approval_persists_after_repository_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "recovery.db"
    repository = SQLiteRecoveryRepository(database_path)
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)
    repository.approve_plan(plan.plan_id)

    reopened_repository = SQLiteRecoveryRepository(database_path)

    assert reopened_repository.get_plan(plan.plan_id).approval_status is PlanStatus.APPROVED
    assert reopened_repository.get_active_plan(case.case_id).plan_id == plan.plan_id


def test_unknown_plan_approval_fails_clearly(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")

    with pytest.raises(ValueError, match="does not exist"):
        repository.approve_plan(UUID("88888888-8888-4888-8888-888888888888"))


def test_empty_plan_approval_fails_without_persisting_changes(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id, proposed_tasks=[])
    repository.save_draft_plan(plan)

    with pytest.raises(ValueError, match="empty recovery plan"):
        repository.approve_plan(plan.plan_id)

    assert repository.get_plan(plan.plan_id) == plan
    assert repository.get_active_plan(case.case_id) is None


def test_repeated_approval_is_rejected(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)
    repository.approve_plan(plan.plan_id)

    with pytest.raises(ValueError, match="not a draft"):
        repository.approve_plan(plan.plan_id)


def test_approval_is_blocked_when_danger_is_reported(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=True)
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)

    with pytest.raises(ValueError, match="immediate danger is reported"):
        repository.approve_plan(plan.plan_id)

    assert repository.get_plan(plan.plan_id) == plan
    assert repository.get_active_plan(case.case_id) is None


def test_unassessed_danger_blocks_approval(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case()
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)

    with pytest.raises(ValueError, match="must be explicitly assessed"):
        repository.approve_plan(plan.plan_id)


def test_active_plan_is_empty_before_approval_and_available_after(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)

    assert repository.get_active_plan(case.case_id) is None

    repository.approve_plan(plan.plan_id)

    assert repository.get_active_plan(case.case_id) == repository.get_plan(plan.plan_id)


def test_initial_approval_cannot_replace_active_plan(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    first_task = make_task()
    first_plan = make_plan(
        case.case_id,
        UUID("99999999-9999-4999-8999-999999999999"),
        [first_task],
    )
    second_plan = make_plan(
        case.case_id,
        UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    )
    repository.save_draft_plan(first_plan)
    repository.approve_plan(first_plan.plan_id)
    repository.update_task_status(
        first_plan.plan_id, first_task.task_id, TaskStatus.COMPLETED
    )
    repository.save_draft_plan(second_plan)

    with pytest.raises(ValueError, match="use reassessment"):
        repository.approve_plan(second_plan.plan_id)

    assert repository.get_active_plan(case.case_id).plan_id == first_plan.plan_id
    previous_plan = repository.get_plan(first_plan.plan_id)
    assert previous_plan is not None
    assert previous_plan.approval_status is PlanStatus.APPROVED
    assert previous_plan.proposed_tasks[0].status is TaskStatus.COMPLETED


def test_task_updates_require_approved_active_plan(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    draft_plan = make_plan(case.case_id)
    repository.save_draft_plan(draft_plan)

    with pytest.raises(ValueError, match="approved plan"):
        repository.update_task_status(
            draft_plan.plan_id, draft_plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED
        )

    repository.approve_plan(draft_plan.plan_id)
    newer_plan = make_plan(
        case.case_id, UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    )
    repository.save_draft_plan(newer_plan)
    from recovery.reassessment import preview_reassessment
    revision = preview_reassessment(case, repository.get_active_plan(case.case_id), case.intake)
    repository.approve_reassessment(revision, explicitly_approved=True)

    with pytest.raises(ValueError, match="active plan"):
        repository.update_task_status(
            draft_plan.plan_id, draft_plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED
        )


def test_task_status_update_persists_after_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "recovery.db"
    repository = SQLiteRecoveryRepository(database_path)
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)
    repository.approve_plan(plan.plan_id)

    updated_task = repository.update_task_status(
        plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.IN_PROGRESS
    )
    reopened_repository = SQLiteRecoveryRepository(database_path)

    assert updated_task.status is TaskStatus.IN_PROGRESS
    assert (
        reopened_repository.get_plan(plan.plan_id).proposed_tasks[0].status
        is TaskStatus.IN_PROGRESS
    )


def test_unknown_task_id_is_rejected(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)
    repository.approve_plan(plan.plan_id)

    with pytest.raises(ValueError, match="does not belong"):
        repository.update_task_status(
            plan.plan_id,
            UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
            TaskStatus.COMPLETED,
        )


def test_updating_one_task_preserves_other_tasks(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    first_task = make_task()
    second_task = make_task(UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"))
    plan = make_plan(case.case_id, proposed_tasks=[first_task, second_task])
    repository.save_draft_plan(plan)
    repository.approve_plan(plan.plan_id)

    repository.update_task_status(plan.plan_id, first_task.task_id, TaskStatus.COMPLETED)

    updated_plan = repository.get_plan(plan.plan_id)
    assert updated_plan.proposed_tasks[0].status is TaskStatus.COMPLETED
    assert updated_plan.proposed_tasks[1] == second_task


def test_failed_task_update_leaves_plan_unchanged(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = make_case(immediate_danger=False)
    repository.create_case(case)
    plan = make_plan(case.case_id)
    repository.save_draft_plan(plan)
    repository.approve_plan(plan.plan_id)
    stored_plan = repository.get_plan(plan.plan_id)

    with pytest.raises(ValueError, match="invalid task status"):
        repository.update_task_status(
            plan.plan_id,
            plan.proposed_tasks[0].task_id,
            "NOT_A_STATUS",  # type: ignore[arg-type]
        )

    assert repository.get_plan(plan.plan_id) == stored_plan


def test_existing_database_schema_is_migrated(tmp_path: Path) -> None:
    database_path = tmp_path / "recovery.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE recovery_cases (case_id TEXT PRIMARY KEY, case_json TEXT NOT NULL)"
        )
        connection.execute(
            """
            CREATE TABLE recovery_plans (
                plan_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES recovery_cases (case_id)
            )
            """
        )

    repository = SQLiteRecoveryRepository(database_path)
    columns = {
        row[1]
        for row in sqlite3.connect(database_path).execute(
            "PRAGMA table_info(recovery_cases)"
        )
    }

    assert "active_plan_id" in columns
    assert repository.get_case(make_case().case_id) is None