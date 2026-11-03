"""Offline lexical retrieval. No model, network, generated advice, or signoff."""
import re

from .candidates import verify_candidate_trace
from .models import (CandidateStatus, EvidenceChunk, EvidenceProvenance, GuidanceResult,
                     KnowledgeRequest, RetrievalStatus, ReviewStatus)
from .review import PublicationError, verify_publication


_STOP = set('a an the and or to of in on for from with is are was be been do does '
            'i me my we our you your it this that what which how should can could '
            'would please about need needs help advice guidance precautions take '
            'around flood hurricane wildfire'.split())


def _terms(text):
    return set(re.findall(r'[a-z0-9]+', text.lower())) - _STOP


def _operational(text):
    """Conservative abstention, not an emergency detector or routing decision."""
    text = text.lower().replace('\u2019', "'")
    patterns = (
        r'\b(live|current|currently|today|tonight|now|latest|real.time)\b',
        r'\b(alerts?|orders?|capacity|vacanc\w*|available|availability|eligible|eligibility|qualify)\b',
        r'\b(am i|are we|can i|can we)\b.*\b(enroll|receive|get assistance|return|reenter|enter|stay|evacuate)\b',
        r'\b(is|are)\b.*\b(home|house|building|apartment)\b.*\bsafe\b',
        r'\b(my|our|this|the)\b.*\b(home|house|building|apartment)\b.*\b(safe|habitable|sound)\b',
        r'\b(should|must|do|can|may)\s+(i|we)\b.*\b(evacuate|return|reenter|enter|stay)\b',
        r'\bsafe (to|for)\b',
        r'\b(will|can)\b.*\b(transport|pick|shelter|assist|enroll)\w*\b',
        r'\b(shelter|transportation|transport)\b.*\b(open|space|spaces|operating|guarantee|accepting)\w*\b',
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _scope_matches(scope, requested):
    return scope == requested or requested.startswith(scope + '-')


def retrieve_guidance(store, request: KnowledgeRequest) -> GuidanceResult:
    """Use safety_topic plus household_needs as query text; phase/hazard/area
    are mandatory hard filters. Evidence is verbatim and citations use candidate
    SHA-256 IDs. Source and candidate proof/context accompany each result.

    Rank by 2 * distinct passage token overlaps + distinct heading overlaps;
    require at least half the non-stopword query terms in the passage. Ties use
    source ID then candidate ID. No synonyms, stemming, or relevance generation.
    SUCCESS means the requested excerpt count was met, not a complete answer.
    INSUFFICIENT_EVIDENCE can contain fewer matches; operational requests contain
    none. No matches in a trustworthy corpus is NO_RELEVANT_EVIDENCE; a missing,
    unreadable, busy, corrupt, or wholly unpublished corpus is UNAVAILABLE.
    """
    request = KnowledgeRequest.model_validate_json(request.model_dump_json())
    limitations = [
        'Static evidence does not establish live alerts, evacuation orders, capacity, transport, eligibility, or building safety.',
        'Lexical matching and requested excerpt count do not establish completeness or personal applicability.',
        'Review validity uses stored review gates and integrity checks; no automatic freshness interval is configured.',
        'Preserve citation context and caveats when displaying or using these excerpts.']

    def result(status, missing, matches=()):
        sources = {bundle.source.source_id: bundle.source for _, _, bundle in matches}
        return GuidanceResult(matching_context=request, retrieval_status=status,
            limitations=limitations, missing_information=missing,
            evidence_records=[EvidenceChunk(chunk_id=c.chunk_id, source_id=c.source_id,
                section_heading=c.section_heading, guidance_text=c.original_passage,
                applicable_hazards=c.hazards, applicable_phases=c.phases,
                geographic_scope=c.jurisdiction, review_status=ReviewStatus.REVIEWED)
                for _, c, _ in matches],
            source_metadata=list(sources.values()),
            evidence_metadata=[EvidenceProvenance(chunk_id=c.chunk_id, source_id=c.source_id,
                parent_chunk_id=c.parent_chunk_id, official_url=c.official_url,
                original_content_hash=c.original_content_hash, passage_start=c.passage_start,
                passage_end=c.passage_end, candidate_review=c.review, source_review=bundle.review,
                surrounding_context=c.surrounding_context, safety_caveats=c.safety_caveats)
                for _, c, bundle in matches])

    query = ' '.join([request.safety_topic or '', *request.household_needs])
    if _operational(query):
        return result(RetrievalStatus.INSUFFICIENT_EVIDENCE,
            ['Live or personal operational determinations require current authoritative information; static excerpts cannot answer this request.'])
    terms = _terms(query)
    if not terms:
        return result(RetrievalStatus.INSUFFICIENT_EVIDENCE, ['A specific static safety topic is required.'])
    try:
        # Never initialize a missing store. Serialize the complete snapshot against
        # supported review/acquisition writers using their existing shared lock.
        if not store.root.is_dir():
            return result(RetrievalStatus.UNAVAILABLE, ['The trusted evidence store is unavailable.'])
        with store.admin_lock():
            matches, trusted = [], 0
            for bundle in store.list_bundles():
                try:
                    verify_publication(store, bundle)
                except PublicationError:
                    continue
                for candidate in store.list_candidates(bundle.source.source_id):
                    if candidate.review_status is not CandidateStatus.APPROVED:
                        continue
                    try:
                        verify_candidate_trace(store, candidate)
                    except PublicationError:
                        continue
                    if candidate.review.reviewed_at < bundle.source.retrieved_at:
                        continue
                    trusted += 1
                    source = bundle.source
                    if (request.hazard not in source.hazards
                            or request.disaster_phase not in source.disaster_phases
                            or not _scope_matches(source.jurisdiction, request.jurisdiction)
                            or request.hazard not in candidate.hazards
                            or request.disaster_phase not in candidate.phases
                            or not _scope_matches(candidate.jurisdiction, request.jurisdiction)):
                        continue
                    # Generic source titles cannot make unrelated passages relevant.
                    overlap = terms & _terms(candidate.original_passage)
                    if not overlap or len(overlap) / len(terms) < 0.5:
                        continue
                    score = 2 * len(overlap) + len(terms & _terms(candidate.section_heading))
                    matches.append((score, candidate, bundle))
            matches.sort(key=lambda item: (-item[0], item[1].source_id, item[1].chunk_id))
            matches = matches[:request.requested_evidence_count]
            if not trusted:
                return result(RetrievalStatus.UNAVAILABLE, ['No evidence satisfies both source and candidate publication gates.'])
            if not matches:
                return result(RetrievalStatus.NO_RELEVANT_EVIDENCE, ['No trustworthy passage matches the requested topic and scope.'])
            if len(matches) < request.requested_evidence_count:
                return result(RetrievalStatus.INSUFFICIENT_EVIDENCE,
                    ['Fewer matching reviewed excerpts are available than requested.'], matches)
            return result(RetrievalStatus.SUCCESS, [], matches)
    except (OSError, ValueError, TypeError):
        # A partial read never yields partial success or raw error details.
        return result(RetrievalStatus.UNAVAILABLE, ['Evidence store validation or access failed; no evidence was returned.'])
