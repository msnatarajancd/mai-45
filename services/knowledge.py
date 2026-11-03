"""M3 retrieval boundary: never present placeholders as retrieved evidence."""
from pathlib import Path

from domain.contracts import GuidanceCitation, GuidanceResult, Household, Source


def retrieve_guidance(query: str, phase: str, context: Household | None = None, *,
                      hazard=None, jurisdiction=None, service=None) -> GuidanceResult:
    """Exact excerpts only, no model. Hazard/geography must be explicit.

    Household context supplies neither hazard nor geography. The default store
    is repo-relative. An injected service is trusted application composition.
    """
    def abstain(status, message, missing=(), limitations=()):
        return GuidanceResult(answer=message, retrieval_status=status,
            insufficient_evidence=True, missing_information=list(missing),
            limitations=list(limitations))

    if not hazard or not jurisdiction:
        return abstain('INSUFFICIENT_EVIDENCE',
            'Insufficient evidence context: select a hazard and jurisdiction first.',
            ['Explicit hazard and jurisdiction are required; household preferences do not establish either.'])
    phases = {'protect': 'prepare', 'prepare': 'prepare', 'respond': 'respond', 'recover': 'recover'}
    if phase not in phases:
        return abstain('INSUFFICIENT_EVIDENCE', 'Insufficient evidence context: unsupported disaster phase.')
    try:
        # Lazy imports keep emergency UI imports independent of the M3 package.
        from knowledge.models import (DisasterPhase, GuidanceResult as M3Result,
            Hazard, KnowledgeRequest, RetrievalStatus, ReviewStatus)
        from knowledge.service import FoundationKnowledgeService
        from knowledge.candidates import public_source_limitations
        from knowledge.store import SourceStore
        request = KnowledgeRequest(hazard=Hazard(hazard), disaster_phase=DisasterPhase(phases[phase]),
            jurisdiction=jurisdiction, safety_topic=query)
        if service is None:
            service = FoundationKnowledgeService(SourceStore(
                Path(__file__).resolve().parents[1] / 'data/official_sources'))
        result = service.retrieve_guidance(request)
        result = M3Result.model_validate_json(result.model_dump_json())
        if result.matching_context != request:
            raise ValueError('retrieval context mismatch')
        if result.retrieval_status not in (RetrievalStatus.SUCCESS, RetrievalStatus.INSUFFICIENT_EVIDENCE):
            return abstain(result.retrieval_status.value,
                'Verified guidance is unavailable.' if result.retrieval_status is RetrievalStatus.UNAVAILABLE
                else 'No relevant reviewed evidence is available for this topic and context.',
                result.missing_information, result.limitations)
        if not result.evidence_records:
            return abstain('INSUFFICIENT_EVIDENCE', 'Insufficient reviewed evidence for this request.',
                           result.missing_information, result.limitations)
        sources = {s.source_id: s for s in result.source_metadata}
        proofs = {p.chunk_id: p for p in result.evidence_metadata}
        if set(proofs) != {e.chunk_id for e in result.evidence_records}:
            raise ValueError('missing citation provenance')
        citations, links = [], []
        for evidence in result.evidence_records:
            source, proof = sources[evidence.source_id], proofs[evidence.chunk_id]
            if (source.review_status is not ReviewStatus.REVIEWED
                    or evidence.review_status is not ReviewStatus.REVIEWED
                    or proof.source_id != source.source_id
                    or proof.original_content_hash != source.original_content_hash
                    or proof.official_url != source.official_url):
                raise ValueError('invalid publication provenance')
            citations.append(GuidanceCitation(citation_id=evidence.chunk_id, source_id=source.source_id,
                parent_chunk_id=proof.parent_chunk_id, title=source.title, publisher=source.publisher,
                official_url=source.official_url, original_content_hash=proof.original_content_hash,
                section_heading=evidence.section_heading, passage=evidence.guidance_text,
                passage_start=proof.passage_start, passage_end=proof.passage_end,
                jurisdiction=evidence.geographic_scope, hazards=[h.value for h in evidence.applicable_hazards],
                phases=[p.value for p in evidence.applicable_phases],
                source_review=proof.source_review.model_dump(mode='json'),
                candidate_review=proof.candidate_review.model_dump(mode='json'),
                safety_caveats=proof.safety_caveats, source_limitations=public_source_limitations(source)))
            links.append(Source(title=source.title, url=source.official_url, publisher=source.publisher,
                reviewed_at=source.reviewed_at.isoformat(), citation_id=evidence.chunk_id,
                source_id=source.source_id, original_content_hash=source.original_content_hash))
        insufficient = result.retrieval_status is not RetrievalStatus.SUCCESS
        return GuidanceResult(answer=('Insufficient evidence: fewer reviewed excerpts are available than requested.'
                if insufficient else 'Reviewed source excerpts. These do not establish current conditions or household safety.'),
            sources=links, citations=citations, insufficient_evidence=insufficient,
            retrieval_status=result.retrieval_status.value, limitations=result.limitations,
            missing_information=result.missing_information)
    except Exception:
        return abstain('UNAVAILABLE', 'Verified guidance is unavailable. No evidence could be validated.')
