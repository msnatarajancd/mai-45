# M1 → M5 recovery extraction contract

Status: compatibility approved by M5; the requested danger-precheck correction passed
on November 4, 2026. Integrated into main after the combined regression checks passed.
The shared contract remains unchanged from the reviewed extraction branch.

```python
extract_recovery_needs(
    message: str,
    *,
    confirmed_context: RecoveryConfirmedContext | None = None,
    client: RecoveryLLMClient | None = None,
) -> RecoveryExtractionResult
```

The function only proposes information. It never applies proposals, accesses a repository
or session state, or submits data to an assistance/insurance service. Its only external
operation is the requested model extraction using the existing Nebius client.

## Result

| Property | Contract |
| --- | --- |
| `status` | `SUCCESS`, `NEEDS_CLARIFICATION`, `DANGER_DETECTED`, `UNAVAILABLE`, or `ERROR` |
| `base_context_fingerprint` | SHA-256 of the validated, canonical confirmed-context DTO, computed locally; null only for invalid context |
| `fields` | Typed field proposals listed below; every field is present |
| `new_damage` | Additive proposed damage entries; never a replacement inventory |
| `clarification_questions` | Bounded list of questions; no safety clearance or executable instructions |
| `error_code` | Application-owned code or null; no raw provider errors |

Each field has `state`, `value`, and `source_quote`:

- `UNKNOWN`: value and quote are null; no confirmed value and no supported proposal.
- `UNCHANGED`: value is the confirmed value and quote is null. The application fills this
  from confirmed context rather than accepting model-generated prior information.
- `PROPOSED`: non-null, field-specific value and an exact supporting substring from the
  current message. Human correction and confirmation are required before saving.

## Field names and values

| Field | Non-null value type |
| --- | --- |
| `disaster_type` | `Flood` or `Hurricane` |
| `reported_county` | Bounded text explicitly supplied by the user; no city/location-ID conversion |
| `housing_condition` | `Flooded`, `Minor reported damage`, `Major reported damage`, `Destroyed`, or `No damage reported`; never inferred from utility conditions |
| `electricity` | `Available` or `Unavailable` |
| `water` | `Available` or `Unavailable`; describes reported availability, never potability |
| `temporary_accommodation` | `Needed`, `Staying with others`, `Temporary lodging`, or `Not needed` |
| `household_recovery_needs` | List drawn from `Temporary housing`, `Water and household supplies`, `Transportation`, `Damage documentation`, `Insurance preparation` |
| `children` | Strict integer 0–100, only when explicitly stated |
| `adults` | Strict integer 0–100, only when explicitly stated; never inferred from pronouns, children, or a household total |
| `insurance_preparation_requested` | Strict boolean, only when explicitly requested or declined |

Each `new_damage` entry has `state=PROPOSED`, a bounded text `value` describing a reported
damaged item, and an exact `source_quote`. Existing damage stays in confirmed context.
No item IDs, estimated values, ownership, coverage decisions, or claim submissions are inferred.

`RecoveryConfirmedContext` contains the same nullable field values, `reported_damage`
(a bounded list of text entries), and `danger_reported` (boolean or null). It contains no
record IDs, addresses, approvals, tasks, private notes, or M5 model references. Unknown
properties and invalid types are rejected. The function never mutates the DTO.

## Safety and consumer responsibilities

Current explicit danger, or `danger_reported=True` in confirmed context, returns
`DANGER_DETECTED` before any model call. This is a conservative routing signal, not a
complete danger classifier. Absence of a detected phrase does not establish safety.

No output field may set or clear danger, declare a household safe, approve a plan, or
execute an action. `SUCCESS` means validated extraction, not completeness, safety,
approval, or persistence. M5 must still perform its separate safety assessment.

M5 owns displaying the proposals and quotes, asking clarification questions, allowing
corrections, rechecking the latest confirmed-context fingerprint, enforcing persisted-danger
protection, and obtaining explicit confirmation before applying changes. Only PROPOSED
fields are candidates for update; new damage is additive. Unknown fields never erase data.
`household_recovery_needs` proposals contain the union of confirmed needs and supported
additions. The quote supports the additions; confirmed needs remain supported by the base
context. Removal is not implemented in this extraction interface. Damage entries are
deduplicated case-insensitively by item text; distinguishing multiple identical items or
editing existing damage belongs to M5 review.

Invalid model JSON, unknown properties, invalid types, and unsupported/nonverbatim quotes
return an error without usable proposed changes. Provider/configuration failures return
sanitized unavailable results. No mock is silently substituted for live generation.

Error codes: `invalid_context`, `invalid_message`, `invalid_model_output`,
`unsupported_extraction`, `missing_key`, `timeout`, `provider_error`. Failure results
contain no proposed changes and retain validated confirmed values where available.
Messages are bounded to 2,500 characters; damage proposals to 20; confirmed damage to
50 items. Fields use strict JSON types (numeric strings and booleans are not counts).

Two calls use the same `RecoveryLLMClient`: structured extraction and semantic support/
ambiguity review. Both use the existing `NebiusClient` transport; the default Qwen model
follows `NEBIUS_CHAT_MODEL`, then `NEBIUS_MODEL`, then
`Qwen/Qwen3-235B-A22B-Instruct-2507`. Each request has a 25-second timeout; no automatic retry
or mock fallback. The second model check reduces unsupported interpretations but is not
an independent truth source or a guarantee of correctness. Human review remains mandatory.

Counts additionally require a verbatim count next to children/kids or adults/grown-ups.
Digits 0–100 and words zero–twenty/no are supported by this conservative lexical check;
other phrasing may fail validation and can be corrected in M5's review flow. County and
damage-item names must appear verbatim in the quote (case-insensitive name matching).
Flooded housing does not imply major damage. Reported water availability does not imply
potability. Fixed application-owned clarification questions are used instead of model prose.

## Examples

For the lead's flooded-apartment scenario: propose Flood, Miami-Dade, two children,
unavailable electricity, needed accommodation, furniture damage, and requested insurance
preparation. Adults remain UNKNOWN. Housing can only describe explicitly reported flooding;
no damage severity or safety conclusion is inferred.

For “Electricity came back, but our refrigerator is damaged”: propose available electricity
and additive refrigerator damage. Confirmed furniture and all other confirmed information
remain unchanged. If confirmed danger is true, return DANGER_DETECTED without model extraction.

## Implementation and verification scope

Implementation stays in `services/assistant.py`, focused tests in
`tests/test_recovery_extraction.py`, and the final agreed contract in `docs/ASSISTANT.md`.
The executable Action union, `services/generation.py`, M5 persistence, and Recovery UI
remain unchanged. Test both lead scenarios, ambiguity, unsupported values/quotes,
strict JSON/schema rejection, sanitized failures, danger bypass, and no mutation.
Run existing assistant and grounded-generation tests. Report a real fictional Nebius
extraction separately from test doubles. Merge only after interface coordination.
