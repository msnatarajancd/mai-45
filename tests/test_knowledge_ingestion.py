import hashlib
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

import pytest

from knowledge.ingestion import (Download, FailureCategory, OfficialHTTPTransport,
    _CuratedRedirects, acquire_source)
from knowledge.models import Classification, ReviewStatus
from knowledge.sources import CURATED_SOURCES, SourceSpec
from knowledge.store import SourceStore, replace_record

DEMO_HTML = b'''<!doctype html><html><body><nav>SIMULATED navigation</nav><main>
<h1>SIMULATED_DEMO Floodwater</h1><p>This is synthetic test content, not official guidance.</p>
<h2>Conditional test section</h2><p>If a test condition applies, preserve this entire sentence.</p>
<script>alert('must not appear')</script><style>.unsafe{display:none}</style>
<p>Do not omit this synthetic caveat.</p></main><footer>SIMULATED footer</footer></body></html>'''


@pytest.fixture
def demo_spec(monkeypatch):
    original = CURATED_SOURCES[1]
    source = replace_record(original.source, classification=Classification.SIMULATED_DEMO)
    spec = SourceSpec(source, original.allowed_urls, ('floodwater',))
    monkeypatch.setattr('knowledge.ingestion.get_source', lambda source_id: spec)
    return spec


class FakeTransport:
    def __init__(self, spec, body=DEMO_HTML, **changes):
        self.spec, self.body, self.changes = spec, body, changes
    def fetch(self, spec, **kwargs):
        values = dict(body=self.body, final_url=spec.source.official_url, http_status=200,
                      content_type='text/html', charset='utf-8', retrieved_at=datetime.now(timezone.utc))
        return Download(**(values | self.changes))


def test_bounded_download_hash_and_headed_extraction(tmp_path, demo_spec, monkeypatch):
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    store = SourceStore(tmp_path)
    bundle = acquire_source(demo_spec.source.source_id, store, transport=FakeTransport(demo_spec))
    assert bundle.source.original_content_hash == hashlib.sha256(DEMO_HTML).hexdigest()
    assert bundle.source.byte_count == len(DEMO_HTML)
    assert bundle.source.http_status == 200
    assert bundle.source.retrieved_at.tzinfo is not None
    assert bundle.source.review_status is ReviewStatus.DOWNLOADED_UNREVIEWED
    assert bundle.source.reviewer is None and bundle.source.reviewed_at is None
    assert store.original(bundle.source.original_content_hash) == DEMO_HTML
    assert len(bundle.chunks) == 2
    text = '\n'.join(c.guidance_text for c in bundle.chunks)
    assert 'If a test condition' in text and 'Do not omit' in text
    assert 'alert' not in text and 'navigation' not in text and 'footer' not in text
    assert store.load(bundle.source.source_id) == bundle


@pytest.mark.parametrize('changes,category', [({'http_status': 404}, FailureCategory.HTTP_ERROR),
    ({'http_status': 500}, FailureCategory.HTTP_ERROR),
    ({'final_url': 'https://attacker.example/document'}, FailureCategory.UNEXPECTED_REDIRECT),
    ({'content_type': 'application/pdf'}, FailureCategory.UNSUPPORTED_CONTENT_TYPE)])
def test_bad_downloads_unavailable(tmp_path, demo_spec, changes, category):
    store = SourceStore(tmp_path)
    bundle = acquire_source(demo_spec.source.source_id, store,
                             transport=FakeTransport(demo_spec, **changes))
    assert bundle.source.review_status is ReviewStatus.UNAVAILABLE
    assert bundle.source.failure_category is category
    assert bundle.source.original_content_hash is None
    assert not bundle.chunks


@pytest.mark.parametrize('body', [b'<body>no identifiable heading</body>', b'',
                                  b'<body><h1>Blocked page</h1><p>Not source guidance</p></body>'])
def test_extraction_failures_are_explicit(tmp_path, demo_spec, body):
    bundle = acquire_source(demo_spec.source.source_id, SourceStore(tmp_path),
                            transport=FakeTransport(demo_spec, body))
    assert bundle.source.failure_category is FailureCategory.EXTRACTION_FAILED
    assert bundle.source.review_status is not ReviewStatus.REVIEWED
    assert not bundle.chunks


def test_oversize_rejected(tmp_path, demo_spec):
    bundle = acquire_source(demo_spec.source.source_id, SourceStore(tmp_path),
                            transport=FakeTransport(demo_spec), max_bytes=20)
    assert bundle.source.failure_category is FailureCategory.TOO_LARGE
    assert bundle.source.original_content_hash is None


def test_reacquisition_invalidates_old_hash_and_chunks(tmp_path, demo_spec):
    store = SourceStore(tmp_path)
    first = acquire_source(demo_spec.source.source_id, store, transport=FakeTransport(demo_spec))
    changed = acquire_source(demo_spec.source.source_id, store,
        transport=FakeTransport(demo_spec, DEMO_HTML.replace(b'synthetic caveat', b'changed synthetic caveat')))
    assert first.source.original_content_hash != changed.source.original_content_hash
    assert changed.source.review_status is ReviewStatus.REVIEW_REQUIRED
    assert all(c.review_status is ReviewStatus.REVIEW_REQUIRED for c in changed.chunks)
    assert {c.chunk_id for c in first.chunks}.isdisjoint(c.chunk_id for c in changed.chunks)
    assert store.original(first.source.original_content_hash) == DEMO_HTML


@pytest.mark.parametrize('error,category', [(TimeoutError('do-not-log-secret'), FailureCategory.TIMEOUT),
    (URLError('do-not-log-secret'), FailureCategory.NETWORK_ERROR),
    (HTTPError('secret-url', 404, 'secret', {}, None), FailureCategory.HTTP_ERROR),
    (HTTPError('secret-url', 500, 'secret', {}, None), FailureCategory.HTTP_ERROR)])
def test_actual_adapter_failures_are_sanitized(tmp_path, demo_spec, monkeypatch, caplog, capsys, error, category):
    class Opener:
        def open(self, *args, **kwargs): raise error
    monkeypatch.setattr('knowledge.ingestion.build_opener', lambda *args: Opener())
    bundle = acquire_source(demo_spec.source.source_id, SourceStore(tmp_path))
    assert bundle.source.failure_category is category
    assert bundle.source.review_status is ReviewStatus.UNAVAILABLE
    assert 'secret' not in bundle.model_dump_json()
    assert not caplog.records and not capsys.readouterr().out


def test_redirect_is_rejected_before_following(demo_spec):
    from urllib.request import Request
    from knowledge.ingestion import AcquisitionFailure
    handler = _CuratedRedirects(demo_spec)
    for location in ['https://www.cdc.gov.evil.example/page', 'http://www.cdc.gov/page',
                     'https://www.cdc.gov/unrelated', 'https://127.0.0.1/private']:
        with pytest.raises(AcquisitionFailure):
            handler.redirect_request(Request(demo_spec.source.official_url), None, 302, '', {}, location)


@pytest.mark.parametrize('content_type,size', [('application/pdf', 10), ('text/html', 2_000_001)])
def test_http_adapter_rejects_headers_before_read(demo_spec, monkeypatch, content_type, size):
    from knowledge.ingestion import AcquisitionFailure
    class Response:
        status = 200
        headers = {'Content-Type': content_type, 'Content-Length': str(size)}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def geturl(self): return demo_spec.source.official_url
        def read(self, size): raise AssertionError('must reject before body read')
    class Opener:
        def open(self, *args, **kwargs): return Response()
    monkeypatch.setattr('knowledge.ingestion.build_opener', lambda *args: Opener())
    with pytest.raises(AcquisitionFailure):
        OfficialHTTPTransport().fetch(demo_spec, timeout=5, max_bytes=2_000_000)


def test_decode_error_does_not_invent_extracted_text(tmp_path, demo_spec):
    bundle = acquire_source(demo_spec.source.source_id, SourceStore(tmp_path),
        transport=FakeTransport(demo_spec, DEMO_HTML + b'\xff'))
    assert bundle.source.failure_category is FailureCategory.DECODE_FAILED
    assert bundle.source.original_content_hash == hashlib.sha256(DEMO_HTML + b'\xff').hexdigest()
    assert bundle.source.review_status is ReviewStatus.REVIEW_REQUIRED
    assert not bundle.chunks
