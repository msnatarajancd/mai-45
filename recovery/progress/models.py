"""Typed facts shared by deterministic specialists and the preview runtime.

Unknown facts remain None. Presentation dictionaries never drive calculations.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceMode(StrEnum):
    SYNTHETIC = 'synthetic'
    SAVED_CASE = 'saved_case'


class SignalState(StrEnum):
    RED = 'red'
    YELLOW = 'yellow'
    GREEN = 'green'
    UNKNOWN = 'unknown'
    NOT_APPLICABLE = 'not_applicable'


class ExecutionState(StrEnum):
    QUEUED = 'queued'
    CHECKING = 'checking'
    COMPLETE = 'complete'
    NEEDS_INFORMATION = 'needs_information'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class HouseholdContext(Model):
    label: str
    total: int | None = Field(default=None, ge=1, strict=True)
    adults: int | None = Field(default=None, ge=0, strict=True)
    children: int | None = Field(default=None, ge=0, strict=True)
    zip_code: str | None = None
    address: str | None = None
    county: str | None = None
    area: str | None = None
    accessibility: bool | None = None
    pets: bool | None = None
    has_vehicle: bool | None = None
    housing_budget: Decimal | None = Field(default=None, ge=0)
    contribution_band: str | None = None


class Provenance(Model):
    source_mode: SourceMode
    source: str
    observed_at: datetime
    valid_until: datetime | None = None
    scope: str = 'household'

    @field_validator('observed_at', 'valid_until')
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('timestamps must be timezone-aware')
            return value.astimezone(timezone.utc)
        return None


class HousingSite(Model):
    id: str
    name: str
    category: Literal['hotel', 'church', 'school', 'official shelter']
    county: str = 'Miami-Dade'
    area: str
    activated: bool | None = None
    capacity_unit: Literal['rooms', 'spaces']
    available_units: int | None = Field(default=None, ge=0)
    room_occupancy: int | None = Field(default=None, ge=1)
    can_keep_together: bool | None = None
    accessible: bool | None = None
    accepts_pets: bool | None = None
    nightly_cost_per_unit: Decimal | None = Field(default=None, ge=0)
    distance_miles: Decimal | None = Field(default=None, ge=0)
    transport_available: bool | None = None
    provenance: Provenance


class UtilityObservation(Model):
    service: Literal['electricity', 'water', 'gas']
    status: Literal['available', 'partial', 'outage', 'unknown', 'not_applicable']
    provider: str
    provenance: Provenance
    potable: bool | None = None
    note: str = ''


class EvidenceRecord(Model):
    id: str
    requirement_ids: list[str] = Field(default_factory=list)
    status: Literal['unavailable', 'not_collected', 'reported_available', 'saved', 'unknown', 'not_applicable'] = 'unknown'
    description: str = ''


class ChecklistRequirement(Model):
    id: str
    title: str
    applicable: bool = True


class ChecklistProfile(Model):
    id: str
    label: str
    description: str
    requirements: list[ChecklistRequirement]


class MoneyFact(Model):
    amount: Decimal = Field(ge=0)
    currency: str = 'USD'
    stage_id: str
    observed_at: datetime
    valid_until: datetime | None = None

    @field_validator('observed_at', 'valid_until')
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        return Provenance.aware(value)


class FundingContext(Model):
    stage_id: str | None = None
    stage_label: str | None = None
    estimated_cost: MoneyFact | None = None
    exact_allocation: MoneyFact | None = None
    spent_from_allocation: MoneyFact | None = None
    expected_payment: MoneyFact | None = None
    approved_payment: MoneyFact | None = None
    received_payment: MoneyFact | None = None
    # Received payments are separately visible; only an explicit allocation
    # determines cash available for this stage, preventing double counting.
    decision: Literal['unknown', 'pending', 'approved', 'declined', 'not_applicable'] = 'unknown'


class RepairProvider(Model):
    id: str
    name: str
    trade: Literal['Electrician', 'Contractor', 'Plumber', 'Roofer', 'Pool specialist']
    county: str = 'Miami-Dade'
    areas: list[str]
    rating: Decimal | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)
    availability: Literal['available', 'waiting', 'unavailable', 'unknown'] = 'unknown'
    accessible_service: bool | None = None
    provenance: Provenance


class ProviderInteraction(Model):
    provider_id: str
    state: Literal['shortlisted', 'enquiry_recorded', 'awaiting_reply', 'declined', 'quote_received', 'quote_accepted', 'work_committed']
    quote: MoneyFact | None = None
    note: str = ''


class ReviewedTask(Model):
    task_id: str
    key: str
    title: str
    reason: str = ''
    tier: int = Field(default=4, ge=0)
    destination: str = 'My Recovery Plan'
    completed: bool = False
    applicable: bool = True
    dependencies: list[str] = Field(default_factory=list)


class ProgressInput(Model):
    context_key: str
    source_mode: SourceMode
    scenario_id: str | None = None
    checkpoint_id: str | None = None
    as_of: datetime
    recovery_started: date | None = None
    household: HouseholdContext
    immediate_danger: bool | None = None
    profile_version: int = Field(default=0, ge=0)
    case_version: str | None = None
    accommodation_status: Literal['needed', 'arranged', 'home', 'unknown'] = 'unknown'
    home_returned: bool | None = None
    repairs_complete: bool | None = None
    housing_sites: list[HousingSite] = Field(default_factory=list)
    utilities: list[UtilityObservation] = Field(default_factory=list)
    insurance_applicable: bool | None = None
    checklist_id: str | None = None
    checklist: ChecklistProfile | None = None
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    general_preparation_missing: list[str] = Field(default_factory=list)
    funding: FundingContext = Field(default_factory=FundingContext)
    needed_trades: list[str] = Field(default_factory=list)
    providers: list[RepairProvider] = Field(default_factory=list)
    interactions: list[ProviderInteraction] = Field(default_factory=list)
    reviewed_tasks: list[ReviewedTask] = Field(default_factory=list)
    insurance_timing: str | None = None
    recovery_timing: str | None = None
    timing_assumptions: list[str] = Field(default_factory=list)
    specialist_failures: list[str] = Field(default_factory=list)

    @field_validator('as_of')
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return Provenance.aware(value)


class ResultItem(Model):
    id: str
    title: str
    category: str
    state: SignalState
    summary: str
    fields: dict[str, str] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)


class ActionCandidate(Model):
    key: str
    title: str
    reason: str
    tier: int = Field(ge=0)
    destination: str
    task_id: str | None = None
    dependencies: list[str] = Field(default_factory=list)


class SpecialistResult(Model):
    specialist: Literal['housing', 'utilities', 'insurance', 'rebuild']
    state: SignalState
    headline: str
    summary: str
    items: list[ResultItem] = Field(default_factory=list)
    actions: list[ActionCandidate] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    source_mode: SourceMode
    observed_at: datetime | None = None
    execution_state: ExecutionState = ExecutionState.COMPLETE
    provenance: list[Provenance] = Field(default_factory=list)


class Milestone(Model):
    title: str
    state: SignalState
    detail: str


class MilestoneView(Model):
    elapsed_days: int | None
    elapsed_label: str
    home: list[Milestone] = Field(default_factory=list)
    funding: list[Milestone] = Field(default_factory=list)
    insurance_range: str
    recovery_range: str
    assumptions: list[str] = Field(default_factory=list)


class ScenarioSummary(Model):
    id: str
    label: str
    description: str
    checkpoints: list[str]
    featured: bool = False


def fingerprint(inputs: ProgressInput) -> str:
    """Bind all input facts and context, independent of dictionary order."""
    import json
    payload = json.dumps(inputs.model_dump(mode='json'), sort_keys=True, separators=(',', ':'))
    return sha256(payload.encode()).hexdigest()
