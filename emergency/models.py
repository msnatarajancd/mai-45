"""Small validated report inputs; no identity or precise address is required."""
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from domain.contracts import IncidentType

Entrypoint = Literal['respond', 'guardian', 'recovery', 'assistant', 'guidance']


class CommunicationContext(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cannot_speak_safely: bool = False
    hearing_or_speech_access: bool = False
    device_cannot_call: bool = False
    no_usable_connection: bool = False


class SituationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    text: str = Field(default='', max_length=10000, strict=True)
    category: IncidentType | None = Field(default=None, validation_alias=AliasChoices('category', 'selected_type'))
    immediate_danger: bool = Field(default=False, strict=True)
    entrypoint: Entrypoint = 'respond'
    incident_county: str | None = Field(default=None, max_length=100)
    language: str = Field(default='en', max_length=35)
    communication: CommunicationContext | None = None
