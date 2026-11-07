# Recovery Progress design

Status: approved for implementation, including the later LangGraph and MCP decisions.
Baseline: `Recovery-Progress`, `be0b99adbe2bb9ffe6e97716f59649db86fcce85`.

## Intent and agreed experience

Help a household understand what changed, what is holding up recovery, and the next manageable action. The approved visual direction is one next-action panel, four specialist cards with detail views, elapsed recovery time, and understandable milestones. Preserve the current Recovery workflows.

User decisions from the design conversation:

- Make Recovery Progress directly visible in navigation, grouped under Recover. Keep Recover's current destination during preview.
- Show saved results on entry. Run checks only after **Refresh checks**. Show the coordinator and each specialist visibly working before completion.
- Housing matching considers household size, location, accessibility, pets, budget and transport when known; missing optional facts remain unknown.
- Track **Home & daily life** and **Costs & funding** together. Insurance timing affects recovery through available funding; completed repairs and a settled claim are different milestones.
- Broaden the visible Recovery Blocker card to **Insurance & funding**. Keep Recovery Blocker as its internal specialist name if useful.
- Ask an optional recovery contribution question with broad ranges, Not sure and Prefer not to say. Do not require financial details.
- Illustrative timing ranges are allowed only for synthetic households. Other cases display **Not enough information** until a defensible estimate exists.
- Begin with fictional repair providers, responses and quotes. Add user-recorded real contacts later. Actual sending requires a later, explicitly confirmed action.
- Miami-Dade is the initial geography. Preserve county/provider identifiers so expansion does not require rewriting specialist logic.

## Approaches and scope

The conversation considered a separate top-level destination, a button hidden inside Recovery, and visible children grouped under Recover. The selected navigation is the third option: discovery without creating competing recovery products.

Implementation approach: an isolated preview screen and read-only specialist projections over shared case data. Replacing the existing dashboard immediately would risk established workflows; a disconnected permanent duplicate would create conflicting task and evidence records. The preview will use separate result storage, then connect through a consistent read-only case snapshot.

Build in three independently reviewable increments:

1. **Synthetic preview:** new screen, four specialists, coordinator, next action, two-track milestones, details, manual refresh animation and persistent fictional snapshots. Three featured stories, plus three edge-case stories, all selectable. No service network requests and no changes to existing case records.
2. **Saved-case integration:** optional confirmed profile fields on the Recovery home/workspace, consistent case reads, reuse of actual saved evidence metadata, and local dashboard observations. Cases without integration data return unknown. The repository is currently a local fictional-data prototype; this increment does not authorize real personal-data use or production hosting.
3. **External integrations:** establish supported electricity/provider access, then independently review live housing/provider sources and user-recorded contacts. No real outreach, booking, submission or money movement in the first two increments.

Approved architecture refinement: retain Python/Streamlit/Pydantic/SQLite, add LangGraph to orchestrate the specialist workflow and the official MCP Python SDK for one local stdio Recovery server. Domain-specific read-only tools call the same deterministic specialist functions as the app. No vector database or paid search service is needed for the preview. The system demonstrates actual graph orchestration and MCP request/response calls; it must not claim LLM analysis or live verification when none occurs. AI explanations can be evaluated separately later.

## Existing functionality and reuse

| Existing component | Use in Recovery Progress | Deprecation decision |
|---|---|---|
| `ui/recovery_page.py` and CAP06–09 | Existing assessment, plan review, task updates and reassessment remain the editing flows | Keep |
| `recovery/task_view.py:current_task_views()` | Effective reviewed priorities and applicability for next-action candidates | Reuse; no second task-status store |
| `ui/insurance_workspace.py` | Existing inventory, JPEG/PNG attachments, evidence, communication log and exports | Keep; detail actions link here |
| `recovery/insurance_exports.py:missing_information()` | General preparation omissions, distinct from a selected insurer checklist | Reuse as a general signal, not as insurer approval logic |
| Existing task/plan/journey history | Show accepted history in details and use it for later activity integration | Keep; consolidate presentation only after preview validation |
| Recovery onboarding ribbon | Existing creation/review navigation | Keep initially; later omit from the returning-user overview |
| `recovery/ui.py` | Separate developer-preview compatibility surface | Do not replace or make it the integrated app entry |

There is no structured ZIP/full home address in the current case. Household total exists only in session preferences; Recovery separately persists optional adults and children. Gas is not a first-class capture field. Insurance already has real saved image attachments, but no PDF ingestion or document-content analysis. These are actual gaps, not features to claim are present.

## Navigation and presentation

Use one navigation descriptor shared by desktop, mobile and search. Canonical route `Recover` retains its existing behavior. Add canonical route `Recovery Progress` with visible label `Recovery Progress · Preview` under Recover. The group also exposes `My Recovery Plan` and `Insurance & Documents` as destinations into existing Recover focus values, not new duplicate pages.

Preserve `open recovery` and `tasks` → Recover. Explicit `recovery progress` and `dashboard` → Recovery Progress. Preserve the assistant's existing rule that questions and mixed commands do not auto-navigate. Visiting preview alone must not change `rr_focus`, selected case, task statuses, records or plan approval.

The screen order is:

1. Existing global emergency controls, rendered before optional page imports/I/O.
2. Title, household context, explicit synthetic/source label, Refresh checks and timestamps.
3. Elapsed days and two milestone tracks. Use a confirmed recovery-start date; otherwise label case age accurately or show start date unknown. Synthetic time follows the selected story date, not the machine clock.
4. What changed since the previous comparable snapshot, followed by one next action and at most two secondary actions.
5. Temporary housing; Utility health checker; Insurance & funding; Rebuild my life.
6. Compact legend and access to existing plan/evidence/history.

Each View details shows: state, why, contributing facts, relevant missing facts, source/provenance, observation time, scope, next step and any dependency. Use native accessible expandable regions or a detail section with focus management, not a new modal framework. Escape all user/provider text. Keyboard access, small-screen layout, Bright/Dark themes and reduced motion are required.

## State semantics

Execution states are separate from household/service states:

- Execution: Queued → Checking → Complete, Needs information, Couldn't update, or Cancelled.
- Domain: red = action/blocker/outage; yellow = partial or in progress; green = the specifically named condition is met; gray = unknown/stale. Not applicable has a distinct neutral label and is excluded from denominators.
- A successful check may return red. A timeout never returns green. No single global color certifies that a home is safe or a family has recovered.

Refreshing captures an immutable input fingerprint and emergency epoch. Housing starts first; other specialists may run concurrently after its dispatch. Next Best Action waits for all specialist terminal results and can produce an explicitly partial recommendation if one fails. Workers never call Streamlit or modify case records. Bound execution, support cancellation, prevent duplicate submissions, and reject late results after case/mode/checkpoint/profile/emergency changes.

Use actual lifecycle events for animation. A synthetic adapter may model short, explicitly simulated response times; do not add fake waiting to live results or call elapsed animation a real service check. Retain a readable run summary after completion. Reduced motion replaces animation with text/icon updates.

Loading the page, returning to it, opening details and refreshing the browser do not start a check. Keep last successful observation times distinct from last-attempt/run-finished times. After a failed refresh retain earlier observations as historical/stale; do not stamp them as newly verified. Changed input context invalidates their applicability even when retained for history.

## Specialist rules

### Temporary housing

Represent hotel room inventory and person-space inventory separately. Hotel matching needs room occupancy, units required, available rooms and whether the allocation keeps the household together. A church/school is listed only as an explicitly activated fictional accommodation location. Each listing has source mode, observation time, availability validity and match reasons.

Known unmet accessibility/pet requirements exclude a match. Unknown requirements or unknown capacity make suitability uncertain, not guaranteed. Use declared housing nightly budget separately from repair funds. Missing ZIP/address/total yields a helpful information request without blocking access to categories. Synthetic fixture geography supplies distances; never claim a geocoded route or real travel time from it. No booking or guaranteed capacity.

### Utility health checker

Electricity, water and gas each carry status, provider, geography/scope, source, observation time and applicability. An area outage cannot establish a specific address's service. Household-reported values remain user-reported. Conflicting or stale evidence yields uncertainty and retains both explanations. Water pressure/availability does not establish potability. Gas can be Not applicable.

The first release uses synthetic observations. FPL's official map accepts address/ZIP searches for area information, but explicitly does not expose specific street-address outage status: https://www.fpl.com/storm/map-faq.html . A supported address-level flow/API must be established before promising automatic verification. No bypassing authentication or inferring restoration from an empty map.

### Insurance & funding / Recovery Blocker

Show two sub-statuses: **Preparation** and **Funding for the next stage**. Green preparation means the selected fictional checklist's applicable items have matching evidence, not accepted claim/coverage/approval. A saved image is not automatically sufficient for an arbitrary requirement; use explicit requirement-to-evidence links. Unavailable, not collected, reported available, saved, unknown and not applicable stay distinct.

Use neutral fictional profiles Sample A–D. Actual insurer names never automatically map to these rules. Without a selected verified checklist, saved cases show general preparation omissions and checklist suitability unknown. No claim-document content interpretation or policy decisions in this increment.

Model costs and cash separately. Next-stage estimated cost, quote, household allocation, insurer decision, promised/approved payment, received money, spent money and remaining available allocation are different facts. Expected reimbursement and approved-but-unpaid amounts are not cash available. A receipt supports an incurred-cost record, not reimbursement certainty. Never double-count funds between allocations, paid costs or stages.

For contribution bands use: None available, Under $500, $500–$1,999, $2,000–$4,999, $5,000 or more, Not sure, Prefer not to say. These are proposed UI choices, not financial guidance. No exact gap is calculated from a band. An optional exact user-declared allocation and exact next-stage cost in USD can produce `max(0, cost - available allocation)` when both refer to the same stage and current context. Missing/stale/mixed-currency facts produce no exact gap. Label all saved-case amounts user-reported. Housing budget is a separate input.

No-insurance households have an applicable funding track and an insurance track marked Not applicable. Pending reimbursement may remain visible after repairs are complete. Do not encourage spending or borrowing on an assumed future payout.

### Rebuild my life

Categories: Electrician, Contractor, Plumber, Roofer, Pool specialist. Synthetic provider cards include trade, fictional service area, review count/rating when supplied, availability, source and any match constraints. Unknown ratings are unrated, not zero stars. Do not represent fictional contact information as a real destination.

Track shortlisted, enquiry recorded, awaiting reply, declined, quote received, quote accepted and work commitment as separate states. A quote does not imply acceptance or scheduled work. Preview controls explicitly simulate actions and write only preview state. Real user-recorded contact tracking is a later increment; sending messages is outside current scope.

### Next Best Action

Use an explainable deterministic ranking over specialist findings and the existing reviewed task projection. Priority order: emergency interruption first; current accommodation/essential needs; blockers to the next feasible step (including funding/evidence); feasible repairs/follow-up; ordinary maintenance. Safety interruption suppresses routine recommendations. Do not use a universal numeric score that can let a cheap repair outrank a critical need.

Deduplicate by existing task ID or stable action key. Exclude completed/non-applicable tasks. Never reopen completed work, approve a plan, reserve a place, accept a quote or change a case during ranking. Show the facts, dependency and freshness behind the selected action. Unknown affordability is not assumed affordability or a zero-dollar budget. Mixed partial results disclose which specialist could not be checked.

## Milestones, time and synthetic scenarios

Home and funding milestones can progress in parallel or have setbacks; avoid a universal recovery percentage. User-reported completion remains a report, and returning home is not inferred solely from restored utilities or paid bills. Insurance decision and receipt of funds are separate events. Estimated repair timing is conditional on scope, resources and funding; it is never a promise of approval/reimbursement.

Use three featured stories and three additional scenarios, each with three explicit checkpoints:

| Story | Focus |
|---|---|
| Rivera, 4 people | Displaced; pets/transport constraints; housing first; contribution unknown |
| Chen, 2 people | Some repairs paid upfront; reimbursement unresolved after home progress |
| Alvarez, 5 people | Next repair stage waiting on funding; expected payment is excluded from available money |
| Baptiste, 3 people | Accessibility matching; accommodation becomes arranged; paperwork remains |
| Morgan, 1 person | No insurance; funding and recovery still useful |
| Williams, total unconfirmed | Incomplete saved-case-shaped input; unknown address/total/budget; no invented defaults |

Fixture minimums: 12 accommodation sites (3 per category); 15 repair providers (3 per trade); 4 checklist profiles (basic preparation, itemized evidence, incurred-cost preparation, proposed-work preparation); utilities for every checkpoint plus stale/conflict/failure/gas-not-applicable overrides. Profiles vary required evidence, not promised insurer generosity. All addresses, people, capacities, reviews, prices, responses and timing are fictional. Do not use real contact endpoints in demo actions.

Checkpoints are authored stories, not independent outcome observations or a forecasting training set. Refresh never advances story time by itself. Selecting a new checkpoint changes inputs and labels previous results outdated until refreshed. Comparison never crosses households or synthetic/saved-case modes. Simulated user interaction overrides are scoped to the selected household and checkpoint; a later quote must never appear when replaying an earlier checkpoint.

## Saved-case data and storage boundaries

Preview uses its own local SQLite store for run summaries and simulated interaction state. It must not create or edit a real Recovery case simply to show a scenario. Never put databases, addresses, financial inputs or attachment bytes in Git.

Saved-case integration adds one versioned optional progress profile associated with the existing case: confirmed total, ZIP, structured address, recovery start date, accessibility/pets/transport needs, housing budget, repair contribution and gas applicability/report. Existing adults/children, intake, insurance and task records remain authoritative for their fields. A known adults+children sum can suggest a total for confirmation; one known count cannot establish a total. Session defaults never become confirmed Recovery facts silently. Updates affecting the accepted plan go through existing reassessment approval.

Scope decision after builder review: stage costs, exact allocations and insurer decision/payment events exist as explicit synthetic fixture facts in the first increment. The saved-case increment captures contribution bands but does not add a financial ledger or infer allocations/payments from inventory estimates or communication notes. Its exact stage funding gap and unsupported financial milestones remain unknown. A later, separately reviewed funding-record editor can capture stage scope/cost, allocations and user-reported decision/received/spent events with confirmation and correction history. This keeps the first saved-case integration read-only apart from the optional profile.

Add an atomic repository read that supplies case, records, active plan, insurance evidence metadata, journey events and profile version. Do not load photo bytes into each animation tick or expose policy/claim references to specialist outputs. Snapshots bind source mode, scenario/case identity, selected checkpoint, input versions, run ID and emergency epoch. Case/profile changes make old observations historical; detailed views must not mix households.

A new input/agent result never automatically mutates the existing accepted plan or historical task state. Users follow existing editors to make confirmed changes. A later live adapter must explicitly disclose when an address will be sent to a named provider; no generic search queries containing full addresses, financial details or policy references.

## Release checks and what is deferred

Each increment must preserve existing assessment, acceptance, persistence, reassessment, insurance and emergency regression coverage. Add focused checks for demo/saved-case isolation, stale/cancelled results, financial bounds, no-insurance paths, capacity units and navigation aliases. Browser acceptance includes phone-link inspection without dialing, refreshed results, detail navigation, reduced motion, mobile and both themes. CI's visual baseline platform is Windows; macOS rendering must not blindly replace those baselines.

No features are deprecated in this project. Future candidates are presentation-only: make Progress the returning-user Recover landing; consolidate redundant history navigation; remove the creation ribbon from that landing. Preserve the underlying tasks, evidence, exports and audit history.

Deferred: actual provider messages/bookings/submissions, live shelter capacity claims, automatic dispatch, real insurer decisions, document AI/OCR/PDF intake, credit/loan recommendations, validated duration forecasting, production authentication/privacy work, and expansion beyond Miami-Dade. These are separate increments, not silently included capabilities.
