"""Small official-SDK client boundary; domain code does not depend on MCP."""
from __future__ import annotations

import os
from pathlib import Path
import sys

from mcp import Client, StdioServerParameters

from .models import ProgressInput, SpecialistResult, fingerprint

TOOLS = {'housing': 'find_temporary_housing', 'utilities': 'check_utility_health',
         'insurance': 'assess_insurance_readiness', 'rebuild': 'search_repair_providers'}


class RecoveryToolClient:
    def __init__(self):
        # A local server has no need for the application's model/provider secrets.
        env = {key: os.environ[key] for key in ('PATH', 'HOME', 'SYSTEMROOT', 'WINDIR') if key in os.environ}
        env.update(PYTHONUNBUFFERED='1', LANGSMITH_TRACING='false', LANGCHAIN_TRACING_V2='false')
        params = StdioServerParameters(command=sys.executable,
            args=['-m', 'recovery.progress.mcp_server'],
            cwd=Path(__file__).resolve().parents[2], env=env)
        self.client = Client(params, read_timeout_seconds=12)
        self.last_fingerprint: str | None = None

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self.client.__aexit__(*args)

    async def list_tools(self):
        return (await self.client.list_tools()).tools

    async def check(self, specialist: str, inputs: ProgressInput) -> SpecialistResult:
        if inputs.immediate_danger is not False:
            raise ValueError('Routine checks paused: safety assessment required.')
        result = await self.client.call_tool(TOOLS[specialist],
                                             {'payload': inputs.model_dump(mode='json')})
        if result.is_error:
            raise ValueError('The local specialist could not complete its check.')
        payload = result.structured_content
        if not isinstance(payload, dict):
            raise ValueError('Specialist returned an invalid structured response.')
        expected = fingerprint(inputs)
        if (payload.get('context_key') != inputs.context_key
                or payload.get('input_fingerprint') != expected
                or payload.get('source_mode') != inputs.source_mode.value):
            raise ValueError('Specialist result belongs to a changed recovery context.')
        checked = SpecialistResult.model_validate(payload['result'])
        if checked.specialist != specialist or checked.source_mode != inputs.source_mode:
            raise ValueError('Specialist result identity does not match this request.')
        self.last_fingerprint = expected
        return checked
