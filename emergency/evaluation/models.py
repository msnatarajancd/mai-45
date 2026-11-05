"""Strict proposed fixture schemas; they cannot impersonate official review."""
from typing import Literal

from pydantic import Field, model_validator

from emergency.demo import FixtureSituationInput, SyntheticModel


class Expectations(SyntheticModel):
    incident_types: list[Literal['flood', 'trapped', 'medical', 'evacuation_support', 'utility_hazard', 'unknown']] = Field(min_length=1)
    urgency: Literal['immediate', 'urgent', 'ordinary', 'uncertain']
    route: Literal['emergency', 'resources']
    interrupt_routine: bool
    persist_danger: bool


class EvaluationCase(SyntheticModel):
    id: str
    classification: Literal['SYNTHETIC_EVALUATION']
    input: FixtureSituationInput
    expected: Expectations
    forbidden_outcomes: list[Literal[
        'connection_confirmed', 'message_delivered', 'dispatch_confirmed',
        'rescue_confirmed', 'transport_booked', 'eligibility_approved',
    ]]
    mandatory: bool


class Authorship(SyntheticModel):
    method: str
    author_role: Literal['fixture_agent', 'independent_fixture_agent']
    human_reviewed: Literal[False]


class EvaluationDataset(SyntheticModel):
    schema_version: Literal['1.0']
    dataset_id: str
    dataset_version: str
    classification: Literal['SYNTHETIC_EVALUATION']
    expectation_status: Literal['PROPOSED']
    authorship: Authorship
    limitations: list[str] = Field(min_length=1)
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_case_ids(self):
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError('Evaluation case IDs must be unique')
        return self
