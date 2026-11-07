"""Compact offline demo evaluation; actual local MCP/graph, no model or external contact."""
import argparse
import json
from datetime import timedelta
from pathlib import Path

from recovery.progress.fixtures import load_scenario
from recovery.progress.housing import check_housing
from recovery.progress.utilities import check_utilities
from recovery.progress.insurance import check_insurance_and_funding
from recovery.progress.rebuild import check_rebuild
from recovery.progress.orchestrator import run_once
from recovery.progress.milestones import build_milestones
from recovery.progress.models import SourceMode


def evaluate():
    rows = []

    def record(identifier, input_text, expected, actual, passed, reference, mode='SIMULATED DEMO'):
        rows.append(dict(id=identifier, synthetic_input=input_text, expected=expected, actual=actual,
            result='PASS' if passed else 'FAIL', execution_mode=mode, source=reference,
            error_details='' if passed else 'Actual behavior did not satisfy the declared expectation'))

    inputs = load_scenario('williams').model_copy(update={'immediate_danger': False})
    housing = check_housing(inputs, now=inputs.as_of)
    categories = sorted({i.category for i in housing.items})
    record('DEMO-01', 'Fictional Williams catalog with explicit assessed-no-danger test input',
        'Four fictional housing categories, no booking or guaranteed capacity',
        {'categories': categories, 'summary': housing.summary, 'source_mode': housing.source_mode.value},
        set(categories) == {'hotel', 'church', 'school', 'official shelter'} and 'no booking' in housing.summary,
        'recovery/progress/housing.py; authored housing.json')

    inputs = load_scenario('chen')
    inputs.housing_sites = [inputs.housing_sites[0]]
    inputs.housing_sites[0].provenance.valid_until = inputs.as_of - timedelta(seconds=1)
    housing = check_housing(inputs, now=inputs.as_of)
    record('DEMO-02', 'Chen housing observation deliberately expired', 'Unknown suitability, never fresh availability',
        {'states': [i.state.value for i in housing.items]},
        bool(housing.items) and all(i.state.value == 'unknown' for i in housing.items), 'recovery/progress/housing.py')

    inputs = load_scenario('chen', 'update')
    inputs.utilities[0].provenance.scope = 'area'
    inputs.utilities[1].potable = None
    utility = check_utilities(inputs, now=inputs.as_of)
    states = {i.id: i.state.value for i in utility.items}
    record('DEMO-03', 'Area electricity observation; water available without potability confirmation',
        'Electricity unknown; water yellow; no home-safety certification',
        {'states': states, 'summary': utility.summary},
        states['electricity'] == 'unknown' and states['water'] == 'yellow' and 'does not establish home safety' in utility.summary,
        'recovery/progress/utilities.py')

    inputs = load_scenario('chen', 'later')
    for evidence in inputs.evidence:
        evidence.status = 'reported_available'
    insurance = check_insurance_and_funding(inputs, now=inputs.as_of)
    prep = next(i for i in insurance.items if i.id == 'preparation')
    record('DEMO-04', 'All linked fictional preparation evidence is reported available, not uploaded',
        'Preparation yellow, not saved/approved', {'state': prep.state.value, 'summary': prep.summary},
        prep.state.value == 'yellow', 'recovery/progress/insurance.py')

    inputs.source_mode = SourceMode.SAVED_CASE
    saved = check_insurance_and_funding(inputs, now=inputs.as_of)
    prep = next(i for i in saved.items if i.id == 'preparation')
    record('DEMO-05', 'Saved-mode projection cannot inherit a fictional insurer checklist',
        'Checklist suitability unknown', {'state': prep.state.value, 'summary': prep.summary},
        prep.state.value == 'unknown', 'recovery/progress/insurance.py', 'DETERMINISTIC APPLICATION CHECK')

    inputs = load_scenario('chen', 'update')
    provider = next(i for i in check_rebuild(inputs, now=inputs.as_of).items if i.id == 'contractor-1')
    record('DEMO-06', 'Fictional contractor quote received, no accepted work or external outreach',
        'Quote received is yellow and remains distinct from commitment',
        {'state': provider.state.value, 'interaction': provider.fields['Interaction'], 'summary': provider.summary},
        provider.state.value == 'yellow' and provider.fields['Interaction'] == 'quote_received', 'recovery/progress/rebuild.py')

    inputs = load_scenario('rivera')
    before = inputs.model_dump_json()
    events = []
    result = run_once(inputs, event_callback=events.append, simulation_delay=0)
    calls = [e['specialist'] for e in events if e['state'] == 'checking']
    record('DEMO-07', 'Rivera assessed synthetic story through actual local MCP and LangGraph',
        'Four specialists, housing first, next_action last, housing prioritized, input unchanged',
        {'checking_order': calls, 'primary_action': result.actions[0].key, 'events': events,
         'states': {r.specialist: r.state.value for r in result.results}},
        calls[0] == 'housing' and calls[-1] == 'next_action' and len(calls) == 5
        and result.actions[0].key == 'housing:confirm-accommodation' and inputs.model_dump_json() == before,
        'recovery/progress/orchestrator.py; mcp_client.py; mcp_server.py', 'DETERMINISTIC APPLICATION CHECK')

    inputs = inputs.model_copy(update={'specialist_failures': ['utilities']})
    partial = run_once(inputs, simulation_delay=0)
    failed = next(r for r in partial.results if r.specialist == 'utilities')
    record('DEMO-08', 'Synthetic utility tool failure through actual local MCP',
        'Unknown failed utility result, no fresh observation, partial disclosure',
        {'state': failed.state.value, 'execution': failed.execution_state.value,
         'observed_at': failed.observed_at, 'partial': partial.partial},
        failed.state.value == 'unknown' and failed.execution_state.value == 'failed'
        and failed.observed_at is None and partial.partial,
        'recovery/progress/orchestrator.py::_failed_result', 'DETERMINISTIC APPLICATION CHECK')

    for danger in (True, None):
        denied = False
        try:
            run_once(load_scenario('rivera').model_copy(update={'immediate_danger': danger}), simulation_delay=0)
        except ValueError:
            denied = True
        record('DEMO-09' if danger else 'DEMO-10', {'immediate_danger': danger},
            'Reject routine graph before entering MCP', {'denied': denied}, denied,
            'recovery/progress/orchestrator.py::_run_graph', 'DETERMINISTIC APPLICATION CHECK')

    inputs = load_scenario('rivera')
    inputs.source_mode = SourceMode.SAVED_CASE
    inputs.recovery_started = None
    view = build_milestones(inputs, [])
    record('DEMO-11', 'Saved-mode unknown start and unsupported duration predictions',
        'No elapsed date or supported numerical prediction invented',
        {'elapsed_days': view.elapsed_days, 'insurance_range': view.insurance_range, 'recovery_range': view.recovery_range},
        view.elapsed_days is None and view.insurance_range == 'Not enough information'
        and view.recovery_range == 'Not enough information', 'recovery/progress/milestones.py', 'DETERMINISTIC APPLICATION CHECK')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.local/progress-demo-evaluation.json'))
    args = parser.parse_args()
    rows = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'label': 'Synthetic data; zero live model/provider calls',
        'passed': sum(r['result'] == 'PASS' for r in rows), 'total': len(rows), 'cases': rows}, indent=2), encoding='utf-8')
    print(f"{sum(r['result'] == 'PASS' for r in rows)}/{len(rows)} evaluation cases passed; no paid model calls")
    return int(any(r['result'] == 'FAIL' for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
