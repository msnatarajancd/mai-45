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
from recovery.models import RecoveryCase, RecoveryIntake


def make_intake(immediate_danger: bool | None) -> RecoveryIntake:
    return RecoveryIntake(
        disaster_type="fictional storm",
        housing_condition="fictional roof damage",
        utility_availability={"electricity": None, "water": False},
        temporary_accommodation_status="fictional temporary lodging",
        immediate_danger=immediate_danger,
        household_recovery_needs=["fictional shelter assistance"],
    )


def test_danger_true_returns_emergency_handoff() -> None:
    result = evaluate_recovery_intake(make_intake(True))

    assert result.outcome is RecoveryAssessmentOutcome.EMERGENCY_HANDOFF


def test_unassessed_danger_returns_danger_not_assessed() -> None:
    result = evaluate_recovery_intake(make_intake(None))

    assert result.outcome is RecoveryAssessmentOutcome.DANGER_NOT_ASSESSED


def test_danger_false_allows_recovery_without_certifying_safety() -> None:
    result = evaluate_recovery_intake(make_intake(False))

    assert result.outcome is RecoveryAssessmentOutcome.CONTINUE_RECOVERY
    assert "safety" not in result.model_dump_json().lower()


def test_valid_intake_creates_recovery_case(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")

    case = start_recovery_case(make_intake(False), repository)

    assert isinstance(case, RecoveryCase)
    assert case.intake.immediate_danger is False


def test_created_recovery_case_persists_in_sqlite(tmp_path: Path) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")
    case = start_recovery_case(make_intake(False), repository)

    assert repository.get_case(case.case_id) == case


@pytest.mark.parametrize(
    ("immediate_danger", "expected_outcome"),
    [
        (None, RecoveryAssessmentOutcome.DANGER_NOT_ASSESSED),
        (True, RecoveryAssessmentOutcome.EMERGENCY_HANDOFF),
    ],
)
def test_danger_states_prevent_normal_case_creation(
    tmp_path: Path,
    immediate_danger: bool | None,
    expected_outcome: RecoveryAssessmentOutcome,
) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")

    with pytest.raises(RecoveryIntakeNotPermitted) as error:
        start_recovery_case(make_intake(immediate_danger), repository)

    assert error.value.assessment.outcome is expected_outcome
    assert repository.get_case(UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")) is None


def test_rejected_intake_does_not_call_repository_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SQLiteRecoveryRepository(tmp_path / "recovery.db")

    def reject_write(case: RecoveryCase) -> None:
        raise AssertionError("repository write must not run for a rejected intake")

    monkeypatch.setattr(repository, "create_case", reject_write)

    with pytest.raises(RecoveryIntakeNotPermitted) as error:
        start_recovery_case(make_intake(True), repository)

    assert error.value.assessment.outcome is RecoveryAssessmentOutcome.EMERGENCY_HANDOFF