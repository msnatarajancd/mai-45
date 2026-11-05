from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HouseholdRecoveryDetails(BaseModel):
    """Additional confirmed facts; absent values are never household defaults."""
    model_config = ConfigDict(extra='forbid')
    children: int | None = Field(default=None, ge=0, strict=True)
    adults: int | None = Field(default=None, ge=0, strict=True)
    reported_property_damage: str | None = Field(default=None, max_length=2000)
    wants_insurance_help: bool | None = Field(default=None, strict=True)
    housing_type: str | None = Field(default=None, max_length=120)
    accessibility_needs: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(default_factory=list, max_length=5)
    insurer_contact_status: Literal['Unknown', 'Not contacted', 'Contacted', 'Follow-up requested'] = 'Unknown'


class DamageRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    damage_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    item_description: str = Field(min_length=1, max_length=500)
    damage_description: str = Field(min_length=1, max_length=2000)
    incident_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator('item_description', 'damage_description')
    @classmethod
    def require_reported_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('a reported description is required')
        return value


class RecoveryRecords(BaseModel):
    """One versioned aggregate, including damage IDs, bound to a single case."""
    model_config = ConfigDict(extra='forbid')
    case_id: UUID
    reported_county: Literal['Miami-Dade'] | None = None
    version: int = Field(default=0, ge=0, strict=True)
    household: HouseholdRecoveryDetails = Field(default_factory=HouseholdRecoveryDetails)
    damage_records: list[DamageRecord] = Field(default_factory=list, max_length=100)
    incident_date: date | None = None
    next_check_in_date: date | None = None


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
    planning_key: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    resource_categories: list[Literal["Housing", "Disaster assistance", "Electricity", "Water"]] = Field(default_factory=list)

    @field_validator("title", "reason_for_recommendation")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class TaskReview(BaseModel):
    priority: TaskPriority | None = None
    applicable: bool = True
    description: str
    explanation: str


class RecoveryPlan(BaseModel):
    planning_basis: RecoveryCase | None = None
    records_version: int | None = None
    task_reviews: dict[str, TaskReview] = Field(default_factory=dict)
    confirmed_damage_ids: list[UUID] = Field(default_factory=list)
    planning_disclosure: str | None = None
    progress_version: int = Field(default=0, ge=0)
    plan_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    proposed_tasks: list[RecoveryTask]
    approval_status: PlanStatus = PlanStatus.DRAFT
