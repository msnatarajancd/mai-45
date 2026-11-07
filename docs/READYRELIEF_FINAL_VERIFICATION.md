# ReadyRelief — Final Verification Record

Audit date: **November 6, 2026**. Scope: complete merged application and documentation, no feature development.

## Repository and isolation

| Check | Observed result |
|---|---|
| Repository | `msnatarajancd/mai-45` |
| PR #6 | Merged; confirmed through GitHub metadata and fetched history |
| Latest fetched main / audited HEAD | `be0b99adbe2bb9ffe6e97716f59649db86fcce85` |
| Merge subject | `Merge pull request #6 from msnatarajancd/integration/recovery-m6m9-selected` |
| Integration ancestry | `0c0b5597833468e10689e2efc47b8e64365b16b3` is an ancestor of main; normal merge retains integration history |
| Audit checkout | `readyrelief-final-audit` (historical isolated worktree), clean detached main at start |
| Preserved original checkout | `mai-45`, `feature/m5-insurance-workspace`, `2553619c7f8a02449e84941ccf468ae73ab8b6f7` |
| Preserved integration checkout | `recovery-m6m9-selected`, `integration/recovery-m6m9-selected`, `0c0b5597833468e10689e2efc47b8e64365b16b3` |
| Preserved teammate ref | `origin/feature/m6-M9`, `822767153da5c59a08eb3b79995bb6de6650840d` |
| Application/source changes | None during the original audit. Its documentation/assets remained uncommitted; this documentation-only PR integrates the reviewed evidence |
| Browser DB | Isolated ignored `.local/final-demo.sqlite3`; exclusively fictional UI-created cases; no direct SQL inserts |
| Visual-suite DB | Separate ignored `.local/visual-only.sqlite3` |

The audit DB includes abandoned synthetic rehearsal cases from selector development. Final successful case IDs are explicitly recorded below. They are not existing household records, and no existing database was reset. The harness reads snapshots using SQLite `mode=ro`; all durable scenario writes used production UI controls.

## Environment

Windows 10, Python **3.13.3**, SQLite **3.49.1**, Node **22.23.4**, Playwright **1.62.1** with installed Chromium **151.0.7922.34** (Playwright revision 1234). Python direct dependencies: Pydantic **2.14.2**, Streamlit **1.66.1**, pytest **9.2.0**, Pillow **13.0.0**, ReportLab **5.1.0**, pypdf **6.21.4**. Exact complete installed Python distribution inventory, including audit-only tools, is [PYTHON_ENVIRONMENT.txt](audit/PYTHON_ENVIRONMENT.txt). Application requirements remain unchanged. Node dependencies are supplied by the existing `mai-45/node_modules`; no new runtime dependencies were installed.

`READYRELIEF_DB_PATH` selected the synthetic database. `NEBIUS_API_KEY` was unset/empty in audit servers; no credential value was printed. Optional model selection uses `NEBIUS_CHAT_MODEL` / `NEBIUS_MODEL`. Production `app.py` ran on localhost:8520 with headless Streamlit configuration. PyMuPDF was used only to render downloaded PDFs for inspection, not added as an application dependency.

## Fresh automated verification

Portable equivalents of the audit commands, from the repository root after activating its Python environment (see the happy-path prerequisites):

```powershell
python -B -m pytest -q -p no:cacheprovider

python -B -m pytest -q -p no:cacheprovider tests/test_pending_danger.py tests/test_reassessment.py tests/test_extraction_consumer.py tests/test_recovery_extraction.py tests/test_insurance_workspace.py tests/test_publication_context.py tests/test_alert_freshness.py

$env:READYRELIEF_PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
$env:READYRELIEF_DB_PATH = Join-Path $PWD '.local\visual-only.sqlite3'
$env:NEBIUS_API_KEY = ''
# Requires the repository's pinned npm dependencies and Playwright Chromium.
npm run test:visual

git diff --check
```

| Verification | Fresh result |
|---|---|
| Full Python | **1,024 passed, 11 skipped, 10 subtests passed**, 163.75 seconds |
| Focused safety/integrity group above | **242 passed**, 35.48 seconds |
| Normal full visual suite, no snapshot regeneration | **62 passed, 1 skipped**, about 4.4 minutes |
| Visual layouts | Desktop 1440×1000, tablet 1024×900, mobile 390×844 |
| Existing visual skip | Mobile horizontal sidebar-animation test; not silently converted into a pass |
| Startup | Actual production Streamlit server started successfully; browser loaded application |
| Whitespace checks | `git diff --check` passed; documentation additionally checked separately because new files are untracked |

No test assertions, screenshot tolerances, baselines, requirements, or application files changed. Python's skipped tests remain exclusions, not verified functionality. Automated tests use fake model responses; they do not prove fresh provider availability.

## Actual Chromium household acceptance

**PASS on desktop and mobile**, separate browser contexts, production `app.py`, real visible controls. This was not Streamlit AppTest and not the injected browser model fixture.

| Step group | Desktop / mobile result |
|---|---|
| Home, search/navigation, simulated Protect | PASS; simulated result visibly distinguished from official current information |
| Respond / Call 911 / I Can't Call 911 | PASS; visible and unobstructed; information panel opened; no call placed |
| Natural-language start / actual unavailable-model fallback | PASS; description alone creates no case; structured fields remain usable |
| Confirmed adults, narrative and two actual damage records | PASS; adults 3, children unknown, incident 2026-11-01 |
| Draft plan / separate explicit approval | PASS; no active plan until approval; no unmet housing task when staying with others |
| Completed task / refresh / resume / timeline | PASS; task identity/status and accepted user-reported event retained |
| Electricity reassessment | PASS; preview leaves current plan active; approval retains completed work and historical plan |
| Finder | PASS; official links, organizations, unknown-county message and limitations; no model or live availability assumption |
| Insurance profile and item-specific details | PASS; two rooms/estimates persisted and independently asserted |
| Actual PNG upload / unsaved preview / confirmed save / reopen | PASS; one original attachment persisted; no file saved before confirmation |
| Receipt status and fictional communication | PASS; receipt has no attachment; communication is explicitly user-reported |
| Actual PDF/CSV/ZIP downloads | PASS; contents and byte integrity checked below |
| Return to progress | PASS; accepted task plan snapshot unchanged by Insurance edits |

Final successful desktop case: `2d8897b2-27f9-43d5-9e51-ced75c3a31e8`; mobile: `bada4e0c-6c96-43e5-88ec-e909c706ff35`. Machine snapshots and step lists: [desktop result](audit/desktop/result.json), [mobile result](audit/mobile/result.json). Ten screenshots per layout document the journey. [Full Happy Path](READYRELIEF_FULL_HAPPY_PATH.md) supplies exact labels, values, launch and replay instructions.

### Screens and interaction coverage

The new household walkthrough directly exercised Home, Protect, Respond and Recover, including all four Insurance stages. The full visual suite additionally exercises all seven screens in bright/dark mode, search/chat navigation, tour, narration events, overlays, fixed header and emergency visibility across three layouts. Household/Evidence/Assistant live-Qwen operation was not separately paid-tested in this audit. General Household preferences are session state, not automatically durable confirmed Recovery information.

### Harness development deviations

Early attempts stopped because audit selectors expected a different fallback message, treated segmented date controls as ordinary textboxes, or entered the next item's details before the rerendered form changed. These were harness assumptions, not demonstrated application defects. The final script uses actual labels, date spinbutton segments, an item-specific heading wait, and saved estimate assertions. Both final complete reruns passed. Initial diagnostic screenshots/traces are retained only in ignored local diagnostics, not presented as successful evidence.

## Download and visual inspection

Both final `preparation.pdf` files contain **two pages**. All four rendered pages were visually inspected: no overlap, item details/costs kept together, readable tables inside margins, matching evidence path, clear preparation/non-submission disclaimer. Both CSVs contain Refrigerator/Kitchen/450.00 USD and Sofa/Living room/200.00 USD. Both ZIPs contain a preparation PDF, inventory CSV, `evidence-manifest.json`, and exactly one original PNG attachment. The reported receipt is explicitly not uploaded and has no file in the ZIP.

Original PNG SHA-256: `3622e06b98419355d8ee61244711f0eec7e2cd93205885c09aa3c9580960e1b2`. Its **actual bytes** match the ZIP attachment, manifest hash and length. The PDF's human-readable Refrigerator/Photograph description refers to the same ZIP filename. No uploaded bytes were rewritten. [EXPORT_VERIFICATION.json](audit/EXPORT_VERIFICATION.json) records both outputs. Samples: [desktop PDF](audit/desktop/preparation.pdf), [desktop ZIP](audit/desktop/evidence.zip).

Saved-image previews, final progress, simulated alert, assistance, unapproved plan, timeline and mobile emergency screenshots were inspected. One existing minor presentation issue is mojibake in some legacy interface strings, including the simulated-source sender separator and Evidence-page wording. It does not change the displayed simulation boundary; no source or application strings were changed in this documentation task.

## Safety and failure-path evidence

These destructive/adversarial cases were exercised in isolated test fixtures, **not the successful household**:

| Safeguard | Exact evidence / result |
|---|---|
| Emergency access, danger interruption, no automatic calling | Full `tests/visual/emergency.spec.cjs` across layouts; current-danger interruption, contact ordering and overlay visibility pass |
| Pending danger before confirmation | `tests/test_pending_danger.py::test_pending_danger_precedes_valid_confirmation_and_preserves_all_progress` passes |
| Failed danger persistence and reruns | `test_failed_danger_persistence_blocks_reruns_and_retry_stale_confirmation` and last-moment handler guards pass |
| Persisted danger and unknown safety | `tests/test_reassessment.py`; preview and transactional acceptance reject ordinary updates, preserve plan/history/state |
| Stale/current concurrent updates | Reassessment, extraction consumer, Insurance expected-case/records/workspace-version tests pass |
| Case-isolated attachments and rollback | `test_other_case_cannot_read_remove_or_reuse_attachment_identity`, `test_database_failure_rolls_back_inserted_blob_and_workspace`, corrupt-image/hash and limits tests pass |
| Unknown counts / unsupported model facts | `tests/test_recovery_extraction.py`, `test_extraction_consumer.py`: strict validation and confirmation; no fresh live model claim |
| No-alert/expiry/failed recheck | `tests/test_alert_freshness.py`: exact five-minute boundary, `ends`/`expires`, invalid timestamps, no automatic lookup, failed-recheck unavailable state pass |
| Unapproved context | `tests/test_publication_context.py` and M3 integration suites pass; public evidence excludes raw neighboring parent instructions |

## Current source integrity and retrieval

The read-only store audit found **eight source records, seven hash-matching preserved captures, six currently publishable approved passages and twenty-three PENDING candidates**. Five approved CDC reentry passages and one USAGov passage validate through the existing candidate publication gate. FCC source is UNAVAILABLE without a capture. NFIP remains REVIEW_REQUIRED; all four NFIP candidates remain PENDING. Other held USAGov candidates remain PENDING. Parent-source approval alone does not publish pending neighbors. No source, hash, acquisition history, approval decision or reviewer record changed.

The historical USAGov reviewer placeholders remain in their original approval snapshots. The existing human-authored `M3_REVIEW_ATTRIBUTION_ADDENDUM.md` provides the transparent attribution correction; this audit does not rewrite or reapprove them. Full results and stable IDs: [KNOWLEDGE_AUDIT.json](audit/KNOWLEDGE_AUDIT.json).

All query checks used `services.knowledge.retrieve_guidance(query, 'recover', hazard='flood', jurisdiction='US-FL-MIAMI-DADE')`, default requested evidence count:

| Query | Actual result |
|---|---|
| What does official guidance say about qualifying for transitional housing? | NO_RELEVANT_EVIDENCE, zero citations; lexical recall limitation |
| Where can I find temporary housing after flooding? | INSUFFICIENT_EVIDENCE, one USAGov citation; not a location, hotel room or eligibility decision |
| electrician electrical hazards | INSUFFICIENT_EVIDENCE, one CDC citation |
| building inspector flooded home | INSUFFICIENT_EVIDENCE, two CDC citations |
| Which shelters have rooms available tonight? | INSUFFICIENT_EVIDENCE, zero citations; operational request abstained |
| Is my home safe to enter now? | INSUFFICIENT_EVIDENCE, zero citations; no personal safety determination |
| Are there evacuation orders right now? | INSUFFICIENT_EVIDENCE, zero citations; no inferred live order |

INSUFFICIENT_EVIDENCE is not mislabeled as storage UNAVAILABLE. Six publishable passages do not imply every query retrieves six. Exact original approved passages and substantive caveats are preserved. Assistance Finder's five dated official link pathways are a separate directory; they are not converted into M3-reviewed evidence.

## Unverified, partial, or absent behavior

- **No new paid Qwen calls**: real provider availability, extraction variability and grounded prose generation were not freshly verified. Earlier live evidence is historical. The final guaranteed demo uses actual structured fallback.
- **No live NWS request required**: official network/API currentness was not certified; simulated mode and deterministic official-response tests were verified.
- **Narrow RAG coverage**: NFIP damage-documentation passages remain unpublished; the app's damage organization is an application recommendation, not reviewed NFIP advice. A natural-language housing paraphrase misses available evidence. Static text cannot answer current operational availability.
- **Idle-page freshness**: no automatic polling. Freshness updates on a rerender/recheck, not merely passage of time on a completely idle screen.
- **Prototype storage/privacy**: no login, authorization, encryption-at-rest service, production document security, malware scanning, or hosted-disk durability guarantee. Case IDs are not credentials. Original EXIF/GPS is preserved.
- **Partial structured household coverage**: age/walker information is confirmed narrative; no dedicated comprehensive medical/accessibility profile. Unknown children/provider/county remain unknown.
- **Insurance scope**: only JPEG/PNG actual uploads; no receipt/estimate PDF attachments, OCR, photo analysis, insurer contact/submission, coverage/eligibility decision, or verified deadlines.
- **Evidence page presentation**: some integration descriptions still name CDC only and older PR provenance even though the actual store includes USAGov and Insurance is implemented. This is stale descriptive copy, not a failing retrieval gate; no UI rewrite made.
- **No new framework claims**: no runtime multi-agent orchestration, MCP or LangGraph. MINT course definition unavailable; mapping is explicitly project-based.
- Optional DOCX was not produced: python-docx and a suitable office renderer were unavailable in the existing environment; no substantial tooling was installed. The four required Markdown documents are complete.

## Deliverables and final disposition

The original audit produced four reports, the replay harness, synthetic image, inventories, acceptance/export results, twenty screenshots, six downloaded files and four PDF page renders. This integration includes the four reports, seven evaluation deliverables and 32 explicitly selected supporting assets: referenced screenshots/data plus one sample PDF/CSV/ZIP set. Duplicate mobile download binaries and PDF page renders remain in the preserved source worktree and are not included. [FILES_CREATED.txt](audit/FILES_CREATED.txt) lists the exact integrated file set, including itself. Existing tracked application, tests, approvals and original feature branches remain unchanged. The audit server was stopped after verification; Windows emitted connection-reset messages while browser sockets closed, not a failed application assertion during the completed journeys. Audit-only databases, traces and failed-selector diagnostics stay under ignored `.local/`.

**End-to-end result: PASS for the explicitly scoped structured-fallback local household journey on desktop and mobile.** No major new safety or persistence blocker was demonstrated. This does not certify live external services or operational emergency readiness. No Git publication was performed during the original audit. This follow-up PR checkpoints only reviewed documentation and evaluation deliverables.

## Linked AI evaluation

The separate [AI evaluation report](evals/READYRELIEF_AI_EVALUATION_REPORT.md) records 40 scenarios: 39 passed and R04 failed. These are 16 OFFLINE MODEL FIXTURE and 24 DETERMINISTIC APPLICATION CHECK executions, not fresh live Qwen accuracy measurements. The historical browser/full-suite results above remain distinct from that evaluation.
