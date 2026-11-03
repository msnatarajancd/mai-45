# M1 completion handoff — 2026-11-03

## Implemented

M1 owns the Nebius/Qwen generation layer in `services/generation.py`. It calls the existing M3 `services.knowledge.retrieve_guidance()` adapter first, with explicit query, phase, hazard and jurisdiction. Only approved public passages, citation IDs, headings, public caveats and limitations enter Qwen prompts. Parent context, source/candidate review records, private notes, household state, conversation history and persisted tasks are excluded.

Every generated statement requires an existing citation and an exact supporting quote. A second constrained Qwen call checks semantic support, conditions and limitations; rejected/invalid/provider-failed output is not displayed. Model checking is fallible and does not constitute human safety review. Official URLs come from M3, never the model. Evidence fingerprints are revalidated after generation and on rerender; changed/revoked evidence removes the old answer without an automatic model retry.

SUCCESS preserves success. INSUFFICIENT_EVIDENCE with approved passages permits only a prominently labeled partial explanation, retaining all limitations. Without passages, or when UNAVAILABLE/NO_RELEVANT_EVIDENCE, the model is not called. There is no silent mock or simulated model response.

Protect, Respond, Recover and the expanded Assistant have an explicit **Ask Qwen about reviewed guidance** panel. Protect's original deterministic excerpt view remains available without AI. The current real CDC approvals cover recovery; no recovery passage is silently reused for preparedness or response.

M2 Guardian is connected by direct import, with county-wide scope, source, issued/effective/expiry timestamps, original instructions and request-start time. Simulation stays clearly separate; failed and empty requests never establish safety. NWS weather alerts are not county evacuation orders.

Emergency controls render before service work and remain independent of Qwen and retrieval. Danger messages interrupt generation before retrieval. Persisted/pending danger reports pause routine guidance even after returning to another screen. M4's reviewed routing rules and full safety evaluation are still pending.

M5's original domain/database code is unchanged. Deterministic draft review, approval, persisted task updates, resume, reassessment and concurrency guards continue to work. Grounded explanations do not write tasks. The integrated UI no longer exposes the earlier ungrounded experimental task generator. Further source-supported task generation needs M5/M3 agreement on durable citation snapshots and task-level semantic support.

## Acceptance evidence

- Real NWS probe returned two official county alerts at 2026-11-03 20:38 UTC (historical observation, not a current-condition claim). Failure and no-alert behavior are tested with injected fixtures.
- Real Nebius/Qwen generation and verification succeeded at 2026-11-03 20:44 UTC using `Qwen/Qwen3-235B-A22B-Instruct-2507`. The question **electrical hazards**, flood/recover/Miami-Dade, retrieved approved CDC citation `ffa4fe9ae4c8f85d1030c5907c403b265370c503fefd6ab9f87e097ccf620465` with INSUFFICIENT_EVIDENCE. The app displayed a partial cited explanation, preserving the limit.
- [Live public prompt/response record](evidence/m1-qwen-live-2026-11-03.json) includes the reviewed passage, generated claim, official URL, content hash and both model calls. It contains no credentials or administrative review context. The unsupported FEMA-eligibility query made no model call.
- Reproduce explicitly: `python scripts/verify_grounded_generation.py --live`. Live calls require `NEBIUS_API_KEY` in the server environment; no .env auto-loading or key copying occurs.
- **482 tests passed, 11 skipped, 10 subtests passed**. Skips are the optional M2 HTTP API tests because FastAPI/httpx are absent; the app uses the tested direct-import service. On this Windows host, run `python -m pytest -q --basetemp="D:/Documents/Code Repos/.t-m1"` to avoid long-path errors in M3 fixtures. Pytest owns/clears that dedicated temporary path. `pytest.ini` resolves duplicate test filenames and preserves M3 fixture imports.
- Browser acceptance passed real Qwen partial-answer display, official NWS retrieval, and danger interruption with Call 911 and alternative text information. Unit/UI tests additionally cover no automatic model calls, private-note exclusion, malformed/invented citations, semantic-check rejection, unavailable evidence/provider, review revocation, persisted danger and existing M5 approved task persistence.

## Shared branches and remaining ownership

Integration branch: `feature/m1-grounded-integration`. M3 PR #3 is already merged into shared main (`88adb40`). M2's `feature/m2-guardian` was integrated via a real Git merge, not copied files. GitHub API status on 2026-11-03: PR #2 open, **draft=false**, unmerged, clean mergeability; its earlier draft status is outdated. See [M2 review](M2_M1_REVIEW.md).

Remaining team work:

- M3: approve additional source coverage for Protect/Respond and build the reviewed resource directory. M1 must not invent missing material.
- M4: deliver reviewed emergency/routing rules and golden safety cases; review alternative-contact wording and agree with M5 on a safe process for clearing persisted danger reports.
- M5/M3: agree any future grounded task suggestions, durable plan-to-citation snapshots and household context persistence. Existing user-approved task persistence is complete.
- Deployment: use server-side secrets, reliable outbound NWS/Nebius access, persistent SQLite storage for a single-user demo; design authentication, isolation and retention before any real multi-user deployment. Case IDs are not authentication. Optional M2 HTTP hosting is separate and not required by this application.

No external applications, emergency dispatches, real benefit claims, or service reservations are performed.
