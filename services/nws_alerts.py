"""M2 integration boundary. Replace this adapter, preserve AlertResult semantics."""
from domain.contracts import Alert, AlertResult, AppMode, LOCATIONS


def get_alerts(location_id: str, mode: AppMode) -> AlertResult:
    if location_id not in LOCATIONS:
        return AlertResult(status='unavailable', message='Select a supported Miami-Dade area.')
    if mode == AppMode.DEMO:
        return AlertResult(status='alerts', simulated=True, alerts=[Alert(
            headline='SIMULATED • Hurricane warning', severity='Severe',
            description='Fictional hurricane conditions for the Rivera household walkthrough. This is not a current NWS warning.',
        )], message='Demonstration fixture • no live weather request was made.')
    # TODO(M2): Request NWS with bounded timeout + User-Agent; normalize alerts,
    # none and unavailable separately. Return UTC checked_at only after a request.
    return AlertResult(status='unavailable', message='Live weather checks are not connected yet. Current conditions are unknown. Open the National Weather Service for official updates.')
