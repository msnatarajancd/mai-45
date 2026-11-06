"""Confirmed, case-bound preparation records; never coverage or submission decisions."""
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field
from .models import RecoveryCase, RecoveryRecords


class InsuranceModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class InsuranceProfile(InsuranceModel):
    insurer_name: str | None = Field(None, max_length=200)
    insurance_type: str | None = Field(None, max_length=200)
    policy_reference: str | None = Field(None, max_length=200)
    claim_reference: str | None = Field(None, max_length=200)
    incident_date: date | None = None
    property_description: str | None = Field(None, max_length=2000)
    insurer_contacted: bool | None = Field(None, strict=True)
    notes: str | None = Field(None, max_length=4000)


class ItemPreparation(InsuranceModel):
    damage_id: UUID
    category: str | None = Field(None, max_length=200)
    location: str | None = Field(None, max_length=200)
    quantity: int | None = Field(None, ge=1, le=10000, strict=True)
    brand: str | None = Field(None, max_length=200)
    model: str | None = Field(None, max_length=200)
    serial_reference: str | None = Field(None, max_length=200)
    purchase_date: date | None = None
    purchase_price: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    estimated_cost: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(None, pattern=r'^[A-Z]{3}$')
    additional_damage: str | None = Field(None, max_length=4000)
    notes: str | None = Field(None, max_length=4000)


class EvidenceType(StrEnum):
    PHOTOGRAPH = 'Photograph'
    RECEIPT = 'Receipt'
    ESTIMATE = 'Estimate'
    OTHER = 'Other'


class EvidenceStatus(StrEnum):
    FILE_SAVED = 'File saved'
    REPORTED_AVAILABLE = 'Reported available, not uploaded'
    NOT_COLLECTED = 'Not yet collected'
    UNAVAILABLE = 'Unavailable'
    NOT_APPLICABLE = 'Not applicable'


class EvidenceRecord(InsuranceModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    damage_id: UUID | None = None
    evidence_type: EvidenceType
    status: EvidenceStatus
    attachment_id: UUID | None = None
    description: str = Field(default='', max_length=2000)
    relevant_date: date | None = None


class InsuranceCommunication(InsuranceModel):
    communication_id: UUID = Field(default_factory=uuid4)
    contact_date: date | None = None
    method: str = Field(min_length=1, max_length=100)
    representative: str | None = Field(None, max_length=200)
    reference: str | None = Field(None, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    next_follow_up: str | None = Field(None, max_length=2000)


class InsuranceWorkspace(InsuranceModel):
    case_id: UUID
    version: int = Field(default=0, ge=0, strict=True)
    profile: InsuranceProfile = Field(default_factory=InsuranceProfile)
    items: list[ItemPreparation] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceRecord] = Field(default_factory=list, max_length=200)
    communications: list[InsuranceCommunication] = Field(default_factory=list, max_length=200)


class InsuranceAttachment(InsuranceModel):
    attachment_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    damage_id: UUID | None = None
    evidence_type: EvidenceType = EvidenceType.PHOTOGRAPH
    original_name: str = Field(min_length=1, max_length=200)
    media_type: str
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    byte_count: int = Field(gt=0, le=5*1024*1024)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    description: str = Field(default='', max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def safe_filename(self):
        return str(self.attachment_id) + ('.png' if self.media_type == 'image/png' else '.jpg')


class SavedPhoto(InsuranceModel):
    metadata: InsuranceAttachment
    content: bytes = Field(repr=False)


class InsuranceSnapshot(InsuranceModel):
    case: RecoveryCase
    records: RecoveryRecords
    workspace: InsuranceWorkspace
    attachments: list[SavedPhoto] = Field(default_factory=list)
