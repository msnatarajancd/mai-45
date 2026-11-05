# M5 recovery records and insurance preparation

The integrated Recover page supports confirmed household details, damage records,
and a deterministic insurance discussion draft. Use fictional information only.
Case-ID reopening is not authentication. No insurer is contacted, no claim is
submitted, and no photograph is uploaded or processed.

## Persistence

Repository initialization adds `recovery_records(case_id PRIMARY KEY REFERENCES
recovery_cases(case_id), records_json NOT NULL)` with `CREATE TABLE IF NOT EXISTS`.
Existing case, plan and reassessment rows are unchanged. Old cases read as empty
records at version 0, with unknown household values, without an insertion.

`get_recovery_records(case_id)` loads the case-linked aggregate.
`save_recovery_records(records, expected_version=..., explicitly_confirmed=True)`
requires explicit confirmation. Within `BEGIN IMMEDIATE` it reloads the persisted
case, requires `immediate_danger is False`, verifies the records version and damage
identities, then writes the next version. Errors roll back. Existing damage IDs
must be retained; deletion is intentionally unsupported. No plan, task or intake
is written by this operation. Utilities/housing/danger remain authoritative in
the existing intake; these forms do not provide a danger-clearance path.

The insurance summary reads saved reports only. It is generated on demand, not
stored as a separate document, and can be downloaded as plain text. Unsaved form
values do not enter it. It makes no independent coverage, cause or valuation
determination. No new dependency or model call is required.

## Run

From the `mai-45` directory in this workspace:

```powershell
..\.venv\Scripts\python.exe -m streamlit run app.py
```

`READYRELIEF_DB_PATH` optionally selects the SQLite file. Otherwise the integrated
page uses `.local/recovery.sqlite3`. Keep that file on persistent storage when
reopening across application restarts.

## Required manual verification before demonstration

Automated Streamlit AppTest coverage does not replace this browser rehearsal:

1. Open Recover. Verify Call 911 and I Can't Call 911 are immediately accessible.
2. Create a fictional flood case, explicitly reporting no immediate danger.
3. Record two children; leave adults blank. Confirm and save. Check the saved
   confirmation appears only after success.
4. Add furniture with a reported damage description, leaving the date unknown.
   Confirm and save. Edit its notes and confirm the edit.
5. Preview and download the insurance discussion draft. Check adults/date/insurance
   values remain unknown; coverage is undetermined and no claim submitted.
6. Approve the existing recovery plan and save one completed task.
7. Open a different case, then resume using the original case ID. Restart the
   application and repeat. Check saved records, notes and task progress remain.
8. Add refrigerator damage. Use the existing reassessment to report electricity
   restored and approve it. Regenerate the summary; it must retain the warning
   that utility restoration does not establish household safety.
9. Open the case in two browser sessions. Save a record edit in one; submitting
   an older edit in the other must fail until Reload saved household and damage
   records is used. Check unsubmitted edits do not persist.
10. Report danger using the existing emergency path. Check the records forms and
    ordinary updates are paused after reopening and emergency actions still work.

Photographs, conversational extraction, resource matching, authentication and
insurance submissions are outside this enhancement. M1/M3 interfaces are unchanged.
