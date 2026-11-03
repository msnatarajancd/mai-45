"""Deterministic, source-anchored review preparation; no retrieval or signoff."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import (CandidatePacket, CandidateStatus, DisasterPhase as Phase,
                     Hazard, ReviewCandidate, ReviewStatus)
from .store import SourceStore


def candidate_context_hash(candidate: ReviewCandidate) -> str:
    data = candidate.model_dump(mode='json', exclude={'review_status', 'review', 'rejection'})
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def verify_candidate_trace(store: SourceStore, candidate: ReviewCandidate):
    from .review import PublicationError, verify_original
    candidate = ReviewCandidate.model_validate_json(candidate.model_dump_json())
    bundle = store.load(candidate.source_id)
    if bundle is None or (bundle.source.original_content_hash != candidate.original_content_hash
            or bundle.source.official_url != candidate.official_url
            or bundle.source.classification != candidate.classification
            or bundle.source.jurisdiction != candidate.jurisdiction):
        raise PublicationError('candidate source provenance changed or is unavailable')
    if bundle.source.review_status in (ReviewStatus.STALE, ReviewStatus.UNAVAILABLE):
        raise PublicationError('candidate source is stale or unavailable')
    verify_original(store, bundle)
    lookup = {c.chunk_id: c for c in bundle.chunks}
    for context in candidate.surrounding_context:
        current = lookup.get(context.chunk_id)
        if current is None or current.model_dump(exclude={'review_status'}) != context.model_dump(exclude={'review_status'}):
            raise PublicationError('candidate context changed since preparation')
    return bundle


def verify_candidate_publication(store, candidate, request=None):
    """Shared fail-closed publication gate. Caller holds the store admin lock."""
    from .review import PublicationError, verify_publication
    candidate = ReviewCandidate.model_validate_json(candidate.model_dump_json())
    if candidate.review_status is not CandidateStatus.APPROVED:
        raise PublicationError('only an approved candidate may be published')
    bundle = verify_candidate_trace(store, candidate)
    verify_publication(store, bundle)
    if candidate.review.reviewed_at < bundle.source.retrieved_at:
        raise PublicationError('candidate review predates the current acquisition')
    if request is not None:
        from .models import KnowledgeRequest
        request = KnowledgeRequest.model_validate_json(request.model_dump_json())
        def scope_matches(scope):
            return scope == request.jurisdiction or request.jurisdiction.startswith(scope + '-')
        source = bundle.source
        if (request.hazard not in source.hazards or request.hazard not in candidate.hazards
                or request.disaster_phase not in source.disaster_phases
                or request.disaster_phase not in candidate.phases
                or not scope_matches(source.jurisdiction) or not scope_matches(candidate.jurisdiction)):
            raise PublicationError('reviewed evidence is not applicable to the requested context')
    return bundle


def make_candidate(bundle, parent, *, start=0, end=None, phases, hazards=None, context=(), caveats=()):
    end = len(parent.guidance_text) if end is None else end
    passage = parent.guidance_text[start:end]
    hazards = list(hazards or bundle.source.hazards)
    phases = list(phases)
    identity = dict(source_id=bundle.source.source_id, source_hash=bundle.source.original_content_hash,
        parent_chunk_id=parent.chunk_id, start=start, end=end, passage=passage,
        hazards=[h.value for h in hazards], phases=[p.value for p in phases])
    context_records = list({c.chunk_id: c for c in [parent, *context]}.values())
    return ReviewCandidate(chunk_id=hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
        source_id=bundle.source.source_id, classification=bundle.source.classification,
        official_url=bundle.source.official_url, original_content_hash=bundle.source.original_content_hash,
        parent_chunk_id=parent.chunk_id, section_heading=parent.section_heading,
        passage_start=start, passage_end=end, original_passage=passage, proposed_chunk=passage,
        surrounding_context=context_records, jurisdiction=bundle.source.jurisdiction, hazards=hazards, phases=phases,
        safety_caveats=['PENDING human review; not operational guidance or household safety verification.', *caveats])


def prepare_candidates(store: SourceStore) -> CandidatePacket:
    """Curated exact passages. Missing anchors fail instead of inventing coverage."""
    from .review import PublicationError, verify_original
    result = []
    for source_id in ('cdc-flood-reentry', 'cdc-floodwater', 'miami-dade-eeap'):
        bundle = store.load(source_id)
        if bundle is None:
            raise PublicationError('required acquired source is missing')
        verify_original(store, bundle)
        def section(suffix):
            found = [c for c in bundle.chunks if c.section_heading.endswith(suffix)]
            if len(found) != 1:
                raise PublicationError('required authentic passage is missing or ambiguous')
            return found[0]
        def add(parent, phases, *, first=None, before=None, line=False, context=(), hazards=None, caveats=()):
            start = parent.guidance_text.index(first) if first is not None else 0
            end = parent.guidance_text.index(before, start) if before is not None else len(parent.guidance_text)
            if line:
                newline = parent.guidance_text.find('\n', start)
                end = newline if newline != -1 else len(parent.guidance_text)
            # Trim only boundary whitespace; every remaining character is source text.
            while end > start and parent.guidance_text[end-1].isspace(): end -= 1
            result.append(make_candidate(bundle, parent, start=start, end=end, phases=phases,
                                         context=context, hazards=hazards, caveats=caveats))
        if source_id == 'cdc-flood-reentry':
            entry = section('Take these steps when you first reenter your flooded home.')
            warning = section('Warning!')
            add(entry, [Phase.PREPARE], first='Before\n', before='\nAfter', hazards=[Hazard.HURRICANE],
                context=[warning], caveats=['The source labels this infographic Before; PREPARE is a proposed phase beyond the current source-level RECOVER tag. Human scope review is required.'])
            add(entry, [Phase.RECOVER], first='If your home has damage, do not reenter', line=True, context=[warning])
            add(warning, [Phase.RECOVER], context=[entry], caveats=['Preserve NEVER and while standing in water; this is not electrical-repair permission.'])
            add(entry, [Phase.RECOVER], first="Have an electrician check the house's electrical system", line=True,
                context=[warning], caveats=['Electricity availability does not establish general household safety.'])
            add(entry, [Phase.RECOVER], first='Tap water may not be safe to drink.', line=True, context=[warning])
            add(section('Key points'), [Phase.RECOVER], context=[entry, warning])
        elif source_id == 'cdc-floodwater':
            overview = section('Overview')
            risks = section('Floodwaters contain many things that may harm health.')
            add(section('Key points'), [Phase.RESPOND], context=[overview])
            add(section("Don't drive in flooded areas."), [Phase.RESPOND], context=[overview])
            add(section("Turn around, don't drown!"), [Phase.RESPOND], context=[overview])
            add(risks, [Phase.PREPARE], first='Recognize Flood Risk\n', before='\nAfter',
                caveats=['Hazard-awareness text only. Shelter names, capacity, evacuation orders and route availability are not established.',
                         'PREPARE is proposed from the infographic context; current source-level tags do not yet include PREPARE.'])
            add(section('Avoid electrical hazards inside or outside your home.'), [Phase.RESPOND, Phase.RECOVER],
                first='NEVER touch a fallen power line.', before='\nKeep Reading',
                caveats=['Preserve the negative instructions and conditional emergency-help sentence. No responder contact is made by this application.'])
            add(section('Protect yourself and your loved ones from diarrheal diseases.'), [Phase.RESPOND],
                first='Do not allow children to play in floodwater areas.', before='\nKeep Reading')
        else:
            description = section('longDescription')
            no_guarantee = section('Can I get assistance if I am not enrolled in the event of an emergency?')
            limits = ['Static program description is not live shelter, enrollment, transport or pickup availability.',
                      'No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.']
            add(no_guarantee, [Phase.RESPOND], hazards=[Hazard.HURRICANE], context=[description], caveats=limits)
            add(section('Am I eligible for the EEAP?'), [Phase.PREPARE, Phase.RESPOND], hazards=[Hazard.HURRICANE],
                context=[description, no_guarantee], caveats=limits + ['Criteria are quoted for human review, not an eligibility determination; retain the residential-facility exclusion.'])
            add(section('What does the EEAP offer and when is it used?'), [Phase.PREPARE, Phase.RESPOND],
                hazards=[Hazard.HURRICANE], context=[description, no_guarantee],
                caveats=limits + ['Retain the caregiver requirement and refuge-of-last-resort / health-care-level limitations.'])
            add(section('How do I register for the EEAP?'), [Phase.PREPARE], hazards=[Hazard.HURRICANE],
                first='If more than one eligible person', before='\nAfter you apply:', context=[description, no_guarantee],
                caveats=limits + ['Preserve separate-application, physician-signature and Do not wait conditions; this is not a current enrollment window or evacuation notice.'])
    packet = CandidatePacket(prepared_at=datetime.now(timezone.utc), candidates=result,
        coverage_gaps=['No substantive acquired instruction supporting safe damage documentation was selected; a Damage Reporting link label is not guidance.',
                       'No live resource availability, personal eligibility or county evacuation order is evidenced.',
                       'PROTECT phase tags are proposals grounded in Before / Recognize Flood Risk text, not approved source scope.'])
    with store.admin_lock():
        for candidate in packet.candidates:
            verify_candidate_trace(store, candidate)
            previous = store.load_candidate(candidate.source_id, candidate.chunk_id)
            if previous is not None and previous != candidate:
                raise PublicationError('preparation will not overwrite a prior human decision or changed candidate')
        for candidate in packet.candidates:
            if store.load_candidate(candidate.source_id, candidate.chunk_id) is None:
                store.save_candidate_locked(candidate)
        store._atomic_write(store.root / 'candidate_packet.json', packet.model_dump_json(indent=2).encode())
    return packet


def _fenced(text):
    import re
    longest = max((len(m.group()) for m in re.finditer(r'`+', text)), default=0)
    fence = '`' * max(3, longest + 1)
    return fence + 'text\n' + text + '\n' + fence


def render_packet(packet: CandidatePacket, output: Path):
    lines = ['# M3-2A human review packet', '', '**All candidates: PENDING. No approval or rejection command has been run.**',
        'Source quotations are acquired historical text, not current service availability or safety verification.',
        'Editorial safety caveats below are review annotations, not quotations or official orders.',
        f'Packet prepared at: {packet.prepared_at.isoformat()}', '',
        '## Extraction repair and provenance', '',
        'The preserved EEAP response contains program text in main/div#service-data/service: an escaped longDescription and six related-faq name/answer pairs. The old generic extractor failed on metadata before a usable heading. A source-scoped static parser decodes only those fields without executing scripts.',
        'Actual section counts: CDC flood reentry 13; CDC floodwater 17; Miami-Dade EEAP 7. The original HTTP timestamps, URLs, byte counts and SHA-256 values are unchanged. Re-extraction is recorded separately in extraction metadata/history; no new download occurred.',
        'Obfuscated contact markup remains source context only. No hidden email address is reconstructed and no contact availability is verified. All original acquisition history is retained.', '',
        '## Review procedure', '',
        'Read each exact passage and every linked context section against the preserved original hash. Check geography, hazard/phase scope and ALL conditional/negative language.',
        'The proposed chunk is verbatim; no generated paraphrase fills coverage gaps. Source authority and accuracy still require human judgment.',
        'Use the existing knowledge.review CLI commands shown below. Replace the reviewer/reason placeholders yourself. Do not approve by copying commands without inspection.',
        'Candidate approval records only that candidate decision. It does not mark the source REVIEWED, publish guidance, or enable retrieval. Existing export still requires source-level review.',
        'If hashes/context change, inspect again and prepare a new packet. Rejected candidates remain non-publishable. No live acquisition is needed for these commands.', '',
        '## Coverage gaps', '', *['- ' + gap for gap in packet.coverage_gaps], '']
    contexts = {}
    for i, candidate in enumerate(packet.candidates, 1):
        fingerprint = candidate_context_hash(candidate)
        commands = (f'python -m knowledge.review {{action}} --root data/official_sources --source-id {candidate.source_id} '
                    f'--chunk-id {candidate.chunk_id}')
        context_links = []
        for context in candidate.surrounding_context:
            contexts[context.chunk_id] = context
            context_links.append(f'[Context {context.chunk_id[:12]}](#context-{context.chunk_id})')
        lines += [f'## Candidate {i}: {candidate.chunk_id}', '', '**Review status: PENDING**',
            f'- Source: `{candidate.source_id}` — {candidate.official_url}',
            f'- Original SHA-256: `{candidate.original_content_hash}`',
            f'- Parent section: `{candidate.parent_chunk_id}`; character span [{candidate.passage_start}, {candidate.passage_end}).',
            f'- Intended hazards: {", ".join(h.value for h in candidate.hazards)}; phases: {", ".join(p.value for p in candidate.phases)}; geography: `{candidate.jurisdiction}`.',
            f'- Source section heading: {candidate.section_heading}', '',
            '**Original passage from acquired content:**', '', _fenced(candidate.original_passage), '',
            '**Surrounding context:** ' + ', '.join(context_links), '',
            '**Proposed short retrieval chunk (verbatim, pending review):**', '', _fenced(candidate.proposed_chunk), '',
            '**Safety caveats (editorial review annotations):**', '', *['- '+c for c in candidate.safety_caveats], '',
            '**Inspect / approve / reject this candidate:**', '', '```powershell', commands.format(action='inspect'),
            commands.format(action='approve') + f' --reviewer "<HUMAN_REVIEWER>" --expected-content-hash {candidate.original_content_hash} --expected-context-hash {fingerprint} --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved',
            commands.format(action='reject') + f' --reviewer "<HUMAN_REVIEWER>" --expected-content-hash {candidate.original_content_hash} --expected-context-hash {fingerprint} --reason "<HUMAN_REJECTION_REASON>"', '```', '']
    lines += ['## Acquired surrounding context', '', 'Text is decoded from the preserved HTML; HTML tags and layout whitespace are normalized. Guidance wording is not rewritten. Heading paths retain parent conditions.', '']
    for chunk_id, context in contexts.items():
        lines += [f'<a id="context-{chunk_id}"></a>', f'### Context {chunk_id[:12]}',
            f'Source `{context.source_id}`; extracted section `{chunk_id}`.', context.section_heading, '', _fenced(context.guidance_text), '']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Prepare exact candidate excerpts and a PENDING human review packet; never approve.')
    parser.add_argument('--root', type=Path, default=Path('data/official_sources'))
    parser.add_argument('--output', type=Path, default=Path('docs/M3_REVIEW_PACKET.md'))
    args = parser.parse_args()
    packet = prepare_candidates(SourceStore(args.root))
    render_packet(packet, args.output)
    counts = {source: sum(c.source_id == source for c in packet.candidates) for source in sorted({c.source_id for c in packet.candidates})}
    print(json.dumps({'candidate_counts': counts, 'review_status': 'PENDING', 'packet': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
