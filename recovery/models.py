from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class PlanStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class RecoveryIntake(BaseModel):
    disaster_type: str = Field(min_length=1)
    housing_condition: str = Field(min_length=1)
    utility_availability: dict[str, bool | None]
    temporary_accommodation_status: str = Field(min_length=1)
    immediate_danger: bool | None = Field(
        description=(
            "True means danger reported, False means no immediate danger reported, "
            "and None means not assessed."
        )
    )
    household_recovery_needs: list[str]

    @field_validator(
        "disaster_type", "housing_condition", "temporary_accommodation_status"
    )
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("household_recovery_needs")
    @classmethod
    def reject_blank_recovery_needs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("recovery needs must not contain blank entries")
        return values


class RecoveryCase(BaseModel):
    case_id: UUID = Field(default_factory=uuid4)
    intake: RecoveryIntake
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_timezone_and_normalize_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)


class RecoveryTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1)
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.NOT_STARTED
    reason_for_recommendation: str = Field(min_length=1)
    source_reference: str | None = None

    @field_validator("title", "reason_for_recommendation")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class RecoveryPlan(BaseModel):
    planning_disclosure: str | None = None
    progress_version: int = Field(default=0, ge=0)
    plan_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    proposed_tasks: list[RecoveryTask]
    approval_status: PlanStatus = PlanStatus.DRAFT