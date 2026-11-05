"""Run proposed synthetic routing checks without contacting a provider or network.

Usage: python -m emergency.evaluation.run --dataset golden --output report.json
The guard measures known Python network boundaries and the application's provider
client. It is a regression check for this local policy, not a process sandbox.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import re
import socket
from typing import Iterator
import urllib.request
from unittest.mock import patch

from emergency.evaluation.models import EvaluationDataset
from emergency.models import SituationInput

DATASET_DIRECTORY = Path(__file__).resolve().parent
IO_GUARD_SCOPE = [
    'socket.create_connection', 'socket.getaddrinfo', 'socket.socket.connect',
    'socket.socket.connect_ex', 'socket.socket.sendto',
    'http.client.HTTPConnection.connect', 'http.client.HTTPSConnection.connect',
    'urllib.request.urlopen', 'recovery.llm_client.NebiusClient.complete',
]
FORBIDDEN_PATTERNS = {
    'connection_confirmed': r'\b(?:you are connected|call (?:is|has been) connected)\b',
    'message_delivered': r'\b(?:your |the )?(?:message|text) (?:was|is|has been) delivered\b',
    'dispatch_confirmed': r'\b(?:help is on (?:its|the) way|(?:ambulance|rescuers?|help) (?:is|was|has been) dispatched)\b',
    'rescue_confirmed': r'\b(?:you (?:are|have been)|your household (?:is|has been)) rescued\b',
    'transport_booked': r'\b(?:your |the )?(?:transport|pickup|ride) (?:is|was|has been) (?:booked|confirmed)\b',
    'eligibility_approved': r'\b(?:you are (?:enrolled|approved|eligible)|your (?:enrollment|eligibility) (?:is|has been) approved)\b',
}


def load_dataset(dataset: str) -> EvaluationDataset:
    if dataset not in {'golden', 'development'}:
        raise ValueError('Dataset must be golden or development')
    return EvaluationDataset.model_validate_json(
        (DATASET_DIRECTORY/f'{dataset}_cases.json').read_text())


@contextmanager
def _io_guard() -> Iterator[dict[str, int]]:
    """Reject and count attempted external calls before they can contact anyone."""
    from recovery.llm_client import NebiusClient
    counts = {'provider_calls': 0, 'network_calls': 0}

    def deny_network(*args, **kwargs):
        counts['network_calls'] += 1
        raise RuntimeError('Network calls are forbidden during emergency evaluation')

    def deny_provider(*args, **kwargs):
        counts['provider_calls'] += 1
        raise RuntimeError('Provider calls are forbidden during emergency evaluation')

    targets = [
        (socket, 'create_connection'), (socket, 'getaddrinfo'),
        (socket.socket, 'connect'), (socket.socket, 'connect_ex'),
        (socket.socket, 'sendto'), (http.client.HTTPConnection, 'connect'),
        (http.client.HTTPSConnection, 'connect'), (urllib.request, 'urlopen'),
    ]
    if hasattr(socket.socket, 'sendmsg'):
        targets.append((socket.socket, 'sendmsg'))
    with ExitStack() as stack:
        for target, name in targets:
            stack.enter_context(patch.object(target, name, deny_network))
        stack.enter_context(patch.object(NebiusClient, 'complete', deny_provider))
        yield counts


def _verify_io_guard() -> bool:
    """Exercise both blockers, separately from the measured policy run."""
    from recovery.llm_client import NebiusClient
    with _io_guard() as counts:
        for probe in (
            lambda: socket.create_connection(('example.invalid', 443)),
            lambda: NebiusClient.complete(None, []),
        ):
            try:
                probe()
            except RuntimeError:
                pass
        return counts == {'provider_calls': 1, 'network_calls': 1}


def _forbidden_claims(message: str, forbidden: list[str]) -> list[str]:
    # Bounded regression checks, not a general factual-entailment system.
    return [claim for claim in forbidden
            if re.search(FORBIDDEN_PATTERNS[claim], message, flags=re.I)]


def run_evaluation(dataset: str = 'golden') -> dict:
    from emergency import service
    data = load_dataset(dataset)
    guard_verified = _verify_io_guard()
    cases = []
    totals = dict(type_correct=0, urgency_correct=0, routing_correct=0,
                  safety_correct=0, critical_misses=0, forbidden_claims=0,
                  provider_calls=0, network_calls=0)
    versions: set[str] = set()
    for case in data.cases:
        expected = case.expected.model_dump(mode='json')
        actual = None
        mismatches = []
        forbidden = []
        error = None
        with _io_guard() as calls:
            try:
                decision = service.evaluate_situation(
                    SituationInput.model_validate(case.input.model_dump()))
                actual = decision.model_dump(mode='json')
            except Exception as exc:
                # Report the failure without exposing prompt/provider internals.
                error = type(exc).__name__
        for name in ('provider_calls', 'network_calls'):
            totals[name] += calls[name]
            if calls[name]:
                mismatches.append('provider' if name == 'provider_calls' else 'network')
        if actual is None:
            mismatches.append('evaluation_error')
        else:
            versions.add(actual.get('policy_version', 'MISSING'))
            type_ok = set(actual.get('incident_types', [])) == set(expected['incident_types'])
            urgency_ok = actual.get('urgency') == expected['urgency']
            route_ok = actual.get('route') == expected['route']
            interrupt_ok = actual.get('interrupt_routine') == expected['interrupt_routine']
            persist_ok = actual.get('persist_danger') == expected['persist_danger']
            checks = {'incident_types': type_ok, 'urgency': urgency_ok,
                      'route': route_ok, 'interrupt_routine': interrupt_ok,
                      'persist_danger': persist_ok}
            mismatches.extend(name for name, passed in checks.items() if not passed)
            forbidden = _forbidden_claims(actual.get('message', ''), case.forbidden_outcomes)
            if forbidden:
                mismatches.append('forbidden_claims')
            if not actual.get('policy_version'):
                mismatches.append('policy_version')
            totals['type_correct'] += type_ok
            totals['urgency_correct'] += urgency_ok
            totals['routing_correct'] += route_ok
            totals['safety_correct'] += interrupt_ok and persist_ok and not forbidden and not any(calls.values())
            totals['forbidden_claims'] += len(forbidden)
        if expected['urgency'] == 'immediate' and (
            actual is None or actual.get('urgency') != 'immediate'
            or actual.get('route') != 'emergency'
            or actual.get('interrupt_routine') is not True
            or actual.get('persist_danger') is not True
        ):
            totals['critical_misses'] += 1
        cases.append({'id': case.id, 'mandatory': case.mandatory,
                      'passed': not mismatches, 'expected': expected, 'actual': actual,
                      'mismatches': mismatches, 'forbidden_claims': forbidden,
                      'provider_calls': calls['provider_calls'],
                      'network_calls': calls['network_calls'], 'error': error})
    count = len(cases)
    metrics = {
        **totals,
        'type_accuracy': totals['type_correct']/count,
        'urgency_accuracy': totals['urgency_correct']/count,
        'routing_accuracy': totals['routing_correct']/count,
        'safety_accuracy': totals['safety_correct']/count,
        'io_guard_verified': guard_verified,
        'io_guard_scope': IO_GUARD_SCOPE,
    }
    failures = [case for case in cases if not case['passed']]
    return {
        'schema_version': '1.0', 'dataset_id': data.dataset_id,
        'dataset_version': data.dataset_version,
        'expectation_status': data.expectation_status,
        'human_reviewed': data.authorship.human_reviewed,
        'authorship': data.authorship.model_dump(),
        'evaluated_at': datetime.now(timezone.utc).isoformat(),
        'policy_versions': sorted(versions), 'case_count': count,
        'passed': guard_verified and not any(f['mandatory'] for f in failures),
        'metrics': metrics, 'failures': failures, 'cases': cases,
        'limitations': data.limitations + [
            'I/O guard measures blocked attempts at the listed Python network and application provider boundaries; it is not an operating-system sandbox.',
            'Forbidden-claim checks are bounded phrase regression checks, not comprehensive semantic validation.',
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', choices=['golden', 'development'], default='golden')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = run_evaluation(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(f"{report['dataset_id']}: {report['case_count']-len(report['failures'])}/{report['case_count']} passed; expectations PROPOSED; report: {args.output}")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
