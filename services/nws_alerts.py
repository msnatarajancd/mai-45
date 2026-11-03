"""M1 adapter for the shared M2 Guardian; no model or HTTP service required."""
from domain.contracts import Alert, AlertResult, AppMode, LOCATIONS
from m2_guardian.service import GuardianService


SCOPE_NOTICE = (
    'County-wide Miami-Dade weather alerts, not address-level predictions. '
    'NWS weather alerts are not county evacuation orders; check local officials '
    'for evacuation instructions.'
)


def get_alerts(location_id: str, mode: AppMode) -> AlertResult:
    """Fresh user-triggered lookup; municipal selections share county coverage.

    checked_at is the live request start, never an alert's issue time. Demo
    timestamps belong to fictional notices and do not represent a live check.
    """
    if location_id not in LOCATIONS:
        return AlertResult(status='unavailable', message='Select a supported Miami-Dade area.')
    if mode not in (AppMode.LIVE, AppMode.DEMO):
        return AlertResult(status='unavailable', message='Select live or simulated demo mode.')
    simulated = mode == AppMode.DEMO
    result = GuardianService().get_alerts(
        'miami_dade', mode='simulated' if simulated else 'live',
    )
    alerts = [Alert(
        headline=('SIMULATED • ' if simulated else '') + (item['headline'] or item['event']),
        severity=item['severity'] or 'Unknown',
        description=item['description'],
        expires_at=item['expires'], sent_at=item['sent'],
        effective_at=item['effective'], instruction=item['instruction'],
        area=item['area'], sender=item['sender'], source_url=item['source_url'],
    ) for item in result['alerts']]
    return AlertResult(
        status={'alerts': 'alerts', 'no_alerts': 'none', 'unavailable': 'unavailable'}[result['status']],
        alerts=alerts, simulated=simulated,
        checked_at=None if simulated else result['checked_at'],
        source=result['source'], message=result['notice'] + ' ' + SCOPE_NOTICE,
        scope=result['location']['scope'], location_label=result['location']['label'],
    )
