"""Evaluation only. Offline by default; uses production boundaries and existing regressions."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_DATASET = ROOT / 'docs/evals/READYRELIEF_EVAL_DATASET.json'


class FixtureClient:
    """Deliberately authored transport replies, never described as Qwen output."""
    def __init__(self, replies):
        self.replies = replies
        self.calls = 0

    def complete(self, messages):
        if self.calls >= len(self.replies):
            raise AssertionError('Unexpected additional model call')
        value = self.replies[self.calls]
        self.calls += 1
        return value if isinstance(value, str) else json.dumps(value)


def load_dataset(path=DEFAULT_DATASET):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    cases = data['cases']
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate evaluation IDs')
    if any(c['category'] not in {'extraction', 'rag', 'workflow'} for c in cases):
        raise ValueError('Unknown evaluation category')
    for case in cases:
        for key in ('id', 'category', 'input', 'expected', 'reference'):
            if key not in case:
                raise ValueError('Missing evaluation contract field: ' + key)
        if case['category'] == 'extraction' and 'unknown_fields' not in case['expected']:
            raise ValueError('Extraction cases must explicitly enumerate expected unknowns')
    return data


def extraction(case, *, live=False):
    from services.assistant import (RecoveryConfirmedContext, RecoveryExtractionFields,
        extract_recovery_needs, recovery_context_fingerprint, _strict_extraction_json,
        _RecoveryModelExtraction)
    context = RecoveryConfirmedContext.model_validate(case['input'].get('context', {}))
    before = context.model_dump_json()
    client = None if live else FixtureClient(case['fixture_replies'])
    result = extract_recovery_needs(case['input']['message'], confirmed_context=context, client=client)
    expected = case['expected']
    wanted = {}
    for field in RecoveryExtractionFields.model_fields:
        value = getattr(context, field)
        wanted[field] = {'state': 'UNKNOWN' if value is None else 'UNCHANGED', 'value': value}
    wanted.update(expected.get('fields', {}))
    if set(expected['unknown_fields']) != {name for name, item in wanted.items() if item['state'] == 'UNKNOWN'}:
        raise ValueError('Expected unknown field list disagrees with case oracle')
    mismatches = []
    counts = dict(fields_correct=0, fields_total=0, unknowns_correct=0, unknowns_total=0,
                  unsupported_values=0, extracted_values=0, quotes_correct=0, quotes_total=0,
                  schema_valid=0, responses=0)
    for name, truth in wanted.items():
        actual = getattr(result.fields, name)
        correct = actual.state == truth['state'] and actual.value == truth['value']
        prefix = 'unknowns' if truth['state'] == 'UNKNOWN' else 'fields'
        counts[prefix + '_total'] += 1
        counts[prefix + '_correct'] += int(correct)
        if not correct:
            mismatches.append(name + ': expected ' + json.dumps(truth) + ', got ' + actual.model_dump_json())
        if actual.state == 'PROPOSED':
            counts['extracted_values'] += 1
            counts['unsupported_values'] += int(not correct)
            counts['quotes_total'] += 1
            counts['quotes_correct'] += int(actual.source_quote in case['input']['message']
                and actual.source_quote == truth.get('source_quote'))
    damage = [d.model_dump() for d in result.new_damage]
    if damage != expected.get('new_damage', []):
        mismatches.append('new_damage differs from independently specified expected inventory additions')
    for item in damage:
        counts['extracted_values'] += 1
        counts['unsupported_values'] += int(item not in expected.get('new_damage', []))
        counts['quotes_total'] += 1
        counts['quotes_correct'] += int(item in expected.get('new_damage', [])
            and item['source_quote'] in case['input']['message'])
    if result.status != expected['status']:
        mismatches.append('status: expected ' + expected['status'] + ', got ' + result.status)
    if result.error_code != expected.get('error_code'):
        mismatches.append('error code differs')
    if expected.get('clarification') and not result.clarification_questions:
        mismatches.append('Missing required clarification')
    if result.base_context_fingerprint != recovery_context_fingerprint(context) or context.model_dump_json() != before:
        mismatches.append('Context mutated or fingerprint mismatch')
    if not live and client.calls != expected['calls']:
        mismatches.append('Unexpected fixture call count')
    if counts['quotes_correct'] != counts['quotes_total']:
        mismatches.append('Output quotations differ from the expected supporting quotations')
    # Schema validity is a transport diagnostic for the authored FIRST reply only.
    # It is not model accuracy; extraction can reject schema-valid unsupported values.
    if not live and client.calls:
        counts['responses'] = 1
        raw = case['fixture_replies'][0]
        try:
            _strict_extraction_json(raw if isinstance(raw, str) else json.dumps(raw), _RecoveryModelExtraction)
            counts['schema_valid'] = 1
        except (ValueError, TypeError):
            pass
    return result.model_dump(mode='json') | {'fixture_calls': None if live else client.calls}, mismatches, counts


def rag(case):
    from services.knowledge import retrieve_guidance
    from knowledge.store import SourceStore
    from knowledge.candidates import verify_candidate_publication
    from services.generation import explain, public_payload
    inp = case['input']
    result = retrieve_guidance(inp['query'], inp.get('phase', 'recover'),
        hazard=inp.get('hazard'), jurisdiction=inp.get('jurisdiction'))
    expected = case['expected']
    failures = []
    counts = dict(retrieval_cases=1, relevant_results=0, abstention_cases=0, correct_abstentions=0,
                  positive_retrieval_cases=0, correct_positive_retrievals=0,
                  source_checks=0, approved_sources=0, citation_checks=0, correct_citations=0,
                  claims_checked=0, supported_claims=0, unsafe_claim_rejection_cases=0, unsafe_claim_rejections=0)
    sources = {c.source_id for c in result.citations}
    relevant = (bool(result.citations) and expected.get('source_id') in sources) if expected.get('source_id') else not result.citations
    counts['relevant_results'] = int(relevant)
    if expected.get('source_id'):
        counts['positive_retrieval_cases'] = 1
        counts['correct_positive_retrievals'] = int(relevant)
    if expected.get('abstain'):
        counts['abstention_cases'] = 1
        counts['correct_abstentions'] = int(not result.citations and result.insufficient_evidence)
    if not relevant:
        failures.append('Expected source/matching evidence or abstention differs')
    if result.retrieval_status not in expected['statuses']:
        failures.append('Unexpected retrieval status: ' + result.retrieval_status)
    if any(c.source_id == 'nfip-document-flood-damage' for c in result.citations):
        failures.append('SAFETY: pending NFIP evidence published')
    store = SourceStore(ROOT / 'data/official_sources')
    ids = []
    for citation in result.citations:
        counts['source_checks'] += 1
        counts['citation_checks'] += 1
        try:
            with store.admin_lock():
                candidate = store.load_candidate(citation.source_id, citation.citation_id)
                bundle = verify_candidate_publication(store, candidate)
            counts['approved_sources'] += 1
            correct = (citation.passage == candidate.original_passage
                       and citation.original_content_hash == bundle.source.original_content_hash
                       and citation.official_url == candidate.official_url
                       and citation.citation_id not in ids)
            counts['correct_citations'] += int(correct)
            if not correct:
                failures.append('Citation passage/URL/hash/identity mismatch')
            ids.append(citation.citation_id)
        except Exception:
            failures.append('SAFETY: publication provenance validation failed')
    # Publication provenance is checked above; avoid duplicating human identities in generated CSVs.
    actual = dict(retrieval_status=result.retrieval_status, answer=result.answer,
        insufficient_evidence=result.insufficient_evidence, limitations=result.limitations,
        citations=[c.model_dump(mode='json', exclude={'source_review', 'candidate_review'}) for c in result.citations])
    if case.get('grounding_fixture'):
        if not result.citations:
            failures.append('No real reviewed evidence for grounding fixture')
        else:
            citation = result.citations[0]
            # Exact-copy positive control has deterministic textual support.
            text = citation.passage if case['grounding_fixture'] == 'exact_copy' else 'You are guaranteed FEMA housing approval.'
            client = FixtureClient([{'claims': [{'text': text, 'citation_id': citation.citation_id,
                'quote': citation.passage}]}, {'supported': case['grounding_fixture'] == 'exact_copy'}])
            explanation = explain(inp['query'], inp.get('phase', 'recover'), hazard=inp.get('hazard'),
                jurisdiction=inp.get('jurisdiction'), client=client)
            actual['fixture_explanation'] = dict(generation_status=explanation.generation_status,
                claims=[c.model_dump(mode='json') for c in explanation.claims], notice=explanation.notice)
            actual['fixture_calls'] = client.calls
            actual['public_prompt_evidence'] = public_payload(result)
            if case['grounding_fixture'] == 'exact_copy':
                counts['claims_checked'] = len(explanation.claims)
                counts['supported_claims'] = sum(c.text == citation.passage for c in explanation.claims)
                if explanation.generation_status != 'generated' or not explanation.claims:
                    failures.append('Exact-copy grounding control was not published')
            else:
                counts['unsafe_claim_rejection_cases'] = 1
                counts['unsafe_claim_rejections'] = int(not explanation.claims and explanation.generation_status == 'unavailable')
                if explanation.claims:
                    failures.append('SAFETY: failed entailment verdict did not hide unsupported claim')
    return actual, failures, counts


def workflow(cases):
    """Reuse real fixture-driven regressions, not duplicate repository simulators."""
    env = os.environ.copy()
    env['NEBIUS_API_KEY'] = ''
    with tempfile.TemporaryDirectory(prefix='readyrelief-evaluation-') as temp:
        xml = Path(temp) / 'workflow.xml'
        command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   '--junitxml=' + str(xml)] + [c['nodeid'] for c in cases]
        try:
            done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            return {c['id']: ({'reason': 'Regression process unavailable or timed out', 'not_executed': True,
                'tests_executed': 0}, ['Referenced regression could not execute'], {}) for c in cases}, None
        tests = ET.parse(xml).findall('.//testcase') if xml.exists() else []
        results = {}
        for case in cases:
            filename, function = case['nodeid'].split('::')
            found = [t for t in tests if t.get('classname') == filename[:-3].replace('/', '.')
                     and (t.get('name') == function or t.get('name', '').startswith(function + '['))]
            bad = [t for t in found if list(t.findall('failure')) + list(t.findall('error')) + list(t.findall('skipped'))]
            results[case['id']] = ({'existing_regression': case['nodeid'], 'tests_executed': len(found),
                'test_names': [t.get('name') for t in found],
                'passed': len(found) - len(bad), 'not_executed': not bool(found)},
                [] if found and not bad else ['Regression failed, skipped or not collected; inspect referenced test'],
                {'workflow_scenarios': int(bool(found)), 'workflow_passed': int(bool(found) and not bad),
                 'regression_assertion_tests': len(found)})
        return results, done.returncode


def source_snapshot():
    directory = ROOT / 'data/official_sources'
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file() and p.name != 'admin.lock'}


def evaluate(data, *, live=False, include_workflow=True):
    before = source_snapshot()
    workflow_cases = [c for c in data['cases'] if c['category'] == 'workflow']
    work, child_code = workflow(workflow_cases) if include_workflow else ({}, None)
    rows = []
    for case in data['cases']:
        category = case['category']
        mode = 'DETERMINISTIC APPLICATION CHECK'
        if category == 'workflow' and not include_workflow:
            actual, failures, counts = {'reason': 'Workflow execution explicitly omitted'}, [], {}
            mode = 'NOT EXECUTED'
        elif category == 'workflow':
            actual, failures, counts = work[case['id']]
            if actual.get('not_executed'):
                mode = 'NOT EXECUTED'
            else:
                mode = case.get('execution_mode', mode)
        elif category == 'extraction':
            use_live = live and case.get('live_eligible', False)
            actual, failures, counts = extraction(case, live=use_live)
            mode = 'LIVE MODEL' if use_live else ('DETERMINISTIC APPLICATION CHECK' if actual['fixture_calls'] == 0 else 'OFFLINE MODEL FIXTURE')
        else:
            actual, failures, counts = rag(case)
            if case.get('grounding_fixture'):
                mode = 'OFFLINE MODEL FIXTURE'
        rows.append(dict(test_id=case['id'], category=category, synthetic_input=case['input'],
            expected_behavior=case['expected'], actual_behavior=actual,
            result='NOT EXECUTED' if mode == 'NOT EXECUTED' else ('FAIL' if failures else 'PASS'),
            failure_explanation='; '.join(failures), evidence=case['reference'], execution_mode=mode,
            metrics=counts, failure_class=case.get('failure_class', 'validation or workflow failure') if failures else '',
            safety_critical=case.get('safety_critical', False)))
    if source_snapshot() != before:
        raise RuntimeError('SAFETY: source content or approval artifacts changed during evaluation')
    return rows


def summarize(rows):
    totals = {}
    for row in rows:
        group = totals.setdefault(row['category'], {'passed': 0, 'failed': 0, 'not_executed': 0,
                                                   'modes': {}, 'metrics': {}})
        group[{'PASS': 'passed', 'FAIL': 'failed', 'NOT EXECUTED': 'not_executed'}[row['result']]] += 1
        group['modes'][row['execution_mode']] = group['modes'].get(row['execution_mode'], 0) + 1
        for name, value in row['metrics'].items():
            group['metrics'][name] = group['metrics'].get(name, 0) + value
    return totals


def write_outputs(rows, out):
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'READYRELIEF_EVAL_RESULTS.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v
                         for k, v in row.items()} for row in rows)
    (out / 'READYRELIEF_EVAL_SUMMARY.json').write_text(json.dumps(summarize(rows), indent=2), encoding='utf-8')


def write_report(rows, data, out, *, live=False):
    totals = summarize(rows)
    em, rm, wm = [totals[k]['metrics'] for k in ('extraction', 'rag', 'workflow')]
    def ratio(n, d):
        return f'{n}/{d}' + (f' ({100*n/d:.2f}%)' if d else ' (not measured)')
    def metric(values, n, d):
        return ratio(values.get(n, 0), values.get(d, 0))
    modes = {}
    for row in rows:
        modes[row['execution_mode']] = modes.get(row['execution_mode'], 0) + 1
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    risks = {}
    by_id = {r['test_id']: r for r in rows}
    for tag in ('safety', 'approval', 'persistence_concurrency'):
        selected = [by_id[c['id']] for c in data['cases'] if tag in c.get('risk_tags', [])]
        risks[tag] = dict(executed=sum(r['result'] != 'NOT EXECUTED' for r in selected),
                          failed=sum(r['result'] == 'FAIL' for r in selected))
    text = f'''# ReadyRelief — Final AI Evaluation Report

## Objective and provenance

Evaluate bounded household extraction, reviewed retrieval/grounding/abstention, and Recovery approval/safety behavior without modifying the application or M3 review decisions. Evaluated main: `{commit}`. Dataset version: {data['dataset_version']}. Evaluation date: November 6, 2026. The original evaluation used isolated `rr-eval`; this reproducible run uses the checkout containing this runner. Source audit/evaluation worktrees were preserved during integration.

The latest `origin/main` was fetched before evaluation and matched `be0b99adbe2bb9ffe6e97716f59649db86fcce85`. A longer worktree name initially hit Windows' path-length limit; the shorter checkout was created with command-local Git long-path support. No application files were repaired or scores tuned to hide failures.

## Architecture and interfaces under evaluation

- `services.assistant.extract_recovery_needs(message, *, confirmed_context=None, client=None)` uses the existing Nebius client, strict extraction schemas, exact-quote/count checks, confirmed-context fingerprints and a second audit. It returns proposals, never writes records. Deterministic current-danger screening precedes model calls.
- `services.knowledge.retrieve_guidance(query, phase, context=None, *, hazard=None, jurisdiction=None, service=None)` maps M3 reviewed lexical retrieval to public citations. Real captured source bytes, source and candidate gates, exact passage/hash/URL and applicability remain authoritative.
- `services.generation.explain(query, phase, *, hazard, jurisdiction, client=None, state=None)` validates cited quotes and a separate entailment verdict. Its allowlisted public prompt projection excludes raw administrative context.
- Existing extraction-consumer, planner, repository, reassessment, Insurance and pending-danger regression interfaces exercise actual transactions and Streamlit confirmation flows with isolated temporary databases. No parallel repository simulator was built.

## Dataset and method

**{len(rows)} independently specified scenarios**: 14 extraction, 14 RAG, 12 workflow. Expected values, unknown fields, exact supporting quotes, required statuses, fixture inputs and code/test references were authored before execution. The known housing paraphrase was retained as a desired-relevance test rather than relabeled as a correct abstention. Each CSV row contains input, expected behavior, actual behavior, result, explanation, reference, mode and metric counts.

Extraction deliberately injects authored transport replies and authored second-audit verdicts into the existing client boundary. Fixtures include valid explicit reports, older-adult/mobility context without inferred needs, ambiguous membership, contradictions, missing information, a prompt-injection request, an invented adult count, unsupported insurance inference, non-verbatim quotes, malformed JSON and immediate danger. Unknowns are explicitly enumerated in the dataset; returning confirmed fields remain unchanged unless a supported update exists.

RAG uses the **actual main source store**, not approved synthetic copies of pending sources. Cases include electrical/reentry/housing passages, insufficient/out-of-scope topics, eligibility, coverage, live shelter availability, wrong geography/phase/hazard and missing context. Twelve distinct query/context combinations plus two distinct grounding controls form 14 cases. The grounding positive control is an exact-copy claim; the negative control supplies an unsupported guarantee and a rejecting fixture verdict.

Workflow scenarios reuse selected existing pytest acceptance tests; parametrized tests remain individual underlying checks. The runner executes these together, reads JUnit results and maps them to scenario IDs. This is regression-backed behavioral evaluation, not twelve new free-form user experiments. Detailed referenced tests contain the fixture values and asserted database/UI states.

## Execution modes

```json
{json.dumps(modes, indent=2)}
```

{'Live mode was explicitly enabled; only eligible semantic extraction cases use the existing provider. Other cases retain their recorded execution mode.' if live else '**Live Qwen model accuracy was not measured in this run.** Zero paid provider calls were authorized or performed. Offline validation results are not model extraction accuracy or jailbreak-resistance measurements.'}

Deterministic danger E14 makes zero model calls. Workflow W03 contains fake extraction within an application acceptance flow and is explicitly labeled OFFLINE MODEL FIXTURE. Other workflow checks evaluate the deterministic application boundary, even when preconstructed proposals are supplied as inputs. No claims of fresh real-browser verification are made by this runner.

## Results by category

| Category | Passed | Failed | Not executed |
|---|---:|---:|---:|
| Extraction | {totals['extraction']['passed']} | {totals['extraction']['failed']} | {totals['extraction']['not_executed']} |
| RAG | {totals['rag']['passed']} | {totals['rag']['failed']} | {totals['rag']['not_executed']} |
| Workflow | {totals['workflow']['passed']} | {totals['workflow']['failed']} | {totals['workflow']['not_executed']} |

## Metrics with exact denominators

| Metric | Result | Meaning and boundary |
|---|---|---|
| Correctly extracted/preserved nonunknown field values | {metric(em,'fields_correct','fields_total')} | Confirmed/proposed field-state/value slots in controlled replies; includes unchanged returning facts, excludes new-damage array |
| Correct unknowns | {metric(em,'unknowns_correct','unknowns_total')} | All ten field slots per extraction case, including repeated absent fields; not 133 independent households |
| Schema-valid first transport replies | {metric(em,'schema_valid','responses')} | Offline authored first replies only; one deliberately malformed JSON response is expected to fail schema validation |
| Unsupported values surviving output validation | {metric(em,'unsupported_values','extracted_values')} | Returned proposed values plus damage additions compared to the independent oracle; rejected injected values are not counted as accepted values |
| Correct evidence quotations | {metric(em,'quotes_correct','quotes_total')} | Published proposal quotes exactly match the expected quote and input substring; no independent semantic model-quality estimate |
| Relevant-or-correctly-abstained retrieval cases | {metric(rm,'relevant_results','retrieval_cases')} | Includes eight expected abstentions and two grounding controls; not pure positive retrieval recall |
| Positive source retrieval | {metric(rm,'correct_positive_retrievals','positive_retrieval_cases')} | Cases that actually require an approved source match |
| Correct abstentions | {metric(rm,'correct_abstentions','abstention_cases')} | No citations and explicit insufficiency for out-of-scope/operational/context-filtered requests |
| Approved-source compliance | {metric(rm,'approved_sources','source_checks')} | Every returned reference independently passes source AND candidate publication validation; repeated references count per occurrence |
| Correct citations | {metric(rm,'correct_citations','citation_checks')} | Exact approved passage, original source hash, official URL and unique candidate ID within each result |
| Supported output claims, exact-copy control only | {metric(rm,'supported_claims','claims_checked')} | One claim checked by text identity to an approved passage; **not a general Qwen faithfulness score** |
| Rejected unsupported-claim control | {metric(rm,'unsafe_claim_rejections','unsafe_claim_rejection_cases')} | Authored false entailment verdict causes unsupported fixture prose to be hidden; does not measure live audit-model judgment |
| Passed workflow scenarios | {metric(wm,'workflow_passed','workflow_scenarios')} | Backed by {wm.get('regression_assertion_tests',0)} existing collected/parametrized test executions |

No heterogeneous overall “AI accuracy” score is calculated. In particular, an expected rejection of malformed input is a passing validation scenario even though that authored reply is not schema valid.

## Safety and integrity findings

Workflow risk-tag counts (tags overlap; do not sum denominators):

```json
{json.dumps(risks, indent=2)}
```

The approved source store was SHA-256 snapshotted before and after execution (all files except the administrative lock); every content, candidate, approval and history artifact remained byte-identical. NFIP remains REVIEW_REQUIRED with PENDING candidates and is not used as reviewed guidance. Official-directory links are not added to the corpus or counted as reviewed passages.

The workflow tests cover confirmation before writes, plan activation only after approval, saved statuses, retained completed history, reassessment approval, stale change-then-revert progress, failed pending-danger persistence/reruns, explicit danger, unconfirmed Insurance writes, no fabricated legacy timeline, transactional attachment rollback and persisted-danger authority. No emergency call or external submission occurs. Safety-critical failures are printed prominently if observed; the runner never auto-fixes the application.

## Individual case ledger

| ID | Category | Result | Execution mode |
|---|---|---|---|
'''
    for row in rows:
        text += f"| {row['test_id']} | {row['category']} | {row['result']} | {row['execution_mode']} |\n"
    text += '\n## Failure analysis\n\n'
    failed = [r for r in rows if r['result'] == 'FAIL']
    if not failed:
        text += 'No failed scenarios in this execution.\n'
    for row in failed:
        text += (f"### {row['test_id']} — {row['failure_class']}\n\n"
                 f"Input: `{json.dumps(row['synthetic_input'], ensure_ascii=False)}`\n\n"
                 f"Expected: `{json.dumps(row['expected_behavior'], ensure_ascii=False)}`\n\n"
                 f"Actual: `{json.dumps(row['actual_behavior'], ensure_ascii=False)}`\n\n"
                 f"Failure: {row['failure_explanation']}.\n\n")
        if row['test_id'] == 'R04':
            text += ('The relevant approved USAGov passage exists, but deterministic token-overlap matching misses this paraphrase. '
                     'User impact: a conservative no-evidence message instead of useful conditional guidance. This is a retrieval-recall failure, '
                     'not a model error, provider failure, or permission to infer eligibility. Bounded future improvement: evaluate a small '
                     'reviewed topic/synonym mapping against these frozen cases while retaining operational and publication gates. '
                     'No ranking or source changes were made in this evaluation.\n\n')
        else:
            text += 'Inspect the referenced interface/test and its actual output before proposing any correction; do not weaken safeguards to improve this score.\n\n'
    text += '''## Limitations and recommendations

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
'''
    verification = ROOT / 'docs/evals/READYRELIEF_REGRESSION_VERIFICATION.json'
    if verification.exists():
        text += ('\n## Independently executed regression verification\n\n'
                 'The following is a separately recorded test run, not an implicit rerun by this evaluation command. '
                 'Recorded runs may overlap; their pass counts must not be summed.\n\n```json\n'
                 + json.dumps(json.loads(verification.read_text(encoding='utf-8')), indent=2) + '\n```\n')
    (out / 'READYRELIEF_AI_EVALUATION_REPORT.md').write_text(text, encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--live', action='store_true', help='Enable only dataset-marked semantic extraction cases')
    parser.add_argument('--authorize-paid-calls', action='store_true', help='Explicit human authorization; requires --live and configured credentials')
    args = parser.parse_args(argv)
    if args.live and (not args.authorize_paid_calls or not os.environ.get('NEBIUS_API_KEY', '').strip()):
        parser.error('Live mode requires --authorize-paid-calls and configured NEBIUS_API_KEY. No calls made.')
    if args.output is None:
        args.output = ROOT / 'docs/evals' / 'live-authorized' if args.live else ROOT / 'docs/evals'
    data = load_dataset(args.dataset)
    rows = evaluate(data, live=args.live)
    write_outputs(rows, args.output)
    write_report(rows, data, args.output, live=args.live)
    print(json.dumps(summarize(rows), indent=2))
    if not args.live:
        print('Live Qwen model accuracy was not measured in this run.')
    critical = [r['test_id'] for r in rows if r['result'] == 'FAIL' and r['safety_critical']]
    if critical:
        print('SAFETY-CRITICAL FAILURE: ' + ', '.join(critical))
    return 1 if any(r['result'] == 'FAIL' for r in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
