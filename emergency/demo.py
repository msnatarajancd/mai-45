"""Demo-only inputs. This module never loads evaluation expectations or evidence."""
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from emergency.models import SituationInput

DEMO_DIRECTORY = Path(__file__).resolve().parents[1] / 'data' / 'emergency_demo'


class SyntheticModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class FixtureSituationInput(SituationInput):
    """Do not permit undeclared contact or review fields in synthetic input."""
    model_config = ConfigDict(extra='forbid')


class ScenarioOption(SyntheticModel):
    id: str
    display_label: str

    @field_validator('display_label')
    @classmethod
    def visibly_synthetic(cls, value: str) -> str:
        if not value.startswith('SIMULATED '):
            raise ValueError('Synthetic inputs require a visible SIMULATED label')
        return value


class DemoScenario(ScenarioOption):
    input: SituationInput


class ScenarioFixture(ScenarioOption):
    classification: Literal['SIMULATED_DEMO']
    expectation_status: Literal['PROPOSED']
    input: FixtureSituationInput


class FictionalHousehold(ScenarioOption):
    classification: Literal['SIMULATED_DEMO']
    members: int = Field(ge=1, le=12)
    mobility_support: bool
    has_vehicle: bool
    pets: bool
    suggested_county: str | None
    limitations: list[str] = Field(min_length=1)


class FailureState(ScenarioOption):
    classification: Literal['SIMULATED_DEMO']
    fault: Literal[
        'ai_missing', 'ai_timeout', 'directory_missing', 'stale_source',
        'revoked_source', 'unknown_county', 'database_failure',
        'unsupported_dialer', 'no_connection',
    ]
    expected_behaviors: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


class SyntheticFile(SyntheticModel):
    schema_version: Literal['1.0']
    dataset_version: str
    classification: Literal['SIMULATED_DEMO']
    expectation_status: Literal['PROPOSED']


class ScenarioFile(SyntheticFile):
    scenarios: list[ScenarioFixture]


class HouseholdFile(SyntheticFile):
    households: list[FictionalHousehold]


class FailureFile(SyntheticFile):
    failure_states: list[FailureState]


def _require_demo(mode: str) -> None:
    if mode != 'demo':
        raise ValueError('Synthetic fixtures may only be loaded in demo mode')


def _scenarios(mode: str) -> list[ScenarioFixture]:
    _require_demo(mode)
    # Do not substitute fixtures when reading or validation fails.
    return ScenarioFile.model_validate_json((DEMO_DIRECTORY/'scenarios.json').read_text()).scenarios


def load_scenarios(*, mode: str = 'demo') -> list[ScenarioOption]:
    """Expose only the visible labels and IDs needed by the demo selector."""
    return [ScenarioOption(id=s.id, display_label=s.display_label) for s in _scenarios(mode)]


def load_scenario(scenario_id: str, mode: str = 'demo') -> DemoScenario:
    """Return only labeled input to feed through the normal assessment workflow."""
    scenario = next((s for s in _scenarios(mode) if s.id == scenario_id), None)
    if scenario is None:
        raise ValueError(f'Unknown synthetic scenario: {scenario_id}')
    return DemoScenario(id=scenario.id, display_label=scenario.display_label,
                        input=SituationInput.model_validate(scenario.input.model_dump()))


def load_households(*, mode: str = 'demo') -> list[FictionalHousehold]:
    _require_demo(mode)
    return HouseholdFile.model_validate_json((DEMO_DIRECTORY/'households.json').read_text()).households


def load_failure_states(*, mode: str = 'demo') -> list[FailureState]:
    _require_demo(mode)
    return FailureFile.model_validate_json((DEMO_DIRECTORY/'failure_states.json').read_text()).failure_states
