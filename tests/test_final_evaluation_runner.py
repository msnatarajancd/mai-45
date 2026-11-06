"""Offline checks of evaluation accounting/oracles, not extra product features."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

FILE = Path(__file__).resolve().parents[1] / 'evaluation/run_final_evaluation.py'
spec = importlib.util.spec_from_file_location('readyrelief_final_evaluation', FILE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_dataset_has_independent_ids_oracles_quotes_and_all_categories():
    data = runner.load_dataset()
    cases = data['cases']
    assert len(cases) == 40
    assert {c['category'] for c in cases} == {'extraction', 'rag', 'workflow'}
    for case in cases:
        if case['category'] == 'extraction':
            for field in case['expected'].get('fields', {}).values():
                if field['state'] == 'PROPOSED':
                    assert field['source_quote'] in case['input']['message']


def test_duplicate_dataset_id_rejected(tmp_path):
    data = runner.load_dataset()
    data['cases'].append(data['cases'][0])
    path = tmp_path / 'duplicate.json'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='Duplicate'):
        runner.load_dataset(path)


def test_live_mode_requires_separate_authorization_and_credentials(monkeypatch):
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    monkeypatch.setattr(runner, 'evaluate', lambda *a, **kw: pytest.fail('Must not execute'))
    for args in [['--live'], ['--live', '--authorize-paid-calls']]:
        with pytest.raises(SystemExit) as error:
            runner.main(args)
        assert error.value.code == 2


def test_default_path_never_constructs_nebius_client(monkeypatch):
    import services.assistant as assistant
    monkeypatch.setattr(assistant, 'NebiusClient', lambda *a, **kw: pytest.fail('Offline path made live call'))
    for case in runner.load_dataset()['cases']:
        if case['category'] == 'extraction':
            _, failures, _ = runner.extraction(case)
            assert not failures, (case['id'], failures)


def test_independent_oracle_detects_missing_model_proposal():
    case = copy.deepcopy(runner.load_dataset()['cases'][0])
    case['fixture_replies'][0] = {'fields': {}}
    _, failures, metrics = runner.extraction(case)
    assert failures
    assert metrics['fields_correct'] < metrics['fields_total']


def test_retrieval_miss_is_not_reclassified_as_success():
    case = next(c for c in runner.load_dataset()['cases'] if c['id'] == 'R04')
    actual, failures, counts = runner.rag(case)
    assert actual['retrieval_status'] == 'NO_RELEVANT_EVIDENCE'
    assert failures and counts['correct_positive_retrievals'] == 0


def test_not_executed_is_excluded_from_pass_totals():
    summary = runner.summarize([dict(category='workflow', result='NOT EXECUTED',
        execution_mode='NOT EXECUTED', metrics={})])
    assert summary['workflow']['passed'] == 0
    assert summary['workflow']['not_executed'] == 1


def test_csv_roundtrip_keeps_input_and_actual_output(tmp_path):
    import csv
    row = dict(test_id='SYNTHETIC', category='extraction', synthetic_input={'message': 'Fictional, quotation "test"'},
        expected_behavior={'status': 'ERROR'}, actual_behavior={'status': 'ERROR'}, result='PASS',
        failure_explanation='', evidence='synthetic accounting test', execution_mode='OFFLINE MODEL FIXTURE',
        metrics={'schema_valid': 0, 'responses': 1}, failure_class='', safety_critical=False)
    runner.write_outputs([row], tmp_path)
    with (tmp_path / 'READYRELIEF_EVAL_RESULTS.csv').open(newline='', encoding='utf-8') as file:
        saved = next(csv.DictReader(file))
    assert json.loads(saved['synthetic_input']) == row['synthetic_input']
    assert json.loads(saved['actual_behavior']) == row['actual_behavior']


def test_source_mutation_fails_closed_without_rewriting_records(monkeypatch):
    data = runner.load_dataset()
    data['cases'] = [next(c for c in data['cases'] if c['id'] == 'E14')]
    snapshots = iter([{'history.json': 'original'}, {'history.json': 'changed'}])
    monkeypatch.setattr(runner, 'source_snapshot', lambda: next(snapshots))
    with pytest.raises(RuntimeError, match='source content or approval artifacts changed'):
        runner.evaluate(data, include_workflow=False)


def test_unavailable_regression_process_is_not_executed(monkeypatch):
    case = next(c for c in runner.load_dataset()['cases'] if c['category'] == 'workflow')
    def unavailable(*args, **kwargs):
        raise OSError('Synthetic missing executable')
    monkeypatch.setattr(runner.subprocess, 'run', unavailable)
    results, code = runner.workflow([case])
    assert results[case['id']][0]['not_executed']
    assert code is None


def test_report_retains_failures_and_discloses_no_live_accuracy(tmp_path):
    data = runner.load_dataset()
    # Run only extraction/RAG interfaces; mark workflows NOT EXECUTED in this report-control test.
    rows = runner.evaluate(data, include_workflow=False)
    runner.write_report(rows, data, tmp_path)
    report = (tmp_path / 'READYRELIEF_AI_EVALUATION_REPORT.md').read_text(encoding='utf-8')
    assert 'Live Qwen model accuracy was not measured in this run.' in report
    assert 'R04' in report and 'NO_RELEVANT_EVIDENCE' in report
    assert 'not a general Qwen faithfulness score' in report
