# M3 source review queue and procedure

This is a safety-sensitive educational prototype, not an operational emergency
service. Government origin, downloading, extraction, and unit tests are not human
review. **No actual source has been marked REVIEWED. No real reviewer signoff was
created.** All approvals in tests exist only in temporary test directories.

## Actual acquisition

The following are results of running the acquisition utility, not browser-search
results or assumed successes. Timestamps below are recorded UTC instants. Each
final URL was identical to its requested official URL; no redirect was followed.

| Source | HTTP | Retrieved at (UTC) | Content type | Bytes | Sections | Current status |
| --- | --- | --- | --- | ---: | ---: | --- |
| CDC flood reentry | 200 | 2026-11-03T03:05:29.105758Z | text/html | 55,838 | 13 | DOWNLOADED_UNREVIEWED |
| CDC floodwater | 200 | 2026-11-03T03:05:29.514595Z | text/html | 56,120 | 17 | DOWNLOADED_UNREVIEWED |
| Miami-Dade EEAP | 200 | 2026-11-03T03:05:30.655165Z | text/html | 129,366 | 0 | REVIEW_REQUIRED / EXTRACTION_FAILED |

Requested and final URLs:

- `cdc-flood-reentry`:
  https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html
- `cdc-floodwater`:
  https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- `miami-dade-eeap`:
  https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672

SHA-256 of downloaded original bytes:

```text
cdc-flood-reentry
61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85
cdc-floodwater
19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8
miami-dade-eeap
4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2
```

Originals are `data/official_sources/originals/<sha256>.bin`. They are preserved
bytes, not rendered HTML. Per-source records contain metadata and extracted text;
immutable history snapshots retain previous attempts. `source_manifest.json` is
the index/summary. Per-source bundles are authoritative for export checks.

Miami-Dade's original HTML was acquired, but the bounded static extractor found
readable content before a usable heading. The response has no h1 and includes
dynamic content. No content was invented or taken from a model/browser cache to
replace it. It needs an explicit, tested extraction improvement and human review
before it can yield evidence. Re-running an unchanged parser is not a review.

## Queue

1. **CDC reentry:** check all extracted sections against the original, especially
   warnings and conditional electrical/gas, water, and building-reentry guidance.
   Check parent context and infographic text. No household safety conclusion may
   be inferred from utility restoration. Remove/reject navigation or resource-link
   sections as publishable guidance through a future reviewed extraction change.
2. **CDC floodwater:** check conditional headings, medical/water caveats and
   hazard applicability. Ensure every separately exported excerpt is sufficiently
   self-contained. National guidance does not establish a county evacuation order.
3. **Miami-Dade EEAP:** resolve extraction failure first, then check county scope,
   registration prerequisites and caveats against acquired content. This is not
   proof of active transport, shelter space, enrollment or individual eligibility.

Initial hazard/phase/geographic tags are provisional curated metadata. A reviewer
must check them; the downloader's tags are not a review. Any missing context or
unsafe section boundary means reject/defer, not sign off with a caveat omitted.
M3-1 has no manual snippet editor or partial-source publication workflow.

## Manually invoked commands

Run from the repository root using a Python environment with Pydantic 2:

```powershell
python -m knowledge.ingestion --all --root data/official_sources
python -m knowledge.review inspect --source-id cdc-floodwater --root data/official_sources
```

The inspector prints complete plain-text sections, provenance, and a context
hash. Inspect the corresponding original bytes using a safe text viewer; never
execute acquired scripts or render untrusted HTML. A real human must verify:

- Original official provenance, HTTP metadata and SHA-256.
- Actual acquired excerpts, complete headings, warnings and conditional language.
- Geographic scope and phase/hazard applicability.
- Every excerpt's suitability as a standalone citation, including parent context.
- All five explicit review checks, with their own nonblank reviewer identity.

Only after that human check, an administrator can run the following template.
Replace the placeholders with the reviewer's identity and the hashes printed by
inspection. **This command was not run against the real source store.**

```powershell
python -m knowledge.review approve --source-id cdc-floodwater --root data/official_sources --reviewer "<human reviewer identity>" --expected-content-hash "<acquired SHA-256>" --expected-context-hash "<inspection context hash>" --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
```

The review operation records its actual timestamp; it accepts no supplied review
time. It verifies original bytes and exact extracted sections, checks both
inspection hashes, and records all attestations. Export rechecks the review,
original hash, context fingerprint, and requested geographic/hazard/phase scope.
Conditional heading paths are included in M5 guidance. Oversized headed excerpts
are rejected, never truncated. Wrong-context or unreviewed content fails closed.

Any reacquisition resets publication eligibility, even if bytes are unchanged.
Changed bytes receive a new hash/chunk IDs and REVIEW_REQUIRED. Old originals and
snapshots remain available. A timeout, network/TLS failure, HTTP failure, rejected
redirect/type, or size failure is recorded UNAVAILABLE with its category; a
successful HTTP download with failed extraction is REVIEW_REQUIRED. No failed
attempt is represented as a successful extraction.

To revoke eligibility explicitly:

```powershell
python -m knowledge.review stale --source-id cdc-floodwater --root data/official_sources
```

## Administrative trust boundary

The JSON store and CLI are trusted local admin tools, not runtime user/LLM input
routes. Human identity is recorded, not authenticated. Anyone allowed to rewrite
the store and code can forge local records; M3-1 does not provide cryptographic
signatures or multi-user authorization. Protect write access before deployment.
The exclusive admin lock prevents concurrent review/acquisition replacement; if a
process crashes, verify that no admin process is running before an administrator
removes a stale lock. It is never removed automatically by another process.
Atomic per-file writes preserve authoritative bundles; a disk failure during the
separate manifest-summary update may require rebuilding that summary. Such a
failure cannot create a valid review record or verified export.
