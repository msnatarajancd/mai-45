# M3 source review state and procedure

Government origin, downloading, extraction, and tests do not constitute human review. The authoritative source/candidate records determine publication, not an old packet or a successful web request. This educational prototype is not an operational emergency service.

## Current review state

| Source | Acquisition/extraction state | Publication state |
| --- | --- | --- |
| CDC flood reentry | Original bytes retained; 13 sections | REVIEWED; five APPROVED recovery candidates and one PENDING candidate |
| CDC floodwater | Original bytes retained; 17 sections | DOWNLOADED_UNREVIEWED; six PENDING candidates |
| Miami-Dade EEAP | Original bytes retained; repaired extraction has 7 sections | REVIEW_REQUIRED; five PENDING candidates |
| Miami-Dade Text 911 | Original bytes retained; 1 section | REVIEW_REQUIRED; one PENDING candidate |
| Miami-Dade Weather Ready contacts | Original bytes retained; 3 sections | REVIEW_REQUIRED; four PENDING candidates |
| FCC Text-to-911 | HTTP acquisition failed; no original capture or extracted sections | UNAVAILABLE; no publishable evidence |

CAP-04 added eight proposed directory listings. **All eight are PENDING:** seven reference acquired-source passages, while the FCC listing remains blocked by failed acquisition. No CAP-04 source, passage, or listing approval was created. Existing CDC review artifacts were preserved. The [CAP-04 review packet](CAP04_SOURCE_REVIEW.md) contains current listing evidence, inspection commands, and unresolved conditions.

The earlier [M3 candidate packet](M3_REVIEW_PACKET.md) records historical preparation, including candidates that have since been reviewed. It is not the authoritative current queue. CDC recovery coverage does not authorize emergency-response advice or publication of a directory listing.

## Preserved provenance

Original HTTP bytes live in `data/official_sources/originals/<sha256>.bin`; authoritative per-source bundles are under `records/`. The manifest is an index, and immutable history retains earlier attempts. The initial captures were:

| Source | Retrieved at (UTC) | Original bytes | SHA-256 |
| --- | --- | ---: | --- |
| CDC reentry | 2026-11-03T03:05:29.105758Z | 55,838 | `61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85` |
| CDC floodwater | 2026-11-03T03:05:29.514595Z | 56,120 | `19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8` |
| EEAP | 2026-11-03T03:05:30.655165Z | 129,366 | `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2` |

EEAP's original failed-extraction snapshot remains in history. Its repaired extractor reads the captured service record and escaped FAQ text without executing page scripts or reconstructing obscured contacts. The original URL, acquisition timestamp, byte count, and hash remain unchanged; extraction has its own timestamp/version.

The CAP-04 packet records the additional captures. Search/extraction service output is not substituted for missing original bytes. A failed request stays UNAVAILABLE; a successful download with unusable extraction stays REVIEW_REQUIRED. Neither creates publishable evidence.

## Review procedure

Inspect from the repository root:

```sh
python -m knowledge.review inspect --source-id cdc-floodwater --root data/official_sources
python -m knowledge.review inspect --source-id <source-id> --chunk-id <candidate-id> --root data/official_sources
python -m knowledge.resources inspect --resource-id <resource-id> --root data/official_sources
```

Use a safe text viewer for original bytes; do not execute acquired scripts. A real human reviewer must check provenance, exact passage and heading boundaries, geographic scope, phase/hazard applicability, warnings, and conditions. Candidate approval additionally requires that the passage and its caveats stand alone without publishing unapproved surrounding instructions.

Source, candidate, and directory approval are distinct. The source/candidate CLI requires the actual reviewer identity, expected hashes, and explicit attestations; directory approval requires the actual reviewer and expected listing fingerprint. Do not create identities, backdate timestamps, or approve records to make a demo pass. Preparation notes and synthetic test approvals do not satisfy these gates.

Source review binds original bytes and extracted context. Candidate review binds exact spans and context hashes. Directory review binds rendered fields, applicability, evidence IDs/hashes, limitations, and the review deadline. Actual review timestamps cannot be future-dated. Directory review deadlines must follow approval and remain within 30 days; this is a project policy, not a guarantee of current service information.

Publication rechecks these records and requested scope locally. Changed or revoked evidence, a changed listing fingerprint, or an expired listing deadline prevents verified display on the next lookup. Reacquisition resets eligibility even when bytes are unchanged. Runtime help requests never fetch and automatically approve updates.

To mark a source stale or revoke a listing:

```sh
python -m knowledge.review stale --source-id <source-id> --root data/official_sources
python -m knowledge.resources revoke --resource-id <resource-id> --reviewer "<actual reviewer>" --reason "<reason>" --root data/official_sources
```

Emergency controls and separately labeled official entry links remain available when review or retrieval fails. Static evidence never establishes live transport, shelter capacity, enrollment, eligibility, message delivery, dispatch, rescue, or household safety.

## Administrative trust boundary

The JSON store and CLI are trusted local administrative tools, not runtime user/model input routes. Reviewer identity is recorded, not authenticated or cryptographically signed. Protect write access before deployment.

Review, acquisition, and directory operations share an exclusive administrative lock and atomic writes. Never remove another process's active lock. A crash may require an administrator to verify no writer is running before removing a stale lock. A manifest-summary failure can require rebuilding the index but cannot create a valid source/candidate/listing approval.

Positive publication tests use temporary stores, reserved `.test` URLs where applicable, and explicitly synthetic review identities. Their success does not approve the production store. Consult [verification](VERIFICATION.md) for coordinated results.
