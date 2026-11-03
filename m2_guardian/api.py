"""Optional HTTP adapter around the existing Guardian module; no business-logic fork."""
from datetime import datetime
import os
import secrets
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

from .service import GuardianService


class Location(BaseModel):
    label: str
    scope: Literal['county', 'point']
    point: str | None = None
    zone: str | None = None


class Alert(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str
    event: str
    area: str
    sender: str
    description: str
    instruction: str | None
    expires: str
    source_url: str
    simulated: bool


class AlertResult(BaseModel):
    schema_version: str
    location_id: str
    location: Location
    mode: Literal['live', 'simulated']
    status: Literal['alerts', 'no_alerts', 'unavailable']
    alerts: list[Alert]
    checked_at: datetime
    source: str
    endpoint: str | None
    notice: str
    error_code: str | None


def create_app(*, service=None, api_key=None):
    """Inject service for offline tests; secret is read once at app creation."""
    guardian = service if service is not None else GuardianService()
    secret = os.environ.get('GUARDIAN_API_KEY', '') if api_key is None else api_key
    app = FastAPI(title='ReadyRelief Guardian API', version='0.1.0',
        description='On-demand official NWS alerts or explicitly simulated classroom scenarios. '
                    'No emergency dispatch, background monitoring, or safety guarantee.')
    header = APIKeyHeader(name='X-API-Key', auto_error=False)

    def authenticate(key: Annotated[str | None, Depends(header)]):
        if secret and (key is None or not secrets.compare_digest(key.encode(), secret.encode())):
            raise HTTPException(status_code=401, detail='Valid API key required')

    @app.middleware('http')
    async def no_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/health', tags=['Health'])
    def health():
        # Process health only; deliberately does not call upstream NWS.
        return {'status': 'ok', 'service': 'guardian', 'upstream_checked': False}

    @app.get('/v1/alerts', response_model=AlertResult, response_model_exclude_unset=True,
             dependencies=[Depends(authenticate)], tags=['Alerts'],
             responses={401:{'description':'Missing or invalid configured API key'},
                        422:{'description':'Invalid or ambiguous location/query'},
                        503:{'description':'Lookup unavailable', 'model':AlertResult}})
    def alerts(request: Request, response: Response,
               location_id: str | None = None,
               latitude: Annotated[float | None, Query(ge=-90, le=90, allow_inf_nan=False)] = None,
               longitude: Annotated[float | None, Query(ge=-180, le=180, allow_inf_nan=False)] = None,
               mode: Literal['live', 'simulated'] = 'live',
               scenario: Literal['warning', 'no_alerts', 'unavailable'] | None = None):
        """Choose location_id OR latitude+longitude. Omit both for Miami-Dade.

        Returns the same body as the Python service. HTTP 503 means unavailable,
        including a deliberately simulated outage. No-match is HTTP 200.
        """
        allowed = {'location_id', 'latitude', 'longitude', 'mode', 'scenario'}
        if set(request.query_params) - allowed:
            raise HTTPException(status_code=422, detail='Unknown query parameter')
        if any(len(request.query_params.getlist(k)) > 1 for k in allowed):
            raise HTTPException(status_code=422, detail='Duplicate query parameter')
        if location_id == '':
            raise HTTPException(status_code=422, detail='location_id cannot be empty')
        point = latitude is not None or longitude is not None
        if point and (location_id is not None or latitude is None or longitude is None):
            raise HTTPException(status_code=422, detail='Use location_id OR both latitude and longitude')
        if mode == 'live' and scenario is not None:
            raise HTTPException(status_code=422, detail='scenario is only valid in simulated mode')
        try:
            if point:
                result = guardian.get_alerts_by_point(latitude, longitude, mode, scenario or 'warning')
            else:
                result = guardian.get_alerts(location_id or 'miami_dade', mode, scenario or 'warning')
        except ValueError:
            raise HTTPException(status_code=422, detail='Unsupported location or input') from None
        if result['status'] == 'unavailable':
            response.status_code = 503
        return result

    return app


app = create_app()
