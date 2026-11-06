# Insurance Preparation Workspace

Integrated entry: Recover > Prepare for insurance. Four visible stages provide
Insurance Details, Damage Inventory, Evidence & Documents, and Review & Download.
No insurer integration, claim filing, eligibility prediction or model call exists.
Use fictional information and synthetic images only.

## Saved information and approval

Canonical damage remains in `RecoveryRecords`, retaining existing damage IDs.
Insurance item details reference those IDs; adding a new damaged item routes to
the existing explicitly confirmed Recovery workflow. Insurance writes never
change intake, plans, task statuses or progress history.

The existing `SQLiteRecoveryRepository` adds two tables with `CREATE TABLE IF NOT
EXISTS`: `recovery_insurance_workspaces(case_id, workspace_json)` and
`recovery_insurance_attachments(attachment_id, case_id, metadata_json, content)`.
The second stores original bytes as BLOBs. Both case columns reference existing
Recovery cases. Existing rows are not migrated or rewritten. Legacy cases read an
empty version-0 workspace without inserting one.

`get_insurance_snapshot(case_id)` reads case, canonical records, workspace and
verified attachments in one SQLite read transaction. `save_insurance_workspace`
requires explicit confirmation and displayed case, Recovery-record version and
workspace version. It reloads authoritative safety and validates all associations
under `BEGIN IMMEDIATE`. Workspace, evidence and BLOB changes commit together or
roll back. Duplicate attachment hashes/IDs and foreign damage/removal references
are rejected. Communications are append-only: append a correction instead of
silently rewriting or removing a historical entry. Evidence records are retained
when an attachment is removed, changing from File saved to Not yet collected.

Pending danger is checked at UI entry and immediately before saving/exporting;
the global emergency workflow retains pending reports if persistence fails.
Persisted True or Unknown safety blocks ordinary preparation independently of UI.
Call 911 and I Can't Call 911 remain outside this optional workspace.

## Actual photographs and scans

JPEG/PNG only, including receipt and estimate scans. Per-file limit: 5 MiB;
case limits: 20 saved attachments and 50 MiB aggregate bytes. Pillow checks actual
format, extension, complete decoding, single frame and dimensions (12 megapixels,
10000 pixels per side). Unsafe filenames/paths, corrupted images and PDFs are
rejected. Previews are small orientation-corrected derivatives; saved originals
are not modified. SHA-256 and byte counts are verified on reads and export.

Uploading creates a temporary preview, not a saved record. Save Attachments plus
explicit confirmation persists the batch. Reopening reads actual saved bytes
from SQLite. Removal needs separate confirmation and the current versions.
Original names are display metadata only; downloaded/archive names use UUIDs.

This is not authenticated multi-user storage. A case ID is not an access
credential. Original files can contain EXIF/GPS metadata, which is retained and
included in exports. SQLite must reside on persistent storage to survive hosting
restarts/redeploys. Backups also contain image bytes. Deletion is not a promise
of forensic secure erasure from SQLite pages or backups. Corruption fails closed
for the complete preparation snapshot; no partial package is silently produced.

## Exports and dependencies

ReportLab 5.1.0 generates a paginated PDF; pypdf 6.21.4 verifies exports in tests.
Pillow 13.0.0 is an explicit dependency. CSV and ZIP use the standard library.
PyMuPDF was used as a local QA renderer, not as an application dependency.

All three downloads are built from saved information. The ZIP contains the same
PDF and CSV, an evidence manifest with case/item/file IDs and hashes, and actual
original images. The PDF is deterministic for an unchanged saved snapshot;
technical timestamps are normalized, while the ZIP manifest has its actual UTC
export-generation timestamp. Unsupported Helvetica characters are shown as
explicit Unicode code-point references; saved originals remain unchanged.
CSV neutralizes leading formula/control prefixes. No totals or coverage amounts
are invented when values are unknown. Every package identifies itself as
USER-REPORTED INSURANCE PREPARATION - NOT A SUBMITTED CLAIM (the PDF/manifest use
the specified em-dash label).

Binary PDF receipts/estimates, OCR, photograph analysis, malware scanning,
authentication, external submission and coverage/deadline determination are not
implemented. NFIP remains REVIEW_REQUIRED; no source approval is changed and no
unreviewed passage is represented as approved guidance.

## Verification

```powershell
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_insurance_workspace.py tests/test_insurance_ui.py
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Browser acceptance uses the existing locked Playwright/Chromium installation and
`tests/insurance_browser_acceptance.cjs`. Start the actual `app.py` on port 8518
with `READYRELIEF_DB_PATH` set to the absolute path of
`node_modules/insurance-browser.sqlite3`. The seed explicitly rejects any other
database path. Run the driver from the repository root with width 1440, then
`INSURANCE_BROWSER_WIDTH=390`. Synthetic cases are appended, not reset; no real
emergency call or paid model call is made. Downloads/screenshots are in ignored
`artifacts/insurance-desktop` and `artifacts/insurance-mobile`. The download
inspection helper parses the actual PDF/CSV/ZIP and compares original image
hashes. The full visual suite remains `npm run test:visual`.
