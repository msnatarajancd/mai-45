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



class _FragmentText(HTMLParser):
    """Decode the acquired encoded fragment once; never render or execute it."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in _Sections.VOID:
            self.stack.append(tag)
        if tag in {'p', 'li', 'br', 'ul', 'ol', 'h2', 'h3', 'h4'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'p', 'li', 'ul', 'ol', 'h2', 'h3', 'h4'}:
            self.parts.append('\n')
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, data):
        if not any(tag in _Sections.SKIP for tag in self.stack):
            self.parts.append(data)


def _fragment_text(fragment):
    parser = _FragmentText()
    parser.feed(fragment)
    parser.close()
    text = re.sub(r'[ \t\r\f\v]+', ' ', ''.join(parser.parts))
    text = re.sub(r'\n\s*\n+', '\n', text).strip()
    if not text or len(text) > 6000:
        raise ExtractionError('empty or oversized acquired service field')
    return text


class _EEAPFields(HTMLParser):
    """Parse only known fields under main/div#service-data/service.

    Featured services, organization descriptions, scripts, and visual page chrome
    are not substituted for program text. Missing/ambiguous field pairs fail closed.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.wrapper_depth = None
        self.service_depth = None
        self.field = None
        self.field_parts = []
        self.fields = {}
        self.faq = None
        self.faqs = []
        self.service_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in _Sections.VOID:
            self.stack.append(tag)
        if tag == 'div' and attrs.get('id') == 'service-data' and 'main' in self.stack:
            if self.wrapper_depth is not None:
                raise ExtractionError('ambiguous service-data containers')
            self.wrapper_depth = len(self.stack)
        if tag == 'service' and self.wrapper_depth is not None and len(self.stack) == self.wrapper_depth + 1:
            self.service_depth = len(self.stack)
            self.service_count += 1
        if self.service_depth is None:
            return
        relative = self.stack[self.service_depth:]
        if relative == ['related-faq']:
            self.faq = {}
        if relative in (['name'], ['longdescription'], ['related-faq', 'name'],
                        ['related-faq', 'faq', 'answer']):
            if self.field is not None:
                raise ExtractionError('nested acquired fields are unsupported')
            self.field = (tag, len(self.stack), self.faq if len(relative) > 1 else self.fields)
            self.field_parts = []

    def handle_endtag(self, tag):
        if self.field is not None and (tag, len(self.stack)) == self.field[:2]:
            field, _, destination = self.field
            if field in destination:
                raise ExtractionError('duplicate acquired service field')
            destination[field] = ''.join(self.field_parts)
            self.field = None
        if tag == 'related-faq' and self.service_depth is not None and self.stack[self.service_depth:] == ['related-faq']:
            if not self.faq or set(self.faq) != {'name', 'answer'}:
                raise ExtractionError('FAQ heading/answer pair missing')
            self.faqs.append(self.faq)
            self.faq = None
        if tag == 'service' and self.service_depth == len(self.stack):
            self.service_depth = None
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, data):
        if self.field is not None and not any(tag in _Sections.SKIP for tag in self.stack):
            self.field_parts.append(data)


def _eeap_sections(html, source):
    parser = _EEAPFields()
    parser.feed(html)
    parser.close()
    if parser.service_count != 1 or set(parser.fields) != {'name', 'longdescription'}:
        raise ExtractionError('unique acquired EEAP description is missing')
    title = ' '.join(parser.fields['name'].split())
    if title != source.title:
        raise ExtractionError('acquired EEAP identity does not match provenance')
    sections = [(title + ' > longDescription', _fragment_text(parser.fields['longdescription']))]
    for faq in parser.faqs:
        question = ' '.join(faq['name'].split())
        if not question:
            raise ExtractionError('empty FAQ heading')
        sections.append((title + ' > ' + question, _fragment_text(faq['answer'])))
    if len({heading for heading, _ in sections}) != len(sections):
        raise ExtractionError('duplicate FAQ headings')
    return sections


def extract_sections(raw: bytes, source, *, charset: str = 'utf-8') -> list[EvidenceChunk]:
    if charset.casefold() not in {'utf-8', 'utf8', 'us-ascii', 'ascii', 'iso-8859-1', 'windows-1252'}:
        raise DecodeError('unsupported character encoding')
    try:
        html = raw.decode(charset, errors='strict')
    except (UnicodeError, LookupError):
        raise DecodeError('HTML decoding failed') from None
    if (source.source_id == 'miami-dade-eeap' and source.official_url ==
            'https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672'):
        sections = _eeap_sections(html, source)
    else:
        target = ('main' if re.search(r'<main\b', html, re.I)
                  else 'article' if re.search(r'<article\b', html, re.I) else 'body')
        parser = _Sections(target)
        try:
            parser.feed(html)
            parser.close()
            parser.flush()
        except (ValueError, AssertionError):
            raise ExtractionError('HTML extraction failed or requires manual section review') from None
        sections = parser.sections
    if not sections:
        raise ExtractionError('no readable headed sections were extracted')
    digest = hashlib.sha256(raw).hexdigest()
    chunks = []
    for index, (heading, text) in enumerate(sections):
        chunk_id = hashlib.sha256(f'{source.source_id}:{digest}:{index}:{heading}'.encode()).hexdigest()
        chunks.append(EvidenceChunk(chunk_id=chunk_id, source_id=source.source_id,
            section_heading=heading, guidance_text=text, applicable_hazards=source.hazards,
            applicable_phases=source.disaster_phases, geographic_scope=source.jurisdiction,
            review_status=ReviewStatus.DOWNLOADED_UNREVIEWED))
    return chunks
