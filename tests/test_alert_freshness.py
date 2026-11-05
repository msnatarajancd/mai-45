"""Synthetic clock/alert fixtures; no live NWS or model requests."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from domain.contracts import Alert, AlertResult
from services.nws_alerts import get_alerts as REAL_GET_ALERTS
from ui import alert_freshness


NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


def result(now=NOW, status='alerts', **changes):
    return AlertResult(status=status, checked_at=now.isoformat(),
        source='https://www.weather.gov/',
        message='SYNTHETIC fixture. NWS weather alerts are not county evacuation orders.',
        alerts=[Alert(headline='SYNTHETIC warning', severity='Severe',
            description='SYNTHETIC original description.', instruction='SYNTHETIC original instructions.',
            source_url='https://api.weather.gov/alerts/synthetic',
            sent_at=(now-timedelta(minutes=1)).isoformat(),
            expires_at=(now+timedelta(hours=1)).isoformat())] if status == 'alerts' else [],
        **changes)


@pytest.mark.parametrize('seconds,stale', [(0, False), (299.999, False), (300, False), (300.001, True), (-1, True)])
def test_five_minute_policy_matches_guardian(seconds, stale, monkeypatch):
    monkeypatch.setattr(alert_freshness, 'utc_now', lambda: NOW+timedelta(seconds=seconds))
    assert bool(alert_freshness.snapshot_staleness(result())) is stale


@pytest.mark.parametrize('field,value', [
    ('checked_at', None), ('checked_at', 'bad'), ('checked_at', '2026-11-04T12:00:00'),
    ('expires_at', None), ('expires_at', 'bad'), ('expires_at', '2026-11-04T13:00:00'),
    ('ends_at', ''), ('ends_at', 'bad'), ('ends_at', '2026-11-04T13:00:00'),
])
def test_invalid_or_missing_metadata_fails_closed(field, value, monkeypatch):
    monkeypatch.setattr(alert_freshness, 'utc_now', lambda: NOW)
    snapshot = result()
    if field == 'checked_at':
        snapshot.checked_at = value
    else:
        setattr(snapshot.alerts[0], field, value)
    assert 'cannot be verified' in alert_freshness.snapshot_staleness(snapshot)


@pytest.fixture
def screen(tmp_path, monkeypatch):
    from services import nws_alerts
    clock, calls = [NOW], []
    monkeypatch.setattr(alert_freshness, 'utc_now', lambda: clock[0])
    def fetch(location, mode):
        calls.append((location, mode))
        return result(clock[0])
    monkeypatch.setattr(nws_alerts, 'get_alerts', fetch)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path/'synthetic.sqlite3'))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Protect'
    app.run()
    next(w for w in app.radio if w.label == 'Alert mode').set_value('LIVE CHECK').run()
    return app, clock, calls


def click(app, label):
    return next(w for w in app.button if w.label == label).click().run()


def emergency_controls(app):
    assert not app.exception
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I can't call 911" in [w.label for w in app.button]


def test_fresh_snapshot_rerenders_without_requests(screen):
    app, _, calls = screen
    assert not calls
    click(app, 'Check official alerts')
    snapshot = app.session_state['alerts'].model_dump_json()
    assert len(calls) == 1
    assert any('OFFICIAL ALERT RESULT' in w.value for w in app.markdown)
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    app.run()
    assert len(calls) == 1
    assert app.session_state['alerts'].model_dump_json() == snapshot
    emergency_controls(app)


@pytest.mark.parametrize('cause', ['expiry', 'age', 'none', 'missing_lookup', 'invalid_expiry'])
def test_stale_ui_preserves_historical_text_and_emergency_access(screen, cause):
    app, clock, calls = screen
    snapshot = result(status='none' if cause == 'none' else 'alerts')
    if cause == 'expiry':
        snapshot.alerts[0].expires_at = (NOW+timedelta(seconds=1)).isoformat()
        clock[0] += timedelta(seconds=1)
    elif cause in {'age', 'none'}:
        clock[0] += timedelta(seconds=301)
    elif cause == 'missing_lookup':
        snapshot.checked_at = None
    else:
        snapshot.alerts[0].expires_at = 'bad'
    original = snapshot.model_dump_json()
    app.session_state['alerts'] = snapshot
    app.run()
    assert any('STALE / UNVERIFIED OFFICIAL SNAPSHOT' in w.value for w in app.warning)
    assert 'Recheck Official Alerts' in [w.label for w in app.button]
    assert app.session_state['alerts'].model_dump_json() == original
    assert not calls
    if cause == 'none':
        assert any('Historical lookup returned no matching alerts' in w.value and 'safe' in w.value for w in app.info)
    else:
        assert any('HISTORICAL OFFICIAL ALERT' in w.value and snapshot.alerts[0].description in w.value for w in app.markdown)
        assert any(w.value == snapshot.alerts[0].instruction for w in app.text)
        assert 'Original official alert' in [w.label for w in app.get('link_button')]
    assert any('not county evacuation orders' in w.value for w in app.caption)
    click(app, "I can't call 911")
    assert not calls
    assert any('not guaranteed' in w.value for w in app.info)
    emergency_controls(app)


def test_explicit_recheck_replaces_stale_snapshot(screen):
    app, clock, calls = screen
    click(app, 'Check official alerts')
    clock[0] += timedelta(seconds=301)
    app.run()
    assert len(calls) == 1
    click(app, 'Recheck Official Alerts')
    assert len(calls) == 2
    assert app.session_state['alerts'].checked_at == clock[0].isoformat()
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    emergency_controls(app)


def test_idle_screen_explains_recheck_without_polling(screen):
    app, clock, calls = screen
    click(app, 'Check official alerts')
    assert any('idle screen does not update automatically' in w.value and
               'Explicitly check or recheck' in w.value and
               'not continuous monitoring' in w.value and
               'does not establish household safety' in w.value for w in app.info)
    snapshot = app.session_state['alerts'].model_dump_json()
    clock[0] += timedelta(seconds=301)
    # Advancing time alone cannot update already-rendered browser content.
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    assert len(calls) == 1
    app.run()
    assert any('STALE / UNVERIFIED' in w.value for w in app.warning)
    assert app.session_state['alerts'].model_dump_json() == snapshot
    assert len(calls) == 1
    emergency_controls(app)


def test_valid_alert_becomes_historical_at_exact_expiry_on_rerender(screen):
    app, clock, calls = screen
    snapshot = result()
    snapshot.alerts[0].expires_at = (NOW+timedelta(seconds=1)).isoformat()
    app.session_state['alerts'] = snapshot
    app.run()
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    clock[0] = NOW+timedelta(seconds=0.999)
    app.run()
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    clock[0] = NOW+timedelta(seconds=1)
    app.run()
    assert any('saved alert has ended or expired' in w.value for w in app.warning)
    assert any('HISTORICAL OFFICIAL ALERT' in w.value for w in app.markdown)
    assert 'Recheck Official Alerts' in [w.label for w in app.button]
    assert app.session_state['alerts'] == snapshot
    assert not calls
    emergency_controls(app)


def test_earlier_nws_end_becomes_historical_on_rerender(screen, monkeypatch):
    from services import nws_alerts
    from m2_guardian.service import GuardianService
    from test_guardian_integration import alert_payload
    app, clock, calls = screen
    payload = alert_payload()
    payload['features'][0]['properties'].update(
        sent=NOW.isoformat(), ends=(NOW+timedelta(seconds=1)).isoformat(),
        expires=(NOW+timedelta(hours=1)).isoformat())
    requests = []
    def transport(*args):
        requests.append(args)
        return payload
    service = GuardianService(transport=transport, clock=lambda: clock[0])
    monkeypatch.setattr(nws_alerts, 'GuardianService', lambda: service)
    # Restore the real adapter; only the upstream transport/clock are synthetic.
    monkeypatch.setattr(nws_alerts, 'get_alerts', REAL_GET_ALERTS)
    click(app, 'Check official alerts')
    snapshot = app.session_state['alerts'].model_dump_json()
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    clock[0] = NOW+timedelta(seconds=2)
    app.run()
    assert any('ended or expired' in w.value for w in app.warning)
    assert any('HISTORICAL OFFICIAL ALERT' in w.value for w in app.markdown)
    assert 'Recheck Official Alerts' in [w.label for w in app.button]
    assert any('NWS event ends: '+(NOW+timedelta(seconds=1)).isoformat() == w.value for w in app.caption)
    assert any('Expires: '+(NOW+timedelta(hours=1)).isoformat() == w.value for w in app.caption)
    assert app.session_state['alerts'].model_dump_json() == snapshot
    assert len(requests) == 1 and not calls
    assert service.get_alerts()['status'] == 'no_alerts'
    emergency_controls(app)


def test_legacy_alert_constructor_and_json_omit_optional_ends():
    legacy = dict(headline='SYNTHETIC old caller',severity='Severe',description='Original text',
                  expires_at=(NOW+timedelta(hours=1)).isoformat())
    assert Alert(**legacy).ends_at is None
    import json
    assert Alert.model_validate_json(json.dumps(legacy)).ends_at is None


def test_retained_legacy_display_object_without_new_field_still_renders(screen):
    app, clock, calls = screen
    snapshot = result()
    # Simulate a pre-update session object whose stored fields omit ends_at.
    del snapshot.alerts[0].__dict__['ends_at']
    app.session_state['alerts'] = snapshot
    app.run()
    emergency_controls(app)
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    clock[0] += timedelta(seconds=301)
    app.run()
    assert any('STALE / UNVERIFIED' in w.value for w in app.warning)
    assert not calls


@pytest.mark.parametrize('failure', ['exception', 'unavailable'])
def test_failed_recheck_replaces_old_alert_with_unavailable(screen, monkeypatch, failure):
    from services import nws_alerts
    app, clock, calls = screen
    click(app, 'Check official alerts')
    clock[0] += timedelta(seconds=301)
    app.run()
    def unavailable(*args):
        calls.append(args)
        if failure == 'exception':
            raise TimeoutError('SYNTHETIC private provider error')
        return AlertResult(
            status='unavailable', checked_at=clock[0].isoformat(), message='SYNTHETIC lookup unavailable.')
    monkeypatch.setattr(nws_alerts, 'get_alerts', unavailable)
    click(app, 'Recheck Official Alerts')
    assert app.session_state['alerts'].status == 'unavailable'
    assert not app.session_state['alerts'].alerts
    assert not any('OFFICIAL ALERT RESULT' in w.value or 'SYNTHETIC warning' in w.value for w in app.markdown)
    assert any('unavailable' in w.value.lower() or 'could not be reached' in w.value for w in app.warning)
    assert not any('private provider error' in w.value for w in app.warning)
    app.run()
    assert len(calls) == 2
    emergency_controls(app)


def test_simulation_stays_simulated_and_ignores_live_freshness(screen):
    app, clock, calls = screen
    app.session_state['alerts'] = result(simulated=True)
    clock[0] += timedelta(days=1)
    app.run()
    assert any('SIMULATED SCENARIO' in w.value for w in app.markdown)
    assert not any('STALE / UNVERIFIED' in w.value for w in app.warning)
    assert not calls
    next(w for w in app.radio if w.label == 'Alert mode').set_value('SIMULATED DEMO').run()
    assert app.session_state['mode'].value == 'SIMULATED DEMO'
    assert 'Show simulated alert' in [w.label for w in app.button]
    emergency_controls(app)
