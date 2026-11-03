"""M1 boundary tests use real Guardian normalization with injected transport."""
from datetime import datetime, timezone

import pytest

from domain.contracts import AppMode
from m2_guardian.service import GuardianService
from services import nws_alerts

NOW = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


def install(monkeypatch, payload=None, failure=None):
    calls = []
    def transport(url, user_agent, timeout):
        calls.append((url, user_agent, timeout))
        if failure:
            raise failure
        return payload
    service = GuardianService(transport=transport, clock=lambda: NOW)
    monkeypatch.setattr(nws_alerts, 'GuardianService', lambda: service)
    return calls


def alert_payload():
    return {'type': 'FeatureCollection', 'features': [{
        'type': 'Feature', 'id': 'https://api.weather.gov/alerts/test',
        'properties': {
            'id': 'test', 'status': 'Actual', 'messageType': 'Alert',
            'sent': '2026-11-03T11:00:00Z', 'expires': '2026-11-03T13:00:00Z',
            'event': 'Flood Warning', 'areaDesc': 'Miami-Dade',
            'senderName': 'NWS Miami', 'description': 'Original official description.',
            'instruction': 'Original official instructions.', 'severity': 'Severe',
        },
    }]}


def test_live_alert_retains_official_provenance_and_text(monkeypatch):
    calls = install(monkeypatch, alert_payload())
    result = nws_alerts.get_alerts('miami', AppMode.LIVE)
    assert result.status == 'alerts' and not result.simulated
    assert result.checked_at == NOW.isoformat()
    alert = result.alerts[0]
    assert alert.description == 'Original official description.'
    assert alert.instruction == 'Original official instructions.'
    assert alert.sent_at == '2026-11-03T11:00:00Z'
    assert alert.expires_at == '2026-11-03T13:00:00Z'
    assert alert.source_url == 'https://api.weather.gov/alerts/test'
    assert 'not county evacuation orders' in result.message
    assert result.scope == 'county'
    assert 'zone=FLC086' in calls[0][0]
    assert calls[0][1] and 0 < calls[0][2] <= 10


@pytest.mark.parametrize('location', ['miami', 'miami-beach', 'homestead'])
def test_no_matches_are_not_an_all_clear(monkeypatch, location):
    install(monkeypatch, {'type': 'FeatureCollection', 'features': []})
    result = nws_alerts.get_alerts(location, AppMode.LIVE)
    assert result.status == 'none' and not result.alerts
    assert 'does not mean conditions are safe' in result.message
    assert result.checked_at == NOW.isoformat()
    assert result.location_label == 'Miami-Dade County, FL'


@pytest.mark.parametrize('failure', [TimeoutError('private error'), OSError('private error')])
def test_outage_is_unavailable_and_never_demo(monkeypatch, failure):
    install(monkeypatch, failure=failure)
    result = nws_alerts.get_alerts('miami', AppMode.LIVE)
    assert result.status == 'unavailable' and not result.simulated
    assert not result.alerts
    assert result.checked_at == NOW.isoformat()
    assert 'private error' not in result.message


def test_malformed_response_is_unavailable(monkeypatch):
    install(monkeypatch, {'unexpected': []})
    assert nws_alerts.get_alerts('miami', AppMode.LIVE).status == 'unavailable'


def test_demo_never_requests_live_data(monkeypatch):
    calls = install(monkeypatch, failure=AssertionError('network requested'))
    result = nws_alerts.get_alerts('miami', AppMode.DEMO)
    assert result.simulated and result.status == 'alerts'
    assert result.checked_at is None
    assert all('SIMULATED' in alert.headline for alert in result.alerts)
    assert 'SIMULATED DEMO' in result.message
    assert not calls


def test_bad_inputs_do_not_request(monkeypatch):
    calls = install(monkeypatch)
    assert nws_alerts.get_alerts('unknown', AppMode.LIVE).status == 'unavailable'
    assert nws_alerts.get_alerts('miami', 'unknown').status == 'unavailable'
    assert not calls
