from enum import StrEnum

from pydantic import BaseModel

from .database import SQLiteRecoveryRepository
from .models import RecoveryCase, RecoveryIntake


class RecoveryAssessmentOutcome(StrEnum):
    EMERGENCY_HANDOFF = "EMERGENCY_HANDOFF"
    DANGER_NOT_ASSESSED = "DANGER_NOT_ASSESSED"
    CONTINUE_RECOVERY = "CONTINUE_RECOVERY"


class RecoveryAssessmentResult(BaseModel):
    outcome: RecoveryAssessmentOutcome


class RecoveryIntakeNotPermitted(ValueError):
    def __init__(self, assessment: RecoveryAssessmentResult) -> None:
        self.assessment = assessment
        super().__init__(f"recovery intake is not permitted: {assessment.outcome}")


def evaluate_recovery_intake(
    intake: RecoveryIntake,
) -> RecoveryAssessmentResult:
    if intake.immediate_danger is True:
        outcome = RecoveryAssessmentOutcome.EMERGENCY_HANDOFF
    elif intake.immediate_danger is None:
        outcome = RecoveryAssessmentOutcome.DANGER_NOT_ASSESSED
    else:
        outcome = RecoveryAssessmentOutcome.CONTINUE_RECOVERY
    return RecoveryAssessmentResult(outcome=outcome)


def start_recovery_case(
    intake: RecoveryIntake | dict[str, object],
    repository: SQLiteRecoveryRepository,
) -> RecoveryCase:
    validated_intake = RecoveryIntake.model_validate(intake)
    assessment = evaluate_recovery_intake(validated_intake)
    if assessment.outcome is not RecoveryAssessmentOutcome.CONTINUE_RECOVERY:
        raise RecoveryIntakeNotPermitted(assessment)

    case = RecoveryCase(intake=validated_intake)
    repository.create_case(case)
    return case