# ReadyRelief — Full Browser-Tested Happy Path

**Result: PASS**, actual Chromium against merged production `app.py`, desktop 1440×1000 and mobile 390×844. Commit: `be0b99adbe2bb9ffe6e97716f59649db86fcce85`. November 6, 2026. No substituted model provider, paid Qwen call, live weather dependency, emergency call, or insurer submission was used.

## Starting conditions and reproducibility

Use a repository checkout containing these documents, Python 3.13 and Node 22 with npm. The recorded audit used an isolated checkout of the commit above; reproduction does not require the author's worktree layout. Set a **new, disposable synthetic database path**, not an existing household database. Do not delete or reset someone else's records.

From the repository root in PowerShell, prepare dependencies if not already installed:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
npx playwright install chromium
```

Then launch the application:

```powershell
# Choose a new unused filename for each clean demonstration.
$env:READYRELIEF_DB_PATH = Join-Path $PWD '.local\demo-replay-01.sqlite3'
$env:NEBIUS_API_KEY = ''
python -B -m streamlit run app.py --server.address 127.0.0.1 --server.port 8520 --server.headless true --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8520`. Do not import a synthetic model fixture. Clearing the key in this shell intentionally selects the actual unavailable-model fallback; no credential value is needed in the demonstration. The app creates the database through normal UI operations. Keep the server running while reopening a case.

Use `Find a screen...` in the header to select Home, Protect, Respond or Recover. On mobile the search/menu replaces the always-visible desktop sidebar. Scroll within the page when a control is below the fold. Emergency controls are independent of this flow; **do not click Call 911 during the demo**.

### Fictional input to copy

```text
Fictional demonstration household: three adults. One adult is 72 years old and uses a walker. We are staying with friends away from the affected property. No one has an immediate injury or current emergency. Earlier flooding on November 1, 2026 damaged our refrigerator and sofa. We need recovery guidance and insurance preparation.
```

| Detail | Confirmed demonstration value |
|---|---|
| Adults | 3 |
| Children | Unknown; leave blank |
| Accommodation | Staying with others |
| Current danger assessment | No immediate danger reported; not an official safety verification |
| Incident | Flood, November 1, 2026 |
| Insurer / policy | Demo Mutual Insurance / DEMO-POL-001 |
| Refrigerator | Water damage after earlier flooding.; Kitchen; user estimate 450.00 USD |
| Sofa | Water damage to upholstery.; Living room; user estimate 200.00 USD |
| County, water/provider, coverage | Unknown; do not infer from the app's Miami-Dade header |
| Upload | [synthetic-flood-damage.png](audit/synthetic-flood-damage.png), visibly fictional |

Age and walker context have no dedicated Recovery typed profile fields. Preserve them in the explicitly confirmed narrative below; do not claim a medical or transport assessment was performed.

## 1. Home, Protect, and Respond

1. Review Home and the navigation/search controls. Screenshot: [desktop Home](audit/desktop/01-home.png), [mobile Home](audit/mobile/01-home.png).
2. Open Protect. Click **Show simulated alert**. Confirm **SIMULATED SCENARIO** is visible. This is not a live NWS lookup or a current evacuation order. Screenshot: [desktop Protect](audit/desktop/02-protect-simulated.png), [mobile Protect](audit/mobile/02-protect-simulated.png).
3. Open Respond. Locate **Call 911** and **I Can't Call 911** without placing a call. Click **I Can't Call 911** and review **If you can't call 911**. These options give information; ReadyRelief does not dispatch anyone. Screenshot: [desktop Respond](audit/desktop/03-respond.png), [mobile Respond](audit/mobile/03-respond.png).

## 2. Describe, review, and create the draft case

4. Open Recover. In **Describe what's happening or what you need help with.**, paste the fictional description. Click **Continue to Review**.
5. Observe: **AI extraction is not configured. Use the structured input below to review and confirm your details.** No case or inferred household information was written from the description alone. This is the real structured fallback, not a mock extraction success.
6. If needed, open **Use structured intake or resume a saved case**. Set:
   - **Immediate danger assessment** → **No immediate danger reported**.
   - **Disaster type** → **Flood**.
   - **Housing condition** → **Minor reported damage**. This is a fictional reported condition, not permission to reenter.
   - **Temporary accommodation** → **Staying with others**.
   - Leave utility values Unknown at this stage.
   - **Household recovery needs** → **Damage documentation**.
7. Click **Create draft plan**. This explicit submission creates the assessed fictional case and a draft; there is still **no approved active plan**.
8. Open **Saved case · Keep this ID to resume** and copy the case UUID. Store it outside the browser for the demo. Screenshot: [desktop unapproved plan](audit/desktop/04-unapproved-plan.png), [mobile unapproved plan](audit/mobile/04-unapproved-plan.png).

## 3. Confirm household details and two damaged items

9. Click **Document damage**. Expand **Optional household details**.
10. **Number of adults (if known)** → `3`; leave child count blank. Set **Reported property damage** to:

```text
Refrigerator and sofa damaged in earlier flooding. Three adults are staying with friends; one adult is 72 and uses a walker. No current emergency reported.
```

11. **Would you like insurance preparation help?** → **Yes**. Check **I confirm these household details**; click **Save confirmed household details**. Unknown values remain unknown.
12. Click **Add Damaged Item**. Enter **Item or area description** `Refrigerator`, **User-reported damage description** `Water damage after earlier flooding.`, and **Incident date (leave blank if unknown)** November 1, 2026. Check **I confirm this damage record**; click **Save confirmed damage record**.
13. Repeat **Add Damaged Item** for `Sofa`, description `Water damage to upholstery.`, same incident date, same confirmation and save action. Screenshot: [desktop confirmed damage](audit/desktop/05-confirmed-damage.png), [mobile confirmed damage](audit/mobile/05-confirmed-damage.png).

## 4. Personalized plan, approval, progress, and reopening

14. Click **Continue my recovery**. Because confirmed records changed after the first draft, click **Generate fresh recovery plan**. Review task rationale, priorities, dependencies and applicable official pathways. Accommodation is already arranged, so it must not appear as a current unmet housing need. Directory links are not labeled M3-reviewed evidence.
15. Check **I reviewed these tasks and want to accept this plan**. Click **Approve my recovery plan**. Only now is the plan APPROVED and active.
16. In the first task's **Status** dropdown, select **Completed**, then its **Save progress**. This is a user-reported status, not agency verification.
17. Refresh the browser. Click **Start my recovery**, **Resume My Recovery**, enter the saved **Recovery case ID**, then click **Open saved recovery**. Confirm the Completed task persists.
18. Open **Recovery timeline**. Confirm the **User-reported task progress** event. Screenshot: [desktop timeline](audit/desktop/06-timeline.png), [mobile timeline](audit/mobile/06-timeline.png).

## 5. Supported reassessment

19. Expand **Circumstances changed? Review an update**. Set **Updated immediate danger assessment** → **No immediate danger reported**, **Electricity availability** → **Available**.
20. Click **Preview proposed changes**. Read what changed and why; the existing active plan remains unchanged during preview. This scenario changes Unknown electricity to a confirmed Available report; it is not a claim of safety or a reconstruction of an earlier outage.
21. Click **Approve this revision**. Confirm the revised plan is active, previous plan is preserved, and the same Completed task retains its identity/status. No task automatically becomes Completed just because electricity is available.

## 6. Official assistance pathways

22. Click **Find Help Now**. Confirm **Official assistance pathways**, source organization, clickable **Open Official Resource** links and availability limitations. With county Unknown, only general US/Florida pathways are appropriate; the app must not assume Miami-Dade eligibility or a household provider. The production directory has independent Housing, Disaster assistance, Electricity and Water filters; local water links require supported confirmed county context.
23. Do not present a static link as an open bed, live shelter, guaranteed assistance, restoration estimate or M3-reviewed passage. Return through **Continue my recovery**. Screenshot: [desktop Finder](audit/desktop/07-assistance.png), [mobile Finder](audit/mobile/07-assistance.png).

## 7. Insurance Details and Damage Inventory

24. Click **Prepare for insurance**. The workspace has four visible stages: **Insurance Details**, **Damage Inventory**, **Evidence & Documents**, **Review & Download**.
25. In Insurance Details enter **Insurer name (optional)** `Demo Mutual Insurance`, **Policy reference (optional)** `DEMO-POL-001`, **Incident date (optional)** November 1, 2026. Leave unsupported policy/claim details blank. Enter **Insurance notes (optional)**:

```text
Fictional preparation only. Three adults; one is 72 and uses a walker. Staying with friends away from the affected property. No current injury or emergency reported.
```

26. Check **I confirm these Insurance details**; click **Save Insurance Details**. No insurer is contacted.
27. Select **Damage Inventory**. The previously confirmed Refrigerator and Sofa already exist. For Refrigerator click its **Edit Details** and wait for heading **Edit Details: Refrigerator**. Set **Room / location (optional)** `Kitchen`, **User-estimated repair / replacement cost (optional)** `450.00`, **Currency (three-letter code) (optional)** `USD`; check **I confirm these item details**, click **Save Item Details**.
28. Select the Sofa's **Edit Details**, wait for **Edit Details: Sofa**, then set room `Living room`, estimate `200.00`, currency `USD`. Confirm and save. Waiting for the correct heading avoids entering details into the previous item's form during a rerender.

## 8. Actual photograph, receipt status, and communication

29. Select **Evidence & Documents**. Set **Associate new evidence with** → **Refrigerator**. In **File description (optional)** type `Clearly synthetic test image; not a real property photograph.` Upload [synthetic-flood-damage.png](audit/synthetic-flood-damage.png). The **Unsaved preview: synthetic-flood-damage.png** is not yet durable storage.
30. Check **I confirm saving these attachments**; click **Save Attachments**. One actual image file is now stored. Do not upload real household photographs or documents to this course prototype.
31. Refresh and reopen the saved case as in step 17. Click **Prepare for insurance**; verify insurer details survived. Select **Evidence & Documents**; verify preview and **Download saved photograph** remain available.
32. Set **Evidence type** → **Receipt**; **Evidence status** → **Reported available, not uploaded**. Enter **Evidence description** `Fictional receipt reported available; no receipt file uploaded.` Check **I confirm this evidence record**; click **Save Evidence Record**. This records a status, not an attachment.
33. Enter **Communication reference (optional)** `DEMO-COMM-001`; retain Phone and enter **Communication summary**:

```text
Fictional user-reported telephone discussion asking which documents the insurer requires. No submission or coverage decision occurred.
```

34. Check **I confirm this user-reported communication**; click **Save Communication**. Screenshot: [desktop evidence](audit/desktop/08-saved-evidence.png), [mobile evidence](audit/mobile/08-saved-evidence.png).

## 9. Review, download, and final consistency

35. Select **Review & Download**. Check the preparation/non-submission disclaimer. Click **Download Preparation PDF**, **Download Damage Inventory CSV**, and **Download Evidence ZIP**. Screenshot: [desktop review](audit/desktop/09-review-download.png), [mobile review](audit/mobile/09-review-download.png).
36. Verify the PDF lists Demo Mutual, the two items and their $450/$200 estimates, item-specific saved photograph, receipt explicitly not uploaded, fictional communication and questions for the insurer. Both final PDFs have two pages; item/cost details stay together with no overlapping content.
37. Inspect CSV rows for Refrigerator/Kitchen/450.00 and Sofa/Living room/200.00. Inspect ZIP for `insurance-preparation.pdf`, `damage-inventory.csv`, `evidence-manifest.json`, and one original PNG under `attachments/`.
38. Compare PNG bytes/SHA-256 with the fixture: `3622e06b98419355d8ee61244711f0eec7e2cd93205885c09aa3c9580960e1b2`. The attachment path in the PDF matches the ZIP manifest. No receipt file is included.
39. Click **Continue my recovery**. Verify **Your Recovery Progress** and the previously Completed task. Insurance edits must not replace/reset accepted tasks. Screenshot: [desktop final progress](audit/desktop/10-final-progress.png), [mobile final progress](audit/mobile/10-final-progress.png).

## Audit outputs and expected state

| Layout | Case ID from this audit | Downloads and machine evidence |
|---|---|---|
| Desktop | `2d8897b2-27f9-43d5-9e51-ced75c3a31e8` | [result](audit/desktop/result.json), [PDF](audit/desktop/preparation.pdf), [CSV](audit/desktop/inventory.csv), [ZIP](audit/desktop/evidence.zip) |
| Mobile | `bada4e0c-6c96-43e5-88ec-e909c706ff35` | [result](audit/mobile/result.json); matching export verification is recorded in [EXPORT_VERIFICATION.json](audit/EXPORT_VERIFICATION.json). Duplicate mobile download binaries are omitted from this documentation package. |

Each final case has three confirmed adults, unknown children/county/water, two confirmed damaged items, an approved revised plan with retained completed work, one saved photograph, a reported-but-unuploaded receipt, and a fictional communication. [Export verification](audit/EXPORT_VERIFICATION.json) records exact bytes/hash and contents. These case IDs only work with the isolated audit database; they are not production records or authentication credentials.

### Automated replay of the same visible controls

With the server above running, in a second PowerShell window from the repository root, activate the same environment:

```powershell
$env:READYRELIEF_DB_PATH = Join-Path $PWD '.local\demo-replay-01.sqlite3'
$env:READYRELIEF_PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
$env:AUDIT_WIDTH = '1440'
node docs/audit/run_happy_path.cjs
$env:AUDIT_WIDTH = '390'
node docs/audit/run_happy_path.cjs
```

The script operates real browser controls. Python reads SQLite with `mode=ro` only to assert state; it does not seed records. Each run creates a new fictional case and writes layout-specific evidence under ignored `.local/audit/desktop` or `.local/audit/mobile`, preserving the committed reference samples. No real Qwen call is made. Session traces belong in ignored `.local/`, not source history.

### Recovery and repetition

If interrupted, use the saved case ID and the same database; do not re-add already-saved damage or files. For a completely new demonstration, stop the server with Ctrl+C, choose a new unused database filename, and restart with that path. Refresh clears session-only navigation but not confirmed SQLite data. Never reset Git, delete existing household databases, or clear a danger flag to make a demonstration continue. Run genuine danger/failure tests in separate test fixtures/sessions, not this successful case.
