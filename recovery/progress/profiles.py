"""Optional, explicitly confirmed fictional case facts; independent of recovery plans."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from recovery.models import RecoveryCase, RecoveryRecords, RecoveryPlan
from recovery.insurance_models import InsuranceWorkspace, InsuranceAttachment

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRIBUTION_BANDS = ('None available', 'Under $500', '$500–$1,999', '$2,000–$4,999', '$5,000 or more', 'Not sure', 'Prefer not to say')


class ProgressProfile(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    case_id: UUID
    version: int = Field(default=0, ge=0, strict=True)
    updated_at: datetime | None = None
    total: int | None = Field(default=None, ge=1, le=10000, strict=True)
    zip_code: str | None = Field(default=None, pattern=r'^\d{5}(?:-\d{4})?$')
    address: str | None = Field(default=None, max_length=500)
    recovery_started: date | None = None
    accessibility: bool | None = Field(default=None, strict=True)
    pets: bool | None = Field(default=None, strict=True)
    has_vehicle: bool | None = Field(default=None, strict=True)
    housing_budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    contribution_band: Literal['None available', 'Under $500', '$500–$1,999', '$2,000–$4,999', '$5,000 or more', 'Not sure', 'Prefer not to say'] | None = None
    gas_applicable: bool | None = Field(default=None, strict=True)
    gas_available: bool | None = Field(default=None, strict=True)

    @field_validator('address')
    @classmethod
    def nonblank_address(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError('Use unknown rather than a blank address')
        return value

    @field_validator('updated_at')
    @classmethod
    def aware(cls, value):
        from .models import Provenance
        return Provenance.aware(value)

    @model_validator(mode='after')
    def applicable_gas_report(self):
        if self.gas_applicable is not True and self.gas_available is not None:
            raise ValueError('A gas availability report requires confirmed gas applicability')
        return self


@dataclass(frozen=True)
class ProgressCaseSnapshot:
    """Detached saved aggregate; original photograph bytes never leave this boundary."""
    case: RecoveryCase
    records: RecoveryRecords
    plan: RecoveryPlan | None
    workspace: InsuranceWorkspace
    attachment_metadata: tuple[InsuranceAttachment, ...]
    journey_events: tuple[dict, ...]
    profile: ProgressProfile
    revision: str
