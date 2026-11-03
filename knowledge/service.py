"""Shared typed boundary. M3-1 intentionally has no query retrieval/ranking engine."""
from typing import Protocol

from .models import (GuidanceResult, KnowledgeRequest, ResourceRecord,
                     ResourceResult, RetrievalStatus)
from .review import PublicationError, verify_publication
from .store import SourceStore


class KnowledgeService(Protocol):
    def retrieve_guidance(self, request: KnowledgeRequest) -> GuidanceResult: ...
    def find_resources(self, request: KnowledgeRequest) -> ResourceResult: ...


def _scope_matches(scope: str, requested: str) -> bool:
    return scope == requested or (scope == 'US' and requested.startswith('US-'))


class FoundationKnowledgeService:
    """Fail-closed interfaces, not a claim that retrieval is implemented."""
    def __init__(self, store: SourceStore):
        self.store = store

    def retrieve_guidance(self, request: KnowledgeRequest) -> GuidanceResult:
        return GuidanceResult(evidence_records=[], source_metadata=[], matching_context=request,
            retrieval_status=RetrievalStatus.UNAVAILABLE,
            limitations=['Query retrieval is not implemented in M3-1.',
                         'Static documents do not establish current orders or assistance availability.'],
            missing_information=['No reviewed query-matched evidence has been retrieved.'])

    def find_resources(self, request: KnowledgeRequest) -> ResourceResult:
        return ResourceResult(resources=[], source_metadata=[], matching_context=request,
            retrieval_status=RetrievalStatus.UNAVAILABLE,
            limitations=['Resource search is not implemented in M3-1.',
                         'No live shelter, transport, program availability or eligibility is established.'],
            missing_information=['No reviewed resource records have been retrieved.'])

    def export_to_m5(self, source_id: str, chunk_id: str, request: KnowledgeRequest) -> dict[str, object]:
        """Explicit exact-ID publication adapter, not automatic retrieval.

        Caller must select at most one complete chunk per source for M5's current
        unique-source-ID contract. No arbitrary text or verification flags accepted.
        """
        with self.store.admin_lock():
            bundle = self.store.load(source_id)
            if bundle is None:
                raise PublicationError('source is unavailable')
            verify_publication(self.store, bundle)
            matches = [c for c in bundle.chunks if c.chunk_id == chunk_id]
            if len(matches) != 1:
                raise PublicationError('reviewed chunk is unavailable')
            chunk = matches[0]
            if (request.hazard not in chunk.applicable_hazards
                    or request.disaster_phase not in chunk.applicable_phases
                    or not _scope_matches(chunk.geographic_scope, request.jurisdiction)):
                raise PublicationError('reviewed evidence is not applicable to the requested context')
            source = bundle.source
            # Heading paths can contain essential conditional language. Never omit
            # them or silently truncate an excerpt to fit a downstream contract.
            guidance = chunk.section_heading + '\n' + chunk.guidance_text
            if len(guidance) > 6000:
                raise PublicationError('complete headed excerpt exceeds the M5 text limit')
            return dict(source_id=source.source_id, source_title=source.title,
                source_url=source.official_url, source_type=source.source_type,
                verified=True, reviewed=True, guidance_text=guidance,
                geographic_scope=chunk.geographic_scope, retrieved_at=source.retrieved_at,
                reviewed_at=source.reviewed_at)

    def validate_resource(self, resource: ResourceRecord) -> ResourceRecord:
        """Validate an admin-curated static listing; never infer live availability.

        No resource finder or automatic contact extraction is implemented here.
        Names, category, prerequisites, area and contacts must be exact strings
        present in reviewed excerpts to prevent fabricated listing details.
        """
        with self.store.admin_lock():
            bundle = self.store.load(resource.source_id)
            if bundle is None:
                raise PublicationError('resource provenance is unavailable')
            verify_publication(self.store, bundle)
            text = '\n'.join(c.guidance_text for c in bundle.chunks)
            if resource.official_url != bundle.source.official_url or resource.service_area != bundle.source.jurisdiction:
                raise PublicationError('resource URL or service area lacks source provenance')
            if any(value not in text for value in [resource.official_name, resource.service_category, *resource.prerequisites]):
                raise PublicationError('resource listing contains unsupported details')
            if resource.official_contact:
                chunks = [c for c in bundle.chunks if c.chunk_id == resource.contact_evidence_chunk_id]
                if len(chunks) != 1 or resource.official_contact not in chunks[0].guidance_text:
                    raise PublicationError('contact information is not supported by reviewed content')
            return resource
