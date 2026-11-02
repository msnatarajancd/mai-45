from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from recovery import (
    PlanStatus,
    RecoveryCase,
    RecoveryIntake,
    RecoveryPlan,
    RecoveryTask,
    TaskPriority,
    TaskStatus,
)


def valid_intake_data() -> dict[str, object]:
    return {
        "disaster_type": "flood",
        "housing_condition": "minor water damage",
        "utility_availability": {"electricity": False, "water": True},
        "temporary_accommodation_status": "staying with family",
        "immediate_danger": None,
        "household_recovery_needs": ["temporary shelter", "clean drinking water"],
    }


def valid_task_data() -> dict[str, object]:
    return {
        "title": "Arrange temporary shelter",
        "description": "Identify an available short-term accommodation option.",
        "priority": TaskPriority.HIGH,
        "reason_for_recommendation": "The household cannot currently use its home.",
    }


def test_valid_recovery_intake() -> None:
    intake = RecoveryIntake.model_validate(valid_intake_data())

    assert intake.disaster_type == "flood"
    assert intake.utility_availability["electricity"] is False


def test_recovery_intake_requires_fields() -> None:
    with pytest.raises(ValidationError):
        RecoveryIntake.model_validate({"disaster_type": "flood"})


@pytest.mark.parametrize(
    "field",
    ["disaster_type", "housing_condition", "temporary_accommodation_status"],
)
def test_recovery_intake_rejects_whitespace_required_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        RecoveryIntake.model_validate({**valid_intake_data(), field: "  \t "})


def test_recovery_intake_rejects_blank_recovery_needs_but_allows_empty_list() -> None:
    with pytest.raises(ValidationError):
        RecoveryIntake.model_validate(
            {**valid_intake_data(), "household_recovery_needs": ["shelter", "  "]}
        )

    intake = RecoveryIntake.model_validate(
        {**valid_intake_data(), "household_recovery_needs": []}
    )
    assert intake.household_recovery_needs == []


def test_utility_availability_accepts_available_unavailable_and_unknown() -> None:
    intake = RecoveryIntake.model_validate(
        {
            **valid_intake_data(),
            "utility_availability": {
                "electricity": True,
                "water": False,
                "gas": None,
            },
        }
    )

    assert intake.utility_availability == {
        "electricity": True,
        "water": False,
        "gas": None,
    }


def test_task_creation_generates_uuid_and_accepts_source_reference() -> None:
    task = RecoveryTask.model_validate(
        {**valid_task_data(), "source_reference": "synthetic-intake-001"}
    )

    assert isinstance(task.task_id, UUID)
    assert task.priority is TaskPriority.HIGH
    assert task.source_reference == "synthetic-intake-001"


def test_invalid_task_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RecoveryTask.model_validate({**valid_task_data(), "status": "UNKNOWN"})


@pytest.mark.parametrize("field", ["title", "reason_for_recommendation"])
def test_task_rejects_whitespace_required_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        RecoveryTask.model_validate({**valid_task_data(), field: " \t "})


def test_plan_defaults_to_draft() -> None:
    plan = RecoveryPlan(
        case_id=UUID("12345678-1234-5678-1234-567812345678"),
        proposed_tasks=[RecoveryTask.model_validate(valid_task_data())],
    )

    assert isinstance(plan.plan_id, UUID)
    assert plan.approval_status is PlanStatus.DRAFT


def test_immediate_danger_is_preserved_and_not_assessed_is_explicit() -> None:
    reported_danger = RecoveryIntake.model_validate(
        {**valid_intake_data(), "immediate_danger": True}
    )
    no_danger_reported = RecoveryIntake.model_validate(
        {**valid_intake_data(), "immediate_danger": False}
    )
    not_assessed = RecoveryIntake.model_validate(valid_intake_data())

    assert reported_danger.immediate_danger is True
    assert no_danger_reported.immediate_danger is False
    assert not_assessed.immediate_danger is None


def test_task_status_defaults_to_not_started() -> None:
    task = RecoveryTask.model_validate(valid_task_data())

    assert task.status is TaskStatus.NOT_STARTED


def test_case_timestamps_are_utc_and_reject_naive_values() -> None:
    case = RecoveryCase(intake=RecoveryIntake.model_validate(valid_intake_data()))

    assert case.created_at.tzinfo is timezone.utc
    assert case.updated_at.tzinfo is timezone.utc
    with pytest.raises(ValidationError):
        RecoveryCase(
            intake=RecoveryIntake.model_validate(valid_intake_data()),
            created_at=datetime(2026, 11, 1),
        )