# Recovery Progress demo verification

Date: 2026-11-06. Educational prototype; fictional scenarios, not live availability.

## Integration and safety correction

Integration branch: `integration/recovery-progress-reviewed`, based on main
`be0b99adbe2bb9ffe6e97716f59649db86fcce85` and teammate Recovery-Progress
`3771a557b3b00f9ba313a3507537b45fbc4c75f3`. Original branches and separate
uncommitted review documents are preserved. Documentation/evaluation PR #7 is
separate and was still open when checked; its changes are not part of this integration.

Reproduced defect: a selected case with persisted danger could display synthetic
recommendations after session emergency flags were absent. The synthetic loader
did not consult the selected case's database safety state.

`ui/recovery_progress_page.py::_unsafe` now reuses
`current_progress_revision` / `SQLiteRecoveryRepository.get_progress_revision`.
The existing repository safety check rejects danger, unassessed safety and missing
cases. Lookup failures also block. The check runs before either input mode,
before publishing a result and before rendering recommendations. Simulated
provider updates also recheck safety. Pending danger uses the existing emergency
guard; failed danger persistence remains pending. No danger-clearance path was
added. Global Call 911 and I Can't Call 911 remain independent of these checks.

Nine new regression cases cover persisted/unassessed safety in both modes,
unavailable safety lookup, successful/failed pending-danger persistence,
case switching, newly persisted danger and direct input loading.

## Actual execution architecture

The existing LangGraph executes a fixed graph: housing first, then utilities,
insurance/funding and rebuild, followed by deterministic prioritization and
milestones. Four specialist calls execute through an actual local stdio MCP
server. Five named tools are exposed; funding shares the insurance specialist.
There is no autonomous agent reasoning, model-selected tool use or LLM-driven
specialist. No model/provider network calls were used for this verification.

## Verified scope and honesty boundaries

- Housing includes fictional hotels, community/church facilities, schools and
  shelter examples. Capacity, prices and suitability are authored simulation data;
  no booking or current shelter opening is established.
- Electricity, water and gas are separate indicators. Area-level observations,
  missing freshness and unconfirmed water potability do not establish usable
  service. A green card never verifies property safety.
- Saved-case mode reads existing confirmed Recovery/Insurance information.
  Reported-but-unuploaded evidence is distinct from saved files. Synthetic
  insurance checklists cannot supply missing real-case insurer requirements.
- Contractor categories/listings and contact/quote events are simulated. Recording
  an event makes no external contact, booking or commitment.
- Next Best Action uses deterministic priorities and explains its basis.
  Dashboard refresh does not approve plans, change task progress or submit claims.
- Elapsed days use a recorded date. Synthetic duration/payment bands are labeled
  illustrative; absent saved-case dates/predictions remain unavailable.

## Verification

- Focused safety/UI/runtime tests: **35 passed**.
- Full Python suite: **1,292 passed, 11 skipped, 10 subtests passed**.
- Compact synthetic evaluation: **11/11 passed**; per-case modes and assertions
  are in [evaluation-results.json](recovery-progress-demo/evaluation-results.json).
- CAP-04 golden evaluation: **24/24 passed**, proposed expectations.
- Tour lifecycle and search-suggestion JavaScript checks passed; compileall passed.
- Full normal visual suite: **74 passed, 1 existing skip** in 7.4 minutes, with
  unchanged screenshot comparison tolerances (not snapshot-update mode).
- Actual desktop/tablet/mobile Chromium exercises refresh, View Details, traffic
  lights, source labels, stale checkpoints, saved-case unknowns, simulated failure,
  danger interruption and emergency/navigation access. Desktop card and mobile
  dashboard captures were also visually inspected.
- Twelve existing screenshot baselines were reviewed for added navigation and
  current styling. Screenshot tolerances/assertions were retained. One explicit
  render-complete wait avoids capturing temporarily disabled widgets; the initial
  emergency-control test wait allows cold application startup (30 seconds).

Reproduce using an environment installed from `requirements.txt`:

```powershell
python -B -m pytest -q -p no:cacheprovider
python -B -m scripts.evaluate_progress_demo --output .local/progress-demo-evaluation.json
node tests/tour_lifecycle.mjs
node tests/search_suggestions.mjs
npm run test:visual
```

## Remaining limitations

This is a course demonstration, not a production readiness assessment. Catalogs
are not live feeds or M3-reviewed guidance. Insurance suitability, eligibility,
coverage and payment are not verified. Saved-case unknowns intentionally remain
unknown. The fixed prioritizer is not a replacement for the accepted Recovery
plan or human judgment. Safety refresh requires application interaction/rerender;
there is no continuous monitoring or emergency dispatch. Existing Insurance files,
M3 approvals and household task progress were not edited by this correction.
