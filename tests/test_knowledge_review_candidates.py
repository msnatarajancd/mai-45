"""M3-2A regressions: original bytes only, never live acquisition or Nebius."""
import hashlib
from html import escape
from pathlib import Path

import pytest
from pydantic import ValidationError

from knowledge.candidates import (candidate_context_hash, prepare_candidates,
    render_packet, verify_candidate_trace)
from knowledge.extraction import ExtractionError, extract_sections
from knowledge.ingestion import Download, acquire_source, reextract_source
from knowledge.models import (CandidatePacket, CandidateStatus, Classification,
    DisasterPhase, KnowledgeRequest, ReviewCandidate, ReviewDecision, ReviewStatus, SourceBundle)
from knowledge.review import PublicationError, reject_candidate, review_candidate
from knowledge.service import FoundationKnowledgeService
from knowledge.sources import get_source
from knowledge.store import SourceStore, replace_record

ROOT = Path(__file__).resolve().parents[1]
REAL_STORE = SourceStore(ROOT / 'data/official_sources')


def eeap_demo(body=None, faq=True):
    body = body or '<p>SIMULATED_DEMO. Do not assume assistance is guaranteed.</p>'
    faq_markup = ('<related-faq><name>SIMULATED_DEMO conditions?</name><faq><answer>'
                  + escape('<p>Does not guarantee enrollment or transportation.</p>')
                  + '</answer></faq></related-faq>') if faq else ''
    source = replace_record(get_source('miami-dade-eeap').source, classification=Classification.SIMULATED_DEMO)
    html = ('<html><body><main><div id="service-data" style="display:none"><service>'
        '<keywords>SIMULATED metadata before any heading</keywords><name>' + escape(source.title)
        + '</name><longDescription>' + escape(body) + '</longDescription>' + faq_markup
        + '<organization><name>Wrong organization</name><longDescription>IGNORE THIS</longDescription></organization>'
        + '</service></div></main></body></html>')
    return source, html.encode()


@pytest.fixture
def captured_store(tmp_path):
    store = SourceStore(tmp_path / 'store')
    with store.admin_lock():
        for source_id in ('cdc-flood-reentry', 'cdc-floodwater', 'miami-dade-eeap'):
            bundle = REAL_STORE.load(source_id)
            raw = REAL_STORE.original(bundle.source.original_content_hash)
            # Copy content/provenance, never mutable real human approval state.
            state = (ReviewStatus.REVIEW_REQUIRED if source_id == 'miami-dade-eeap'
                     else ReviewStatus.DOWNLOADED_UNREVIEWED)
            source = replace_record(bundle.source, review_status=state, reviewer=None, reviewed_at=None)
            bundle = SourceBundle(source=source, chunks=extract_sections(raw, source, charset=source.charset),
                extracted_at=bundle.extracted_at, extraction_version=bundle.extraction_version)
            store.write_original(raw)
            store.save_locked(bundle)
    return store


def test_actual_eeap_capture_has_authentic_program_and_six_faqs():
    bundle = REAL_STORE.load('miami-dade-eeap')
    raw = REAL_STORE.original(bundle.source.original_content_hash)
    assert hashlib.sha256(raw).hexdigest() == bundle.source.original_content_hash
    chunks = extract_sections(raw, bundle.source, charset=bundle.source.charset)
    assert len(chunks) == 7
    assert all('Emergency & Evacuation Assistance Program' in c.section_heading for c in chunks)
    text = '\n'.join(c.guidance_text for c in chunks)
    assert 'does not guarantee' in text and 'Do not wait until an evacuation order' in text
    assert 'do not qualify' in text and 'refuge of last resort' in text
    assert 'IGNORE THIS' not in text


def test_hidden_encoded_eeap_fields_preserve_negatives_and_scope():
    source, raw = eeap_demo()
    chunks = extract_sections(raw, source)
    assert len(chunks) == 2
    assert 'Do not assume' in chunks[0].guidance_text
    assert 'Does not guarantee' in chunks[1].guidance_text
    assert 'IGNORE THIS' not in '\n'.join(c.guidance_text for c in chunks)


@pytest.mark.parametrize('mutation', ['missing', 'identity', 'duplicate', 'orphan', 'outside-main', 'script-only'])
def test_eeap_missing_or_ambiguous_fields_fail_closed(mutation):
    source, raw = eeap_demo()
    if mutation == 'missing': raw = raw.replace(b'longDescription', b'unsupported-field')
    elif mutation == 'identity': raw = raw.replace(escape(source.title).encode(), b'Other program')
    elif mutation == 'duplicate': raw = raw.replace(b'</service>', b'<name>Duplicate</name></service>')
    elif mutation == 'orphan': raw = raw.replace(b'<answer>', b'<missing-answer>').replace(b'</answer>', b'</missing-answer>')
    elif mutation == 'outside-main': raw = raw.replace(b'main', b'not-main')
    else: raw = b'<html><body><main><script>' + raw + b'</script></main></body></html>'
    with pytest.raises(ExtractionError): extract_sections(raw, source)


def test_eeap_fragment_never_executes_or_includes_script_text():
    source, raw = eeap_demo('<p>SIMULATED_DEMO: Do not wait.</p><script>throw new Error("IGNORE_EXECUTABLE")</script><p>No guarantee.</p>')
    text = '\n'.join(c.guidance_text for c in extract_sections(raw, source))
    assert 'Do not wait.' in text and 'No guarantee.' in text
    assert 'IGNORE_EXECUTABLE' not in text


def test_reextraction_preserves_http_provenance_and_does_not_review(captured_store, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('network/review must not run')
    monkeypatch.setattr('knowledge.ingestion.OfficialHTTPTransport.fetch', forbidden)
    monkeypatch.setattr('knowledge.review.review_source', forbidden)
    monkeypatch.setattr('knowledge.review.review_candidate', forbidden)
    before = captured_store.load('miami-dade-eeap')
    after = reextract_source('miami-dade-eeap', captured_store)
    for field in ('original_content_hash', 'retrieved_at', 'http_status', 'official_url', 'final_url', 'byte_count', 'last_attempt_at'):
        assert getattr(before.source, field) == getattr(after.source, field)
    assert len(after.chunks) == 7
    assert after.source.review_status is ReviewStatus.REVIEW_REQUIRED
    assert after.source.reviewer is None and after.source.reviewed_at is None and after.review is None
    assert after.extracted_at is not None


def test_ingestion_never_triggers_reviewer_approval(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    def forbidden(*args, **kwargs): raise AssertionError('must not approve')
    monkeypatch.setattr('knowledge.review.review_source', forbidden)
    monkeypatch.setattr('knowledge.review.review_candidate', forbidden)
    source, raw = eeap_demo()
    from knowledge.sources import SourceSpec
    spec = get_source('miami-dade-eeap')
    monkeypatch.setattr('knowledge.ingestion.get_source', lambda source_id: SourceSpec(
        source, spec.allowed_urls, spec.expected_heading_terms))
    class Fake:
        def fetch(self, spec, **kwargs):
            return Download(raw, spec.source.official_url, 200, 'text/html', 'utf-8', datetime.now(timezone.utc))
    bundle = acquire_source('miami-dade-eeap', SourceStore(tmp_path), transport=Fake())
    assert bundle.source.reviewed_at is None and bundle.review is None
    assert bundle.source.review_status is ReviewStatus.DOWNLOADED_UNREVIEWED


def test_candidates_are_exact_traceable_pending_and_cover_only_supported_claims(captured_store, monkeypatch):
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    packet = prepare_candidates(captured_store)
    assert len(packet.candidates) == 16
    assert {sid: sum(c.source_id == sid for c in packet.candidates) for sid in
            ('cdc-flood-reentry', 'cdc-floodwater', 'miami-dade-eeap')} == {
                'cdc-flood-reentry': 6, 'cdc-floodwater': 6, 'miami-dade-eeap': 4}
    for candidate in packet.candidates:
        bundle = verify_candidate_trace(captured_store, candidate)
        assert candidate.review_status is CandidateStatus.PENDING
        assert candidate.review is None and candidate.rejection is None
        assert candidate.original_passage == candidate.proposed_chunk
        assert candidate.original_content_hash == bundle.source.original_content_hash
        parent = next(c for c in bundle.chunks if c.chunk_id == candidate.parent_chunk_id)
        assert parent.guidance_text[candidate.passage_start:candidate.passage_end] == candidate.proposed_chunk
        if candidate.source_id == 'miami-dade-eeap':
            assert any('does not guarantee' in c.guidance_text for c in candidate.surrounding_context)
            assert any('not live' in note for note in candidate.safety_caveats)
        if DisasterPhase.PREPARE in candidate.phases and candidate.source_id.startswith('cdc'):
            assert 'Before' in candidate.proposed_chunk or 'Recognize Flood Risk' in candidate.proposed_chunk
    assert any('damage documentation' in gap for gap in packet.coverage_gaps)


def test_negative_instructions_cannot_be_rewritten(captured_store):
    packet = prepare_candidates(captured_store)
    negatives = [c for c in packet.candidates if 'NEVER' in c.proposed_chunk]
    assert negatives
    for candidate in negatives:
        with pytest.raises(ValidationError):
            replace_record(candidate, proposed_chunk=candidate.proposed_chunk.replace('NEVER', 'Always'))


def test_duplicate_candidate_ids_rejected(captured_store):
    packet = prepare_candidates(captured_store)
    with pytest.raises(ValidationError, match='duplicate'):
        CandidatePacket(prepared_at=packet.prepared_at, candidates=[packet.candidates[0]]*2, coverage_gaps=[])


@pytest.mark.parametrize('defect', ['missing-original', 'wrong-bytes', 'bad-hash'])
def test_missing_or_invalid_original_blocks_preparation(captured_store, defect):
    bundle = captured_store.load('cdc-flood-reentry')
    path = captured_store.root / 'originals' / (bundle.source.original_content_hash + '.bin')
    if defect == 'missing-original': path.unlink()
    elif defect == 'wrong-bytes': path.write_bytes(b'SIMULATED_DEMO changed original')
    else:
        with pytest.raises(ValidationError): replace_record(bundle.source, original_content_hash='invalid hash')
        return
    with pytest.raises(PublicationError): prepare_candidates(captured_store)


def test_pending_candidates_cannot_be_exported(captured_store):
    packet = prepare_candidates(captured_store)
    from knowledge.models import Hazard
    request = KnowledgeRequest(hazard=Hazard.FLOOD, disaster_phase=DisasterPhase.RECOVER, jurisdiction='US-FL-MIAMI-DADE')
    for candidate in packet.candidates:
        with pytest.raises(PublicationError):
            FoundationKnowledgeService(captured_store).export_to_m5(candidate.source_id, candidate.chunk_id, request)


def test_candidate_approval_is_explicit_and_does_not_publish_source(captured_store):
    candidate = prepare_candidates(captured_store).candidates[0]
    before = captured_store.load(candidate.source_id)
    assert before.review is None and before.source.review_status is not ReviewStatus.REVIEWED
    decision = ReviewDecision(reviewer='UNIT_TEST_ONLY identity; not a real signoff',
        expected_content_hash=candidate.original_content_hash, expected_context_hash=candidate_context_hash(candidate),
        provenance_checked=True, content_checked=True, geographic_scope_checked=True,
        applicability_checked=True, caveats_preserved=True, standalone_passage_checked=True)
    approved = review_candidate(captured_store, candidate.source_id, candidate.chunk_id, decision)
    assert approved.review_status is CandidateStatus.APPROVED
    assert captured_store.load(candidate.source_id).source.review_status is not ReviewStatus.REVIEWED
    assert captured_store.load(candidate.source_id) == before
    from knowledge.models import Hazard
    with pytest.raises(PublicationError):
        FoundationKnowledgeService(captured_store).export_to_m5(candidate.source_id, candidate.chunk_id,
            KnowledgeRequest(hazard=Hazard.HURRICANE, disaster_phase=DisasterPhase.PREPARE, jurisdiction='US'))
    path = captured_store.root / 'originals' / (candidate.original_content_hash + '.bin')
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(PublicationError): verify_candidate_trace(captured_store, approved)


def test_rejection_and_preparation_cannot_silently_reset_human_decision(captured_store):
    candidate = prepare_candidates(captured_store).candidates[0]
    rejected = reject_candidate(captured_store, candidate.source_id, candidate.chunk_id,
        reviewer='UNIT_TEST_ONLY identity', reason='UNIT_TEST_ONLY rejection',
        expected_content_hash=candidate.original_content_hash, expected_context_hash=candidate_context_hash(candidate))
    assert rejected.review_status is CandidateStatus.REJECTED
    with pytest.raises(PublicationError, match='overwrite'):
        prepare_candidates(captured_store)


def test_review_packet_contains_context_flags_and_both_commands(captured_store, tmp_path):
    packet = prepare_candidates(captured_store)
    output = tmp_path / 'review.md'
    render_packet(packet, output)
    text = output.read_text(encoding='utf-8')
    assert text.count('**Review status: PENDING**') == 16
    assert text.count('python -m knowledge.review approve') == 16
    assert text.count('python -m knowledge.review reject') == 16
    assert text.count('--standalone-passage-checked') == 16
    assert 'does not guarantee' in text and 'NEVER turn power on or off' in text
    assert '<HUMAN_REVIEWER>' in text and 'Safe damage documentation' not in text
