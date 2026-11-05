"""Application directory contracts without importing storage or publication code."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResourceQuery(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    needs: str = Field(min_length=1, max_length=200)
    county: str | None = None
    phase: Literal['prepare', 'respond', 'recover'] = 'respond'
    hazard: Literal['flood', 'hurricane', 'wildfire'] | None = None
    purpose: Literal['planning', 'urgent_assistance', 'communication_access'] = 'urgent_assistance'


class VerifiedResource(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    resource_id: str
    source_id: str
    official_name: str
    provider: str
    description: str
    service_category: str
    service_area: str
    official_url: str
    official_contact: str | None = None
    prerequisites: list[str]
    enrollment_timing: str | None = None
    limitations: list[str]
    retrieved_at: datetime
    source_reviewed_at: datetime
    reviewed_at: datetime
    review_due_at: datetime
    availability_status: Literal['UNKNOWN'] = 'UNKNOWN'
    supporting_candidate_ids: list[str]


class ResourceLookupResult(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    status: Literal['matches', 'no_match', 'review_required', 'unavailable']
    records: list[VerifiedResource] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
