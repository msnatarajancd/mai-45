# Live Qwen extraction rejection diagnosis

## Evidence and scope

The earlier integration attempt retained only ERROR / invalid_model_output, not its raw
response; its exact rejected fields cannot be proven retrospectively. One instrumented
reproduction through app.py / request_extraction on November 5, 2026 used the same
fictional five-person/elderly-family-member description.
The existing NebiusClient and real M1 service were used, with no fabricated response.
Diagnostics wrapped the parser/quote validator in memory without changing their behavior.

The response was valid JSON and satisfied _RecoveryModelExtraction's strict schema.
It proposed these invalid facts:

```json
{
  "adults": {"state": "PROPOSED", "value": 5, "source_quote": "We are five people at home"},
  "children": {"state": "PROPOSED", "value": 0, "source_quote": "We are five people at home"}
}
```

_check_recovery_quotes checks children before adults. _count_supported requires an
explicit matching child/adult count in the exact quote; `five people` supplies neither.
The children=0 proposal therefore raises `ValueError: Household count is not explicit`;
the adults=5 proposal independently fails the same rule. The service converts that
failure to ERROR / invalid_model_output before calling the second semantic audit.
No case was created. This is not a transport, enum, JSON, DTO fingerprint or M5 delivery
failure, and the output must NOT be accepted or automatically repaired.

The exact captured response is retained as a fictional test fixture only:
`tests/fixtures/synthetic_qwen_household_total_rejected.json`. It contains no credentials,
request headers, private household information or official guidance.

## Bounded correction

Only extraction prompt wording changes: an explicit five-person-household counterexample
requires omitting both count fields when neither category was reported, distinguishes
zero from unknown, and forbids inferring services from an elderly family member alone.
Schemas, statuses, exact quotes, count validation, parsers, safety checks and persistence
requirements remain unchanged. Invalid replies remain rejected in their entirety.

A synthetic valid counterpart in tests represents a provider omitting unsupported counts;
it is not a production response-repair operation. Additional regression coverage keeps
altered quotes invalid and confirms rejection preserves saved progress and structured input.

## Live limitation

The instrumented live reproduction failed safely. Per the instruction not to repeat paid
calls after a failure, no further paid attempt was made, including after the prompt change.
At that diagnostic checkpoint, successful live proposals remained unverified; mocked tests
alone could not establish model compliance. A separately authorized live acceptance check
subsequently passed, as recorded below. The failed response and its regression fixture
remain unchanged as evidence that invented counts must be rejected.


## Offline verification

Affected extraction/consumer/pending-danger integration tests: **119 passed**.
Complete suite: **744 passed, 11 skipped, 10 subtests passed**.
All automated provider responses are fake or the explicitly labeled recorded synthetic
fixture. No new live calls were made by pytest. Whitespace checks pass.


## Subsequent authorized live verification ? November 5, 2026

The later final verification used four real Nebius requests with the corrected prompt
and unchanged validators, through app.py / Streamlit AppTest. The new-household result
was NEEDS_CLARIFICATION with adult/child counts unknown and supported proposals staged;
the returning result was SUCCESS with supported electricity and refrigerator proposals.
Both quote/schema checks and semantic audits passed, and fingerprints matched.
No household data changed before confirmation. Explicitly confirmed updates preserved
earlier damage, approved-plan history and completed progress in a temporary fictional DB.
This supersedes the earlier live-readiness limitation, not the diagnosis or safety rules.
No real-browser acceptance is claimed. See M5_CONVERSATION_HANDOFF.md for the call path.
