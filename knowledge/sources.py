"""Manually curated candidate allowlist; origin does not imply content review."""
from dataclasses import dataclass
from .models import Classification, DisasterPhase, Hazard, SourceRecord


@dataclass(frozen=True)
class SourceSpec:
    source: SourceRecord
    allowed_urls: tuple[str, ...]
    expected_heading_terms: tuple[str, ...]


def _spec(source_id, publisher, title, url, jurisdiction, phases, terms):
    source = SourceRecord(source_id=source_id, publisher=publisher, title=title,
        official_url=url, source_type='official_static_web_guidance', jurisdiction=jurisdiction,
        hazards=[Hazard.FLOOD, Hazard.HURRICANE], disaster_phases=phases,
        classification=Classification.OFFICIAL_SOURCE,
        limitations=['Candidate source; human review required before publication.',
                     'Static guidance is not live availability or a current evacuation order.',
                     'HTML-only extraction may omit images, embedded documents, or dynamic content.'])
    return SourceSpec(source, (url,), terms)


CURATED_SOURCES = (
    _spec('cdc-flood-reentry', 'Centers for Disease Control and Prevention',
          'Safety Guidelines: Reentering Your Flooded Home',
          'https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html',
          'US', [DisasterPhase.RECOVER], ('reentering', 'flooded home')),
    _spec('cdc-floodwater', 'Centers for Disease Control and Prevention',
          'Safety Guidelines: Floodwater',
          'https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html',
          'US', [DisasterPhase.RESPOND, DisasterPhase.RECOVER], ('floodwater',)),
    _spec('miami-dade-eeap', 'Miami-Dade County',
          'Emergency & Evacuation Assistance Program (EEAP)',
          'https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672',
          'US-FL-MIAMI-DADE', [DisasterPhase.PREPARE, DisasterPhase.RESPOND], ('evacuation assistance',)),
)


def get_source(source_id: str) -> SourceSpec:
    matches = [spec for spec in CURATED_SOURCES if spec.source.source_id == source_id]
    if len(matches) != 1:
        raise ValueError('source ID is not in the curated acquisition allowlist')
    return matches[0]
