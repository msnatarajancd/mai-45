# ReadyRelief integration handoff

The single Streamlit app calls small Python adapters. Keep public signatures and typed results stable; no additional API server or orchestration layer is required. [CAP-04 implementation](CAP04_IMPLEMENTATION.md) describes emergency ownership and [verification](VERIFICATION.md) records the coordinated acceptance results.

## M2 — Guardian and alerts

`services.nws_alerts.get_alerts(location_id: str, mode: AppMode) -> AlertResult` is integrated. Supported area IDs are `miami`, `homestead`, and `miami-beach`; the adapter accurately labels county-wide coverage, not household geolocation. See [M2 review](M2_M1_REVIEW.md).

- Results distinguish `alerts`, `none`, and `unavailable`, with actual check time, source, and simulation status.
- Live checks are explicit, bounded requests. An empty successful response is not proof of safety; failures never substitute fixtures.
- Changing area or mode clears stale results. Alerts remain context: absence of an alert cannot override a new danger report.

## M3 — Knowledge and directory

`services.knowledge.retrieve_guidance(query, phase, context=None, *, hazard=None, jurisdiction=None, service=None)` publishes approved, applicable passages through the existing source and candidate gates. Five CDC recovery candidates are approved; coverage for other phases remains limited. `services.generation` consumes allowlisted public evidence and keeps partial/unavailable status visible. It does not invent missing operational guidance.

The CAP-04 directory is implemented in `knowledge/resources.py`, with the UI boundary `services.resources.lookup_resources(request, now=None, *, store=None)`. `ResourceQuery`, `VerifiedResource`, and `ResourceLookupResult` live in `domain/resources.py`. `find_resources(needs, county=None)` remains a compatibility projection.

- Lookup distinguishes `matches`, `no_match`, `review_required`, and `unavailable` under one consistent store snapshot.
- Publication requires reviewed source bytes, approved standalone candidates, exact field support, a separate listing approval, current review deadline, and matching county/phase/purpose/hazard scope. Unknown hazard requires an explicitly reviewed hazard-independent listing.
- Editing a field, matching tag, evidence reference, or deadline invalidates listing approval. Source/candidate changes, revocation, and expiry prevent publication on the next lookup. Runtime lookup does not fetch or approve sources.
- Availability remains `UNKNOWN`. No match is an assurance of eligibility, enrollment, pickup, placement, or capacity.
- **All eight prepared listings are PENDING.** Seven have acquired-source passages; the FCC listing is blocked by failed acquisition. Official entry links remain separate and do not imply a verified service match. See the [source review packet](CAP04_SOURCE_REVIEW.md).

The [M3 contract](M3_INTEGRATION_CONTRACT.md) and [review procedure](M3_SOURCE_REVIEW.md) describe evidence and administration boundaries.

## M4 — CAP-04 emergency access and routing

`emergency.service.evaluate_situation(SituationInput(...)) -> RouteResult` is the pure local evaluator; `screen_report(text, *, entrypoint)` provides shared screening. `services.emergency.assess_situation` accepts typed input and `route_situation(text_or_category)` preserves the prior adapter signature.

Decisions carry multiple incident types (`flood`, `trapped`, `medical`, `evacuation_support`, `utility_hazard`, or `unknown`), urgency (`immediate`, `urgent`, `ordinary`, `uncertain`), route, interruption/persistence flags, reason codes, and policy version. This is a navigation aid, not a diagnosis or proof of safety. Present danger wins over future context, selected category, old household information, and past safety reports; unresolved danger remains conservative.

`ui/emergency_page.py` renders the shared **Call 911** and **I Can't Call 911** actions before optional page work. Neither needs AI, classification, a profile, incident area, or a storage write. The telephone link is user initiated and does not report a connection. The optional current county controls local alternatives; saved/monitored area is not inferred as the incident location. Cannot-call information acknowledges device/network uncertainty and cannot send messages or restore connectivity.

`emergency.workflow.begin_emergency(state, decision, *, entrypoint, event_id)` is the idempotent transition. It advances an emergency epoch, invalidates routine proposals/results and tour state, and queues a danger save only for qualifying reports. Shared screening precedes routine generation and recovery writes. Existing M5 repository guards remain the final write boundary. Failed saves remain pending and cannot remove emergency access. Leaving the view does not clear saved danger.

Synthetic inputs are isolated from official evidence: 6 demos, 3 profiles, 9 failure descriptions, 48 development cases, and 24 independently authored golden cases. Expectations are **PROPOSED**, with no human safety approval. Live mode cannot load demo scenarios. The UI receives labeled input only; expected labels remain in evaluation files. Run `python -m emergency.evaluation.run --dataset golden --output artifacts/cap04-evaluation.json`; consult its [guard scope and limitations](../emergency/evaluation/README.md).

## M5 — Recovery continuity

The app reuses `start_recovery_case`, `create_demo_draft_plan`, `SQLiteRecoveryRepository` persistence and task methods, `preview_reassessment`, `approve_reassessment`, approved-plan history, and `report_immediate_danger`.

Household preferences can prefill intake needs but are session-only and do not rewrite saved cases. Plan approval and task updates require explicit user action. Saved revisions retain existing task IDs and completion state; stale writes are rejected. Constrained explanations never automatically create or complete tasks.

A danger-reported case stays paused. A reviewed same-case danger-clearance workflow, durable household/context persistence, and verified source-grounded task planning remain M4/M5/M3 follow-up work. Use a separate fictional case after the danger scene in a demonstration.

## Integration checks and limits

Run the Python suite, golden evaluation, compilation, JavaScript checks, and relevant browser cases before reporting completion. Exercise AI, directory, source-review, and storage failure paths with emergency controls present. Update product status from runtime behavior and actual review records. Tests use temporary stores and labeled synthetic review identities; they cannot confer production approval.

M1's optional generation uses the shared Nebius client, public evidence projections, citation support checks, entailment checking, and rerender revalidation. Model checking is not human safety certification. The app remains an online-only educational prototype with no dispatch, booking, live capacity, authentication, or private multi-user isolation.
