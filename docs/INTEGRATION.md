# M1 integration handoff

M1 calls services through small adapters. Teammates should keep signatures/return models stable and replace the adapter bodies. UI imports service modules so tests can substitute providers without changing pages. No frontend rebuild, network service, or orchestration layer is required.

## M2 — Guardian and alerts

**Connected 2026-11-03:** see [M2 review](M2_M1_REVIEW.md). The bullets below describe the original contract; the current adapter uses explicitly labeled county coverage, not invented municipality coordinates.

**Implemented M1/M2 contract:** `services/nws_alerts.get_alerts(location_id: str, mode: AppMode) -> AlertResult`.

- Supported IDs: `miami`, `homestead`, `miami-beach`. Supply reviewed representative coordinates; selection is an area, not household geolocation.
- Return `status=alerts|none|unavailable`, normalized alerts, `checked_at` with timezone, source URL, and accurate `simulated` flag.
- Use bounded timeouts and an identifying NWS User-Agent. No automatic calls from page load.
- `none` means a successful empty response, never request failure. Never return fixture alerts in LIVE CHECK.
- Only use checked_at after a real attempt, and expose expiry/issue metadata as appropriate. M1 clears results when area/mode changes.
- Add active/empty/timeout/invalid payload tests and one captured successful probe before claiming connected. Update Evidence's status when the integration actually works.

## M3 — Knowledge and directory

**Connected from merged PR #3:** `retrieve_guidance(query: str, phase: str, context: Household | None) -> GuidanceResult` in `services/knowledge.py`.

- Return answer, actual retrieved source records (title, URL, publisher, reviewed date), insufficient_evidence flag.
- Download and review the master plan's 8–12 official items. Preserve source bytes and manifest; links alone are not a corpus.
- Abstain on unsupported claims. Use only validated official HTTPS URLs; render plain text, not provider HTML.
- The current adapter publishes approved CDC recovery passages and preserves retrieval status. M1 services/generation.py consumes its public fields only; no synthetic evidence is passed off as real. Task planning remains a deterministic template with explicit approval.

**TODO(M3/M4)** `find_resources(needs: str, county: str='Miami-Dade') -> list[Resource]` in `services/resources.py`.

- Provide 5–8 reviewed county records with geography, prerequisites, source, last-checked date, contact and explicit availability caveats. Extend the model deliberately for those fields.
- Empty list currently means no verified match. The UI separately links official entry points; it never claims a pickup, opening, capacity or eligibility.
- Transport examples must show registration/eligibility caveats. Directory records should never be inferred from model memory.

## M4 — Emergency routing and review

**TODO(M4)** `route_situation(text_or_category: str) -> RouteResult` in `services/emergency.py`.

- Call 911 / cannot-call controls are independent of this adapter, AI, location, profile and persistence.
- Current placeholder permits only exact resource categories; everything else is possible danger. The UI accepts categories, not arbitrary diagnostic chat.
- Add reviewed hazard rules and 20–24 master-plan golden cases; preserve conservative fallback on uncertainty.
- Review the alternative-contact wording against local county information. Do not promise delivery or service availability.
- A danger event pauses routine UI and persists to the active M5 case when possible. Failure to save a danger report does not hide emergency access.
- Existing M5 policy makes danger-reported cases read-only in this UI. **TODO(M4/M5):** define a reviewed explicit process to clear a persisted danger flag; M1 does not silently clear it.

## M5 — Integrated from PR #1

M1 consumes, without modifying `recovery/`:

- `start_recovery_case`, `create_demo_draft_plan`.
- `SQLiteRecoveryRepository.get_case/save_draft_plan/approve_plan/get_active_plan/update_task_status`.
- `preview_reassessment`, `approve_reassessment(..., explicitly_approved=True)`.
- `list_approved_plans`, `report_immediate_danger`.
- M1 reuses `NebiusClient` for constrained explanations; the integrated UI no longer exposes ungrounded experimental task generation. The standalone M5 implementation remains unchanged.

Shared household preferences prefill transportation needs during intake. The existing case model has no location/profile fields; M1 does not mutate it. **TODO(M5):** agree on versioned household/context persistence if required beyond the session, connect verified M3 evidence to planning, and define safe re-entry for danger-reported cases. Initial plan and task persistence already work locally. Do not replace them with stubs.

M1 retains the version the user last saw for task updates; the repository must reject stale writes. Reassessment previews compare snapshots before approval. Existing task IDs and completion states must survive approved revisions. Never automatically accept a draft.

## M1 UI status and integration checks

1. Implement adapter and its contract tests.
2. Run the whole suite (`python -m pytest -q`), including M5 tests.
3. Exercise the service failure path with emergency controls still visible.
4. Update Evidence and README to reflect actual connectivity; never just remove a TODO label.
5. Rehearse the single household story. Ensure LIVE CHECK contains no fictional warnings and no-alert still has the safety caveat.

Only fictional local demonstration data should be used until hosting isolation, authentication and retention are designed by the team.

## M1 generation completion

See [current handoff](M1_COMPLETION_HANDOFF.md) for acceptance evidence, remaining owner work and deployment limits. Public DTO projection excludes review metadata and surrounding context; exact support and citation membership are checked, followed by model entailment checking. Model checking reduces risk but is not a human safety certification. Every rerender revalidates the evidence fingerprint; revocation removes prior output.
