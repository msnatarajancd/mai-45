from enum import StrEnum
from pydantic import BaseModel, Field


class AppMode(StrEnum):
    DEMO = 'SIMULATED DEMO'
    LIVE = 'LIVE CHECK'


LOCATIONS = {'miami': 'Miami', 'homestead': 'Homestead', 'miami-beach': 'Miami Beach'}


class Household(BaseModel):
    label: str = 'Your fictional household'
    members: int = Field(default=1, ge=1, le=12)
    mobility_support: bool = False
    has_vehicle: bool = True
    pets: bool = False


class Source(BaseModel):
    title: str
    url: str
    publisher: str
    reviewed_at: str | None = None
    citation_id: str | None = None
    source_id: str | None = None
    original_content_hash: str | None = None


class Alert(BaseModel):
    headline: str
    severity: str
    description: str
    expires_at: str | None = None
    ends_at: str | None = None
    sent_at: str | None = None
    effective_at: str | None = None
    instruction: str | None = None
    area: str | None = None
    sender: str | None = None
    source_url: str = 'https://www.weather.gov/'


class AlertResult(BaseModel):
    status: str  # alerts | none | unavailable
    alerts: list[Alert] = Field(default_factory=list)
    simulated: bool = False
    checked_at: str | None = None
    source: str = 'https://www.weather.gov/mfl/'
    message: str = ''
    scope: str | None = None
    location_label: str | None = None


class GuidanceCitation(BaseModel):
    """Trusted display DTO; JSON proof avoids coupling emergency UI imports to M3."""
    citation_id: str
    source_id: str
    parent_chunk_id: str
    title: str
    publisher: str
    official_url: str
    original_content_hash: str
    section_heading: str
    passage: str
    passage_start: int
    passage_end: int
    jurisdiction: str
    hazards: list[str]
    phases: list[str]
    source_review: dict[str, object]
    candidate_review: dict[str, object]
    surrounding_context: list[dict[str, object]] = Field(default_factory=list, max_length=0)
    safety_caveats: list[str]
    source_limitations: list[str]


class GuidanceResult(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    insufficient_evidence: bool = True
    retrieval_status: str = 'UNAVAILABLE'
    citations: list[GuidanceCitation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class RouteResult(BaseModel):
    route: str  # emergency | resources
    urgency: str
    message: str


class Resource(BaseModel):
    title: str
    url: str
    category: str
    caveat: str
    last_checked: str | None = None
