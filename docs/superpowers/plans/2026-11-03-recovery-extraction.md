# Recovery needs extraction implementation plan

**Goal:** Provide M5 a non-executing, validated Qwen extraction interface for human review.

**Architecture:** Add isolated schemas and an extraction function to `services/assistant.py`.
Reuse `RecoveryLLMClient` / `NebiusClient`. Keep the executable Action union, generation,
repositories, UI, and persisted danger handling unchanged. Publish on a feature branch for
interface review before merging.

**Contract under review:** `extract_recovery_needs(message, *, confirmed_context=None,
client=None) -> RecoveryExtractionResult`. Result fields: status, base_context_fingerprint,
fields, new_damage, clarification_questions, error_code. Statuses: SUCCESS,
NEEDS_CLARIFICATION, DANGER_DETECTED, UNAVAILABLE, ERROR. Each field has UNKNOWN,
UNCHANGED, or PROPOSED state, a typed nullable value, and an exact source_quote for proposals.
Unknown/unchanged state and the fingerprint are resolved locally, not trusted to the model.
Damage proposals are additive; confirmed damage is never replaced.

**Boundary:** Safety assessment is always separate and still required. Danger in the
message or confirmed context interrupts before Qwen. No record IDs, safety decisions,
approvals, actions, session access, or database access are accepted by the new interface.

- [x] Settle the exact contract with the user/M5 before implementation.
- [x] Add failing tests for both lead scenarios, state preservation, unknown adults,
  ambiguity, quote validation, malformed responses, provider errors, and danger bypass.
- [x] Implement strict typed DTOs, canonical context fingerprinting, deterministic danger
  routing, provider calls, validation, and sanitized outcomes.
- [x] Document field names/types, merge semantics, limitations, and caller obligations in
  `docs/ASSISTANT.md`.
- [x] Run focused extraction, existing assistant, and grounded-generation tests.
- [x] Run one real fictional Qwen extraction using the existing server credential if available;
  report the actual result separately from test doubles, without printing credentials.
- [ ] Commit/push the review branch; obtain interface coordination before merging.
