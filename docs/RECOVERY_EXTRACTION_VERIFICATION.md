# Recovery extraction verification

Review branch: `m1/recovery-needs-extraction`. No Recovery UI or persistence changes.

## Automated tests — synthetic provider replies

Command:

```text
.venv/Scripts/python.exe -m pytest tests/test_recovery_extraction.py tests/test_assistant.py tests/test_assistant_ui.py tests/test_grounded_generation.py tests/test_grounded_ui.py -q --basetemp="D:/Documents/Code Repos/.t-extract" --tb=short
```

Result: **100 passed**. Coverage includes both lead scenarios, unknown adults, preserved
confirmed information, additive/deduplicated damage and recovery needs, ambiguity,
unsupported counts/quotes, malformed/duplicate-key JSON, forbidden properties,
strict boolean/integer types, invalid confirmed context, sanitized errors in both model
stages, prior/current danger bypass, context fingerprint changes, concurrent caller list
mutation, no repository/session access, and existing assistant/grounded generation behavior.
Tests use labelled provider doubles; they do not claim real model generation.

## Real Nebius/Qwen calls — fictional data

Final check started **November 3, 2026 at 10:00:57 PM Eastern**
(`2026-11-04T03:00:57.774892+00:00`). Model:
`Qwen/Qwen3-235B-A22B-Instruct-2507`, using the existing `NebiusClient` and server credential.
Each scenario made two real requests: extraction and support/ambiguity verification.
No mock, database write, action execution, or external assistance submission was used.

### New household

Input: “Our apartment flooded in Miami-Dade. We have two children, no electricity, and
nowhere to stay tonight. Our furniture is damaged and I need insurance help.”

Returned `SUCCESS` in **4.81 seconds**:

| Information | Returned proposal | Supporting quote |
| --- | --- | --- |
| Disaster | Flood | Our apartment flooded in Miami-Dade. |
| County | Miami-Dade | Our apartment flooded in Miami-Dade. |
| Housing | Flooded | Our apartment flooded in Miami-Dade. |
| Children | 2 | We have two children |
| Adults | UNKNOWN / null | None |
| Electricity | Unavailable | no electricity |
| Temporary accommodation | Needed | nowhere to stay tonight |
| New damage | furniture | Our furniture is damaged |
| Insurance preparation | true | I need insurance help |

Recovery needs contained Temporary housing and Insurance preparation. Water stayed unknown.
There was no safety-clearance field or decision. M5's separate assessment is still required.

### Returning household

Confirmed DTO: electricity Unavailable; damage Furniture; children 2; danger not assessed.
Input: “Electricity came back, but our refrigerator is damaged.”

Returned `SUCCESS` in **2.64 seconds**:

- Electricity: PROPOSED Available, quote `Electricity came back`.
- New damage: PROPOSED refrigerator, quote `our refrigerator is damaged`.
- Children: UNCHANGED 2. Adults: UNKNOWN. Confirmed Furniture remained untouched.
- No safety decision or automatic save occurred.

## Limits observed

Earlier live prompt iterations sometimes requested unnecessary clarification, omitted a
reported field, inferred a documentation need, or emitted an incorrectly nested damage field.
The validator rejected malformed/unsupported output; ambiguous fields were withheld.
Prompts were clarified and an explicit documentation-request check added. The final two
results above passed. They are observations, not a guarantee of future model accuracy.

Exact quotes and the second Qwen check reduce errors but cannot prove semantic correctness.
M5 must retain review/correction, explicit confirmation, current-context fingerprint checking,
transaction/version checks, and persisted-danger protection. The deterministic danger matcher
is conservative and incomplete; an unflagged message never establishes safety.
