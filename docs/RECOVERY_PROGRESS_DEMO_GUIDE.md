# ReadyRelief Recovery Progress demo guide

Generated from the synthetic fixtures on 2026-11-06. Rebuild with `.venv/bin/python scripts/build_recovery_demo_guide.py`. PDF generation requires `reportlab`; use `--markdown-only` to generate Markdown with the application dependencies alone.

## Start the demo

Recovery Progress / Demonstrator's guide

24 fictional households. 72 authored checkpoints. Four specialist views and one ranked next step. Use this guide to show why a result changes, what remains unknown, and what the prototype does with those facts.

### Open the preview

```bash
python -m streamlit run app.py
```

1. Use the interpreter where requirements.txt is installed (for example .venv/bin/python). In the app navigation, open Recover > Recovery Progress · Preview.
2. Expand Choose story or saved case. Set Dashboard source to Synthetic stories. Choose Household story and Story checkpoint.
3. The checkpoint labels are 1 · Starting point (initial), 2 · An update (update), and 3 · Later in recovery (later). Select Refresh checks after each change.
4. Wait for Last run activity and the four specialist cards. Read One manageable next step, open relevant View details, then compare Your two recovery tracks.

### Say this before showing results

All identities, addresses, prices, capacities, ratings, observations, provider responses and timing are fictional. Local deterministic checks run through LangGraph and the actual MCP stdio boundary. This demo does not reserve space, send enquiries, approve claims or dispatch work.

### Reading the signals

| Signal | Meaning |
| --- | --- |
| Red | Action needed for the named condition |
| Yellow | In progress |
| Green | Condition met for the named check |
| Unknown | Missing, stale or unavailable information |
| Not applicable | A separate status, not success or failure |

Execution and condition are different. Complete + Red means the check ran and found a problem. Needs information or Couldn't update appears gray. Green does not certify home safety or insurer approval.

## Choose a demo route

### Five minutes: the main recovery story

| Time | Presenter action | Point to make |
| --- | --- | --- |
| 0:00-1:00 | Rivera / initial > Refresh checks | Show the source badge, four cards and primary action. Open housing details to compare rooms with spaces. |
| 1:00-2:30 | Rivera / update > Refresh checks | Read What changed and compare the Home & daily life and Costs & funding tracks. |
| 2:30-4:00 | Chen / later > Refresh checks | Repairs and return home do not establish reimbursement receipt. Inspect preparation, funding and payment separately. |
| 4:00-5:00 | Open Timing & assumptions | Illustrative story ranges are not forecasts. End with the next action and the evidence behind it. |

### Fifteen minutes: dependencies and uncertainty

1. Minutes 0-5: follow the five-minute route. Use the scenario pages to read exact card states and action text.
2. Minutes 5-8: Alvarez initial > update > later. Compare exact stage cost, explicit allocation and the remaining gap with provider quotes and work commitments.
3. Minutes 8-10: Baptiste initial > update. Show accessibility, household suitability, pets, transport and availability as separate housing constraints.
4. Minutes 10-12: Morgan initial > later. Insurance can be not applicable while household funding still needs information. Completed repairs remain distinct from funding certainty.
5. Minutes 12-14: Campbell initial > update > later. Read Couldn't update / No new observation at update and the partial recommendation from the remaining checks. Show the fresh utility result at later.
6. Minutes 14-15: Williams initial. Refresh checks is disabled until immediate safety is explicitly assessed; missing facts are not filled from another household.

### Technical route: fifteen additional minutes

1. List the five MCP tools and invoke the compact scenario payload examples on the next page.
2. Compare assess_insurance_readiness and assess_funding_gap for the same checkpoint: both expose the same shared preparation/funding result.
3. Inspect source_mode, context_key and input_fingerprint. Explain how context changes make earlier snapshots historical.
4. Record a simulated provider update, refresh, then switch checkpoints to show the override is scoped to one story checkpoint.
5. Use the fixture and metadata files in the catalog reference to trace a displayed condition to exact source facts.

For a rehearsed baseline, use a fresh demo-only progress database path at launch. Do not clear the existing progress database or the accepted recovery-case database.

## Demonstrate the five MCP tools

Run the server from this repository with the installed interpreter. It uses local stdio; no API key or external provider integration is required.

```bash
.venv/bin/python -m recovery.progress.mcp_server
```

In a compatible MCP host, configure the interpreter as command, [-m, recovery.progress.mcp_server] as args, and the repository as cwd (or set PYTHONPATH to its absolute path). Call each tool using the arguments below.

### `find_temporary_housing`

```json
{"scenario_id": "baptiste", "checkpoint_id": "initial"}
```

Compare needs, room/space units, budget and suitability; no booking.

### `check_utility_health`

```json
{"scenario_id": "rivera", "checkpoint_id": "initial"}
```

Read address scope, observation age, electricity, water supply, potability and gas applicability.

### `assess_insurance_readiness`

```json
{"scenario_id": "chen", "checkpoint_id": "later"}
```

Inspect preparation, stage funding and decision/receipt as separate result items.

### `assess_funding_gap`

```json
{"scenario_id": "alvarez", "checkpoint_id": "initial"}
```

Explain a gap using current exact same-stage USD cost and explicit allocation.

### `search_repair_providers`

```json
{"scenario_id": "alvarez", "checkpoint_id": "update"}
```

Read trade/area matches, catalog availability, simulated interaction and quote; no contact.

### Response and context contract

Successful responses contain source_mode, context_key, input_fingerprint and result. The result includes state, execution_state, items, missing facts and action candidates. The graph uses four specialist calls (insurance already includes funding), then selects up to three next actions.

Use either scenario_id/checkpoint_id or a complete typed payload. The app supplies payload when it has saved-case facts or simulated overrides; never pass both mechanisms. A scenario-only tool call uses fixture baseline data and does not read dashboard interaction overrides.

Repeat the fixture sanity check through the real MCP boundary with this repository command (it validates synthetic expectations, not live availability):

```bash
python -m scripts.verify_recovery_demo_data \
  --output artifacts/recovery-demo-data-verification.json
```

Safety-unknown or danger checkpoints reject routine MCP calls. A configured service failure returns a tool error; the graph shows Couldn't update with no new observation and excludes that specialist's old actions.

## Synthetic data catalog

The guide is generated from the JSON fixtures and checked against the authored demo expectations. Story ordering and existing IDs are retained. Catalog selections and overrides apply only to their checkpoint.

| File / count | Fields and coverage |
| --- | --- |
| scenarios.json / 24 stories, 72 checkpoints | Household size, adults/children, fictional location, access/pets/transport, nightly budget, contribution band, safety, accommodation, utilities, evidence, funding, trades and interactions. |
| housing.json / 48 sites | Four categories: hotel, church, school, official shelter. Rooms vs spaces, occupancy, capacity, activation, household togetherness, accessibility, pets, price, distance and transport. |
| providers.json / 60 providers | Five trades: Electrician, Contractor, Plumber, Roofer, Pool specialist. County/areas, fictional rating/review count, availability and accessible service. |
| checklists.json / 8 profiles | Neutral fictional requirements with explicit evidence links. No real insurer policy or approval rules. |
| demo_scenarios.json / 24 presenter records | Theme, presenter goal, key lesson, recommended tool, checkpoint talk track, expected four signals/execution states and primary action key. |

### Stable IDs

Housing: hotel: hotel-1 through hotel-12 (12); church: church-1 through church-12 (12); school: school-1 through school-12 (12); official shelter: official-shelter-1 through official-shelter-12 (12).

Providers: Electrician: electrician-1 through electrician-12 (12); Contractor: contractor-1 through contractor-12 (12); Plumber: plumber-1 through plumber-12 (12); Roofer: roofer-1 through roofer-12 (12); Pool specialist: pool-specialist-1 through pool-specialist-12 (12).

Checklists: sample-a (Sample A: Basic preparation); sample-b (Sample B: Itemized evidence); sample-c (Sample C: Incurred-cost preparation); sample-d (Sample D: Proposed-work preparation); sample-e (Sample E: Fictional temporary-stay document preparation; a neutral demo example, not an insurer requirement.); sample-f (Sample F: Fictional inspection and proposed-work document preparation; a neutral demo example, not an insurer requirement.); sample-g (Sample G: Fictional belongings and repair-progress document preparation; a neutral demo example, not an insurer requirement.); sample-h (Sample H: Fictional combined scope and incurred-cost document preparation; a neutral demo example, not an insurer requirement.).

Checkpoint catalog controls: housing_ids/provider_ids select known records; an empty list selects none. housing_overrides/provider_overrides alter allowed fields on selected records. *_age_hours and *_validity_hours control freshness. IDs and synthetic provenance cannot be overwritten.

## Interactions, history and safe rehearsal

### Record a simulated provider response

1. Choose Synthetic stories > Alvarez > 1 · Starting point, then Refresh checks. Expand View details · Rebuild my life.
2. Find Demo Bay Contractor (contractor-1); if the saved checkpoint already has a different interaction, use the next allowed event shown or start with a new demo-only progress database.
3. In Simulated update choose an offered event, then select Record simulated update. The app says the update was recorded and asks for Refresh checks.
4. Refresh checks. Inspect the Interaction field and next step. The supported forward chain is shortlisted > enquiry recorded > awaiting reply > quote received > quote accepted > work committed; decline is offered at awaiting reply or quote received.
5. The control changes only interaction state. It does not invent a monetary quote, send a message or complete repairs. Work committed remains distinct from repairs reported complete.
6. Switch to a different Story checkpoint. Refresh manually. Its authored interactions and separately stored overrides apply; a change at initial does not edit update or later.

### Resume without deleting data

Reloading does not start checks. The latest attempt survives reload; an abandoned in-flight attempt becomes interrupted and needs Refresh checks. After an input, checkpoint or source change, earlier results are historical and current recommendations stay hidden until a successful refresh.

What changed compares the latest stored snapshot for that household context with the new one. Present initial > update > later for chronological narration. Jumping backwards is a comparison with a different authored checkpoint, not real recovery history.

After a specialist fails, Earlier successful observation - outdated is available only if a prior successful result exists for the same household context, source and checkpoint. It retains its original timestamp and never supplies a current recommendation. Campbell initial > update crosses checkpoints, so that sequence does not show the initial observation inside the failed update's details.

```bash
READYRELIEF_PROGRESS_DB_PATH=.local/recovery-demo-session-01.sqlite3 \
  .venv/bin/python -m streamlit run app.py
```

Choose a new, unused filename for each clean rehearsal. This changes only the preview result store. Do not remove the existing database. Saved recovery case remains a separate source, with user-reported facts and unsupported availability, exact funding and timing left unknown.

### Claims to avoid

Capacity is a synthetic observation, not a reservation. Water supply does not prove drinking-water safety; an area report does not prove address restoration. Saved evidence does not prove insurer acceptance. Expected or approved payment is not received money, and received-but-unallocated money is not available stage allocation. A quote is not accepted, scheduled or completed work.

Source references: docs/RECOVERY_PROGRESS.md; ui/recovery_progress_page.py and ui/recovery_progress_components.py; recovery/progress/{fixtures,models,mcp_server,orchestrator,priorities}.py; recovery/progress/data/*.json. All scenario names and catalog labels in this guide are synthetic.

## Story index and presenter cues

Choose the exact household label in Household story. The ID is the scenario_id for MCP calls. Each story has initial, update and later. H / U / I / R on the following pages means Housing / Utilities / Insurance & funding / Rebuild.

| Household / ID | Theme | Presenter cue |
| --- | --- | --- |
| Rivera household / rivera | Housing before recovery administration | Possible housing matches do not establish an arrangement; saved preparation is separate from exact stage funding. |
| Chen household / chen | Repairs complete while reimbursement is pending | Repair completion, evidence readiness and payment receipt are separate facts. |
| Alvarez household / alvarez | Expected payment is not current allocation | Expected or approved payment cannot be added to funds currently allocated to a stage. |
| Baptiste household / baptiste | Accessible housing with continuing utilities | Accessibility fit is one constraint, and reported repair completion does not confirm payment receipt. |
| Morgan household / morgan | Uninsured does not mean no funding question | Insurance preparation and payments may be not applicable while household funding remains unknown. |
| Williams household / williams | Unconfirmed intake pauses routine checks | Unknown safety is not a successful recovery check; do not run the ordinary specialists at any checkpoint. |
| Santos household / santos | Eight people staying together | Capacity is counted in the site's units, and a suitable candidate does not reserve accommodation. |
| Patel household / patel | Pets, transport and a budget | A cheap option can still fail transport or pet requirements, and a fit does not imply a booking. |
| Okafor household / okafor | Accessibility across accommodation and repairs | Unknown accessibility needs confirmation; provider accessibility is assessed independently of housing. |
| Rodriguez household / rodriguez | Full capacity, available space, arranged stay | A capacity update can create an option while the housing signal remains red until arrangement is reported. |
| Thompson household / thompson | Area electricity versus address evidence | Area information cannot establish household service restoration. |
| Garcia household / garcia | Water supply versus drinking confirmation | Water supply, potability and home safety are different facts. |
| Lopez household / lopez | Explicit gas applicability | Gas becomes not applicable only after an explicit household report; no observation is not the same as no gas. |
| Nguyen household / nguyen | Conflicting utility observations | Conflicting current reports stay unknown until the contradictory observation is resolved in a new checkpoint. |
| Johnson household / johnson | Observation age and refresh | Stale candidate observations are not fresh availability, and refreshed availability still does not reserve a stay or work. |
| Martinez household / martinez | Uninsured household funding | No insurance does not remove the need for an explicit current allocation. |
| Singh household / singh | Approved, received, allocated | A received payment is not added to stage funds until explicitly allocated. |
| Robinson household / robinson | Consistent currency for exact funding | The demo does not infer exchange rates or silently convert currency. |
| Lewis household / lewis | Correct stage and spend once | Stage IDs must match, and spending reduces both remaining cost and allocation once. |
| Brown household / brown | A larger estimate is a real setback | New information can worsen a signal without reopening completed historical work. |
| Wilson household / wilson | Explicit evidence links | A saved file alone is not checklist evidence; requirement links and evidence status both matter. |
| Davis household / davis | Declined quote to new commitments | Declined providers, received quotes and work commitments are separate states; none proves completed work. |
| Fernandez household / fernandez | New danger pauses completed-work story | Completed repair history survives new danger; a later false danger flag is an authored assessment, not a safety clearance. |
| Campbell household / campbell | Partial tool failure and recovery | Failed tools yield unknown current signals and no stale actions; remaining recommendations disclose partial information. |

Expected states assume fixture baseline data with no dashboard interaction overrides. Insurance & funding is the combined card; sub-signals list preparation/funding/payment. Paused checkpoints produce no routine result or primary action. $ means USD; other currencies are labeled. Cost/allocation are authored totals; a gap requires current same-stage USD facts. Evidence counts summarize supplied records, not insurer verification.

## The 24 stories and their expected checkpoints

$ means USD; other currencies are labeled. Stage cost/allocation are the authored totals; exact gap uses current matching facts after recorded spend. Evidence counts summarize supplied records; only explicit requirement links drive readiness. Execution status is listed independently of signal color.

### 01. Rivera household (`rivera`)

**Theme:** Housing before recovery administration

4 people (2 adults, 2 children); Miami-Dade, Bay demo area. Housing budget unknown/night; accessibility no, pets yes, vehicle no. Contribution: Not sure.

**Presenter goal:** Start with displacement, pets and transport constraints, then move through service and funding needs.

**Key lesson:** Possible housing matches do not establish an arrangement; saved preparation is separate from exact stage funding.

**Recommended MCP tool:** `find_temporary_housing`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Red | Red | Yellow | Confirm a suitable place to stay |
| update | Green | Yellow | Red | Yellow | Confirm electricity and essential needs |
| later | Green | Green | Unknown | Yellow | Confirm funds for the next repair stage |

**initial - 2026-10-02:** Accommodation: needed. Evidence: 2 not collected. Stage gap: unknown. Stage cost / allocation: $2,000 / unknown.

Execution: all four checks complete. Insurance detail: prep Red; funds Unknown; payment Yellow.

Presenter: Accommodation and two services are unresolved. Housing leads the next actions.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 1 not collected, 1 saved. Stage gap: unknown. Stage cost / allocation: $2,000 / unknown.

Execution: all four checks complete. Insurance detail: prep Red; funds Unknown; payment Yellow.

Presenter: Accommodation is reported arranged, while electricity is partial and water is reported not potable.

Primary action key: `utilities:electricity`. Partial service reported

**later - 2026-10-23:** Accommodation: arranged. Evidence: 2 saved. Stage gap: unknown. Stage cost / allocation: $2,000 / unknown.

Execution: I needs information; remaining checks complete. Insurance detail: prep Green; funds Unknown; payment Yellow.

Presenter: Named utilities and preparation evidence are complete in the fictional record; exact allocation remains unknown.

Primary action key: `funding:confirm-next-stage`. Not enough information about funds available for the next stage; future reimbursement is not available cash.

### 02. Chen household (`chen`)

**Theme:** Repairs complete while reimbursement is pending

2 people (2 adults, 0 children); Miami-Dade, Bay demo area. Housing budget $150/night; accessibility no, pets no, vehicle yes. Contribution: $2,000-$4,999.

**Presenter goal:** Show paid repair costs, remaining preparation, and a reimbursement follow-up after reported completion.

**Key lesson:** Repair completion, evidence readiness and payment receipt are separate facts.

**Recommended MCP tool:** `assess_insurance_readiness`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Red | Yellow | Review missing preparation information |
| update | Green | Yellow | Red | Yellow | Confirm water and essential needs |
| later | Green | Green | Yellow | Green | Review pending insurance reimbursement |

**initial - 2026-10-02:** Accommodation: home. Evidence: 3 not collected. Stage gap: $0.00. Stage cost / allocation: $3,000 / $3,000. Spent: $1,000. Payment: expected $3,000.

Execution: all four checks complete. Insurance detail: prep Red; funds Green; payment Yellow.

Presenter: The household reports being home and exact funding covers the stage; missing evidence leads.

Primary action key: `insurance:prepare-evidence`. Some applicable preparation evidence is missing or unconfirmed

**update - 2026-10-09:** Accommodation: home. Evidence: 2 not collected, 1 saved. Stage gap: $0.00. Stage cost / allocation: $3,000 / $3,000. Spent: $2,500. Payment: expected $3,000.

Execution: all four checks complete. Insurance detail: prep Red; funds Green; payment Yellow.

Presenter: Water confirmation is now unresolved and takes priority over preparation.

Primary action key: `utilities:water`. Water available; drinking safety is not confirmed

**later - 2026-10-23:** Accommodation: home. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $3,000 / $3,000. Spent: $3,000. Payment: expected $3,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Yellow.

Presenter: Repairs and preparation are reported complete, but no received payment is recorded; reimbursement follow-up remains.

Primary action key: `insurance:follow-payment`. Reported repairs are complete; payment is still unresolved.

### 03. Alvarez household (`alvarez`)

**Theme:** Expected payment is not current allocation

5 people (2 adults, 3 children); Miami-Dade, Bay demo area. Housing budget $150/night; accessibility no, pets no, vehicle yes. Contribution: Under $500.

**Presenter goal:** Compare a large expected payment with a small explicit allocation and then a later allocation.

**Key lesson:** Expected or approved payment cannot be added to funds currently allocated to a stage.

**Recommended MCP tool:** `assess_funding_gap`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Red | Yellow | Confirm funds for the next repair stage |
| update | Green | Unknown | Red | Yellow | Confirm electricity and essential needs |
| later | Green | Green | Green | Yellow | Review a fictional repair provider |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 3 not collected. Stage gap: $6500.00. Stage cost / allocation: $7,000 / $500. Payment: expected $6,000.

Execution: all four checks complete. Insurance detail: prep Red; funds Red; payment Yellow.

Presenter: Accommodation and named utilities are met; the explicit stage funding gap leads.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 2 not collected, 1 saved. Stage gap: $6500.00. Stage cost / allocation: $7,000 / $500. Payment: expected $6,000, approved $6,000.

Execution: U needs information; remaining checks complete. Insurance detail: prep Red; funds Red; payment Yellow.

Presenter: Stale utility observations interrupt the funding story and require fresh address reports.

Primary action key: `utilities:electricity`. No fresh address-level report; area information cannot confirm restoration

**later - 2026-10-23:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $7,000 / $7,000. Payment: expected $6,000, approved $6,000, received $6,500.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The fictional record now has received and allocated funds. The expanded catalog still offers uncommitted contractor and roofer candidates; deterministic ordering puts contractor-12 first, while roof arrangements remain incomplete.

Primary action key: `rebuild:contractor-12`. Contractor: Availability listed in the fictional catalog; no appointment confirmed. Availability and affordability require confirmation.

### 04. Baptiste household (`baptiste`)

**Theme:** Accessible housing with continuing utilities

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $150/night; accessibility yes, pets no, vehicle yes. Contribution: $2,000-$4,999.

**Presenter goal:** Show that accommodation can be arranged while water and gas needs remain.

**Key lesson:** Accessibility fit is one constraint, and reported repair completion does not confirm payment receipt.

**Recommended MCP tool:** `find_temporary_housing`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Red | Red | Yellow | Confirm a suitable place to stay |
| update | Green | Yellow | Red | Yellow | Confirm water and essential needs |
| later | Green | Green | Unknown | Green | Review pending insurance reimbursement |

**initial - 2026-10-02:** Accommodation: needed. Evidence: 3 not collected. Stage gap: unknown. Stage cost / allocation: $2,000 / unknown.

Execution: all four checks complete. Insurance detail: prep Red; funds Unknown; payment Yellow.

Presenter: Accessible accommodation is needed, with water and gas interruptions reported.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 2 not collected, 1 saved. Stage gap: unknown. Stage cost / allocation: $2,000 / unknown.

Execution: all four checks complete. Insurance detail: prep Red; funds Unknown; payment Yellow.

Presenter: Accommodation is arranged but water drinking confirmation remains unresolved.

Primary action key: `utilities:water`. Water available; drinking safety is not confirmed

**later - 2026-10-23:** Accommodation: home. Evidence: 3 saved. Stage gap: unknown. Stage cost / allocation: $2,000 / unknown.

Execution: I needs information; remaining checks complete. Insurance detail: prep Green; funds Unknown; payment Yellow.

Presenter: Repairs are reported complete, while payment remains pending and exact stage funding is unknown.

Primary action key: `insurance:follow-payment`. Reported repairs are complete; payment is still unresolved.

### 05. Morgan household (`morgan`)

**Theme:** Uninsured does not mean no funding question

1 person (1 adult, 0 children); Miami-Dade, Bay demo area. Housing budget $150/night; accessibility no, pets no, vehicle yes. Contribution: Under $500.

**Presenter goal:** Follow an uninsured household from displacement to reported completion without inventing insurance activity.

**Key lesson:** Insurance preparation and payments may be not applicable while household funding remains unknown.

**Recommended MCP tool:** `assess_funding_gap`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Red | Unknown | Yellow | Confirm a suitable place to stay |
| update | Green | Yellow | Unknown | Yellow | Confirm water and essential needs |
| later | Green | Green | Unknown | Green | No next action |

**initial - 2026-10-02:** Accommodation: needed. Evidence: none linked. Stage gap: unknown. Stage cost / allocation: unknown / unknown.

Execution: I needs information; remaining checks complete. Insurance detail: prep Not Applicable; funds Unknown; payment Not Applicable.

Presenter: Housing and essential services lead; insurance preparation and payment are not applicable.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: arranged. Evidence: none linked. Stage gap: unknown. Stage cost / allocation: unknown / unknown.

Execution: I needs information; remaining checks complete. Insurance detail: prep Not Applicable; funds Unknown; payment Not Applicable.

Presenter: Accommodation is arranged; water confirmation and exact repair allocation remain unresolved.

Primary action key: `utilities:water`. Water available; drinking safety is not confirmed

**later - 2026-10-23:** Accommodation: home. Evidence: none linked. Stage gap: unknown. Stage cost / allocation: unknown / unknown.

Execution: I needs information; remaining checks complete. Insurance detail: prep Not Applicable; funds Unknown; payment Not Applicable.

Presenter: Home return and repairs are reported complete. The historical funding gap is still unknown, and no new routine action is generated.

### 06. Williams household (`williams`)

**Theme:** Unconfirmed intake pauses routine checks

Household size unconfirmed; Miami-Dade, Bay demo area. Housing budget unknown/night; accessibility unknown, pets unknown, vehicle unknown. Contribution: Not sure.

**Presenter goal:** Show that missing danger assessment prevents routine tool execution.

**Key lesson:** Unknown safety is not a successful recovery check; do not run the ordinary specialists at any checkpoint.

**Recommended MCP tool:** `find_temporary_housing`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Paused | Paused | Paused | Paused | Routine checks paused |
| update | Paused | Paused | Paused | Paused | Routine checks paused |
| later | Paused | Paused | Paused | Paused | Routine checks paused |

**initial - 2026-10-02:** Accommodation: unknown. Evidence: none linked. Stage cost / allocation: unknown / unknown.

Paused: no routine check or primary action is produced.

Presenter: Immediate danger has not been assessed. The routine preview remains paused; confirm safety before checking.

**update - 2026-10-09:** Accommodation: unknown. Evidence: none linked. Stage cost / allocation: unknown / unknown.

Paused: no routine check or primary action is produced.

Presenter: Safety is still unassessed. The authored rebuild-failure flag is not exercised because the safety gate comes first.

**later - 2026-10-23:** Accommodation: unknown. Evidence: none linked. Stage cost / allocation: unknown / unknown.

Paused: no routine check or primary action is produced.

Presenter: No new household or safety facts are supplied. Routine checks remain paused, without fresh signals or actions.

### 07. Santos household (`santos`)

**Theme:** Eight people staying together

8 people (3 adults, 5 children); Miami-Dade, Bay demo area. Housing budget $100/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Compare two hotel rooms with eight person-spaces and a household-together requirement.

**Key lesson:** Capacity is counted in the site's units, and a suitable candidate does not reserve accommodation.

**Recommended MCP tool:** `find_temporary_housing`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Green | Red | Yellow | Confirm a suitable place to stay |
| update | Red | Green | Red | Yellow | Confirm a suitable place to stay |
| later | Green | Green | Red | Yellow | Confirm funds for the next repair stage |

**initial - 2026-10-02:** Accommodation: needed. Evidence: 3 saved. Stage gap: $1500.00. Stage cost / allocation: $2,000 / $500. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: One family room or seven person-spaces cannot fit eight people; a site that splits the household is excluded.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: needed. Evidence: 3 saved. Stage gap: $1500.00. Stage cost / allocation: $2,000 / $500. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: Two rooms at four people each or enough person-spaces now fit. Accommodation is still explicitly needed.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $1500.00. Stage cost / allocation: $2,000 / $500. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: A separate fictional report says accommodation is arranged. The remaining stage funding gap becomes the next action.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

### 08. Patel household (`patel`)

**Theme:** Pets, transport and a budget

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $60/night; accessibility no, pets yes, vehicle no. Contribution: Not sure.

**Presenter goal:** Show why separate pet, transport and cost filters must all be satisfied.

**Key lesson:** A cheap option can still fail transport or pet requirements, and a fit does not imply a booking.

**Recommended MCP tool:** `find_temporary_housing`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Green | Red | Yellow | Confirm a suitable place to stay |
| update | Red | Green | Red | Yellow | Confirm a suitable place to stay |
| later | Green | Green | Red | Yellow | Confirm funds for the next repair stage |

**initial - 2026-10-02:** Accommodation: needed. Evidence: 3 saved. Stage gap: $1500.00. Stage cost / allocation: $2,000 / $500. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: The pet-excluding hotel, no-transport hotel and two-room cost above USD 60 are all excluded.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: needed. Evidence: 3 saved. Stage gap: $1500.00. Stage cost / allocation: $2,000 / $500. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: The selected hotel and community hall support pets and transport within the declared nightly budget, but no arrangement is reported.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $1500.00. Stage cost / allocation: $2,000 / $500. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: Accommodation is reported arranged; the household still needs to close a stage funding gap.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

### 09. Okafor household (`okafor`)

**Theme:** Accessibility across accommodation and repairs

2 people (2 adults, 0 children); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility yes, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Distinguish explicitly inaccessible options from unknown accessibility and supported alternatives.

**Key lesson:** Unknown accessibility needs confirmation; provider accessibility is assessed independently of housing.

**Recommended MCP tool:** `find_temporary_housing`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Green | Green | Unknown | Confirm a suitable place to stay |
| update | Red | Green | Green | Yellow | Confirm a suitable place to stay |
| later | Green | Green | Green | Yellow | Review a fictional repair provider |

**initial - 2026-10-02:** Accommodation: needed. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: R needs information; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The inaccessible hotel and contractor are excluded. Remaining candidates have unknown capacity or accessibility.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: needed. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Current accessible accommodation candidates and an accessible provider are supplied, but accommodation is still needed.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Accommodation is reported arranged. Review the accessible fictional contractor; listed availability is not a work commitment.

Primary action key: `rebuild:contractor-7`. Contractor: Availability listed in the fictional catalog; no appointment confirmed. Availability and affordability require confirmation.

### 10. Rodriguez household (`rodriguez`)

**Theme:** Full capacity, available space, arranged stay

4 people (2 adults, 2 children); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Show three distinct accommodation facts rather than treating vacancy as a reservation.

**Key lesson:** A capacity update can create an option while the housing signal remains red until arrangement is reported.

**Recommended MCP tool:** `find_temporary_housing`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Green | Green | Green | Confirm a suitable place to stay |
| update | Red | Green | Green | Green | Confirm a suitable place to stay |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: needed. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: All three selected sites have zero available spaces, so there are no matches.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: needed. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: One fictional shelter now reports six spaces for a four-person household; housing remains needed.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The household separately reports an arrangement. The authored checks generate no further routine action; this is not a home-safety clearance.

### 11. Thompson household (`thompson`)

**Theme:** Area electricity versus address evidence

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Move from area news to a partial address report and then reported availability.

**Key lesson:** Area information cannot establish household service restoration.

**Recommended MCP tool:** `check_utility_health`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Unknown | Green | Green | Confirm electricity and essential needs |
| update | Green | Yellow | Green | Green | Confirm electricity and essential needs |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: U needs information; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: A fresh area report says electricity is available, but the household address is unconfirmed.

Primary action key: `utilities:electricity`. No fresh address-level report; area information cannot confirm restoration

**update - 2026-10-09:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: A fresh fictional address report establishes only partial electricity service.

Primary action key: `utilities:electricity`. Partial service reported

**later - 2026-10-23:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The fictional address report now says available. It makes no claim about overall home safety.

### 12. Garcia household (`garcia`)

**Theme:** Water supply versus drinking confirmation

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Explain why running water can remain yellow until explicit potability is reported.

**Key lesson:** Water supply, potability and home safety are different facts.

**Recommended MCP tool:** `check_utility_health`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Red | Green | Green | Confirm water and essential needs |
| update | Green | Yellow | Green | Green | Confirm water and essential needs |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Water supply is interrupted; the water action leads.

Primary action key: `utilities:water`. Address-level interruption reported

**update - 2026-10-09:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Water is available, but potability is not confirmed, so the service remains yellow.

Primary action key: `utilities:water`. Water available; drinking safety is not confirmed

**later - 2026-10-23:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The new fictional address report explicitly says potable. This is a synthetic report, not drinking-water advice or verification.

### 13. Lopez household (`lopez`)

**Theme:** Explicit gas applicability

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Show that an area gas outage cannot establish whether this household uses gas.

**Key lesson:** Gas becomes not applicable only after an explicit household report; no observation is not the same as no gas.

**Recommended MCP tool:** `check_utility_health`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Unknown | Green | Green | Confirm gas and essential needs |
| update | Green | Unknown | Green | Green | Confirm gas and essential needs |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: U needs information; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Gas use and service are unknown, so an address-level confirmation action remains.

Primary action key: `utilities:gas`. Service is unconfirmed

**update - 2026-10-09:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: U needs information; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The area outage report does not establish household gas use or address service. The gas item stays unknown.

Primary action key: `utilities:gas`. No fresh address-level report; area information cannot confirm restoration

**later - 2026-10-23:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The household explicitly reports no gas use. Gas is not applicable, while electricity and water remain green.

### 14. Nguyen household (`nguyen`)

**Theme:** Conflicting utility observations

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Resolve electricity conflict first while preserving the separate water-potability conflict.

**Key lesson:** Conflicting current reports stay unknown until the contradictory observation is resolved in a new checkpoint.

**Recommended MCP tool:** `check_utility_health`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Unknown | Green | Green | Confirm electricity and essential needs |
| update | Green | Unknown | Green | Green | Confirm water and essential needs |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: U needs information; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Fresh address reports conflict on electricity status and water potability; electricity sorts first among unresolved utilities.

Primary action key: `utilities:electricity`. Conflicting reports; restoration is unconfirmed

**update - 2026-10-09:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: U needs information; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Electricity reports now agree, but water potability still conflicts, so water becomes the lead action.

Primary action key: `utilities:water`. Conflicting reports; restoration is unconfirmed

**later - 2026-10-23:** Accommodation: arranged. Evidence: 2 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The new checkpoint supplies consistent current address observations for each service.

### 15. Johnson household (`johnson`)

**Theme:** Observation age and refresh

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Compare stale housing and provider observations with a fresh authored update.

**Key lesson:** Stale candidate observations are not fresh availability, and refreshed availability still does not reserve a stay or work.

**Recommended MCP tool:** `search_repair_providers`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Red | Green | Green | Unknown | Confirm a suitable place to stay |
| update | Red | Green | Green | Yellow | Confirm a suitable place to stay |
| later | Green | Green | Green | Yellow | Review the simulated quote |

**initial - 2026-10-02:** Accommodation: needed. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: R needs information; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The selected catalogs are 72 hours old with 24-hour validity. Housing candidates and provider observations are unknown.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**update - 2026-10-09:** Accommodation: needed. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Both catalogs are refreshed. Accommodation is still needed and one fictional roofer is waiting.

Primary action key: `housing:confirm-accommodation`. Current accommodation is not confirmed. Availability and suitability require confirmation.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Accommodation is reported arranged; a contractor quote and a roofer awaiting reply remain distinct from work commitments.

Primary action key: `rebuild:contractor-6`. Contractor: Quote received; not accepted or scheduled. Availability and affordability require confirmation.

### 16. Martinez household (`martinez`)

**Theme:** Uninsured household funding

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Track a concrete stage gap without an insurance preparation or payment track.

**Key lesson:** No insurance does not remove the need for an explicit current allocation.

**Recommended MCP tool:** `assess_funding_gap`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Red | Yellow | Confirm funds for the next repair stage |
| update | Green | Green | Red | Yellow | Confirm funds for the next repair stage |
| later | Green | Green | Green | Yellow | Follow up on the simulated provider response |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: none linked. Stage gap: $3000.00. Stage cost / allocation: $3,500 / $500.

Execution: all four checks complete. Insurance detail: prep Not Applicable; funds Red; payment Not Applicable.

Presenter: The USD 3,500 stage has USD 500 explicitly allocated: a USD 3,000 gap. Insurance preparation and payment are not applicable.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

**update - 2026-10-09:** Accommodation: arranged. Evidence: none linked. Stage gap: $2000.00. Stage cost / allocation: $3,500 / $1,500.

Execution: all four checks complete. Insurance detail: prep Not Applicable; funds Red; payment Not Applicable.

Presenter: The allocation rises to USD 1,500, leaving a USD 2,000 gap even though a quote is received.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

**later - 2026-10-23:** Accommodation: arranged. Evidence: none linked. Stage gap: $0.00. Stage cost / allocation: $3,500 / $3,500.

Execution: all four checks complete. Insurance detail: prep Not Applicable; funds Green; payment Not Applicable.

Presenter: The explicit allocation covers USD 3,500. The accepted fictional quote still needs a work commitment.

Primary action key: `rebuild:plumber-6`. Plumber: Quote accepted in the simulation; work not yet committed. Availability and affordability require confirmation.

### 17. Singh household (`singh`)

**Theme:** Approved, received, allocated

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Display payment receipt independently from available repair-stage allocation.

**Key lesson:** A received payment is not added to stage funds until explicitly allocated.

**Recommended MCP tool:** `assess_funding_gap`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Red | Yellow | Confirm funds for the next repair stage |
| update | Green | Green | Red | Yellow | Confirm funds for the next repair stage |
| later | Green | Green | Green | Yellow | Review the simulated quote |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $4000.00. Stage cost / allocation: $5,000 / $1,000. Payment: approved $4,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Yellow.

Presenter: A fictional USD 4,000 payment is approved but not received. Only USD 1,000 is allocated to a USD 5,000 stage.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $4000.00. Stage cost / allocation: $5,000 / $1,000. Payment: approved $4,000, received $4,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: The payment is recorded received, yet the allocation remains USD 1,000 and the USD 4,000 gap remains.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $5,000 / $5,000. Payment: approved $4,000, received $4,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: USD 5,000 is now explicitly allocated. The received payment is not counted again; the quote still needs follow-up.

Primary action key: `rebuild:electrician-6`. Electrician: Quote received; not accepted or scheduled. Availability and affordability require confirmation.

### 18. Robinson household (`robinson`)

**Theme:** Consistent currency for exact funding

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Demonstrate that mismatched currency in allocation or spend prevents an exact USD answer.

**Key lesson:** The demo does not infer exchange rates or silently convert currency.

**Recommended MCP tool:** `assess_funding_gap`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Unknown | Yellow | Confirm funds for the next repair stage |
| update | Green | Green | Unknown | Yellow | Confirm funds for the next repair stage |
| later | Green | Green | Green | Yellow | Review the simulated quote |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 4 saved. Stage gap: unknown. Stage cost / allocation: $3,000 / EUR 3,000. Payment: received $2,000.

Execution: I needs information; remaining checks complete. Insurance detail: prep Green; funds Unknown; payment Green.

Presenter: The stage cost is USD 3,000, but the allocation is EUR 3,000. Exact stage funding is unknown.

Primary action key: `funding:confirm-next-stage`. Not enough information about funds available for the next stage; future reimbursement is not available cash.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 4 saved. Stage gap: unknown. Stage cost / allocation: $3,000 / $3,000. Spent: EUR 500. Payment: received $2,000.

Execution: I needs information; remaining checks complete. Insurance detail: prep Green; funds Unknown; payment Green.

Presenter: Cost and allocation are USD, but the spend record remains EUR 500, so the answer is still unknown.

Primary action key: `funding:confirm-next-stage`. Not enough information about funds available for the next stage; future reimbursement is not available cash.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $3,000 / $3,000. Spent: $500. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: All three records now use USD. After USD 500 spend, USD 2,500 cost and allocation remain, with no exact gap.

Primary action key: `rebuild:plumber-7`. Plumber: Quote received; not accepted or scheduled. Availability and affordability require confirmation.

### 19. Lewis household (`lewis`)

**Theme:** Correct stage and spend once

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Show an allocation to the wrong stage, then correct it and record partial spending.

**Key lesson:** Stage IDs must match, and spending reduces both remaining cost and allocation once.

**Recommended MCP tool:** `assess_funding_gap`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Unknown | Yellow | Confirm funds for the next repair stage |
| update | Green | Green | Green | Yellow | Review the simulated quote |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 4 saved. Stage gap: unknown. Stage cost / allocation: $3,000 / $3,000. Payment: received $2,000.

Execution: I needs information; remaining checks complete. Insurance detail: prep Green; funds Unknown; payment Green.

Presenter: The USD 3,000 allocation belongs to roof-stabilization, while the current stage is essential-repairs, so funding is unknown.

Primary action key: `funding:confirm-next-stage`. Not enough information about funds available for the next stage; future reimbursement is not available cash.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $3,000 / $3,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The explicit allocation is corrected to the current stage; the fictional quote is still awaiting commitment.

Primary action key: `rebuild:roofer-7`. Roofer: Quote received; not accepted or scheduled. Availability and affordability require confirmation.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $3,000 / $3,000. Spent: $1,200. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: USD 1,200 spending leaves USD 1,800 cost and USD 1,800 allocation. Work is committed in the simulation, not marked complete.

### 20. Brown household (`brown`)

**Theme:** A larger estimate is a real setback

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Keep completed cleanup visible while a roof-stage cost increase creates a renewed funding gap.

**Key lesson:** New information can worsen a signal without reopening completed historical work.

**Recommended MCP tool:** `assess_funding_gap`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Green | Yellow | Review the simulated quote |
| update | Green | Green | Red | Yellow | Confirm funds for the next repair stage |
| later | Green | Green | Red | Yellow | Confirm funds for the next repair stage |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: USD 2,000 allocation covers the original roof-stage estimate. Completed cleanup remains recorded.

Primary action key: `rebuild:roofer-9`. Roofer: Quote received; not accepted or scheduled. Availability and affordability require confirmation.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $3500.00. Stage cost / allocation: $5,500 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: The estimate rises to USD 5,500 while allocation stays USD 2,000. The USD 3,500 gap takes priority.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $3000.00. Stage cost / allocation: $5,500 / $2,500. Spent: $1,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Red; payment Green.

Presenter: An allocation of USD 2,500 and spend of USD 1,000 still leave a USD 3,000 gap. The story intentionally ends unresolved.

Primary action key: `funding:confirm-next-stage`. A funding gap blocks the next stage; future reimbursement is not available cash.

### 21. Wilson household (`wilson`)

**Theme:** Explicit evidence links

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Follow a saved but unlinked photo, a linked reported-available record, and finally linked saved evidence.

**Key lesson:** A saved file alone is not checklist evidence; requirement links and evidence status both matter.

**Recommended MCP tool:** `assess_insurance_readiness`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Red | Green | Review missing preparation information |
| update | Green | Green | Yellow | Green | Review missing preparation information |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Red; funds Green; payment Green.

Presenter: The photo record is saved but has no requirement link. The selected fictional photo requirement remains red.

Primary action key: `insurance:prepare-evidence`. Some applicable preparation evidence is missing or unconfirmed

**update - 2026-10-09:** Accommodation: arranged. Evidence: 1 reported available, 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Yellow; funds Green; payment Green.

Presenter: The photo requirement is linked to reported-available evidence, which is yellow rather than saved.

Primary action key: `insurance:prepare-evidence`. Some applicable preparation evidence is missing or unconfirmed

**later - 2026-10-23:** Accommodation: arranged. Evidence: 4 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The linked photo evidence is now saved. Preparation is green without asserting insurer acceptance or coverage.

### 22. Davis household (`davis`)

**Theme:** Declined quote to new commitments

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Retain a declined provider while comparing new quotes for two needed trades.

**Key lesson:** Declined providers, received quotes and work commitments are separate states; none proves completed work.

**Recommended MCP tool:** `search_repair_providers`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Green | Yellow | Follow up on the simulated provider response |
| update | Green | Green | Green | Yellow | Review the simulated quote |
| later | Green | Green | Green | Green | No next action |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The old contractor is declined and excluded from actions. New contractor and roofer responses are still awaited.

Primary action key: `rebuild:contractor-9`. Contractor: Awaiting a simulated reply. Availability and affordability require confirmation.

**update - 2026-10-09:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Both new providers supply fictional quotes. Neither quote is accepted or committed merely by appearing.

Primary action key: `rebuild:contractor-9`. Contractor: Quote received; not accepted or scheduled. Availability and affordability require confirmation.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Both needed trades have fictional work commitments. Repairs remain explicitly incomplete.

### 23. Fernandez household (`fernandez`)

**Theme:** New danger pauses completed-work story

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Demonstrate the safety gate after a previously successful checkpoint, then resume only at a newly assessed checkpoint.

**Key lesson:** Completed repair history survives new danger; a later false danger flag is an authored assessment, not a safety clearance.

**Recommended MCP tool:** `check_utility_health`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Green | Green | Green | No next action |
| update | Paused | Paused | Paused | Paused | Routine checks paused |
| later | Green | Yellow | Green | Green | Confirm electricity and essential needs |

**initial - 2026-10-02:** Accommodation: home. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Original repairs and home return are reported complete in the fictional record; no new routine action is generated.

**update - 2026-10-09:** Accommodation: needed. Evidence: 3 saved. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Paused: no routine check or primary action is produced.

Presenter: New immediate danger is true. Do not run ordinary tools or show fresh specialist results; routine actions are absent.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: A new fictional checkpoint explicitly assesses immediate danger as false. Accommodation is arranged, electricity remains partial, and the completed original repair history stays complete.

Primary action key: `utilities:electricity`. Partial service reported

### 24. Campbell household (`campbell`)

**Theme:** Partial tool failure and recovery

3 people (2 adults, 1 child); Miami-Dade, Bay demo area. Housing budget $120/night; accessibility no, pets no, vehicle yes. Contribution: Not sure.

**Presenter goal:** Contrast a successful check, a failed utility tool and a fresh retry while provider work remains pending.

**Key lesson:** Failed tools yield unknown current signals and no stale actions; remaining recommendations disclose partial information.

**Recommended MCP tool:** `check_utility_health`

| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |
| --- | --- | --- | --- | --- | --- |
| initial | Green | Yellow | Green | Yellow | Confirm water and essential needs |
| update | Green | Unknown | Green | Yellow | Review the simulated quote |
| later | Green | Green | Green | Yellow | Review the simulated quote |

**initial - 2026-10-02:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: Water potability is unconfirmed and leads; the pool-specialist quote remains pending.

Primary action key: `utilities:water`. Water available; drinking safety is not confirmed

**update - 2026-10-09:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: U failed; remaining checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The utility tool is deliberately unavailable. Its current signal is unknown and execution failed; the provider action must disclose the partial check.

Primary action key: `rebuild:pool-specialist-6`. Pool specialist: Quote received; not accepted or scheduled. Availability and affordability require confirmation. Partial check: utilities could not be checked; recommendation uses the remaining information.

**later - 2026-10-23:** Accommodation: arranged. Evidence: 3 saved. Stage gap: $0.00. Stage cost / allocation: $2,000 / $2,000. Payment: received $2,000.

Execution: all four checks complete. Insurance detail: prep Green; funds Green; payment Green.

Presenter: The utility tool succeeds with a fresh fictional potable-water report. The unresolved provider quote remains the next action.

Primary action key: `rebuild:pool-specialist-6`. Pool specialist: Quote received; not accepted or scheduled. Availability and affordability require confirmation.
