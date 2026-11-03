"""On-demand NWS lookups. No background monitoring or emergency decisions."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from numbers import Real
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE = 'https://www.weather.gov/'
LOCATIONS = {
    'miami_dade': {'label': 'Miami-Dade County, FL', 'zone': 'FLC086', 'scope': 'county'},
    'miami_point': {'label': 'Illustrative Miami point (25.7617, -80.1918)',
                    'point': '25.7617,-80.1918', 'scope': 'point'},
}
MODES = {'live', 'simulated'}
STATUSES = {'alerts', 'no_alerts', 'unavailable'}


def _time(value):
    if not isinstance(value, str):
        raise ValueError('Missing or invalid timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return result


def fetch_json(url, user_agent, timeout):
    request = Request(url, headers={'User-Agent': user_agent,
                                   'Accept': 'application/geo+json'})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Response too large')
        return json.loads(raw)


def normalize(payload, now, simulated=False):
    """Reject malformed collections; exclude tests, stale and superseded messages.

    Geography is selected by NWS query parameters, not guessed from polygons.
    Null geometries are valid. A future onset remains an applicable active notice.
    """
    if not isinstance(payload, dict) or payload.get('type') != 'FeatureCollection':
        raise ValueError('Expected GeoJSON FeatureCollection')
    features = payload.get('features')
    if not isinstance(features, list):
        raise ValueError('Expected features array')
    # Paginated/incomplete snapshots must never silently appear complete.
    if payload.get('pagination', {}).get('next'):
        raise ValueError('Incomplete paginated response')
    candidates, superseded = {}, set()
    for feature in features:
        if not isinstance(feature, dict) or feature.get('type') != 'Feature':
            raise ValueError('Invalid feature')
        p = feature.get('properties')
        if not isinstance(p, dict):
            raise ValueError('Invalid alert properties')
        if p.get('status') != 'Actual':
            continue
        message_type = p.get('messageType')
        if message_type not in {'Alert', 'Update', 'Cancel'}:
            continue
        identifier = p.get('id') or feature.get('id')
        if not isinstance(identifier, str) or not identifier:
            raise ValueError('Missing alert ID')
        sent = _time(p.get('sent'))
        expires = _time(p.get('expires'))
        ends = _time(p['ends']) if p.get('ends') else expires
        if sent > now:
            raise ValueError('Alert issue time is in the future')
        refs = p.get('references') or []
        if not isinstance(refs, list):
            raise ValueError('Invalid references')
        if message_type in {'Update', 'Cancel'}:
            for ref in refs:
                if not isinstance(ref, dict):
                    raise ValueError('Invalid reference')
                superseded.update(v for v in (ref.get('identifier'), ref.get('@id'))
                                  if isinstance(v, str))
        if message_type == 'Cancel' or min(expires, ends) <= now:
            continue
        for field in ('event', 'areaDesc', 'description', 'senderName'):
            if not isinstance(p.get(field), str) or not p[field].strip():
                raise ValueError('Missing required alert text: ' + field)
        for field in ('instruction', 'headline'):
            if p.get(field) is not None and not isinstance(p[field], str):
                raise ValueError('Invalid optional alert text')
        item = {
            'id': identifier, 'feature_id': feature.get('id'),
            'event': p['event'], 'headline': p.get('headline'),
            'area': p['areaDesc'], 'sender': p['senderName'],
            'severity': p.get('severity'), 'urgency': p.get('urgency'),
            'certainty': p.get('certainty'), 'message_type': message_type,
            'sent': p['sent'], 'effective': p.get('effective'),
            'onset': p.get('onset'), 'expires': p['expires'], 'ends': p.get('ends'),
            'description': p['description'], 'instruction': p.get('instruction'),
            'geometry': feature.get('geometry'), 'affected_zones': p.get('affectedZones', []),
            'source_url': SOURCE if simulated else feature.get('id', SOURCE),
            'simulated': simulated,
        }
        # Only retain navigable source URLs on the official API host.
        if not isinstance(item['source_url'], str) or not item['source_url'].startswith('https://api.weather.gov/'):
            item['source_url'] = SOURCE
        if identifier not in candidates or sent > _time(candidates[identifier]['sent']):
            candidates[identifier] = item
    severity = {'Extreme': 0, 'Severe': 1, 'Moderate': 2, 'Minor': 3, 'Unknown': 4}
    alerts = [v for k, v in candidates.items()
              if k not in superseded and v['feature_id'] not in superseded]
    return sorted(alerts, key=lambda a: (severity.get(a['severity'], 4), a['sent'], a['id']))


class GuardianService:
    def __init__(self, *, transport=fetch_json, clock=None,
                 user_agent='ReadyRelief-Course-Prototype/0.1', timeout=10):
        self.transport = transport
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.user_agent = user_agent
        self.timeout = timeout

    def get_alerts(self, location_id='miami_dade', mode='live', scenario='warning'):
        """Return a fresh independent result. Unsupported inputs raise ValueError.

        scenario is only used for simulated mode; never a live fallback.
        """
        if location_id not in LOCATIONS:
            raise ValueError('Unsupported location_id')
        return self._lookup(location_id, deepcopy(LOCATIONS[location_id]), mode, scenario)

    def get_alerts_by_point(self, latitude, longitude, mode='live', scenario='warning'):
        """Lookup explicit coordinates; NWS coverage is US/served territories.

        Accept finite real numbers, not strings or booleans. No geocoding or
        device location collection. Caller obtains any required location consent.
        """
        for value, bound, name in ((latitude, 90, 'latitude'), (longitude, 180, 'longitude')):
            if (isinstance(value, bool) or not isinstance(value, Real) or
                    not math.isfinite(value) or not -bound <= value <= bound):
                raise ValueError(name + ' must be a finite number in range')
        point = f'{float(latitude):.6f},{float(longitude):.6f}'
        location = {'label': 'Selected coordinates (' + point + ')',
                    'point': point, 'scope': 'point'}
        return self._lookup('custom_point', location, mode, scenario)

    def _lookup(self, location_id, location, mode, scenario):
        if mode not in MODES:
            raise ValueError('mode must be live or simulated')
        if mode == 'simulated' and scenario not in {'warning', 'no_alerts', 'unavailable'}:
            raise ValueError('Unsupported simulated scenario')
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError('Clock must be timezone-aware')
        params = {k: location[k] for k in ('zone', 'point') if k in location}
        endpoint = 'https://api.weather.gov/alerts/active?' + urlencode(params)
        result = {'schema_version': '0.1', 'location_id': location_id, 'location': location,
                  'mode': mode, 'status': 'unavailable', 'alerts': [],
                  'checked_at': now.isoformat(), 'source': SOURCE,
                  'endpoint': endpoint if mode == 'live' else None,
                  'notice': '', 'error_code': None}
        try:
            if mode == 'simulated':
                if scenario == 'unavailable':
                    raise OSError('Simulated outage')
                payload = {'type': 'FeatureCollection', 'features': []}
                if scenario == 'warning':
                    payload = json.loads((Path(__file__).parent / 'data/demo/warning.json').read_text())
                    # Relative dates keep fictional demo data usable; never touch live data.
                    from datetime import timedelta
                    for feature in payload['features']:
                        p = feature['properties']
                        p['sent'] = (now - timedelta(minutes=5)).isoformat()
                        p['effective'] = p['sent']
                        p['expires'] = (now + timedelta(hours=1)).isoformat()
                alerts = normalize(payload, now, simulated=True)
            else:
                alerts = normalize(self.transport(endpoint, self.user_agent, self.timeout), now)
            result.update(alerts=alerts, status='alerts' if alerts else 'no_alerts')
            result['notice'] = ('Read the official warning and local instructions.' if alerts else
                                'No matching active alerts were returned. This does not mean conditions are safe.')
        except (OSError, URLError, ValueError, TypeError, KeyError, AttributeError):
            result['error_code'] = 'SIMULATED_OUTAGE' if mode == 'simulated' and scenario == 'unavailable' else 'LOOKUP_FAILED'
            result['notice'] = 'Alert lookup unavailable. Check NWS and local official updates; do not infer safe conditions.'
        if mode == 'simulated':
            result['notice'] = 'SIMULATED DEMO — fictional conditions, not a current warning. ' + result['notice']
        return result


def get_alerts(location_id='miami_dade', mode='live', scenario='warning'):
    return GuardianService().get_alerts(location_id, mode, scenario)


def get_alerts_by_point(latitude, longitude, mode='live', scenario='warning'):
    return GuardianService().get_alerts_by_point(latitude, longitude, mode, scenario)
