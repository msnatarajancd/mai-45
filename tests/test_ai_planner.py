import json
import socket
from urllib.error import HTTPError, URLError
from uuid import UUID

import pytest

from recovery.ai_planner import (AIPlanningError, CATALOGUE, REASON, UNGROUNDED,
                                 RecoveryEvidence, create_ai_draft_plan)
from recovery.assessment import RecoveryIntakeNotPermitted
from recovery.database import SQLiteRecoveryRepository
from recovery.llm_client import DEFAULT_MODEL, NebiusClient, PlanningClientError
from recovery.models import RecoveryCase, RecoveryIntake, PlanStatus, TaskStatus


@pytest.fixture
def case():
    return RecoveryCase(intake=RecoveryIntake(disaster_type='Fictional flood',
        housing_condition='Reported fictional damage', utility_availability={'water': None},
        temporary_accommodation_status='Fictional temporary stay', immediate_danger=False,
        household_recovery_needs=['Supplies']))


def response():
    return {'tasks': [dict(title=title, description=description, priority='HIGH',
                          reason_for_recommendation=REASON, source_reference=None)
                      for title, description in CATALOGUE[:3]]}


class Fake:
    def __init__(self, value=None):
        self.value = json.dumps(response() if value is None else value) if not isinstance(value, str) else value
        self.calls = []
    def complete(self, messages):
        self.calls.append(messages)
        return self.value


def evidence(**changes):
    return dict(source_id='fictional-1', source_title='Fictional organizational guidance',
        source_url='https://example.org/guidance', source_type='fictional demo', verified=True,
        reviewed=True, geographic_scope='Fictional region',
        guidance_text='Organize reported household needs and utility gaps.', **changes)


def test_valid_json_and_application_state(case):
    client = Fake()
    plan = create_ai_draft_plan(case, [], client)
    assert plan.approval_status is PlanStatus.DRAFT
    assert plan.planning_disclosure == UNGROUNDED
    assert len(plan.proposed_tasks) == 3
    assert all(t.status is TaskStatus.NOT_STARTED and t.task_id.version == 4 for t in plan.proposed_tasks)
    assert plan.plan_id.version == 4 and plan.case_id == case.case_id
    assert len(client.calls) == 1
    sent = json.loads(client.calls[0][1]['content'])
    assert sent['intake'] == case.intake.model_dump(mode='json')
    assert 'case_id' not in sent


@pytest.mark.parametrize('mutation', ['malformed', 'missing', 'priority', 'duplicate', 'citation',
    'availability', 'unsafe', 'state', 'task_id', 'plan_id', 'approval', 'long', 'too_many',
    'water', 'insurance', 'submission', 'unknown_advice', 'url'])
def test_invalid_outputs_rejected(case, mutation):
    value = response()
    task = value['tasks'][0]
    if mutation == 'malformed': value = '{bad json'
    elif mutation == 'missing': del task['description']
    elif mutation == 'priority': task['priority'] = 'SUPER_URGENT'
    elif mutation == 'duplicate': value['tasks'][1] = dict(task)
    elif mutation == 'citation': task['source_reference'] = 'invented'
    elif mutation == 'availability': task['description'] = 'A shelter is available nearby.'
    elif mutation == 'unsafe': task['description'] = 'Enter the damaged building for inspection.'
    elif mutation == 'state': task['status'] = 'COMPLETED'
    elif mutation == 'task_id': task['task_id'] = str(UUID(int=1))
    elif mutation == 'plan_id': value['plan_id'] = str(UUID(int=1))
    elif mutation == 'approval': value['approval_status'] = 'APPROVED'
    elif mutation == 'long': task['description'] = 'x' * 601
    elif mutation == 'too_many': value['tasks'] *= 3
    elif mutation == 'water': task['description'] = 'Unknown water quality can be treated as safe.'
    elif mutation == 'insurance': task['description'] = 'You qualify for FEMA and insurance reimbursement.'
    elif mutation == 'submission': task['description'] = 'We submitted a request on your behalf.'
    elif mutation == 'unknown_advice': task['description'] = 'Proceed inside the structurally compromised residence.'
    elif mutation == 'url': task['description'] = 'Apply at https://example.org/program.'
    client = Fake(value)
    with pytest.raises(AIPlanningError, match='rejected'):
        create_ai_draft_plan(case, [evidence()], client)
    assert len(client.calls) == 2


@pytest.mark.parametrize('danger', [True, None])
def test_danger_precedes_client_or_evidence(case, danger):
    case.intake.immediate_danger = danger
    client = Fake()
    with pytest.raises(RecoveryIntakeNotPermitted):
        create_ai_draft_plan(case, ['invalid'], client)
    assert not client.calls


def test_no_persistence_or_approval(case, tmp_path):
    path = tmp_path / 'recovery.db'
    repo = SQLiteRecoveryRepository(path)
    repo.create_case(case)
    before = path.read_bytes()
    plan = create_ai_draft_plan(case, [], Fake())
    assert path.read_bytes() == before
    assert repo.get_plan(plan.plan_id) is None
    assert repo.get_active_plan(case.case_id) is None


@pytest.mark.parametrize('records', [[], [{'unknown': 'schema'}], [evidence() | {'verified': False}]])
def test_empty_unknown_unverified_evidence(case, records):
    if records and 'unknown' in records[0]:
        with pytest.raises(AIPlanningError, match='evidence'):
            create_ai_draft_plan(case, records, Fake())
    else:
        assert create_ai_draft_plan(case, records, Fake()).planning_disclosure == UNGROUNDED


def test_citations_must_be_verified_and_supplied(case):
    value = response()
    value['tasks'][0]['source_reference'] = 'fictional-1'
    plan = create_ai_draft_plan(case, [evidence()], Fake(value))
    assert plan.proposed_tasks[0].source_reference == 'fictional-1'
    assert 'not official safety verification' in plan.planning_disclosure
    with pytest.raises(AIPlanningError):
        create_ai_draft_plan(case, [evidence() | {'verified': False}], Fake(value))


def test_controlled_retry_can_succeed(case):
    class Retry(Fake):
        def complete(self, messages):
            self.calls.append(messages)
            return 'bad json' if len(self.calls) == 1 else json.dumps(response())
    client = Retry()
    assert create_ai_draft_plan(case, [], client).approval_status is PlanStatus.DRAFT
    assert len(client.calls) == 2
    assert 'bad json' not in str(client.calls[1])


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    with pytest.raises(PlanningClientError, match='not configured'):
        NebiusClient().complete([])


@pytest.mark.parametrize('error', [socket.timeout('secret-provider-details'),
    HTTPError('secret-url', 401, 'secret-provider-details', {}, None),
    URLError('secret-provider-details')])
def test_provider_errors_sanitized(monkeypatch, error):
    monkeypatch.setenv('NEBIUS_API_KEY', 'fictional-secret')
    class Opener:
        def open(self, *args, **kwargs): raise error
    monkeypatch.setattr('recovery.llm_client.build_opener', lambda *args: Opener())
    with pytest.raises(PlanningClientError) as caught:
        NebiusClient().complete([])
    assert 'secret' not in str(caught.value)
    assert caught.value.__suppress_context__


def test_adapter_payload_and_response(monkeypatch):
    monkeypatch.setenv('NEBIUS_API_KEY', 'fictional-secret')
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit):
            return json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(response())}}]}).encode()
    class Opener:
        def open(self, request, **kwargs):
            captured.update(payload=json.loads(request.data), timeout=kwargs['timeout'], url=request.full_url)
            return Response()
    monkeypatch.setattr('recovery.llm_client.build_opener', lambda *args: Opener())
    assert json.loads(NebiusClient(model='fictional-model', timeout=12).complete([])) == response()
    assert captured['payload']['model'] == 'fictional-model'
    assert captured['timeout'] == 12
    assert captured['payload']['response_format'] == {'type': 'json_object'}
    assert captured['url'].endswith('/v1/chat/completions')


def test_provider_failure_not_retried_or_exposed(case):
    class Broken:
        def complete(self, messages): raise RuntimeError('fictional-secret and household data')
    with pytest.raises(AIPlanningError) as caught:
        create_ai_draft_plan(case, [], Broken())
    assert 'secret' not in str(caught.value) and 'household data' not in str(caught.value)


def test_all_catalogue_entries_accepted(case):
    for start in range(6):
        value = response()
        value['tasks'] = [dict(title=t, description=d, priority='MEDIUM',
            reason_for_recommendation=REASON, source_reference=None) for t, d in CATALOGUE[start:start+3]]
        if len(value['tasks']) == 3:
            assert create_ai_draft_plan(case, [], Fake(value)).proposed_tasks


@pytest.mark.parametrize('provider_response', ['malformed', 'truncated', 'oversized', 'empty'])
def test_adapter_invalid_envelope_rejected(monkeypatch, provider_response):
    monkeypatch.setenv('NEBIUS_API_KEY', 'fictional-secret')
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit):
            if provider_response == 'malformed': return b'{bad'
            if provider_response == 'oversized': return b'x' * limit
            return json.dumps({'choices': [{'finish_reason': 'length' if provider_response == 'truncated' else 'stop',
                'message': {'content': ''}}]}).encode()
    class Opener:
        def open(self, *args, **kwargs): return Response()
    monkeypatch.setattr('recovery.llm_client.build_opener', lambda *args: Opener())
    with pytest.raises(PlanningClientError):
        NebiusClient().complete([])


def test_oversized_llm_and_context_rejected(case):
    with pytest.raises(AIPlanningError):
        create_ai_draft_plan(case, [], Fake('x' * 24001))
    case.intake.household_recovery_needs = ['x' * 60001]
    client = Fake()
    with pytest.raises(AIPlanningError, match='context'):
        create_ai_draft_plan(case, [], client)
    assert not client.calls


@pytest.mark.parametrize('bad', [{'source_url': 'file:///secret'}, {'verified': 'yes'},
    {'source_id': ' '}, {'retrieved_at': '2026-11-02T12:00:00'}])
def test_evidence_schema_rejected(case, bad):
    with pytest.raises(AIPlanningError, match='evidence'):
        create_ai_draft_plan(case, [evidence() | bad], Fake())


@pytest.mark.parametrize('failed', [False, True])
def test_ai_ui_requires_generate_then_explicit_approval(case, tmp_path, monkeypatch, failed):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    path = tmp_path / 'ui.db'
    repo = SQLiteRecoveryRepository(path)
    repo.create_case(case)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    calls = []
    def complete(self, messages):
        calls.append(messages)
        return 'invalid' if failed else json.dumps(response())
    monkeypatch.setattr(NebiusClient, 'complete', complete)
    app = AppTest.from_file(str(Path('dev_recovery_preview.py').resolve()), default_timeout=10)
    app.session_state['case_id'] = str(case.case_id)
    app.session_state['recovery_page'] = 'planning'
    app.run()
    assert not calls
    next(r for r in app.radio if r.label == 'Initial planner').set_value('AI-assisted (experimental)').run()
    assert not calls
    next(b for b in app.button if b.label == 'Generate AI Draft Plan').click().run()
    assert repo.get_active_plan(case.case_id) is None
    assert any(UNGROUNDED in w.value for w in app.warning)
    if failed:
        assert len(calls) == 2
        assert any('rejected' in e.value for e in app.error)
        assert 'Approve Recovery Plan' not in [b.label for b in app.button]
        # Explicitly changing the selector is the only way to get the demo draft.
        next(r for r in app.radio if r.label == 'Initial planner').set_value('SIMULATED DEMO').run()
        assert 'Approve Recovery Plan' in [b.label for b in app.button]
    else:
        assert len(calls) == 1
        next(b for b in app.button if b.label == 'Approve Recovery Plan').click().run()
        plan = repo.get_active_plan(case.case_id)
        assert plan and plan.approval_status is PlanStatus.APPROVED
        assert plan.planning_disclosure == UNGROUNDED
        assert any(UNGROUNDED in w.value for w in app.warning)
    assert not app.exception
