# M5 conversational extraction consumer

Contract inspected: origin/m1/recovery-needs-extraction at
5a6391d0887ba39dde948d6db862fc29bcdbe518, including its actual DTO definitions,
fingerprint implementation and contract. M1 is correcting its danger precheck.
No M1 file is edited, no branch merged, and no live model call is made.

## Disabled real integration

The landing description still selects a section locally. It invokes no extractor.
There is no environment switch to enable the unmerged code. After M1's corrected
implementation is reviewed and merged, its validated result can be delivered to:

```python
from recovery.extraction_consumer import confirmed_context
from ui.recovery_page import stage_extraction_result
# Future owner-approved caller constructs M1.RecoveryConfirmedContext from
# confirmed_context(saved_case, saved_records), then invokes M1's extractor.
stage_extraction_result(state, repository, validated_result, message,
    case_snapshot=saved_case, records_snapshot=saved_records, plan_snapshot=saved_plan)
```

Capture the snapshots before starting extraction; use null snapshots for a new
household. Delivery checks active case identity and those original snapshots
against authoritative storage, then stages an ephemeral review only. This prevents
case-switch and reverted-value races that a DTO fingerprint alone cannot detect.
M5 accepts M1's validated model or serialized dictionary, checks exact wire
names/states and preserves supporting quotes. It does not copy M1's generic DTOs
or mix household facts with M3's grounded-guidance contract.

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

Tests use simulated M1-contract results. An optional pinned Git-object test loads
M1 definitions in memory for DTO/fingerprint parity, without calling extraction.
No live Qwen behavior is claimed. After M1 merges, delivery must still be explicitly
wired and both synthetic journeys rehearsed in a browser. Emergency controls remain
global and independent; persisted danger cannot be cleared by this consumer.

```powershell
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_extraction_consumer.py tests/test_recovery_records.py tests/test_recovery_landing.py tests/test_reassessment.py
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Browser rehearsal: review/correct/cancel; explicit confirmation; unknown adults;
county save/reopen; additive furniture/refrigerator damage; electricity reassessment;
two-tab stale rejection; emergency interruption with model/storage unavailable.
Assistance Finder, photographs and external submissions remain outside this task.
