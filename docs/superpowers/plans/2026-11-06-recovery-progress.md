# Recovery Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an isolated, explainable Recovery Progress dashboard with four specialist checks, a next-action coordinator, and connected home/funding milestones while preserving existing Recovery behavior.

**Architecture:** A separate Streamlit route consumes immutable typed specialist results from `recovery/progress/`. LangGraph coordinates actual calls through a local stdio MCP server backed by synthetic data and shared deterministic specialist functions. The preview has its own local result store; then a consistent read-only projection connects existing cases through additive profile/storage changes. No LLM or external provider service is required.

**Tech Stack:** Existing Python 3.12, Streamlit 1.66.1, Pydantic 2.14.2, SQLite, pytest 9.2.0, Node 22 and Playwright 1.62.1; approved additions LangGraph 1.2.20 and official MCP Python SDK 2.3.0. Existing pins remain unchanged.

**Spec:** [Recovery Progress design](../specs/2026-11-06-recovery-progress-design.md).

## Delivered implementation — November 6, 2026

Increments A and B are implemented in the working tree on `Recovery-Progress`. Increment C remains separately scoped. The task checklists below preserve the original design and proposed API/test names; the implementation map is:

| Tasks | Delivered code and checks |
|---|---|
| 1–4 | Typed domain, six stories/18 checkpoints, four specialists, ranking and two milestone tracks in `recovery/progress/`; corresponding `tests/test_progress_*` domain tests |
| 5, 8 | Actual LangGraph workflow in `orchestrator.py`, official MCP client/server, snapshot/attempt storage; `tests/test_progress_runtime.py` exercises the real stdio boundary and publication guards |
| 6 | Shared grouped navigation, focused search/chat destinations, preview feature flag and unchanged legacy aliases |
| 7 | Manual refresh, lifecycle, four cards/details, simulated interactions, historical failures and responsive views; UI and browser tests |
| 9 | Existing Python/Node regressions and responsive Progress/emergency browser checks; existing Windows screenshot baselines preserved |
| 10–11 | Reviewed optional profile, additive repository methods, atomic saved-case projection and cheap revision polling; profile/case integration tests |

Final runtime entry points are `start_run`, `poll_run`, `cancel_run`, `publish_run` and `run_once`; the planned coordinator class was replaced by LangGraph and the local MCP client. Saved inputs use `load_saved_input` and `current_progress_revision`. Fixtures are `scenarios.json`, `housing.json`, `checklists.json` and `providers.json`; utility observations live in each scenario checkpoint. No implementation checkpoint commits, push or merge were made. See [usage and MCP setup](../../RECOVERY_PROGRESS.md) for the executable interface.

## Global Constraints

- Keep Recover's current destination during preview.
- Show saved results on entry. Run checks only after **Refresh checks**.
- Execution states are separate from household/service states.
- Illustrative timing ranges are allowed only for synthetic households. Other cases display **Not enough information** until a defensible estimate exists.
- Expected reimbursement and approved-but-unpaid amounts are not cash available.
- No exact gap is calculated from a band.
- No features are deprecated in this project.
- Preserve emergency access before all optional page I/O; changes in emergency epoch invalidate in-flight routine results.
- Use `rp_` session keys and a new screen container, not `rr_progress` keys that existing cleanup deletes.
- Demo refreshes make zero service network requests and do not modify existing cases, records, tasks, plans or insurance workspaces.
- New addresses/financial values remain fictional in this local prototype; never put runtime databases or personal data in Git.
- User has now authorized implementation, including LangGraph and MCP. Preserve reviewable changes on Recovery-Progress; never push or merge to main automatically.

## Review Focus

- Case/checkpoint/mode changes during checks: reject late results and preserve the correct household's history (Tasks 5, 8, 11).
- A range, unknown or already-spent amount: never turn it into an exact available balance or double-count funds (Tasks 1, 3, 10).
- Insufficient hotel occupancy, unactivated school/church, or stale capacity: never promise a household fit (Tasks 2, 7).
- Navigation ambiguity and staged drafts: preserve `open recovery`, the selected case, review proposals and existing save behavior (Tasks 6, 9, 11).
- Saved evidence changes or a danger report while the screen is open: remove stale readiness/actions without discarding historical work (Tasks 5, 8, 11).

## Delivery boundaries

**Increment A — synthetic preview (Tasks 1–9):** a working integrated screen with all four cards and details, simulated provider interaction, six stories/18 checkpoints, refresh lifecycle, elapsed time, two milestone tracks, next action and local preview persistence. Feature can be disabled without disabling existing Recover. Review the first three featured stories before broadening the fixture walkthrough.

**Increment B — saved-case integration (Tasks 10–11):** add optional confirmed matching/funding facts to the Recovery home/workspace, load case data atomically, link to the existing Insurance/Plan editors and preserve read-only analysis. It does not enable real service availability or real household use.

**Increment C — provider integrations:** bounded feasibility work described after Task 11. Implement only after supported sources and data access are known. No promise of a live address-outage API in this plan.

Execution order for an early visible checkpoint: Task 1 → Task 6 (navigable preview shell and scenario selector, with truthful Not checked placeholders) → Tasks 2–5 → Tasks 7–9. Task numbers group responsibilities, not a requirement to delay the first visible screen until every specialist is complete. Tasks 2 and 3 can be implemented independently after the shared contracts; a reviewer checks the combined interfaces before coordinator integration.

## File structure and ownership

New runtime files, created only during execution:

| File | Responsibility |
|---|---|
| `recovery/progress/__init__.py` | Package exports only |
| `recovery/progress/models.py` | Shared immutable input, findings, provenance, action and snapshot contracts |
| `recovery/progress/fixtures.py` | Validated fixture loading and checkpoint selection |
| `recovery/progress/data/households.json` | Six fictional stories and 18 checkpoints |
| `recovery/progress/data/housing.json` | Twelve fictional accommodation locations |
| `recovery/progress/data/utilities.json` | Utility observations and error/conflict overrides |
| `recovery/progress/data/checklists.json` | Four fictional checklist definitions |
| `recovery/progress/data/providers.json` | Fifteen fictional repair providers and interaction fixtures |
| `recovery/progress/housing.py` | Capacity/constraint matching and explanations |
| `recovery/progress/utilities.py` | Per-service scope/freshness/applicability evaluation |
| `recovery/progress/insurance.py` | Checklist/evidence mapping and funding state |
| `recovery/progress/rebuild.py` | Trade filtering, match explanations and simulated interaction transitions |
| `recovery/progress/priorities.py` | Deterministic next-action selection and deduplication |
| `recovery/progress/milestones.py` | Separate home/funding projections, elapsed time and guarded demo ranges |
| `recovery/progress/orchestrator.py` | Bounded run lifecycle, cancellation and immutable result publication |
| `recovery/progress/store.py` | Preview-only snapshot/history/interaction persistence |
| `recovery/progress/profiles.py` | Increment B optional confirmed profile model |
| `recovery/progress/case_reader.py` | Increment B conversion of atomic saved case snapshot to specialist input |
| `ui/recovery_progress_page.py` | New page, context selection and result presentation |
| `ui/recovery_progress_components.py` | Cards, details, run strip and two milestone tracks |
| `ui/recovery_progress_profile.py` | Increment B optional profile editor and explicit save |

Existing files requiring narrowly scoped changes: `app.py`, `ui/capabilities.py`, `ui/pages.py`, `ui/shell.py`, `ui/search_component.py` if shared alias handling needs JS parity, `ui/styles.css`, `services/assistant.py`, `ui/emergency_page.py`, `emergency/workflow.py`, `ui/state.py`, and README. Increment B also touches `recovery/database.py` and `ui/recovery_page.py`. Keep unrelated modules and dependency pins unchanged.

## Shared contracts

Define these in Task 1 so independently implemented specialists share one meaning:

- `SourceMode`: `SYNTHETIC` / `SAVED_CASE`. LIVE is a later adapter mode, not a label for simulated data.
- `SignalState`: `RED` / `YELLOW` / `GREEN` / `UNKNOWN` / `NOT_APPLICABLE`.
- `RunState`: `QUEUED` / `CHECKING` / `COMPLETE` / `NEEDS_INFORMATION` / `FAILED` / `CANCELLED`.
- `Provenance`: source ID/name, source mode, observed-at, valid-until when supplied, scope (`scenario`, `area`, `address`, `user_report`) and optional official URL. Missing freshness cannot imply current verified service.
- `MoneyFact`: exact Decimal amount with ISO currency OR contribution band OR unknown/declined; purpose, stage ID, reported-at and available/expected/received/spent distinction. Preview fixture amounts use USD. Amounts are non-negative; exact and band values are mutually exclusive. Other currencies are never silently converted or combined. Do not log these values.
- `HouseholdContext`: nullable confirmed total, adults/children references, ZIP/address, accessibility/pets/transport, housing budget, recovery contribution and confirmed recovery-start date. Unknown and declined values are explicit; no default member count or zero budget.
- `ProgressInput`: context key, source mode, checkpoint ID when synthetic, as-of date, household, safety assessment, reviewed task projections, damage/evidence metadata, checklist ID, funding allocations, provider interactions and fixture observations. No raw image bytes, policy/claim references or provider credentials.
- `RunToken`: run UUID, context key, complete input fingerprint, emergency epoch and algorithm/fixture versions.
- `Finding`: stable ID, signal state, concise title, explanation, missing facts, provenance and applicable flag. Domain-specific result classes extend the common contract within their specialist module.
- `SpecialistResult`: common typed envelope with specialist ID, execution state, findings, suggested actions, missing facts and provenance. `HousingResult`, `UtilitiesResult`, `BlockerResult` and `RebuildResult` extend it in their respective modules. Define a `SpecialistAdapter` protocol with `check(inputs: ProgressInput, *, now: datetime) -> SpecialistResult`; function-based specialists can be wrapped without an AI framework.
- `ActionCandidate`: stable action key, optional existing task ID, title, rationale, priority tier, dependencies, proposed destination, provenance and applicability. It is not a persisted accepted task.
- `DashboardSnapshot`: token, attempted-at/finished-at, per-specialist terminal results, retained historical observation metadata, milestone view, selected actions and comparable change summary. Schema-versioned and immutable after publication.

Use aware UTC timestamps for observations and America/New_York calendar dates for elapsed days. Inject clocks in tests; synthetic elapsed days use fixture as-of dates. Keep source observation time separate from run finish time.

## Task 1: Contracts, fixtures and the shared result boundary

**Files:** Create `models.py`, `fixtures.py`, five data files and `tests/test_progress_models.py`, `tests/test_progress_fixtures.py` under the paths above.

**Interfaces:** `load_scenario(scenario_id: str, checkpoint_id: str) -> ProgressInput`; `list_scenarios() -> tuple[ScenarioSummary, ...]`; `fingerprint(inputs: ProgressInput) -> str`. Define `ScenarioSummary` with ID/label/checkpoints/featured flag in `fixtures.py`.

- [ ] Write failing tests `test_fixture_coverage` asserting 6 stories, 18 checkpoints, 12 housing locations with 3/category, 15 providers with 3/trade and 4 checklist profiles; `test_missing_total_is_not_inferred_from_one_count`; `test_money_range_is_not_exact`; `test_every_fixture_is_explicitly_synthetic`; `test_checkpoint_time_is_not_wall_clock`.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_models.py tests/test_progress_fixtures.py`; expect failures for missing contracts/loaders.
- [ ] Implement strict contracts and validated authored fixtures. Feature Rivera/Chen/Alvarez; add Baptiste/Morgan/Williams for accessibility/no-insurance/missing-context. Use fake contact tokens, not working phone/email endpoints. Include a setback and terminal unresolved blocker, not only success stories.
- [ ] Rerun those tests; expect PASS and no service network requests during loading.
- [ ] Review fixture wording and checkpoint consistency; checkpoint commit `feat: define recovery progress contracts and fictional scenarios`.

## Task 2: Housing and utility checks

**Files:** Create `housing.py`, `utilities.py`, `tests/test_progress_housing.py`, `tests/test_progress_utilities.py`.

**Interfaces:** `check_housing(inputs: ProgressInput, *, now: datetime) -> HousingResult`; `check_utilities(inputs: ProgressInput, *, now: datetime) -> UtilitiesResult`. Each result exposes findings, missing facts, suggested actions and provenance. Housing also exposes category inventories and per-option fit reasons; Utilities exposes electricity/water/gas independently.

- [ ] Write `test_rooms_require_occupancy_and_whole_household_allocation`, `test_full_or_unactivated_site_is_not_a_match`, `test_unknown_accessibility_is_uncertain`, `test_stale_capacity_not_current`, `test_housing_budget_not_repair_budget`, `test_area_clear_does_not_mean_address_restored`, `test_water_available_is_not_potable`, `test_gas_not_applicable`, `test_conflicting_utility_reports_are_unknown`.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_housing.py tests/test_progress_utilities.py`; expect missing-specialist failures.
- [ ] Implement deterministic filtering and status rules. Known incompatibility excludes, unknown critical fit makes uncertain, and all capacity units remain explicit. Synthetic fixture distances are labelled as such; no geocoding/network call.
- [ ] Rerun focused tests; expect PASS. Assert saved-case-shaped input with no provider observation yields UNKNOWN, never synthetic fallback.
- [ ] Review explanations; checkpoint commit `feat: add housing and utility progress specialists`.

## Task 3: Insurance preparation and stage-specific funding

**Files:** Create `insurance.py`, `tests/test_progress_insurance.py`, `tests/test_progress_funding.py`.

**Interfaces:** `check_insurance_and_funding(inputs: ProgressInput, *, now: datetime) -> BlockerResult`; `funding_gap(cost: MoneyFact, allocation: MoneyFact) -> Decimal | None`. Result has separate preparation and funding findings plus unresolved requirements and stage dependencies.

- [ ] Write `test_uploaded_photo_does_not_satisfy_unlinked_requirement`; `test_green_means_selected_checklist_prepared`; `test_no_insurance_is_not_a_claim_blocker`; `test_unselected_checklist_stays_unknown`; `test_gap_4000_minus_1000_is_3000`; `test_range_unknown_declined_stale_or_mixed_stage_has_no_exact_gap`; `test_expected_or_approved_unpaid_funds_are_excluded`; `test_spent_or_other_stage_allocation_not_counted_twice`.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_insurance.py tests/test_progress_funding.py`; expect missing-specialist failures.
- [ ] Implement explicit requirement mapping and Decimal arithmetic only when stage, currency, currentness and exactness match. Profiles A–D are neutral fictional preparation patterns. Generic existing insurance omissions cannot establish insurer-specific completeness.
- [ ] Rerun tests; expect PASS. Chen must support advanced home milestones with unresolved reimbursement; Alvarez must expose a funding dependency rather than imply reimbursement is available.
- [ ] Review financial copy and evidence distinctions; checkpoint commit `feat: explain recovery preparation and funding blockers`.

## Task 4: Repair-provider results, next actions and two-track milestones

**Files:** Create `rebuild.py`, `priorities.py`, `milestones.py`, `tests/test_progress_rebuild.py`, `tests/test_progress_priorities.py`, `tests/test_progress_milestones.py`.

**Interfaces:** `check_rebuild(inputs: ProgressInput, *, now: datetime) -> RebuildResult`; `simulate_provider_event(current: ProviderInteraction, event: ProviderEvent) -> ProviderInteraction` (models local to `rebuild.py`); `select_next_actions(inputs: ProgressInput, results: tuple[SpecialistResult, ...]) -> tuple[ActionCandidate, ...]`; `build_milestones(inputs: ProgressInput, results: tuple[SpecialistResult, ...]) -> MilestoneView` (define view in `milestones.py`).

- [ ] Write tests for all 5 trade filters, unrated vs zero, enquiry vs quote vs commitment, and no outbound contact; `test_future_quote_does_not_leak_into_earlier_checkpoint`; `test_current_housing_need_outranks_routine_repair`; `test_funding_dependency_precedes_scheduling`; `test_completed_and_nonapplicable_tasks_not_reopened`; `test_at_most_three_explained_actions`; `test_safety_blocks_routine_actions`; `test_saved_case_has_no_illustrative_ranges`; `test_day_12_uses_confirmed_start_and_scenario_date`.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_rebuild.py tests/test_progress_priorities.py tests/test_progress_milestones.py`; expect missing-function failures.
- [ ] Implement deterministic transitions and tiered ranking. Bind simulated interaction overrides to household plus checkpoint (include checkpoint ID in `ProviderInteraction` and its store key); do not mutate authored fixtures. Reuse `current_task_views()` when a saved plan exists. Separate home and financial milestones, permit setbacks, avoid universal completion percentages, and do not infer home safety or claim approval.
- [ ] Rerun focused tests; expect PASS. Source/checklist facts explaining an action must be included in its detail output; failed specialist data must be disclosed.
- [ ] Checkpoint commit `feat: prioritize recovery actions and separate home from funding progress`.

## Task 5: Coordinator, cancellation and preview persistence

**Files:** Create `orchestrator.py`, `store.py`, `tests/test_progress_orchestrator.py`, `tests/test_progress_store.py`.

**Interfaces:** Construct `ProgressCoordinator(adapters: Mapping[str, SpecialistAdapter], store: SQLiteProgressStore, *, clock: Callable[[], datetime], max_workers: int = 4)`. It provides `start(inputs: ProgressInput, *, emergency_epoch: int) -> RunToken`, `poll(token: RunToken) -> RunUpdate`, `cancel(token: RunToken) -> None` and `publish_if_current(token: RunToken, *, current_fingerprint: str, emergency_epoch: int) -> DashboardSnapshot | None`. Define `RunUpdate` as per-specialist execution events plus optional terminal snapshot. `SQLiteProgressStore(path)` provides `latest(context_key: str) -> DashboardSnapshot | None`, `history(context_key: str) -> tuple[DashboardSnapshot, ...]`, `save(snapshot: DashboardSnapshot) -> None`, `save_interaction(context_key: str, interaction: ProviderInteraction) -> None` and `interactions(context_key: str) -> tuple[ProviderInteraction, ...]`.

- [ ] Write tests asserting Housing dispatches first, bounded workers, actual QUEUED/CHECKING events, successful red result remains red, single-flight refresh, per-agent error isolation, repeatable fixture time, late result rejection after checkpoint/mode/context/epoch changes, stale previous observations after failure, history per household/mode, and persistence across a fresh store instance. Assert cancelled/interrupted runs never publish current results.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_orchestrator.py tests/test_progress_store.py`; expect missing coordinator/store failures.
- [ ] Use a bounded executor (maximum 4 workers), no Streamlit calls in workers and timeout-bounded adapters. Capture immutable inputs. Housing is dispatched first; all four terminal states precede next-action synthesis. Implement idempotent schema-versioned preview persistence in a separate SQLite file (`READYRELIEF_PROGRESS_DB_PATH`; default `.local/recovery-progress.sqlite3`). Persist findings/interaction state only, never attachment bytes or existing Recovery mutations.
- [ ] Rerun tests; expect PASS. Simulated latency belongs to the synthetic adapter and is explicitly labelled. Restore persisted result history on page entry, not unfinished executors; interrupted runs are not complete. Preserve observed-at independently of attempt timestamps.
- [ ] Checkpoint commit `feat: orchestrate and persist isolated recovery progress checks`.

## Task 6: Navigation and isolated page entry

**Files:** Modify `app.py`, `ui/capabilities.py`, `ui/pages.py`, `ui/shell.py`, `ui/search_component.py` only if needed for alias parity, `services/assistant.py`, `ui/emergency_page.py`; create initial `ui/recovery_progress_page.py`; extend `tests/test_navigation_routes.py`, `tests/search_suggestions.mjs`, `tests/test_shell.py`, `tests/test_assistant.py`.

**Interfaces:** Add shared `NavigationItem` descriptor and `navigation_items(*, progress_enabled: bool) -> tuple[NavigationItem, ...]` in `ui/capabilities.py`. Canonical progress route is `Recovery Progress`; existing plan/insurance destinations resolve to Recover with their existing `rr_focus` values. Existing `navigate(page)` remains backward-compatible; add an explicit focus-aware navigation helper for the new destinations.

- [ ] Write regressions: `search_pages('open recovery') == ['Recover']`, `search_pages('recovery progress') == ['Recovery Progress']`, `search_pages('tasks') == ['Recover']`, desktop/mobile discoverability, assistant navigate schema acceptance, feature disabled fallback, preview visit preserves staged Recovery draft/review objects and emergency entrypoint is `recovery`.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_navigation_routes.py tests/test_shell.py tests/test_assistant.py`; run `node tests/search_suggestions.mjs`; expect only new-route expectations to fail.
- [ ] Add `READYRELIEF_PROGRESS_PREVIEW` feature switch, enabled for this development preview, with disabled direct-route fallback to Recover. The initial page has its title, synthetic scenario/checkpoint selector and Not checked placeholders; working specialist rendering is Task 7. Preserve the global frame before page-specific imports/I/O and the original Recover renderer. Keep exact known route aliases ahead of broad token matching; use shared metadata for browser suggestions as well as Python search.
- [ ] Rerun the commands; expect PASS and unchanged existing navigation behavior. No case creation on progress-route entry.
- [ ] Checkpoint commit `feat: add grouped recovery progress preview navigation`.

## Task 7: Dashboard, specialist details and synthetic interactions

**Files:** Expand `ui/recovery_progress_page.py`; create `ui/recovery_progress_components.py`; add screen-scoped rules to `ui/styles.css`; create `tests/test_progress_ui.py` and `tests/visual/progress.spec.cjs`.

**Interfaces:** `render() -> None`; `render_dashboard(snapshot: DashboardSnapshot) -> None`; `render_specialist_details(result: SpecialistResult) -> None`; `render_run_status(update: RunUpdate) -> None`. Page owns context selection; components cannot save Recovery records or call providers.

- [ ] Write UI checks for visible synthetic badge, six scenario choices, explicit checkpoint selection, all 4 housing categories/5 trades, View details reasons/source times, independent utility tiles, preparation/funding sub-statuses, two milestone tracks, at most 3 action suggestions and scenario-specific funding views. Assert displayed capacities have units and timing carries the illustrative label.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_ui.py`; expect missing page-content failures.
- [ ] Implement the approved mockup with the revised Insurance & funding card and two tracks. Keep four cards; use a compact funding line, not a fifth large card. Simulated enquiry/quote controls are labelled and write only preview interaction state. Details never render real-looking demo contact links. Show useful empty/start/resume states.
- [ ] Rerun UI tests; expect PASS. Browser spec checks desktop/tablet/mobile, both themes, keyboard navigation, readable detail content, no horizontal overflow and HTML escaping. The unrefreshed view shows Not checked or historical data, not fabricated fresh results.
- [ ] Checkpoint commit `feat: render recovery progress cards and explainable details`.

## Task 8: Wire manual refresh animation and interruption behavior

**Files:** Modify new progress UI/components, `emergency/workflow.py`, `ui/state.py`; extend `tests/test_progress_ui.py`, `tests/test_progress_orchestrator.py`, `tests/test_emergency_workflow.py`, `tests/visual/progress.spec.cjs`, `tests/visual/emergency.spec.cjs`.

**Interfaces:** New screen keys start `rp_`; store active run token and immutable input fingerprint only for the current context. Add `invalidate_progress_run(state: MutableMapping[str, object]) -> None` in the progress page/state helper chosen during implementation, without deleting accepted Recovery keys.

- [ ] Test page entry/details/browser reload cause zero starts; one Refresh creates one run; checking animation reflects lifecycle; refresh disabled while active; cancellation invalidates token; changed scenario/case/source context/epoch rejects late events; persisted danger and missing safety assessment pause routine work; reduced-motion run status stays understandable.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_ui.py tests/test_progress_orchestrator.py tests/test_emergency_workflow.py`; expect new wiring failures.
- [ ] Wire a short Streamlit polling fragment while a run exists; cancel polling at terminal state. Render emergency controls throughout and call the shared guard before starting/publishing routine work. Emergency invalidation clears only new pending-run state; workers can finish harmlessly but cannot publish. Keep last observation time and last attempt time separate, with historical results clearly stale after failures.
- [ ] Rerun Python checks and `READYRELIEF_PYTHON=.venv/bin/python npm run test:visual -- tests/visual/progress.spec.cjs tests/visual/emergency.spec.cjs`; expect functional PASS. Inspect phone targets without dialing. Do not mask a failed check with a completion animation or green signal.
- [ ] Checkpoint commit `feat: show cancellable specialist progress during manual refresh`.

## Task 9: Preview acceptance and preservation of existing workflows

**Files:** Extend `tests/test_progress_ui.py`, `tests/visual/progress.spec.cjs`, `tests/visual/experience.spec.cjs`; update README with preview usage, isolation and data limits. Add relevant baseline images only after visual review on the CI platform.

**Interfaces:** No new runtime interface. Exercise the public app and repository behavior.

- [ ] Add acceptance assertions that database case/record/plan/task/insurance contents are unchanged by every preview action; loading progress does not consume or overwrite staged Recovery drafts/reviews; disabling preview preserves existing route behavior. Preserve existing form/widget lifecycle rather than introducing a new autosave behavior. Test Rivera housing, Chen reimbursement-pending, Alvarez funding-blocked, plus accessibility/uninsured/incomplete variants.
- [ ] Run the focused suite below; investigate failures before broadening. Existing status persistence and approved-history behavior must pass.
- [ ] Run full Python and Node checks and browser tests once the focused suite passes. For visual updates, compare intended grouped-navigation changes separately from unexpected screen changes. Windows CI baselines are authoritative for existing snapshots; do not replace them with macOS renders.
- [ ] Walk through first three featured stories with a reviewer: understand the next action, locate reasons, observe partial failure, switch checkpoints and see completed work retained. Capture results without claiming production safety or forecasting validation.
- [ ] Checkpoint commit `test: verify recovery progress preview and existing workflows`; review this increment before proceeding to saved-case data changes.

## Task 10: Optional confirmed profile on Recovery home

**Files:** Create `recovery/progress/profiles.py`, `ui/recovery_progress_profile.py`, `tests/test_progress_profiles.py`; modify `recovery/database.py`, `ui/recovery_page.py`; extend `tests/test_recovery_records.py` and `tests/test_recovery_landing.py`.

**Interfaces:** `ProgressProfile` is a versioned case-bound model with confirmed total, structured address/ZIP, start date, accessibility/pets/transport, housing budget, recovery contribution and gas applicability/report. Add repository `get_progress_profile(case_id: UUID) -> ProgressProfile` and `save_progress_profile(profile: ProgressProfile, *, expected_version: int, expected_case: RecoveryCase, explicitly_confirmed: bool) -> ProgressProfile`. `render_progress_profile(repo, case) -> None` is shared by existing Recovery home and a progress detail destination.

- [ ] Write tests for additive migration preserving existing JSON/history; optional blanks vs zero vs declined; session household defaults never auto-saved; incomplete adult/child counts never establish total; conflicting confirmed counts produce Needs information; explicit save/confirmation; stale version rejection; no precise cash gap from broad contribution bands; profile save does not alter accepted task statuses.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_profiles.py tests/test_recovery_records.py tests/test_recovery_landing.py`; expect missing profile/repository failures.
- [ ] Add a side table `recovery_progress_profiles` with case FK and versioned JSON; no destructive schema rewrite. Put optional inputs on Recovery home/workspace, with a preview before confirmation. Offer session preference reuse explicitly; do not silently import. Profile changes affecting needs produce an existing reassessment entry link/proposal, not an automatic plan revision. Housing budget and repair contribution remain separate.
- [ ] Rerun focused tests; expect PASS. Keep exact address out of the sidebar, logs, exports, model prompts and provider queries; mask it on the overview. The prototype continues to request fictional details only.
- [ ] Checkpoint commit `feat: capture optional confirmed recovery matching context`.

## Task 11: Consistent saved-case reads and read-only recommendations

**Files:** Create `recovery/progress/case_reader.py`, `tests/test_progress_case_reader.py`, `tests/test_progress_case_integration.py`; modify `recovery/database.py`, progress page/store and relevant existing integration tests.

**Interfaces:** Add `SQLiteRecoveryRepository.get_progress_snapshot(case_id: UUID) -> ProgressCaseSnapshot` using a single SQLite read transaction. Define snapshot in `case_reader.py`: case, records, active plan, insurance workspace, attachment metadata, journey events, progress profile. `from_saved_case(snapshot: ProgressCaseSnapshot, *, as_of: date) -> ProgressInput` strips sensitive references and preserves unknowns. Never load image bytes on every polling tick.

- [ ] Test atomic versions under concurrent updates; emergency/unknown-safety cases do not run; checklist suitability unknown without a reviewed selection; evidence deletion invalidates readiness; original `File saved` integrity rules remain; no raw image bytes/policy references in dashboard outputs; actual/saved mode never loads demo capacities/providers/ranges; completed task IDs persist; returning to the saved case restores only that case's observations.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_progress_case_reader.py tests/test_progress_case_integration.py tests/test_insurance_workspace.py tests/test_recovery_selected_integration.py`; expect missing read-adapter failures.
- [ ] Implement the consistent read and version fingerprint; use existing validators for saved evidence and case safety. Build a fresh snapshot once per refresh, compare current versions before publication and mark views outdated after edits. Link actions into existing `rr_focus` destinations. With no provider adapter show Unknown and official-check entry links where reviewed, not invented live results. Saved-case forecasts display **Not enough information**. Stage-specific costs/allocations and payment events remain unknown: the current records and new contribution band are not a financial ledger. Never derive payment approval/receipt from free-text communications or aggregate inventory cost.
- [ ] Rerun focused then full regression commands. Verify no new plan approval, contact, booking or insurance submission occurs on refresh or View details.
- [ ] Checkpoint commit `feat: connect recovery progress to confirmed saved case data`; review this increment independently of external integrations.

## Increment C: external integration work, separately scoped

1. **Electricity feasibility:** inspect supported FPL/provider interfaces and required authentication/consent. Deliver a documented capability matrix: area outage, reported service-address status, timestamp, failure/rate-limit handling and whether programmatic access is supported. If unsupported, offer the official status flow and an explicitly user-reported result; do not ship a scraper that guesses a household's status.
2. **Provider contracts:** implement one read-only adapter at a time behind the specialist interfaces. Test timeouts, stale data, scope mismatch and no-data cases. Keep fixture and external outputs strictly separated. Geography/provider identity must be explicit; county alone is not a utility-service lookup.
3. **Housing/provider directories:** identify reviewed sources and real capacity semantics. A directory listing is not activated shelter inventory. Real contractor reviews need their source, timestamp and terms understood; do not transfer fictional ratings to real providers.
4. **User-recorded contacts:** add confirmed contact/quote/commitment records with correction history. A recorded call or sent request does not establish response or work acceptance. Message sending/booking remains a separate future feature.
5. **Confirmed funding records:** add a separately reviewed editor for next repair stage, stage cost, exact earmarked allocations, and user-reported decision/received/spent events. Preserve corrections and prevent allocation reuse between stages. Only then calculate saved-case exact gaps; contribution bands alone remain insufficient. Do not treat user reports as externally verified financial status.
6. **Forecasting:** define outcomes and collect valid time-stamped observations before building a predictor. Synthetic checkpoints do not train or validate insurance/recovery duration estimates. Keep ranges conditional and insurance decision/payment/home milestones separate.

## Verification commands for implementation

Focused existing regressions:

```bash
.venv/bin/python -m pytest -q tests/test_navigation_routes.py tests/test_assistant.py tests/test_assistant_ui.py tests/test_recovery_landing.py tests/test_recovery_selected_integration.py tests/test_recovery_capabilities.py tests/test_recovery_records.py tests/test_recovery_flow.py tests/test_recovery_task_projection_ui.py tests/test_insurance_ui.py tests/test_insurance_workspace.py tests/test_emergency_workflow.py tests/test_emergency_service_integration.py tests/test_emergency_ui.py
```

Established full checks (run after focused coverage passes):

```bash
.venv/bin/python -m pytest -q
node tests/search_suggestions.mjs
node tests/tour_lifecycle.mjs
.venv/bin/python -m compileall -q app.py domain services ui recovery emergency knowledge m2_guardian
READYRELIEF_PYTHON=.venv/bin/python npm run test:visual
```

Use the existing Node runtime or normal configured PATH; do not install/upgrade dependencies just to write this plan. Browser tests use isolated temporary databases and fixed synthetic clock/checkpoints. On Windows use the environment's Python path and shell syntax. Older standalone acceptance scripts hardcode Windows fixture paths; use the maintained Playwright config rather than assuming those scripts are portable. New preview result DBs must also be temporary during tests.

## Completion criteria

Increment A is complete when the isolated preview works through every synthetic scenario, visible agent lifecycle, partial failure, details and next-action explanation; resumes snapshots; remains accessible; and passes existing workflow regressions. Increment B additionally requires confirmed optional fields, consistent saved-case reads, unknown results for unavailable integrations and no mutation of existing accepted history. Neither increment claims real availability, insurer approval, real contractor contact or validated recovery dates.

No main-branch merge, live integration, real contact or deprecation is part of this plan's first execution slice.
