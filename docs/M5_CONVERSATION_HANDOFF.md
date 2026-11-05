# M5 conversational extraction integration

M1's corrected extractor (`677e92a`) arrived through main `1653ae6` in local merge `e2f6327`.

## Explicit real extraction

In Recover, select **Use Qwen to propose details for my review** and submit the description.
Unchecked input retains local section navigation without a model call. The existing M1
`services.assistant.extract_recovery_needs()` uses the shared `NebiusClient`, with two
bounded requests (extraction and support/ambiguity review). No second client is introduced.

`ui.recovery_page.request_extraction()` retains the case, confirmed records/version and
active plan before calling M1. It builds `RecoveryConfirmedContext` from M5's
`confirmed_context()`, then delivers the result plus ORIGINAL snapshots to
`stage_extraction_result()`. Delivery and confirmation reject stale saved context.
No extraction call or ordinary rerender writes household facts or approves tasks.

Both UI and consumer use the corrected shared deterministic danger precheck. Pending
danger is checked before and after generation and before writes; persisted danger remains
authoritative. A hypothetical danger question is not a current danger report. Failure,
invalid output or unavailable credentials leave structured input accessible. Rejected
proposals and raw descriptions are not saved to SQLite.

Credentials use `NEBIUS_API_KEY` (never displayed); model selection follows
`NEBIUS_CHAT_MODEL`, then `NEBIUS_MODEL`, then M1's default. Use fictional information only.

Complete visual browser acceptance remains outstanding: native capture timed out and
installed browser automation was unavailable. Automated Streamlit tests are not screenshots.
Manual check: launch `..\.venv\Scripts\python.exe -m streamlit run app.py`, open Recover,
select Qwen, submit a fictional description, review quotes, edit and confirm selected facts
with an explicit safety answer. Approve the initial plan, complete a task, reopen the case,
then propose electricity restoration and refrigerator damage; approve its reassessment and
verify prior progress, damage and insurance draft. Never activate emergency call links.

## Mapping and limits

- Disaster and housing use existing intake text fields.
- Available/Unavailable electricity and water map explicitly to true/false under
  utility_availability. Availability does not establish safety or potability.
- temporary_accommodation maps to temporary_accommodation_status, preserving the
  supported literal. Legacy Staying in temporary lodging maps explicitly to M1's
  Temporary lodging. Other unsupported descriptions stay unresolved and preserved.
- Recovery needs are additive. Unsupported saved needs are never removed.
- children/adults map directly to existing household fields. Session members,
  pronouns and child counts never supply an inferred adult or total count.
- insurance_preparation_requested maps to household.wants_insurance_help.
- New damage appends case-bound M5 IDs. Supporting quotes become confirmed damage
  descriptions. Existing IDs stay intact; normalized case/whitespace duplicates
  are skipped. Multiple identical items require structured editing.
- County is a nullable Miami-Dade literal in RecoveryRecords.reported_county.
  User confirmation is required; no city setting supplies it. Other counties stay
  unresolved. The existing household-details form also supports county selection.

County is an additive JSON property in the existing recovery_records table. No
SQL migration or new table is needed. Old JSON loads with county null and reads
never rewrite records. Intake remains authoritative for housing, utilities and danger.

M1 accepts at most 50 damage names of 120 characters, counts 0-100 and a fixed
vocabulary. Unsupported saved values are flagged and preserved in full M5 snapshots.
Damage exceeding context limits uses structured fallback, never silent truncation.
Quotes/message remain ephemeral except explicitly confirmed damage passages; no
raw conversation is automatically persisted.

## Confirmation and saving

Recover displays "Here's what I understood. Please review." for a delivered
result. Users select and edit proposed fields, review a separate preview and
explicitly confirm. Rejection writes nothing. UNKNOWN/UNCHANGED never replace
saved facts. Unsupported values and clarification questions remain visible;
unavailable/error results retain structured fallback without applicable changes.

New-household review prefills the optional existing intake form. Creating a case
there requires explicit safety selection and confirmation of the selected
household/damage details. Either confirmation path creates case and records in
one transaction. The initial task plan remains unapproved.

Returning intake changes follow the existing deterministic reassessment preview
and explicit approval. approve_reassessment's optional confirmed_records and
expected_records_version arguments save records, assessment and revised plan in
one transaction. Failure rolls back all changes, preserving plans and progress.
Without an approved initial plan, intake changes must wait for existing approval.
Records-only changes use save_recovery_records with the displayed version and
original case snapshot, checked inside the same write transaction.

The M1-compatible fingerprint checks the projected confirmed DTO. Full M5 case,
records and plan snapshots plus transactional version checks additionally protect
identity, stale edits and reverted changes. Fingerprints never replace database
checks. New-case reviews have stable UUIDs to reject duplicate acceptance.

## Verification and remaining handoff

Automated tests use synthetic providers with the real M1 service and M5 UI/consumer.
An optional pinned Git-object test also checks DTO/fingerprint parity. Real Qwen was
separately verified through app.py using Streamlit AppTest, as recorded below. Browser
rehearsal remains outstanding. Emergency controls remain global and independent;
persisted danger cannot be cleared by this consumer.

```powershell
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_extraction_consumer.py tests/test_recovery_records.py tests/test_recovery_landing.py tests/test_reassessment.py
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Browser rehearsal: review/correct/cancel; explicit confirmation; unknown adults;
county save/reopen; additive furniture/refrigerator damage; electricity reassessment;
two-tab stale rejection; emergency interruption with model/storage unavailable.
Assistance Finder, photographs and external submissions remain outside this task.


## Integration verification

UI checkpoint: `2a56756`; corrected main merge: `e2f6327`.
The first expanded integration regression run passed 300 tests (11 skipped,
10 subtests passed), using synthetic providers only.

A separate real-Qwen attempt through app.py / Streamlit AppTest on November 4,
2026 reached the existing Nebius extraction path.
The fictional five-person-household response was rejected by M1 as
`ERROR / invalid_model_output`. No case was created; no mock replaced the response.
That initial live journey stopped at the validation gate; the separately authorized
post-correction verification below supersedes its readiness limitation. No extractor validation was
weakened or M1 code altered to accept invalid output. This was not a browser test.

Final full regression suite after integration: **738 passed, 11 skipped,
10 subtests passed**. Pytest uses provider doubles; no paid model calls are
required by tests. The subsequent diagnostic regressions brought the full suite to 744 passed,
11 skipped and 10 subtests passed; the final checkpoint reruns these checks.


## Final live verification ? November 5, 2026

Four real requests used Nebius Token Factory and
`Qwen/Qwen3-235B-A22B-Instruct-2507`: extraction plus semantic audit for each journey.
This was app.py exercised by Streamlit AppTest, NOT real-browser testing. No provider
reply was mocked or manually inserted. The strict schema, quote and count validators
were unchanged. Only fictional data and an isolated temporary SQLite database were used.

- New household: NEEDS_CLARIFICATION. Flood, flooded housing, unavailable electricity,
  needed accommodation and reported house damage staged as editable proposals. Adults
  and children remained unknown; no service needs were inferred from the elderly member.
  Clarification asked about counts, water and recovery needs; these were not saved as facts.
- Returning household: SUCCESS. Electricity Available (`Electricity is back`) and additive
  refrigerator damage (`our refrigerator is damaged`) staged with exact source quotes.
- Both extraction schemas and audits passed; context fingerprints matched. Database
  snapshots were unchanged before confirmation. Explicit UI confirmation, initial plan
  approval, damage saves and the returning reassessment used existing repository methods.
- Reopening retained saved records; earlier damage, historical plans and completed task
  progress survived the revision. The insurance draft included confirmed saved damage.

This is a bounded successful observation, not a guarantee of future model compliance.
Invalid outputs must still fail closed. More clarification than necessary can occur.
No additional paid calls are needed for the checkpoint; browser visual/download acceptance
remains a separate manual task.


## Final local checkpoint review

Final focused extraction/Recovery/danger/Guardian/navigation suite: **333 passed,
11 skipped, 10 subtests passed**. Complete application suite: **744 passed,
11 skipped, 10 subtests passed**. No paid Qwen calls were made for this review.
Shared danger detection and strict schema/quote/count validators match the reviewed
main merge; the only M1 generation change is the bounded household-total prompt example.
Clarification questions, supported editable proposals, explicit unknown labels, structured
fallback and Find Help Now remain available. Browser acceptance is still outstanding.
