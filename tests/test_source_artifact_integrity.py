"""Offline integrity of checked-in acquisition artifacts; never downloads sources."""
import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest

from knowledge.extraction import ExtractionError, extract_sections
from knowledge.models import ReviewStatus, SourceBundle, SourceManifest
from knowledge.review import PublicationError, verify_publication
from knowledge.store import SourceStore

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/official_sources'
MANIFEST = SourceManifest.model_validate_json((DATA / 'source_manifest.json').read_bytes())


@pytest.mark.parametrize('source', MANIFEST.sources, ids=lambda source: source.source_id)
def test_captured_original_and_history_match_provenance(source):
    bundle = SourceBundle.model_validate_json((DATA / 'records' / (source.source_id + '.json')).read_bytes())
    assert bundle.source == source
    if source.original_content_hash is None:
        # Failed acquisition is an audited unavailable result, never a fabricated
        # original or a publishable empty document.
        assert source.review_status is ReviewStatus.UNAVAILABLE
        assert source.failure_category is not None
        assert source.reviewed_at is None
        assert not bundle.chunks
        with pytest.raises(PublicationError):
            verify_publication(SourceStore(DATA), bundle)
        raw = None
    else:
        path = DATA / 'originals' / (source.original_content_hash + '.bin')
        assert path.is_file()
        raw = path.read_bytes()
        assert len(raw) == source.byte_count
        assert hashlib.sha256(raw).hexdigest() == source.original_content_hash
    histories = list((DATA / 'history' / source.source_id).glob('*.json'))
    assert histories
    for history in histories:
        snapshot = SourceBundle.model_validate_json(history.read_bytes())
        if snapshot.source.original_content_hash is None:
            assert snapshot.source.review_status is ReviewStatus.UNAVAILABLE
            assert snapshot.source.failure_category is not None
            assert not snapshot.chunks
            continue
        original = DATA / 'originals' / (snapshot.source.original_content_hash + '.bin')
        assert original.is_file()
        assert hashlib.sha256(original.read_bytes()).hexdigest() == snapshot.source.original_content_hash
    # Audit invariant: the recorded current state has an immutable matching snapshot.
    assert any(SourceBundle.model_validate_json(p.read_bytes()) == bundle for p in histories)
    if raw is None:
        return
    if source.failure_category is None:
        extracted = extract_sections(raw, source, charset=source.charset)
        assert [c.model_dump(exclude={'review_status'}) for c in extracted] == [
            c.model_dump(exclude={'review_status'}) for c in bundle.chunks]
    else:
        assert source.review_status is ReviewStatus.REVIEW_REQUIRED
        with pytest.raises(ExtractionError):
            extract_sections(raw, source, charset=source.charset)
        assert not bundle.chunks


@pytest.mark.parametrize('source', MANIFEST.sources, ids=lambda source: source.source_id)
def test_git_filters_preserve_original_capture_bytes(source):
    if source.original_content_hash is None:
        assert source.review_status is ReviewStatus.UNAVAILABLE
        assert source.failure_category is not None
        return  # There are no captured bytes to send through Git's clean filter.
    if shutil.which('git') is None:
        pytest.skip('Git is required to check repository clean filters')
    path = 'data/official_sources/originals/' + source.original_content_hash + '.bin'
    def object_id(*args):
        return subprocess.run(['git', '-C', str(ROOT), 'hash-object', *args, path],
                              check=True, capture_output=True, text=True).stdout.strip()
    # hash-object without -w does not write objects, stage files, or modify refs.
    assert object_id('--no-filters') == object_id('--path=' + path)
