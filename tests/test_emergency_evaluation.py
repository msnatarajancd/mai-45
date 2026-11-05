"""Independent expected labels and measured, blocked side effects are acceptance gates."""
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError


def test_dataset_counts_and_proposed_independent_authorship():
    from emergency.evaluation.run import load_dataset
    golden = load_dataset('golden')
    development = load_dataset('development')
    assert len(golden.cases) == 24
    assert len(development.cases) == 48
    assert golden.authorship.author_role == 'independent_fixture_agent'
    assert golden.authorship.human_reviewed is False
    assert golden.expectation_status == 'PROPOSED'
    assert len({c.id for c in golden.cases}) == 24


def test_golden_run_reports_all_mandatory_cases_and_zero_io():
    from emergency.evaluation.run import run_evaluation
    report = run_evaluation('golden')
    assert report['case_count'] == 24
    assert report['passed'], report['failures']
    assert report['metrics']['critical_misses'] == 0
    assert report['metrics']['forbidden_claims'] == 0
    assert report['metrics']['provider_calls'] == 0
    assert report['metrics']['network_calls'] == 0
    assert report['metrics']['io_guard_verified'] is True
    assert report['dataset_version']
    assert report['policy_versions']
    assert report['expectation_status'] == 'PROPOSED'


def test_evaluation_records_blocked_network_attempts(monkeypatch):
    from emergency.evaluation.run import run_evaluation
    from emergency import service
    original = service.evaluate_situation
    def bad_evaluator(request):
        try:
            socket.create_connection(('example.invalid', 443))
        except RuntimeError:
            pass
        return original(request)
    monkeypatch.setattr(service, 'evaluate_situation', bad_evaluator)
    report = run_evaluation('golden')
    assert report['passed'] is False
    assert report['metrics']['network_calls'] == 24
    assert any('network' in failure['mismatches'] for failure in report['failures'])


def test_evaluation_records_provider_attempts_without_credentials(monkeypatch):
    from emergency.evaluation.run import run_evaluation
    from emergency import service
    from recovery.llm_client import NebiusClient
    original = service.evaluate_situation
    def bad_evaluator(request):
        try:
            NebiusClient.complete(None, [])
        except RuntimeError:
            pass
        return original(request)
    monkeypatch.setattr(service, 'evaluate_situation', bad_evaluator)
    report = run_evaluation('golden')
    assert report['passed'] is False
    assert report['metrics']['provider_calls'] == 24


def test_evaluation_rejects_forbidden_outcome_claim(monkeypatch):
    from emergency.evaluation.run import run_evaluation
    from emergency import service
    original = service.evaluate_situation
    def bad_evaluator(request):
        return original(request).model_copy(update={'message': 'Help is on the way. Your transport is booked.'})
    monkeypatch.setattr(service, 'evaluate_situation', bad_evaluator)
    report = run_evaluation('golden')
    assert not report['passed']
    assert report['metrics']['forbidden_claims'] >= 24


def test_cli_writes_report_and_fails_for_bad_evaluator(tmp_path, monkeypatch):
    from emergency.evaluation.run import main
    from emergency import service
    original = service.evaluate_situation
    def bad_evaluator(request):
        return original(request).model_copy(update={'route': 'resources', 'interrupt_routine': False})
    monkeypatch.setattr(service, 'evaluate_situation', bad_evaluator)
    output = tmp_path/'reports'/'evaluation.json'
    assert main(['--dataset', 'golden', '--output', str(output)]) == 1
    report = json.loads(output.read_text())
    assert report['passed'] is False
    assert report['metrics']['critical_misses'] > 0


def test_dataset_rejects_fake_approval_and_contacts():
    from emergency.evaluation.run import load_dataset
    from emergency.evaluation.models import EvaluationDataset
    raw = load_dataset('golden').model_dump(mode='json')
    for mutation in ({'expectation_status': 'APPROVED'}, {'reviewer': 'Emergency official'}):
        with pytest.raises(ValidationError):
            EvaluationDataset.model_validate({**raw, **mutation})
    raw['cases'][0]['input']['phone'] = '555-0100'
    with pytest.raises(ValidationError):
        EvaluationDataset.model_validate(raw)
