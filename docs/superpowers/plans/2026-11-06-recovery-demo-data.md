# Recovery Progress demo data expansion

**Goal:** Expand the existing synthetic preview to 24 distinct households, 72 checkpoints, 48 housing sites, 60 providers and 8 neutral fictional checklists; deliver a demonstrator's guide with verified outcomes.

**Approach:** Extend the existing JSON fixtures and shared deterministic MCP/domain functions. Keep the six existing stories and IDs. New checkpoint catalog selections/overrides allow real differences in capacity, provider availability and observation age. Do not add live integrations, randomize the demo, or change saved cases. User requested implementation; routine size, format and fixture choices are made within that authorization. Work stays on Recovery-Progress, without commit/push.

**Deliverables:** JSON catalogs and stories; typed fixture override loading; machine-readable demo notes/expected outcomes; PDF and Markdown demo guide; updated usage documentation; all-scenario and real-MCP verification.

## Work

- [x] Expand housing/providers/checklists while retaining original order and IDs; validate counts, category coverage, units, synthetic labeling, and foreign references.
- [x] Add 18 coherent three-checkpoint stories and presenter notes covering housing constraints, utilities, evidence, funding, repair responses, setbacks and failure recovery.
- [x] Add strict optional per-checkpoint `catalog` selections, record overrides and observation ages to the fixture loader; reject unknown/duplicate IDs and invalid overrides.
- [x] Check every household/checkpoint through specialist/ranking logic; verify curated expected states and priorities, safety blocking, and source isolation. Exercise all five MCP tools and representative LangGraph runs.
- [x] Produce a concise printable PDF and repository Markdown guide with short demo routes, exact selectors, expected states, next-action explanations, tool examples, and reset/resume notes. Render and inspect the PDF.
- [x] Run focused and full regression checks, browser smoke for expanded selections, and independent consistency review. Refresh local app.

## Shared catalog contract

Each checkpoint may have an optional `catalog` object, removed before ProgressInput validation:

```json
{"housing_ids": ["hotel-1"], "provider_ids": ["electrician-1"],
 "housing_overrides": {"hotel-1": {"available_units": 0}},
 "provider_overrides": {"electrician-1": {"availability": "unavailable"}},
 "housing_age_hours": 0, "provider_age_hours": 0,
 "housing_validity_hours": 24, "provider_validity_hours": 24}
```

Omitted IDs select the full catalog; empty lists select none. Overrides apply only to selected, known IDs and cannot alter IDs or provenance. Final records are validated using the existing domain models. Age is nonnegative; validity may be null to represent unknown freshness. Observed time is checkpoint time minus age; validity is measured from observed time. Original fixture catalog rows never mutate. All injected provenance remains synthetic.

## Review focus

Full or stale accommodation must not promise space; unknown water potability remains distinct from supply; approved/unallocated payments are not cash; completed work survives setback stories; safety/failure cases must be documented as paused/failed rather than successful. Guide expectations must be checked against actual tool results, including combined insurance status versus its separate preparation/funding/payment signals.
