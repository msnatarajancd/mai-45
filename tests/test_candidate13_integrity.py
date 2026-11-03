"""Offline, read-only regressions for the reported EEAP candidate 13 discrepancy."""
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from knowledge.extraction import extract_sections
from knowledge.models import CandidatePacket, ReviewCandidate
from knowledge.store import SourceStore

ROOT = Path(__file__).resolve().parents[1]
STORE = SourceStore(ROOT / 'data/official_sources')
SOURCE = 'miami-dade-eeap'
CHUNK = '1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549'


@pytest.fixture
def candidate():
    return STORE.load_candidate(SOURCE, CHUNK)


def test_candidate13_preserved_capture_and_exact_parent_span(candidate):
    bundle = STORE.load(SOURCE)
    raw = STORE.original(bundle.source.original_content_hash)
    assert hashlib.sha256(raw).hexdigest() == candidate.original_content_hash
    assert b'encouraged to seek alternate transportation' in raw
    stored = next(c for c in bundle.chunks if c.chunk_id == candidate.parent_chunk_id)
    extracted = next(c for c in extract_sections(raw, bundle.source,
        charset=bundle.source.charset) if c.chunk_id == candidate.parent_chunk_id)
    assert extracted.guidance_text == stored.guidance_text
    passage = stored.guidance_text[candidate.passage_start:candidate.passage_end]
    assert passage == candidate.original_passage == candidate.proposed_chunk
    assert candidate.passage_end - candidate.passage_start == len(passage) == 562
    assert 'encouraged to seek alternate transportation' in passage
    assert 'does not guarantee' in passage
    assert hashlib.sha256(passage.encode()).hexdigest() == (
        'b9e7d19a2d41a38d474f44ff90fe4aaefe68a6e669485648959162ff6a8df9ee')


def test_all_verbatim_candidate_spans_preserve_whitespace():
    packet = CandidatePacket.model_validate_json(
        (ROOT / 'data/official_sources/candidate_packet.json').read_text(encoding='utf-8'))
    for item in packet.candidates:
        parent = next(c for c in STORE.load(item.source_id).chunks
                      if c.chunk_id == item.parent_chunk_id)
        assert item.original_passage == item.proposed_chunk
        assert parent.guidance_text[item.passage_start:item.passage_end] == item.original_passage
        assert item.passage_end - item.passage_start == len(item.original_passage)


def test_candidate13_packet_history_and_markdown_are_exact(candidate):
    packet = json.loads((ROOT / 'data/official_sources/candidate_packet.json').read_text(encoding='utf-8'))
    embedded = next(c for c in packet['candidates'] if c['chunk_id'] == CHUNK)
    assert embedded == candidate.model_dump(mode='json')
    history = ROOT / 'data/official_sources/candidate_history' / SOURCE / CHUNK
    snapshots = list(history.glob('*.json'))
    assert snapshots
    for snapshot in snapshots:
        assert json.loads(snapshot.read_text(encoding='utf-8')) == embedded
    packet_text = (ROOT / 'docs/M3_REVIEW_PACKET.md').read_text(encoding='utf-8')
    entry = packet_text.split('## Candidate 13:', 1)[1].split('## Candidate 14:', 1)[0]
    for label in ('**Original passage from acquired content:**',
                  '**Proposed short retrieval chunk (verbatim, pending review):**'):
        passage = entry.split(label, 1)[1].split('```text\n', 1)[1].split('\n```', 1)[0]
        assert passage == candidate.original_passage


@pytest.mark.parametrize('fields', [('original_passage',), ('proposed_chunk',),
                                  ('original_passage', 'proposed_chunk')])
def test_candidate13_rejects_lost_space_even_when_both_passages_agree(candidate, fields):
    data = candidate.model_dump(mode='json')
    for field in fields:
        data[field] = data[field].replace('encouraged to seek', 'encouraged toseek')
    with pytest.raises(ValidationError):
        ReviewCandidate.model_validate_json(json.dumps(data))


@pytest.mark.parametrize('end', [561, 563])
def test_candidate13_rejects_inconsistent_span(candidate, end):
    data = candidate.model_dump(mode='json')
    data['passage_end'] = end
    with pytest.raises(ValidationError):
        ReviewCandidate.model_validate_json(json.dumps(data))
