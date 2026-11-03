"""Strict shared records. These models do not make a reviewer trustworthy."""
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Text = Annotated[str, Field(min_length=1, max_length=200)]
Identifier = Annotated[str, Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$')]
Hash = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
Guidance = Annotated[str, Field(min_length=1, max_length=6000)]


class ReviewStatus(StrEnum):
    LINK_ONLY = 'LINK_ONLY'
    DOWNLOADED_UNREVIEWED = 'DOWNLOADED_UNREVIEWED'
    REVIEW_REQUIRED = 'REVIEW_REQUIRED'
    REVIEWED = 'REVIEWED'
    STALE = 'STALE'
    UNAVAILABLE = 'UNAVAILABLE'


class Classification(StrEnum):
    OFFICIAL_SOURCE = 'OFFICIAL_SOURCE'
    SIMULATED_DEMO = 'SIMULATED_DEMO'


class Hazard(StrEnum):
    FLOOD = 'flood'
    HURRICANE = 'hurricane'
    WILDFIRE = 'wildfire'


class DisasterPhase(StrEnum):
    PREPARE = 'prepare'
    RESPOND = 'respond'
    RECOVER = 'recover'


class FailureCategory(StrEnum):
    TIMEOUT = 'TIMEOUT'
    HTTP_ERROR = 'HTTP_ERROR'
    NETWORK_ERROR = 'NETWORK_ERROR'
    TLS_ERROR = 'TLS_ERROR'
    UNEXPECTED_REDIRECT = 'UNEXPECTED_REDIRECT'
    INVALID_ORIGIN = 'INVALID_ORIGIN'
    TOO_LARGE = 'TOO_LARGE'
    UNSUPPORTED_CONTENT_TYPE = 'UNSUPPORTED_CONTENT_TYPE'
    EXTRACTION_FAILED = 'EXTRACTION_FAILED'
    DECODE_FAILED = 'DECODE_FAILED'


class StrictRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    @field_validator('*')
    @classmethod
    def validate_values(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError('text must not be blank')
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('timestamps must be timezone-aware')
            if value > datetime.now(timezone.utc):
                raise ValueError('timestamps must not be in the future')
            return value.astimezone(timezone.utc)
        if isinstance(value, list):
            if any(isinstance(item, str) and not item.strip() for item in value):
                raise ValueError('list text must not be blank')
            if all(isinstance(item, (str, StrEnum)) for item in value) and len(value) != len(set(value)):
                raise ValueError('duplicate list entries')
            if value and all(isinstance(item, BaseModel) for item in value):
                for identifier in ('chunk_id', 'resource_id', 'source_id'):
                    if all(hasattr(item, identifier) for item in value):
                        identifiers = [getattr(item, identifier) for item in value]
                        if len(identifiers) != len(set(identifiers)):
                            raise ValueError('duplicate record IDs')
                        break
        return value


def validate_official_url(value: str) -> str:
    try:
        url = urlsplit(value)
        valid = (url.scheme == 'https' and bool(url.hostname) and url.username is None
                 and url.password is None and url.port in (None, 443) and not url.fragment
                 and not any(c.isspace() or ord(c) < 32 for c in value)
                 and '\\' not in value and '.' in url.hostname)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('a valid credential-free HTTPS URL is required')
    return value


class SourceRecord(StrictRecord):
    source_id: Identifier
    publisher: Text
    title: Text
    official_url: Annotated[str, Field(max_length=2000)]
    source_type: Text
    jurisdiction: Text
    hazards: list[Hazard] = Field(min_length=1)
    disaster_phases: list[DisasterPhase] = Field(min_length=1)
    classification: Classification
    content_type: Text | None = None
    charset: Text | None = None
    original_content_hash: Hash | None = None
    retrieved_at: datetime | None = None
    reviewed_at: datetime | None = None
    review_status: ReviewStatus = ReviewStatus.LINK_ONLY
    reviewer: Text | None = None
    limitations: list[Text] = Field(min_length=1)
    final_url: Annotated[str, Field(max_length=2000)] | None = None
    http_status: Annotated[int, Field(ge=100, le=599)] | None = None
    byte_count: Annotated[int, Field(gt=0)] | None = None
    last_attempt_at: datetime | None = None
    failure_category: FailureCategory | None = None

    @field_validator('official_url', 'final_url')
    @classmethod
    def valid_url(cls, value):
        return None if value is None else validate_official_url(value)

    @model_validator(mode='after')
    def provenance(self):
        acquired = self.review_status in (ReviewStatus.DOWNLOADED_UNREVIEWED, ReviewStatus.REVIEWED,
                                         ReviewStatus.REVIEW_REQUIRED, ReviewStatus.STALE)
        if acquired and not (self.original_content_hash and self.retrieved_at and self.final_url
                             and self.content_type and self.charset and self.byte_count and self.http_status == 200):
            raise ValueError('acquired records require complete original HTTP provenance')
        if self.review_status is ReviewStatus.REVIEWED:
            if self.classification is Classification.SIMULATED_DEMO:
                raise ValueError('SIMULATED_DEMO cannot become reviewed official evidence')
            if not self.reviewer or self.reviewed_at is None:
                raise ValueError('reviewed records require reviewer identity and timestamp')
        if self.reviewed_at and (not self.retrieved_at or self.reviewed_at < self.retrieved_at):
            raise ValueError('review must follow retrieval')
        return self


class EvidenceChunk(StrictRecord):
    chunk_id: Identifier
    source_id: Identifier
    section_heading: Annotated[str, Field(min_length=1, max_length=1000)]
    guidance_text: Guidance
    applicable_hazards: list[Hazard] = Field(min_length=1)
    applicable_phases: list[DisasterPhase] = Field(min_length=1)
    geographic_scope: Text
    review_status: ReviewStatus = ReviewStatus.DOWNLOADED_UNREVIEWED


class ResourceRecord(StrictRecord):
    resource_id: Identifier
    source_id: Identifier
    official_name: Text
    service_category: Text
    service_area: Text
    official_contact: Text | None = None
    contact_evidence_chunk_id: Identifier | None = None
    official_url: Annotated[str, Field(max_length=2000)]
    prerequisites: list[Text]
    limitations: list[Text] = Field(min_length=1)
    availability_status: Literal['UNKNOWN'] = 'UNKNOWN'

    @field_validator('official_url')
    @classmethod
    def valid_url(cls, value):
        return validate_official_url(value)

    @model_validator(mode='after')
    def contact_has_reference(self):
        if self.official_contact is not None and self.contact_evidence_chunk_id is None:
            raise ValueError('a contact requires reviewed excerpt provenance')
        return self


class ReviewDecision(StrictRecord):
    reviewer: Text
    expected_content_hash: Hash
    expected_context_hash: Hash
    provenance_checked: Literal[True]
    content_checked: Literal[True]
    geographic_scope_checked: Literal[True]
    applicability_checked: Literal[True]
    caveats_preserved: Literal[True]


    @model_validator(mode='before')
    @classmethod
    def explicit_checks(cls, values):
        if isinstance(values, dict):
            names = ('provenance_checked', 'content_checked', 'geographic_scope_checked',
                     'applicability_checked', 'caveats_preserved')
            if any(values.get(name) is not True for name in names):
                raise ValueError('each human review check requires an explicit boolean True')
        return values


class ReviewRecord(StrictRecord):
    reviewer: Text
    reviewed_at: datetime
    content_hash: Hash
    context_hash: Hash
    decision: ReviewDecision


class SourceBundle(StrictRecord):
    source: SourceRecord
    chunks: list[EvidenceChunk]
    review: ReviewRecord | None = None

    @model_validator(mode='after')
    def related_records(self):
        ids = [c.chunk_id for c in self.chunks]
        if len(ids) != len(set(ids)) or any(c.source_id != self.source.source_id for c in self.chunks):
            raise ValueError('duplicate chunk IDs or mismatched source IDs')
        if self.source.review_status is ReviewStatus.REVIEWED:
            if not self.chunks or self.review is None:
                raise ValueError('reviewed sources require actual excerpts and a review record')
            if any(c.review_status is not ReviewStatus.REVIEWED for c in self.chunks):
                raise ValueError('reviewed source and chunks must have matching review state')
            if (self.review.content_hash != self.source.original_content_hash
                    or self.review.reviewer != self.source.reviewer
                    or self.review.reviewed_at != self.source.reviewed_at):
                raise ValueError('review provenance mismatch')
        elif any(c.review_status is ReviewStatus.REVIEWED for c in self.chunks):
            raise ValueError('chunks cannot publish without a reviewed source')
        return self


class SourceManifest(StrictRecord):
    schema_version: Literal[1] = 1
    sources: list[SourceRecord]

    @model_validator(mode='after')
    def unique_ids(self):
        ids = [s.source_id for s in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate source IDs')
        return self


class KnowledgeRequest(StrictRecord):
    hazard: Hazard
    disaster_phase: DisasterPhase
    jurisdiction: Text
    household_needs: list[Text] = Field(default_factory=list, max_length=30)
    safety_topic: Text | None = None
    requested_evidence_count: int = Field(default=3, ge=1, le=10)


class RetrievalStatus(StrEnum):
    SUCCESS = 'SUCCESS'
    NO_RELEVANT_EVIDENCE = 'NO_RELEVANT_EVIDENCE'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'
    UNAVAILABLE = 'UNAVAILABLE'


class GuidanceResult(StrictRecord):
    evidence_records: list[EvidenceChunk]
    source_metadata: list[SourceRecord]
    matching_context: KnowledgeRequest
    retrieval_status: RetrievalStatus
    limitations: list[Text]
    missing_information: list[Text]


class ResourceResult(StrictRecord):
    resources: list[ResourceRecord]
    source_metadata: list[SourceRecord]
    matching_context: KnowledgeRequest
    retrieval_status: RetrievalStatus
    limitations: list[Text]
    missing_information: list[Text]
