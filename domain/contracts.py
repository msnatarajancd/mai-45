from enum import StrEnum
from pydantic import BaseModel, Field


class AppMode(StrEnum):
    DEMO = 'SIMULATED DEMO'
    LIVE = 'LIVE CHECK'


LOCATIONS = {'miami': 'Miami', 'homestead': 'Homestead', 'miami-beach': 'Miami Beach'}


class Household(BaseModel):
    label: str = 'Your fictional household'
    members: int = Field(default=1, ge=1, le=12)
    mobility_support: bool = False
    has_vehicle: bool = True
    pets: bool = False


class Source(BaseModel):
    title: str
    url: str
    publisher: str
    reviewed_at: str | None = None


class Alert(BaseModel):
    headline: str
    severity: str
    description: str
    expires_at: str | None = None


class AlertResult(BaseModel):
    status: str  # alerts | none | unavailable
    alerts: list[Alert] = Field(default_factory=list)
    simulated: bool = False
    checked_at: str | None = None
    source: str = 'https://www.weather.gov/mfl/'
    message: str = ''


class GuidanceResult(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    insufficient_evidence: bool = True


class RouteResult(BaseModel):
    route: str  # emergency | resources
    urgency: str
    message: str


class Resource(BaseModel):
    title: str
    url: str
    category: str
    caveat: str
    last_checked: str | None = None
