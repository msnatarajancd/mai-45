from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from knowledge.models import (Classification, EvidenceChunk, ReviewDecision, ReviewStatus,
                              ResourceRecord, SourceManifest, SourceRecord)
from knowledge.sources import CURATED_SOURCES


def test_valid_source_metadata_is_link_only():
    source = CURATED_SOURCES[0].source
    assert source.review_status is ReviewStatus.LINK_ONLY
    assert source.original_content_hash is None and source.retrieved_at is None
    assert SourceRecord.model_validate_json(source.model_dump_json()) == source


@pytest.mark.parametrize('url', ['http://www.cdc.gov/x', 'https://user:password@www.cdc.gov/x',
    'javascript:alert(1)', 'https://', 'https://www.cdc.gov:99999/x',
    'https://www.cdc.gov/x#secret', 'https://www.cdc.gov/with space'])
def test_invalid_urls_rejected(url):
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(CURATED_SOURCES[0].source.model_dump() | {'official_url': url})


def test_duplicate_source_ids_rejected():
    source = CURATED_SOURCES[0].source
    with pytest.raises(ValidationError, match='duplicate'):
        SourceManifest(sources=[source, source])


@pytest.mark.parametrize('field,value', [('publisher', ''), ('title', ' '),
    ('source_id', '../escape'), ('review_status', 'REVIEWED'), ('unexpected_flag', True)])
def test_strict_metadata_rejects_bad_values(field, value):
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(CURATED_SOURCES[0].source.model_dump() | {field: value})


@pytest.mark.parametrize('timestamp', [datetime(2026, 1, 1), 'not-a-timestamp',
    datetime.now(timezone.utc) + timedelta(days=1), 1])
def test_invalid_timestamps_rejected(timestamp):
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(CURATED_SOURCES[0].source.model_dump() | {'retrieved_at': timestamp})


def test_acquired_records_need_actual_provenance():
    with pytest.raises(ValidationError, match='provenance'):
        SourceRecord.model_validate(CURATED_SOURCES[0].source.model_dump() |
                                    {'review_status': ReviewStatus.DOWNLOADED_UNREVIEWED})


def test_synthetic_source_cannot_be_reviewed():
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(CURATED_SOURCES[0].source.model_dump() |
            {'classification': Classification.SIMULATED_DEMO, 'review_status': ReviewStatus.REVIEWED})


def test_review_checks_require_real_booleans():
    values = dict(reviewer='SIMULATED_DEMO test identity', expected_content_hash='a'*64,
        expected_context_hash='b'*64, provenance_checked=True, content_checked=True,
        geographic_scope_checked=True, applicability_checked=True, caveats_preserved=True)
    for invalid in (False, 'true', 1, None):
        with pytest.raises(ValidationError):
            ReviewDecision(**(values | {'caveats_preserved': invalid}))


def test_resource_cannot_claim_live_availability_or_fabricate_contact():
    values = dict(resource_id='demo-resource', source_id='demo-source',
        official_name='SIMULATED_DEMO resource', service_category='static listing',
        service_area='US', official_url='https://example.org/resource', prerequisites=[],
        limitations=['SIMULATED_DEMO; no current availability.'])
    assert ResourceRecord(**values).availability_status == 'UNKNOWN'
    with pytest.raises(ValidationError):
        ResourceRecord(**(values | {'availability_status': 'AVAILABLE'}))
    with pytest.raises(ValidationError):
        ResourceRecord(**(values | {'official_contact': 'fabricated contact'}))


def test_duplicate_resource_result_ids_rejected():
    from knowledge.models import (DisasterPhase, Hazard, KnowledgeRequest, ResourceResult,
                                  RetrievalStatus)
    resource = ResourceRecord(resource_id='demo', source_id='demo', official_name='SIMULATED_DEMO',
        service_category='SIMULATED_DEMO', service_area='US', official_url='https://example.org/demo',
        prerequisites=[], limitations=['SIMULATED_DEMO; no availability.'])
    request = KnowledgeRequest(hazard=Hazard.FLOOD, disaster_phase=DisasterPhase.RECOVER, jurisdiction='US')
    with pytest.raises(ValidationError, match='duplicate'):
        ResourceResult(resources=[resource, resource], source_metadata=[], matching_context=request,
            retrieval_status=RetrievalStatus.UNAVAILABLE, limitations=['SIMULATED_DEMO'], missing_information=[])
