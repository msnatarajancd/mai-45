# M3-3A.1 trusted knowledge integration contract

M3 is a local Python service using Python 3.11+, Pydantic 2 and the existing
pytest/Streamlit environment. No new dependency, API server, model client, vector
store, automatic review, or external submission is introduced.

## Actual interfaces

```python
# knowledge.service.FoundationKnowledgeService(SourceStore(root))
retrieve_guidance(request: KnowledgeRequest) -> knowledge.models.GuidanceResult
find_resources(request: KnowledgeRequest) -> ResourceResult
export_to_m5(source_id: str, chunk_id: str, request: KnowledgeRequest) -> dict[str, object]
validate_resource(resource: ResourceRecord) -> ResourceRecord

# services.knowledge -- existing positional M1 contract retained
retrieve_guidance(
    query: str,
    phase: str,
    context: Household | None = None,
    *,
    hazard=None,
    jurisdiction=None,
    service=None,
) -> domain.contracts.GuidanceResult
```

The M1 adapter defaults to `data/official_sources` relative to the repository,
not the process working directory. `service` is optional trusted application/test
injection implementing M3 retrieval, never a household/model-supplied object.
There is no default hazard or jurisdiction. Household preferences establish
neither. Missing context abstains before consulting the store. Supported hazard
values are `flood`, `hurricane`, `wildfire` (or the corresponding M3 enums).
Phase mapping is `protect -> prepare`, `respond -> respond`, `recover -> recover`;
`prepare` is also accepted. `guardian` has no implicit mapping.

## Retrieval and status semantics

`KnowledgeRequest` requires hazard, disaster_phase and canonical jurisdiction,
with optional safety_topic, household_needs, and requested_evidence_count (1-10,
default 3). M1 supplies query as safety_topic and does not infer recovery needs
from household flags. Geography uses exact scope or a hyphen-delimited child
(e.g. US includes US-FL; US-FL includes US-FL-MIAMI-DADE). County evidence cannot
answer a national or other-county request. No geocoding occurs.

Retrieval is implemented. It filters source and candidate scope, hazard and
phase, then ranks exact passages by twice the distinct passage-token overlap
plus heading-token overlap. At least half the non-stopword query terms must
match the passage. Ties use source ID then candidate ID. No stemming, embeddings,
semantic generation or model call is used.

- SUCCESS: the requested number of matching excerpts was returned. This does not
  establish a complete answer, personal applicability, or household safety.
- INSUFFICIENT_EVIDENCE: fewer matches than requested, missing topic/context, or
  an unsupported live/personal operational question. Partial reviewed excerpts
  can accompany a count shortfall, with insufficient_evidence remaining true.
- NO_RELEVANT_EVIDENCE: a trustworthy corpus exists but no passage matches scope
  and topic.
- UNAVAILABLE: missing/busy/unreadable/invalid store or no evidence satisfies the
  publication gates. No substitute guidance is generated.

M3's GuidanceResult retains evidence_records, source_metadata, evidence_metadata,
matching_context, retrieval_status, limitations and missing_information. Citation
IDs are candidate SHA-256 IDs, not parent-section IDs or URLs.

## Publication gates and provenance

Both the parent source and the specific candidate must pass publication checks.
A source must have REVIEWED status, matching reviewed sections, a bound human
review record, curated official provenance, intact original bytes, and sections
that re-extract identically. Candidates must be APPROVED, with an exact source
span, stable content-derived ID, matching content/context hashes, explicit review
proof, and unchanged source/context. Review must not predate current acquisition.
Candidate approval additionally requires explicit `standalone_passage_checked=True`
(`--standalone-passage-checked` in the CLI). The human must attest that the exact
passage and its safety caveats preserve essential conditions and warnings without
publishing raw surrounding context. If not, leave it pending for revision. The
flag defaults to false; old approvals without this attestation cannot publish.
Source-level approval does not supply this candidate-level attestation.

`knowledge.candidates.verify_candidate_publication(store, candidate, request=None)`
is shared by retrieval and export. Callers hold the existing admin lock. Export
also checks source and candidate hazard, phase and jurisdiction under that lock.
Supported review/acquisition writers use the same lock. Store errors fail closed;
export raises sanitized PublicationError and M1 returns an unavailable response.
No runtime request or LLM output can approve a record.

Source validity uses explicit stored review/stale states and integrity checks.
There is no automatic review-expiry interval. The JSON/CLI store is admin-owned;
reviewer identity is recorded, not authenticated or cryptographically signed.

## M1 display contract

The existing answer/sources/insufficient_evidence fields remain. GuidanceResult
adds retrieval_status, citations, limitations and missing_information. The answer
is an application-owned status message; it is never generated disaster advice.

Each domain.contracts.GuidanceCitation preserves:

- citation_id (candidate ID), source_id (parent source ID), parent_chunk_id;
- source title, publisher, official URL and original SHA-256;
- exact passage, section heading and start/end span;
- applicable jurisdiction, hazards and phases;
- full source and candidate review records serialized as JSON-compatible values;
- candidate-reviewed safety caveats and source-reviewed limitations.

Full surrounding source sections are administrative review material, not public
guidance. They remain unchanged in ReviewCandidate, history, the human packet and
`knowledge.review inspect --chunk-id ...`. Review fingerprints still bind them.
Public EvidenceProvenance and GuidanceCitation retain `surrounding_context=[]`
for field compatibility but reject any nonempty value. Full context must never
be put into a user response or model prompt, including as "provenance". Runtime
serialization is passage-only; IDs, source hashes and both review records retain
traceability without serializing parent instructions. Adapters revalidate this
boundary and fail unavailable on legacy/nonconforming context-bearing outputs.

Source link records additionally retain citation_id, parent source_id and
original_content_hash. IDs are not reduced to URLs. M3 provenance is mapped by
trusted application code, not accepted from a household or model. The domain DTO
uses plain JSON proof records so importing emergency UI contracts does not
require importing M3 or opening its store.

Protect's existing knowledge panel now offers an explicit hazard and a bounded
static preparedness topic. Known supported named areas map explicitly to
US-FL-MIAMI-DADE; unknown locations provide no jurisdiction. No hazard is inferred
from alert wording. Official/simulated alert details remain separate and retain
their labels. Excerpts, citation IDs, URLs, reviewed caveats, hashes and
review provenance are displayed without an LLM. Requested displays are
revalidated on rerender, and context/topic changes clear old results.

## M5 export compatibility -- candidate IDs required

`export_to_m5(source_id, chunk_id, request)` takes the parent source ID followed
by an APPROVED CANDIDATE ID. Parent-section IDs are rejected even when their
parent source is reviewed. The old parent-only export behavior is removed.

The returned dict exactly matches existing recovery.ai_planner.RecoveryEvidence:
source_id, source_title, source_url, source_type, verified, reviewed,
guidance_text, geographic_scope, retrieved_at, reviewed_at. No extra fields are
passed to M5's extra-forbid schema. Only trusted publication code sets the two
boolean flags.

Compatibility convention: the returned legacy `source_id` is the candidate
citation ID. This permits distinct candidates from the same parent without
violating M5's unique-ID requirement. Parent source identity is explicitly
retained in guidance_text and M3's full provenance. M5 source_reference can use
this supplied citation ID without a planner change.

Guidance text includes only the exact headed candidate passage, candidate-reviewed
safety caveats and source-reviewed limitations. Parent instructions are never
appended. If an essential warning exists only in parent context, a reviewer must
withhold standalone approval and request a revised candidate; the exporter must
not fill the gap with unapproved context. No new instructions are automatically
extracted or paraphrased into caveats. Caveats are review-bound restrictions and
limitations, not an automatic channel for unrelated parent instructions.
It is never truncated. If the complete text exceeds M5's 6000-character limit,
export fails closed. reviewed_at is the earlier source/candidate review timestamp;
retrieved_at remains the source acquisition timestamp.

M5 planner, Recovery UIs, database and deterministic reassessment are unchanged.
They are not wired to M3 in this milestone and still pass empty evidence to AI
planning. M5 still limits evidence to 20 unique IDs and 60KB combined context;
citation membership alone does not prove semantic support for a task. Durable
plan-to-citation snapshot resolution remains a future integration decision.

## Emergency and live-information boundaries

Call 911 and I Can't Call 911 are rendered before retrieval, chat and page work.
They do not depend on evidence, LLMs, location, login or network requests. M3
imports are lazy at the M1 adapter boundary. Retrieval failure does not hide
emergency controls. The app does not send texts, dispatch responders, or verify
safety. Streamlit itself still requires its server/browser environment.

Static evidence cannot establish live alerts, evacuation orders, all-clear
conditions, shelter capacity, transportation availability, eligibility or building
safety. A conservative operational-query guard abstains; it is not a complete
semantic classifier or an emergency triage mechanism. No current alert state is
inferred from static documents.

find_resources remains UNAVAILABLE. validate_resource now accepts listing detail
and contact support only from individually approved standalone candidate passages,
never whole parent text; contact_evidence_chunk_id means a candidate citation ID.
This closes the otherwise dormant parent-context validation path. It does not
create a resource finder or establish live availability.
Existing official directory links are not
verified available services. No resource availability or enrollment is invented.

## Real review queue and remaining cross-team work

All 16 real candidates remain PENDING. No real source/candidate approval or
publication was performed. The actual unreviewed store returns zero verified
excerpts/citations. Existing source captures, hashes and acquisition history are
unchanged.

M1's action-proposal assistant already uses the shared Nebius client for product
help. It is unchanged and is not an unrestricted disaster chatbot. M3 display
needs no model. Do not add another Qwen client.

M2 is not integrated in this checkout. Its remote explanation boundary expects a
snippets dictionary, unique evidence IDs and ISO timestamps; guardian phase
mapping needs agreement. Its domain allowlist excludes cdc.gov and it imposes a
30-day review policy absent from M3. Those require coordinated M2 work, not an
adapter that silently weakens its gates. Alert snapshot fields are also richer
than current M1 Alert records. M4 reviewed routing remains a separate owner task.

## Verification

Run from this checkout with the existing environment:

```powershell
python -m pytest -q
```

Positive integration tests use clearly labeled synthetic documents, reserved
.test URLs, test-scoped allowlists and temporary stores. Test review decisions
are not real human signoffs and never touch the real review queue. Tests cover
both publication gates, parent-ID rejection, scope, tampering, reacquisition,
published size and negative instructions, stable citations, phase mapping, missing
context, no model call, production-store abstention, revocation on rerender, and
emergency controls during M3 failure. Additional context-publication regressions
embed the real Candidate 1/2 quotations in a labeled .test synthetic document and
verify held context never reaches retrieval JSON, M1 display, M5 export or actual
fake-client planner prompts. Human inspection retains it. Pytest requires no
Nebius or live API calls.
