"""Verify every authored demo expectation through the actual local MCP server.

Run from the repository root: python -m scripts.verify_recovery_demo_data
No saved-case database, model API or live provider is accessed.
"""
import argparse
import asyncio
import json
from pathlib import Path

from recovery.progress.fixtures import list_scenarios, load_scenario
from recovery.progress.mcp_client import RecoveryToolClient, TOOLS
from recovery.progress.models import SpecialistResult, fingerprint
from recovery.progress.orchestrator import _failed_result
from recovery.progress.priorities import select_next_actions


async def verify() -> dict:
    metadata = json.loads((Path(__file__).resolve().parents[1] /
        'recovery/progress/data/demo_scenarios.json').read_text(encoding='utf-8'))
    by_id = {row['id']: row for row in metadata}
    scenarios = list_scenarios()
    assert len(by_id) == len(metadata) == len(scenarios)
    assert set(by_id) == {row.id for row in scenarios}
    tool_map = {**TOOLS, 'funding': 'assess_funding_gap'}
    checks, successful, expected_errors, summaries = 0, 0, 0, []
    async with RecoveryToolClient() as client:
        assert {tool.name for tool in await client.list_tools()} == set(tool_map.values())
        for scenario in scenarios:
            notes = {row['id']: row for row in by_id[scenario.id]['checkpoints']}
            assert set(notes) == set(scenario.checkpoints)
            for checkpoint_id in scenario.checkpoints:
                inputs = load_scenario(scenario.id, checkpoint_id)
                expected = notes[checkpoint_id]
                results = {}
                paused = inputs.immediate_danger is not False
                for key, tool in tool_map.items():
                    specialist = 'insurance' if key == 'funding' else key
                    response = await client.client.call_tool(tool, {
                        'scenario_id': scenario.id, 'checkpoint_id': checkpoint_id})
                    checks += 1
                    should_reject = paused or specialist in inputs.specialist_failures
                    assert bool(response.is_error) == should_reject, (scenario.id, checkpoint_id, tool, response)
                    if should_reject:
                        expected_errors += 1
                        if not paused:
                            results[specialist] = _failed_result(specialist, inputs)
                        continue
                    payload = response.structured_content
                    assert payload['input_fingerprint'] == fingerprint(inputs)
                    assert payload['context_key'] == inputs.context_key
                    assert payload['source_mode'] == 'synthetic'
                    result = SpecialistResult.model_validate(payload['result'])
                    assert result.specialist == specialist and result.source_mode.value == 'synthetic'
                    if key == 'funding':
                        assert result == results['insurance'], 'Funding and preparation tools must share one assessment'
                    results[specialist] = result
                    successful += 1
                if paused:
                    signals = {name: None for name in TOOLS}
                    execution = {name: 'paused' for name in TOOLS}
                    actions = ()
                else:
                    signals = {name: results[name].state.value for name in TOOLS}
                    execution = {name: results[name].execution_state.value for name in TOOLS}
                    actions = select_next_actions(inputs, tuple(results[name] for name in TOOLS))
                primary = actions[0].key if actions else None
                assert signals == expected['expected_signals'], (scenario.id, checkpoint_id, signals, expected)
                assert execution == expected['expected_execution'], (scenario.id, checkpoint_id, execution, expected)
                assert primary == expected['expected_primary_action'], (scenario.id, checkpoint_id, primary, expected)
                summaries.append(dict(scenario_id=scenario.id, checkpoint_id=checkpoint_id,
                    signals=signals, execution=execution, primary_action=primary))
    return dict(passed=True, households=len(scenarios), checkpoints=len(summaries),
                tool_calls=checks, successful_tool_calls=successful, expected_rejections=expected_errors,
                source='Actual local stdio MCP, synthetic data only', results=summaries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artifacts/recovery-demo-data-verification.json'))
    args = parser.parse_args()
    report = asyncio.run(verify())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'results'}))


if __name__ == '__main__':
    main()
