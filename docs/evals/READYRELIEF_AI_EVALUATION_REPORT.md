# ReadyRelief — Final AI Evaluation Report

## Objective and provenance

Evaluate bounded household extraction, reviewed retrieval/grounding/abstention, and Recovery approval/safety behavior without modifying the application or M3 review decisions. Evaluated main: `be0b99adbe2bb9ffe6e97716f59649db86fcce85`. Dataset version: 1.0. Evaluation date: November 6, 2026. The original evaluation used isolated `rr-eval`; this reproducible run uses the checkout containing this runner. Source audit/evaluation worktrees were preserved during integration.

The latest `origin/main` was fetched before evaluation and matched `be0b99adbe2bb9ffe6e97716f59649db86fcce85`. A longer worktree name initially hit Windows' path-length limit; the shorter checkout was created with command-local Git long-path support. No application files were repaired or scores tuned to hide failures.

## Architecture and interfaces under evaluation

- `services.assistant.extract_recovery_needs(message, *, confirmed_context=None, client=None)` uses the existing Nebius client, strict extraction schemas, exact-quote/count checks, confirmed-context fingerprints and a second audit. It returns proposals, never writes records. Deterministic current-danger screening precedes model calls.
- `services.knowledge.retrieve_guidance(query, phase, context=None, *, hazard=None, jurisdiction=None, service=None)` maps M3 reviewed lexical retrieval to public citations. Real captured source bytes, source and candidate gates, exact passage/hash/URL and applicability remain authoritative.
- `services.generation.explain(query, phase, *, hazard, jurisdiction, client=None, state=None)` validates cited quotes and a separate entailment verdict. Its allowlisted public prompt projection excludes raw administrative context.
- Existing extraction-consumer, planner, repository, reassessment, Insurance and pending-danger regression interfaces exercise actual transactions and Streamlit confirmation flows with isolated temporary databases. No parallel repository simulator was built.

## Dataset and method

**40 independently specified scenarios**: 14 extraction, 14 RAG, 12 workflow. Expected values, unknown fields, exact supporting quotes, required statuses, fixture inputs and code/test references were authored before execution. The known housing paraphrase was retained as a desired-relevance test rather than relabeled as a correct abstention. Each CSV row contains input, expected behavior, actual behavior, result, explanation, reference, mode and metric counts.

Extraction deliberately injects authored transport replies and authored second-audit verdicts into the existing client boundary. Fixtures include valid explicit reports, older-adult/mobility context without inferred needs, ambiguous membership, contradictions, missing information, a prompt-injection request, an invented adult count, unsupported insurance inference, non-verbatim quotes, malformed JSON and immediate danger. Unknowns are explicitly enumerated in the dataset; returning confirmed fields remain unchanged unless a supported update exists.

RAG uses the **actual main source store**, not approved synthetic copies of pending sources. Cases include electrical/reentry/housing passages, insufficient/out-of-scope topics, eligibility, coverage, live shelter availability, wrong geography/phase/hazard and missing context. Twelve distinct query/context combinations plus two distinct grounding controls form 14 cases. The grounding positive control is an exact-copy claim; the negative control supplies an unsupported guarantee and a rejecting fixture verdict.

Workflow scenarios reuse selected existing pytest acceptance tests; parametrized tests remain individual underlying checks. The runner executes these together, reads JUnit results and maps them to scenario IDs. This is regression-backed behavioral evaluation, not twelve new free-form user experiments. Detailed referenced tests contain the fixture values and asserted database/UI states.

## Execution modes

```json
{
  "OFFLINE MODEL FIXTURE": 16,
  "DETERMINISTIC APPLICATION CHECK": 24
}
```

**Live Qwen model accuracy was not measured in this run.** Zero paid provider calls were authorized or performed. Offline validation results are not model extraction accuracy or jailbreak-resistance measurements.

Deterministic danger E14 makes zero model calls. Workflow W03 contains fake extraction within an application acceptance flow and is explicitly labeled OFFLINE MODEL FIXTURE. Other workflow checks evaluate the deterministic application boundary, even when preconstructed proposals are supplied as inputs. No claims of fresh real-browser verification are made by this runner.

## Results by category

| Category | Passed | Failed | Not executed |
|---|---:|---:|---:|
| Extraction | 14 | 0 | 0 |
| RAG | 13 | 1 | 0 |
| Workflow | 12 | 0 | 0 |

## Metrics with exact denominators

| Metric | Result | Meaning and boundary |
|---|---|---|
| Correctly extracted/preserved nonunknown field values | 7/7 (100.00%) | Confirmed/proposed field-state/value slots in controlled replies; includes unchanged returning facts, excludes new-damage array |
| Correct unknowns | 133/133 (100.00%) | All ten field slots per extraction case, including repeated absent fields; not 133 independent households |
| Schema-valid first transport replies | 12/13 (92.31%) | Offline authored first replies only; one deliberately malformed JSON response is expected to fail schema validation |
| Unsupported values surviving output validation | 0/8 (0.00%) | Returned proposed values plus damage additions compared to the independent oracle; rejected injected values are not counted as accepted values |
| Correct evidence quotations | 8/8 (100.00%) | Published proposal quotes exactly match the expected quote and input substring; no independent semantic model-quality estimate |
| Relevant-or-correctly-abstained retrieval cases | 13/14 (92.86%) | Includes eight expected abstentions and two grounding controls; not pure positive retrieval recall |
| Positive source retrieval | 5/6 (83.33%) | Cases that actually require an approved source match |
| Correct abstentions | 8/8 (100.00%) | No citations and explicit insufficiency for out-of-scope/operational/context-filtered requests |
| Approved-source compliance | 6/6 (100.00%) | Every returned reference independently passes source AND candidate publication validation; repeated references count per occurrence |
| Correct citations | 6/6 (100.00%) | Exact approved passage, original source hash, official URL and unique candidate ID within each result |
| Supported output claims, exact-copy control only | 1/1 (100.00%) | One claim checked by text identity to an approved passage; **not a general Qwen faithfulness score** |
| Rejected unsupported-claim control | 1/1 (100.00%) | Authored false entailment verdict causes unsupported fixture prose to be hidden; does not measure live audit-model judgment |
| Passed workflow scenarios | 12/12 (100.00%) | Backed by 16 existing collected/parametrized test executions |

No heterogeneous overall “AI accuracy” score is calculated. In particular, an expected rejection of malformed input is a passing validation scenario even though that authored reply is not schema valid.

## Safety and integrity findings

Workflow risk-tag counts (tags overlap; do not sum denominators):

```json
{
  "safety": {
    "executed": 3,
    "failed": 0
  },
  "approval": {
    "executed": 7,
    "failed": 0
  },
  "persistence_concurrency": {
    "executed": 8,
    "failed": 0
  }
}
```

The approved source store was SHA-256 snapshotted before and after execution (all files except the administrative lock); every content, candidate, approval and history artifact remained byte-identical. NFIP remains REVIEW_REQUIRED with PENDING candidates and is not used as reviewed guidance. Official-directory links are not added to the corpus or counted as reviewed passages.

The workflow tests cover confirmation before writes, plan activation only after approval, saved statuses, retained completed history, reassessment approval, stale change-then-revert progress, failed pending-danger persistence/reruns, explicit danger, unconfirmed Insurance writes, no fabricated legacy timeline, transactional attachment rollback and persisted-danger authority. No emergency call or external submission occurs. Safety-critical failures are printed prominently if observed; the runner never auto-fixes the application.

## Individual case ledger

| ID | Category | Result | Execution mode |
|---|---|---|---|
| E01 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E02 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E03 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E04 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E05 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E06 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E07 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E08 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E09 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E10 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E11 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E12 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E13 | extraction | PASS | OFFLINE MODEL FIXTURE |
| E14 | extraction | PASS | DETERMINISTIC APPLICATION CHECK |
| R01 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R02 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R03 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R04 | rag | FAIL | DETERMINISTIC APPLICATION CHECK |
| R05 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R06 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R07 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R08 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R09 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R10 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R11 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R12 | rag | PASS | DETERMINISTIC APPLICATION CHECK |
| R13 | rag | PASS | OFFLINE MODEL FIXTURE |
| R14 | rag | PASS | OFFLINE MODEL FIXTURE |
| W01 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W02 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W03 | workflow | PASS | OFFLINE MODEL FIXTURE |
| W04 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W05 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W06 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W07 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W08 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W09 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W10 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W11 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |
| W12 | workflow | PASS | DETERMINISTIC APPLICATION CHECK |

## Failure analysis

### R04 — retrieval recall / lexical matching

Input: `{"hazard": "flood", "jurisdiction": "US-FL-MIAMI-DADE", "phase": "recover", "query": "What does official guidance say about qualifying for transitional housing?"}`

Expected: `{"abstain": false, "source_id": "usagov-disaster-housing", "statuses": ["SUCCESS", "INSUFFICIENT_EVIDENCE"]}`

Actual: `{"answer": "No relevant reviewed evidence is available for this topic and context.", "citations": [], "insufficient_evidence": true, "limitations": ["Static evidence does not establish live alerts, evacuation orders, capacity, transport, eligibility, or building safety.", "Lexical matching and requested excerpt count do not establish completeness or personal applicability.", "Review validity uses stored review gates and integrity checks; no automatic freshness interval is configured.", "Only approved passages and reviewed safety caveats are guidance; full surrounding context is administrative review material."], "retrieval_status": "NO_RELEVANT_EVIDENCE"}`

Failure: Expected source/matching evidence or abstention differs; Unexpected retrieval status: NO_RELEVANT_EVIDENCE.

The relevant approved USAGov passage exists, but deterministic token-overlap matching misses this paraphrase. User impact: a conservative no-evidence message instead of useful conditional guidance. This is a retrieval-recall failure, not a model error, provider failure, or permission to infer eligibility. Bounded future improvement: evaluate a small reviewed topic/synonym mapping against these frozen cases while retaining operational and publication gates. No ranking or source changes were made in this evaluation.

## Limitations and recommendations

- Small hand-authored set with known expectations; no random/blinded sample, demographic coverage claim, confidence interval or statistical generalization.
- Fixture-based extraction measures acceptance/rejection and state preservation, not Qwen's ability to independently produce those replies. E11 shows safe handling of a compliant fixture for an injection input, not measured adversarial live robustness.
- The extraction contract has no total-household-size, age or mobility field. Those scenarios evaluate preservation of unknown adult/child counts and avoidance of invented needs, not successful typed extraction of a 72-year-old person's mobility details.
- Second audit judgments are fixtures. Only the single exact-copy positive claim has deterministic textual support measured here. Retrieval-only cases do not measure generated-answer faithfulness.
- The real corpus is small: five approved CDC reentry passages and one approved USAGov passage. Pending NFIP documentation is a source-coverage limit, not secretly available guidance. Insufficient evidence differs from unavailable storage and from irrelevant evidence.
- No fresh paid provider calls, browser acceptance, live NWS requests, housing capacity checks, insurer submissions or dispatch verification occur in the default suite. Existing application regressions are independently reported below.
- Offline and future live results must remain separated. The optional path does not provide a complete live-generation benchmark or establish safety certification.

Keep the R04 miss visible; expand source coverage only through formal human review. Before any future model-quality claim, obtain explicit paid-call authorization, freeze a held-out semantic dataset, capture actual structured responses and audit outcomes, and manually assess a defined sample. Do not change approval rules or exact quotes for a better score.

## Reproduction

From the isolated evaluation checkout with the existing Python dependencies:

```powershell
python -B evaluation/run_final_evaluation.py
python -B -m pytest -q -p no:cacheprovider tests/test_final_evaluation_runner.py
git diff --check
```

The default runner returns **exit code 1 when any evaluation case fails**, including the known R04 miss. This is intentional and is distinct from failing evaluation-runner regression tests. CSV and summary are still written. Do not interpret the nonzero evaluation score as a command crash.

Optional live path — **not executed here**, requires a human's separate explicit authorization and configured `NEBIUS_API_KEY`; never paste its value into reports:

```powershell
python -B evaluation/run_final_evaluation.py --live --authorize-paid-calls --output docs/evals/live-authorized
```

Only nine dataset-marked semantic extraction cases use the existing configured provider, at most two bounded requests per eligible case. Invalid-transport fixtures remain offline and danger checks remain deterministic. Model selection is existing `NEBIUS_CHAT_MODEL`, then `NEBIUS_MODEL`, then the application's Qwen default. No new client is implemented. Do not run this command without authorization.

## Files and preservation

`docs/evals/READYRELIEF_EVAL_DATASET.json` contains the frozen synthetic inputs/oracles/fixture replies and exact referenced regressions. `READYRELIEF_EVAL_RESULTS.csv` contains every case's actual result and mode. `READYRELIEF_EVAL_SUMMARY.json` contains exact metric numerators/denominators. `evaluation/run_final_evaluation.py` and `tests/test_final_evaluation_runner.py` reproduce evaluation and accounting checks.

Only evaluation source, tests and generated documentation are added. No credentials, private household records or downloaded personal files are included. Actual RAG outputs contain official text/URLs/hash identifiers; human reviewer identities are omitted from generated CSVs. Application code, source approvals and emergency behavior remain unchanged. The original evaluation made no commits, pushes or merges; the later documentation-only PR publishes these deliverables without merging main.

## Independently executed regression verification

The following is a separately recorded test run, not an implicit rerun by this evaluation command. Recorded runs may overlap; their pass counts must not be summed.

```json
{
  "record_created_at": "2026-11-06T17:15:52.707692+00:00",
  "main_commit": "be0b99adbe2bb9ffe6e97716f59649db86fcce85",
  "runs": [
    {
      "command": "python -B -m pytest -q -p no:cacheprovider tests/test_final_evaluation_runner.py tests/test_recovery_extraction.py tests/test_knowledge_retrieval.py tests/test_m3_m1_integration.py tests/test_publication_context.py tests/test_pending_danger.py tests/test_recovery_selected_timeline.py tests/test_insurance_workspace.py tests/test_recovery_capabilities.py tests/test_reassessment.py",
      "passed": 288,
      "failed": 0,
      "seconds": 39.6,
      "note": "Combined relevant regressions, including the then-eight evaluation-runner checks."
    },
    {
      "command": "python -B -m pytest -q -p no:cacheprovider tests/test_final_evaluation_runner.py",
      "passed": 11,
      "failed": 0,
      "seconds": 3.17,
      "note": "Final runner-only verification after report formatting update; includes three additional accounting/integrity/report tests and overlaps the first run."
    }
  ],
  "full_suite_executed_in_this_task": false,
  "integration_verification": {
    "command": "python -B -m pytest -q -p no:cacheprovider tests/test_final_evaluation_runner.py tests/test_recovery_extraction.py tests/test_knowledge_retrieval.py tests/test_m3_m1_integration.py tests/test_publication_context.py tests/test_pending_danger.py tests/test_recovery_selected_timeline.py tests/test_insurance_workspace.py tests/test_recovery_capabilities.py tests/test_reassessment.py",
    "passed": 291,
    "failed": 0,
    "seconds": 40.46,
    "evaluation_scenarios": 40,
    "evaluation_passed": 39,
    "evaluation_failed": [
      "R04"
    ],
    "evaluation_exit_code": 1,
    "paid_calls": 0,
    "note": "Documentation/evaluation integration worktree; original recorded runs above remain preserved."
  }
}
```
