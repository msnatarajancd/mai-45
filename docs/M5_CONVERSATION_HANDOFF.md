# Conversation-first Recovery: M1 extraction handoff

The landing description currently selects a section locally. It is not AI
extraction, is never saved to SQLite, and does not prefill confirmed facts.
Deterministic explicit-danger checks run before opening storage or using a model.
The structured intake remains available in an expander. Saved cases reuse existing
intake/records; utility changes use existing reassessment approval.

## Existing boundaries inspected

`services.generation.explain()` explains approved M3 evidence; it is not a household
extraction API. `services.assistant.propose()` produces bounded actions, but its
`Intake` requires a Hurricane/Flood classification, housing, utilities, accommodation
and needs. It has no nullable per-field recovery extraction result or damage/children
proposal. Its session `Household` defaults must not become confirmed case facts.
No M1/M3 interface or model client was changed for this enhancement.

## Proposed smallest M1-owned addition (not implemented)

```python
extract_recovery_needs(
    message: str, *, confirmed_context: dict, client=None
) -> RecoveryNeedsProposal
```

Reuse the existing Nebius client and structured validation. The proposal should
contain optional explicitly reported intake changes, optional children/adults,
damage descriptions, insurance-help request, supporting user-text spans and missing
information. Omitted fields mean unchanged/unknown, not default values or deletion.
The confirmed context must include case intake and versioned M5 recovery records,
not session household defaults. Keep danger assessment out of model authority.

Reject unknown fields and invalid types; errors return no usable proposal. Do not
persist raw messages or execute writes. M5 can then provide an editable review
card, bind proposals to case/record versions, and use existing explicit approvals.
Newly reported danger interrupts before calling this interface; persisted danger
still blocks acceptance at the repository boundary. Utilities must continue through
existing reassessment rather than record writes. Partial extraction must not
approve plans or mark assistance as available.

Until that owner-reviewed interface exists, invalid/failing Qwen extraction cannot
affect this landing flow because it makes no extraction calls. Users retain fully
working structured confirmation, damage records, summary download and plan progress.

## Browser rehearsal

Open Recover, enter a short description and use Help me get started. Verify no case
was created, section selection is labeled local, and optional intake is accessible.
Resume an existing fictional case; use Document damage, Prepare for insurance and
Continue my recovery independently. Check saved data prefills and only confirmed
edits persist. Enter an explicit danger report and verify emergency interruption.
Repeat with unavailable storage and no API key; emergency controls must remain.
