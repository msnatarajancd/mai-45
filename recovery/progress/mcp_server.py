"""Read-only local MCP tools for Recovery Progress. Run with python -m.

No API credentials, network lookups, dispatch, contact or case writes. The
same deterministic domain functions power both the demo and saved-case reads.
"""
from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from .models import ProgressInput, fingerprint

server = MCPServer('ReadyRelief Recovery', version='1.0.0', log_level='ERROR',
    instructions='Local synthetic and user-reported recovery checks. No live availability or insurer decisions.')
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False,
                           idempotent_hint=True, open_world_hint=False)


def evaluate(specialist: str, payload: ProgressInput | None,
             scenario_id: str | None = None, checkpoint_id: str | None = None) -> dict[str, Any]:
    from importlib import import_module
    try:
        if payload is not None and scenario_id is not None:
            raise ValueError('Choose a supplied context or a fictional scenario, not both.')
        if payload is None:
            if not scenario_id:
                raise ValueError('Supply a fictional scenario ID or structured recovery context.')
            from .fixtures import load_scenario
            inputs = load_scenario(scenario_id, checkpoint_id)
        else:
            inputs = ProgressInput.model_validate(payload)
    except ValidationError:
        raise ValueError('Invalid recovery input; correct the structured fields.') from None
    if inputs.immediate_danger is not False:
        raise ValueError('Routine recovery checks are paused until safety is explicitly assessed.')
    if specialist in inputs.specialist_failures:
        raise ValueError('This synthetic scenario simulates an unavailable service.')
    functions = {'housing': ('housing', 'check_housing'), 'utilities': ('utilities', 'check_utilities'),
                 'insurance': ('insurance', 'check_insurance_and_funding'), 'rebuild': ('rebuild', 'check_rebuild')}
    module, function = functions[specialist]
    result = getattr(import_module(f'recovery.progress.{module}'), function)(inputs, now=inputs.as_of)
    return {'context_key': inputs.context_key, 'input_fingerprint': fingerprint(inputs),
            'source_mode': inputs.source_mode.value, 'result': result.model_dump(mode='json')}


@server.tool(annotations=READ_ONLY)
def find_temporary_housing(payload: ProgressInput | None = None,
                           scenario_id: str | None = None, checkpoint_id: str | None = None) -> dict[str, Any]:
    """Compare supplied accommodation inventory with household needs; no booking."""
    return evaluate('housing', payload, scenario_id, checkpoint_id)


@server.tool(annotations=READ_ONLY)
def check_utility_health(payload: ProgressInput | None = None,
                         scenario_id: str | None = None, checkpoint_id: str | None = None) -> dict[str, Any]:
    """Explain supplied electricity/water/gas observations, scope and uncertainty."""
    return evaluate('utilities', payload, scenario_id, checkpoint_id)


@server.tool(annotations=READ_ONLY)
def assess_insurance_readiness(payload: ProgressInput | None = None,
                               scenario_id: str | None = None, checkpoint_id: str | None = None) -> dict[str, Any]:
    """Explain checklist preparation and funding dependencies; never approve a claim."""
    return evaluate('insurance', payload, scenario_id, checkpoint_id)


@server.tool(annotations=READ_ONLY)
def assess_funding_gap(payload: ProgressInput | None = None,
                       scenario_id: str | None = None, checkpoint_id: str | None = None) -> dict[str, Any]:
    """Explain stage funding using the shared preparation/funding assessment."""
    return evaluate('insurance', payload, scenario_id, checkpoint_id)


@server.tool(annotations=READ_ONLY)
def search_repair_providers(payload: ProgressInput | None = None,
                            scenario_id: str | None = None, checkpoint_id: str | None = None) -> dict[str, Any]:
    """Review supplied providers by trade and reported interaction; no contact."""
    return evaluate('rebuild', payload, scenario_id, checkpoint_id)


if __name__ == '__main__':
    server.run(transport='stdio')
