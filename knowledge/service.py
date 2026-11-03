"""Shared typed boundary for reviewed retrieval and existing publication services."""
from typing import Protocol

from .models import (GuidanceResult, KnowledgeRequest, ResourceRecord,
                     ResourceResult, RetrievalStatus)
from .review import PublicationError, verify_publication
from .store import SourceStore


class KnowledgeService(Protocol):
    def retrieve_guidance(self, request: KnowledgeRequest) -> GuidanceResult: ...
    def find_resources(self, request: KnowledgeRequest) -> ResourceResult: ...


class FoundationKnowledgeService:
    """Deterministic retrieval; other boundaries retain their existing gates."""
    def __init__(self, store: SourceStore):
        self.store = store

    def retrieve_guidance(self, request: KnowledgeRequest) -> GuidanceResult:
        from .retrieval import retrieve_guidance
        return retrieve_guidance(self.store, request)

    def find_resources(self, request: KnowledgeRequest) -> ResourceResult:
        return ResourceResult(resources=[], source_metadata=[], matching_context=request,
            retrieval_status=RetrievalStatus.UNAVAILABLE,
            limitations=['Resource search is not implemented in M3-1.',
                         'No live shelter, transport, program availability or eligibility is established.'],
            missing_information=['No reviewed resource records have been retrieved.'])

    def export_to_m5(self, source_id: str, chunk_id: str, request: KnowledgeRequest) -> dict[str, object]:
        """Export one approved candidate, never a parent-section ID.

        M5's legacy source_id carries the candidate citation ID, permitting unique
        references to multiple candidates from one parent. Parent identity, exact
        context and caveats remain in guidance_text. No truncation is permitted.
        """
        from .candidates import verify_candidate_publication
        try:
            with self.store.admin_lock():
                candidate = self.store.load_candidate(source_id, chunk_id)
                if candidate is None or candidate.source_id != source_id or candidate.chunk_id != chunk_id:
                    raise PublicationError('approved candidate is unavailable; parent-section IDs are not accepted')
                bundle = verify_candidate_publication(self.store, candidate, request)
                source = bundle.source
                parts = [f'Parent source: {source.source_id}\nCitation: {candidate.chunk_id}',
                         candidate.section_heading + '\n' + candidate.original_passage]
                for context in candidate.surrounding_context:
                    if (context.chunk_id == candidate.parent_chunk_id
                            and context.guidance_text == candidate.original_passage):
                        continue
                    parts.append('Source context: ' + context.section_heading + '\n' + context.guidance_text)
                parts.append('Safety caveats:\n' + '\n'.join(candidate.safety_caveats))
                parts.append('Source limitations:\n' + '\n'.join(source.limitations))
                guidance = '\n\n'.join(parts)
                if len(guidance) > 6000:
                    raise PublicationError('complete candidate context exceeds the M5 text limit')
                return dict(source_id=candidate.chunk_id, source_title=source.title,
                    source_url=source.official_url, source_type=source.source_type,
                    verified=True, reviewed=True, guidance_text=guidance,
                    geographic_scope=candidate.jurisdiction, retrieved_at=source.retrieved_at,
                    reviewed_at=min(source.reviewed_at, candidate.review.reviewed_at))
        except PublicationError:
            raise
        except (OSError, ValueError, TypeError):
            raise PublicationError('candidate publication validation or storage access failed') from None

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
