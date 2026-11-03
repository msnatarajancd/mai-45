# M3-1 integration contract

M3 is a shared local Python package for M2 Protect, M4 Respond and M5 Recover.
Runtime: Python 3.11+ and existing Pydantic 2; tests use existing pytest. There are
no new dependencies, hosted API, model calls, vectors, scheduler, or autonomous
crawler. M5 code, persistence, UI and deterministic reassessment are unchanged.

## Public interfaces (actual signatures)

```python
# knowledge.ingestion
acquire_source(
    source_id: str, store: SourceStore, *,
    transport: SourceTransport | None = None,
    timeout: float = 20, max_bytes: int = 2_000_000,
) -> SourceBundle

# knowledge.review
review_source(store: SourceStore, source_id: str, decision: ReviewDecision) -> SourceBundle
mark_stale(store: SourceStore, source_id: str) -> SourceBundle

# knowledge.service.KnowledgeService protocol / FoundationKnowledgeService
retrieve_guidance(request: KnowledgeRequest) -> GuidanceResult
find_resources(request: KnowledgeRequest) -> ResourceResult

# FoundationKnowledgeService: explicit selected-ID publication, NOT search
export_to_m5(source_id: str, chunk_id: str, request: KnowledgeRequest) -> dict[str, object]
validate_resource(resource: ResourceRecord) -> ResourceRecord
```

`SourceStore(root: str | Path)` supports `initialize()`, `load(source_id)`, and
`original(content_hash)`. Administrative writes are internal operations under
`admin_lock()`; they are not exposed to a household request or model. Inject
`SourceTransport.fetch(spec, *, timeout, max_bytes) -> Download` for offline tests.
Only curated IDs/URLs in `knowledge.sources.CURATED_SOURCES` can be acquired.
Requests use HTTPS, exact URL/redirect allowlists, bounded bytes and timeout,
permitted HTML content types, and no credentials or household context. Original
bytes are SHA-256 addressed; script/style and semantic navigation elements are excluded from plain
text extraction; other page chrome still requires review. There is no browser execution or PDF extraction fallback.

**Retrieval and resource search are NOT implemented in M3-1.** Both query methods
return UNAVAILABLE with empty results and explicit missing-information fields.
SUCCESS, NO_RELEVANT_EVIDENCE and INSUFFICIENT_EVIDENCE are defined for M3-2; their
existence does not claim working retrieval. `export_to_m5` verifies a specifically
selected reviewed chunk by exact ID; it is not relevance search/ranking.

## Shared strict schemas

All M3 records use Pydantic `strict=True`, `extra='forbid'`, and `frozen=True`.
Nonblank bounded text, safe IDs (1-80 alphanumeric/underscore/dot/hyphen characters,
starting alphanumeric), unique IDs/list entries, and credential-free HTTPS URLs
are required. UTC-normalized timestamps must be real timezone-aware datetimes,
not naive, future, numeric or arbitrary strings in Python input. JSON decoding
supports ISO timestamps/enums. Python callers supply enum/datetime objects.

- `SourceRecord`: `source_id`, `publisher`, `title`, `official_url`, `source_type`,
  `jurisdiction`, `hazards`, `disaster_phases`, `classification`, `limitations`;
  optional `content_type`, `charset`, `original_content_hash`, `retrieved_at`,
  `reviewed_at`, `reviewer`, `final_url`, `http_status`, `byte_count`,
  `last_attempt_at`, `failure_category`; `review_status` defaults LINK_ONLY.
  Acquired states require original hash, actual retrieval time, final URL, type,
  charset, nonzero byte count and HTTP 200. Reviewed state additionally requires
  an identified reviewer and real review time after retrieval.
- `EvidenceChunk`: `chunk_id`, `source_id`, `section_heading` (1-1000 chars),
  `guidance_text` (1-6000 chars), nonempty `applicable_hazards` and
  `applicable_phases`, `geographic_scope`, `review_status`. Whole sections are
  retained, with hierarchical heading paths; no truncation or invented text.
- `ResourceRecord`: `resource_id`, `source_id`, `official_name`, `service_category`,
  `service_area`, `official_url`, `prerequisites`, nonempty `limitations`, optional
  `official_contact` and `contact_evidence_chunk_id`. `availability_status` can
  only be UNKNOWN. The validator requires reviewed exact-text support for listing
  details/contact; this is not a live availability or eligibility check.
- Review states: LINK_ONLY, DOWNLOADED_UNREVIEWED, REVIEW_REQUIRED, REVIEWED,
  STALE, UNAVAILABLE. Classification is OFFICIAL_SOURCE or SIMULATED_DEMO.
  SIMULATED_DEMO can never become reviewed official evidence.
- `SourceBundle`: source, unique source-linked chunks, optional review record.
  Reviewed bundles require matching reviewed chunks and review provenance.
- `ReviewDecision`: reviewer, expected_content_hash, expected_context_hash, and
  literal boolean True for provenance_checked, content_checked,
  geographic_scope_checked, applicability_checked, caveats_preserved.
  `ReviewRecord` binds decision, reviewer, actual review time and both hashes.

`KnowledgeRequest` requires `hazard` (flood/hurricane/wildfire), `disaster_phase`
(prepare/respond/recover), and `jurisdiction`; optional `household_needs` (up to
30 strings), `safety_topic`, and `requested_evidence_count` (integer 1-10, default
3). Use canonical jurisdictions such as US, US-FL, US-FL-MIAMI-DADE. County scope
matches only that exact county; US national guidance may match US subdivisions.
There is no geocoding or inferred county. Other jurisdictions fail applicability.

`GuidanceResult` contains evidence_records, source_metadata, matching_context,
retrieval_status, limitations, missing_information. `ResourceResult` has resources
instead of evidence_records. Static guidance is separate from live operational
state. NWS alerts belong to M2. M4's Call 911 and I Can't Call 911 must never call
or depend on these interfaces. No service makes external requests for assistance.

## Exact existing M5 RecoveryEvidence contract

The existing class is `recovery.ai_planner.RecoveryEvidence`. It was read directly
and is neither duplicated nor modified by M3. It forbids extra fields:

| Field | Exact existing requirement |
| --- | --- |
| source_id | required string, 1-200 chars, nonblank |
| source_title | required string, 1-200 chars, nonblank |
| source_url | required string, 1-2000 chars; http or https, hostname present, no username/password |
| source_type | required string, 1-200 chars, nonblank |
| verified | required StrictBool |
| reviewed | StrictBool, default False |
| guidance_text | required string, 1-6000 chars, nonblank |
| geographic_scope | required string, 1-200 chars, nonblank |
| reviewed_at | optional datetime, default None; must be timezone-aware when present |
| retrieved_at | optional datetime, default None; must be timezone-aware when present |

M5's current model does not itself enforce timestamp freshness, geographic
applicability, provenance integrity, or real human review; M3's review/export gate
supplies those additional controls. M3 requires HTTPS even though M5 accepts HTTP.
M5 also rejects duplicate evidence source IDs, more than 20 input records, and
oversized combined context. M5's source_reference must match a supplied verified
ID, but M5 does not prove semantic citation support. Its current catalogue-only
planner does not become official guidance merely because evidence was provided.

The M3 adapter maps the parent source ID/title/URL/type, headed whole guidance
excerpt, geographic scope and timestamps to those existing fields. Only after
all publication and applicability checks does the adapter create verified=True
and reviewed=True. Requests accept no such authoritative flags. Headings are
included to preserve conditional language, and >6000-char headed excerpts are
rejected. Supply at most one selected chunk per parent source to M5 until an
agreed chunk-ID/aggregation contract is established; do not silently drop caveats
to concatenate or deduplicate chunks. M3 results retain the original chunk IDs
and source metadata for traceability outside the legacy M5 evidence shape.

Current real sources have no human review. Therefore **there is no verified
production evidence available to export yet**. M5's UI still supplies an empty
list; no M3 wiring is claimed. Empty/unverified input stays experimental and
ungrounded. M4 emergency controls remain independent of source acquisition.

## Offline tests and next milestone

From this checkout, run `python -m pytest` in the existing environment. Tests use
fake HTTP responses labeled SIMULATED_DEMO and captured original CDC bytes for
positive review-gate simulations; simulated signoffs are isolated in temporary
stores, never the real acquisition queue. No Nebius key or network is required.

For M3-2, first resolve Miami-Dade extraction, complete real human review, and
exclude non-guidance sections without losing parent caveats. Then implement a
small deterministic reviewed-only lexical search with explicit scope/hazard/phase
filters and explainable topic/needs matching. Enforce limits and distinguish zero
matches, too few reviewed matches, stale sources and unavailable storage. Add
request-to-evidence provenance and tests before considering embeddings. Agree a
chunk-level ID and context-preserving M5 adapter, freshness/re-review policy,
reviewer authorization, and M1 integration. Do not add live shelter/order claims,
NWS fetching, emergency routing, model-generated source substitutes or automatic
review. Stop M3-1 at the foundation and fail-closed interfaces described here.

## Verification recorded for M3-1

Complete repository suite: **217 passed** (57 M3 tests plus the existing 160).
The first full offline run passed 205 tests before live acquisition; captured
CDC content then enabled additional offline review-integrity/compatibility tests.
No network requests or Nebius calls run during pytest. `git diff -- recovery`
was empty. Work is on `feature/m3-rag`; no commit or push was performed.
Actual source results and the untouched human-review queue are recorded in
[M3_SOURCE_REVIEW.md](M3_SOURCE_REVIEW.md).
