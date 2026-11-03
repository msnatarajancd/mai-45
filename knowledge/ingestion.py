"""Explicit curated acquisition: python -m knowledge.ingestion --all --root PATH."""
import argparse
import hashlib
import json
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .extraction import DecodeError, ExtractionError, extract_sections
from .models import FailureCategory, ReviewStatus, SourceBundle, validate_official_url
from .sources import CURATED_SOURCES, SourceSpec, get_source
from .store import SourceStore, replace_record

MAX_BYTES = 2_000_000
TIMEOUT_SECONDS = 20
CONTENT_TYPES = {'text/html', 'application/xhtml+xml'}


class AcquisitionFailure(ValueError):
    def __init__(self, category: FailureCategory, *, http_status: int | None = None):
        self.category = category
        self.http_status = http_status
        super().__init__(category.value)


def validate_target(spec: SourceSpec, url: str):
    try:
        validate_official_url(url)
    except ValueError:
        raise AcquisitionFailure(FailureCategory.INVALID_ORIGIN) from None
    if url not in spec.allowed_urls:
        raise AcquisitionFailure(FailureCategory.UNEXPECTED_REDIRECT)


@dataclass(frozen=True)
class Download:
    body: bytes
    final_url: str
    http_status: int
    content_type: str
    charset: str
    retrieved_at: datetime


class SourceTransport(Protocol):
    def fetch(self, spec: SourceSpec, *, timeout: float, max_bytes: int) -> Download: ...


class _CuratedRedirects(HTTPRedirectHandler):
    def __init__(self, spec):
        self.spec = spec
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > 3:
            raise AcquisitionFailure(FailureCategory.UNEXPECTED_REDIRECT, http_status=code)
        target = urljoin(req.full_url, newurl)
        try:
            validate_target(self.spec, target)
        except AcquisitionFailure as error:
            raise AcquisitionFailure(error.category, http_status=code) from None
        return super().redirect_request(req, fp, code, msg, headers, target)


class OfficialHTTPTransport:
    def fetch(self, spec, *, timeout, max_bytes):
        validate_target(spec, spec.source.official_url)
        try:
            request = Request(spec.source.official_url,
                headers={'User-Agent': 'ReadyRelief-Educational-SourceReview/0.1',
                         'Accept': 'text/html,application/xhtml+xml', 'Accept-Encoding': 'identity'})
            with build_opener(_CuratedRedirects(spec)).open(request, timeout=timeout) as response:
                status = response.status
                validate_target(spec, response.geturl())
                if status != 200:
                    raise AcquisitionFailure(FailureCategory.HTTP_ERROR, http_status=status)
                if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                    raise AcquisitionFailure(FailureCategory.UNSUPPORTED_CONTENT_TYPE, http_status=status)
                message = Message()
                message['content-type'] = response.headers.get('Content-Type', '')
                content_type = message.get_content_type()
                if content_type not in CONTENT_TYPES:
                    raise AcquisitionFailure(FailureCategory.UNSUPPORTED_CONTENT_TYPE, http_status=status)
                length = response.headers.get('Content-Length', '')
                if length.isdigit() and int(length) > max_bytes:
                    raise AcquisitionFailure(FailureCategory.TOO_LARGE, http_status=status)
                raw = response.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise AcquisitionFailure(FailureCategory.TOO_LARGE, http_status=status)
                return Download(raw, response.geturl(), status, content_type,
                                message.get_content_charset() or 'utf-8', datetime.now(timezone.utc))
        except AcquisitionFailure:
            raise
        except HTTPError as error:
            raise AcquisitionFailure(FailureCategory.HTTP_ERROR, http_status=error.code) from None
        except (TimeoutError, socket.timeout):
            raise AcquisitionFailure(FailureCategory.TIMEOUT) from None
        except ssl.SSLError:
            raise AcquisitionFailure(FailureCategory.TLS_ERROR) from None
        except URLError as error:
            category = (FailureCategory.TIMEOUT if isinstance(error.reason, (TimeoutError, socket.timeout))
                        else FailureCategory.TLS_ERROR if isinstance(error.reason, ssl.SSLError)
                        else FailureCategory.NETWORK_ERROR)
            raise AcquisitionFailure(category) from None
        except OSError:
            raise AcquisitionFailure(FailureCategory.NETWORK_ERROR) from None


def acquire_source(source_id: str, store: SourceStore, *, transport: SourceTransport | None = None,
                   timeout: float = TIMEOUT_SECONDS, max_bytes: int = MAX_BYTES) -> SourceBundle:
    spec = get_source(source_id)
    if not 0 < timeout <= 60 or not 0 < max_bytes <= MAX_BYTES:
        raise ValueError('invalid acquisition bounds')
    attempted_at = datetime.now(timezone.utc)
    try:
        download = (transport or OfficialHTTPTransport()).fetch(spec, timeout=timeout, max_bytes=max_bytes)
        validate_target(spec, download.final_url)
        if download.http_status != 200:
            raise AcquisitionFailure(FailureCategory.HTTP_ERROR, http_status=download.http_status)
        if download.content_type not in CONTENT_TYPES:
            raise AcquisitionFailure(FailureCategory.UNSUPPORTED_CONTENT_TYPE, http_status=download.http_status)
        if len(download.body) > max_bytes:
            raise AcquisitionFailure(FailureCategory.TOO_LARGE, http_status=download.http_status)
    except AcquisitionFailure as failure:
        with store.admin_lock():
            previous = store.load(source_id)
            source = replace_record(previous.source if previous else spec.source,
                review_status=ReviewStatus.UNAVAILABLE, failure_category=failure.category,
                http_status=failure.http_status, last_attempt_at=attempted_at,
                reviewer=None, reviewed_at=None)
            chunks = [replace_record(c, review_status=ReviewStatus.UNAVAILABLE) for c in previous.chunks] if previous else []
            bundle = SourceBundle(source=source, chunks=chunks)
            store.save_locked(bundle)
        return bundle
    if not download.body:
        # Empty responses contain no document provenance and are not successes.
        with store.admin_lock():
            source = replace_record(spec.source, review_status=ReviewStatus.UNAVAILABLE,
                failure_category=FailureCategory.EXTRACTION_FAILED, http_status=download.http_status,
                last_attempt_at=attempted_at)
            bundle = SourceBundle(source=source, chunks=[])
            store.save_locked(bundle)
        return bundle
    digest = hashlib.sha256(download.body).hexdigest()
    source = replace_record(spec.source, content_type=download.content_type, charset=download.charset,
        original_content_hash=digest, retrieved_at=download.retrieved_at, final_url=download.final_url,
        http_status=download.http_status, byte_count=len(download.body) or None,
        last_attempt_at=attempted_at, review_status=ReviewStatus.DOWNLOADED_UNREVIEWED)
    failure = None
    try:
        chunks = extract_sections(download.body, source, charset=download.charset)
        headings = ' '.join(c.section_heading.casefold() for c in chunks)
        if not all(term in headings for term in spec.expected_heading_terms):
            raise ExtractionError('expected page identity heading not found')
    except DecodeError:
        failure = FailureCategory.DECODE_FAILED
        chunks = []
    except ExtractionError:
        failure = FailureCategory.EXTRACTION_FAILED
        chunks = []
    with store.admin_lock():
        previous = store.load(source_id)
        if failure or previous is not None:
            source = replace_record(source, review_status=ReviewStatus.REVIEW_REQUIRED, failure_category=failure)
        chunks = [replace_record(c, review_status=source.review_status) for c in chunks]
        store.write_original(download.body)
        bundle = SourceBundle(source=source, chunks=chunks)
        store.save_locked(bundle)
    return bundle


def main():
    parser = argparse.ArgumentParser(description='Acquire only curated official source candidates; never publish automatically.')
    parser.add_argument('--root', type=Path, default=Path('data/official_sources'))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true')
    group.add_argument('--source-id', choices=[s.source.source_id for s in CURATED_SOURCES])
    args = parser.parse_args()
    store = SourceStore(args.root)
    store.initialize()
    for source_id in ([s.source.source_id for s in CURATED_SOURCES] if args.all else [args.source_id]):
        bundle = acquire_source(source_id, store)
        report = bundle.source.model_dump(mode='json')
        report['extracted_section_count'] = len(bundle.chunks)
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
