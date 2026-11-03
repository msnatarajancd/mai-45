"""Bounded static HTML-to-text extraction. Never executes or renders acquired HTML."""
import hashlib
import re
from html.parser import HTMLParser

from .models import EvidenceChunk, ReviewStatus


class ExtractionError(ValueError):
    pass


class DecodeError(ExtractionError):
    pass


class _Sections(HTMLParser):
    SKIP = {'script', 'style', 'noscript', 'template', 'iframe', 'nav', 'footer',
            'header', 'svg', 'canvas', 'form', 'button'}
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, target):
        super().__init__(convert_charrefs=True)
        self.target = target
        self.stack = []
        self.levels = []
        self.heading = None
        self.heading_text = []
        self.parts = []
        self.sections = []

    def active(self):
        return self.target in self.stack and not any(t in self.SKIP for t in self.stack)

    def flush(self):
        text = re.sub(r'[ \t\r\f\v]+', ' ', ''.join(self.parts))
        text = re.sub(r'\n\s*\n+', '\n', text).strip()
        if text:
            if not self.levels:
                # Content before the first identifiable heading is not publishable.
                raise ExtractionError('readable content lacks an identifiable heading')
            heading = ' > '.join(t for _, t in self.levels)
            if len(text) > 6000 or len(heading) > 1000:
                raise ExtractionError('whole section exceeds safe excerpt bounds; manual extraction required')
            self.sections.append((heading, text))
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)
        if not self.active():
            return
        if re.fullmatch('h[1-6]', tag):
            self.flush()
            self.heading = int(tag[1])
            self.heading_text = []
        elif tag in {'p', 'li', 'div', 'br', 'section', 'ul', 'ol', 'table', 'tr'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.active():
            if self.heading is not None and tag == f'h{self.heading}':
                title = ' '.join(''.join(self.heading_text).split())
                if title:
                    self.levels = [(n, t) for n, t in self.levels if n < self.heading]
                    self.levels.append((self.heading, title))
                self.heading = None
            elif tag in {'p', 'li', 'div', 'section', 'ul', 'ol', 'tr'}:
                self.parts.append('\n')
        if tag in self.stack:
            # Pop the matching element and any malformed unclosed descendants.
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            self.stack = self.stack[:index]

    def handle_data(self, data):
        if self.active():
            if self.heading is not None:
                self.heading_text.append(data)
            else:
                self.parts.append(data)


def extract_sections(raw: bytes, source, *, charset: str = 'utf-8') -> list[EvidenceChunk]:
    if charset.casefold() not in {'utf-8', 'utf8', 'us-ascii', 'ascii', 'iso-8859-1', 'windows-1252'}:
        raise DecodeError('unsupported character encoding')
    try:
        html = raw.decode(charset, errors='strict')
    except (UnicodeError, LookupError):
        raise DecodeError('HTML decoding failed') from None
    target = ('main' if re.search(r'<main\b', html, re.I)
              else 'article' if re.search(r'<article\b', html, re.I) else 'body')
    parser = _Sections(target)
    try:
        parser.feed(html)
        parser.close()
        parser.flush()
    except (ValueError, AssertionError):
        raise ExtractionError('HTML extraction failed or requires manual section review') from None
    if not parser.sections:
        raise ExtractionError('no readable headed sections were extracted')
    digest = hashlib.sha256(raw).hexdigest()
    chunks = []
    for index, (heading, text) in enumerate(parser.sections):
        chunk_id = hashlib.sha256(f'{source.source_id}:{digest}:{index}:{heading}'.encode()).hexdigest()
        chunks.append(EvidenceChunk(chunk_id=chunk_id, source_id=source.source_id,
            section_heading=heading, guidance_text=text, applicable_hazards=source.hazards,
            applicable_phases=source.disaster_phases, geographic_scope=source.jurisdiction,
            review_status=ReviewStatus.DOWNLOADED_UNREVIEWED))
    return chunks
