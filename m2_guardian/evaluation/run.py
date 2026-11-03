"""Offline acceptance runner: python -m m2_guardian.evaluation.run."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from m2_guardian.service import GuardianService


def run_cases():
    document=json.loads(Path(__file__).with_name('golden_cases.json').read_text())
    now=datetime.fromisoformat(document['fixed_time'])
    rows=[]
    for case in document['cases']:
        def transport(*args):
            if case['simulate_transport_error']:
                raise TimeoutError('Synthetic transport timeout')
            return deepcopy(case['payload'])
        result=GuardianService(transport=transport, clock=lambda:now).get_alerts()
        actual={'status':result['status'], 'alert_ids':[a['id'] for a in result['alerts']]}
        checks={'expected_result':actual==case['expected'],
                'no_silent_demo':result['mode']=='live' and not any(a['simulated'] for a in result['alerts'])}
        if result['status']=='no_alerts':
            checks['no_all_clear']='does not mean conditions are safe' in result['notice']
        original={f['properties']['id']:f['properties'].get('instruction')
                  for f in (case['payload'] or {}).get('features',[]) if f.get('properties')}
        checks['verbatim_instructions']=all(a['instruction']==original[a['id']] for a in result['alerts'])
        rows.append({'id':case['id'],'purpose':case['purpose'],'passed':all(checks.values()),
                     'expected':case['expected'],'actual':actual,'checks':checks})
    return {'classification':document['classification'],'network_calls':0,
            'passed':sum(row['passed'] for row in rows),'total':len(rows),'results':rows}

if __name__=='__main__':
    report=run_cases()
    output=Path(__file__).parents[1]/'evidence'/'guardian_acceptance_results.json'
    output.write_text(json.dumps(report,indent=2))
    print(f"M2 synthetic acceptance: {report['passed']}/{report['total']} passed; no network or model calls.")
    print(f'Report: {output}')
    raise SystemExit(0 if report['passed']==report['total'] else 1)
