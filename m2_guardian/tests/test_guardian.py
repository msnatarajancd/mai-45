from copy import deepcopy
from datetime import datetime, timezone
import unittest
from m2_guardian.service import GuardianService, normalize

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
def feature(identifier='urn:alert:1', **changes):
    p = dict(id=identifier, status='Actual', messageType='Alert',
             sent='2026-11-01T11:00:00Z', expires='2026-11-01T13:00:00Z',
             event='Flood Warning', areaDesc='Example area', senderName='NWS Example',
             description='Original official text.', instruction='Original instruction.',
             severity='Severe')
    p.update(changes)
    return dict(type='Feature', id='https://api.weather.gov/alerts/' + identifier,
                geometry=None, properties=p)
def collection(*features):
    return dict(type='FeatureCollection', features=list(features))
def service(payload):
    return GuardianService(transport=lambda *args: deepcopy(payload), clock=lambda: NOW)

class GuardianTests(unittest.TestCase):
    def test_three_states(self):
        self.assertEqual(service(collection(feature())).get_alerts()['status'], 'alerts')
        self.assertEqual(service(collection()).get_alerts()['status'], 'no_alerts')
        self.assertEqual(service({}).get_alerts()['status'], 'unavailable')
    def test_no_alerts_not_safe(self):
        self.assertIn('does not mean', service(collection()).get_alerts()['notice'])
    def test_null_geometry_and_verbatim_text(self):
        r = service(collection(feature())).get_alerts()['alerts'][0]
        self.assertIsNone(r['geometry'])
        self.assertEqual(r['instruction'], 'Original instruction.')
    def test_expired(self):
        self.assertEqual(normalize(collection(feature(expires=NOW.isoformat())), NOW), [])
    def test_ends_before_expires(self):
        self.assertEqual(normalize(collection(feature(ends='2026-11-01T11:30:00Z')), NOW), [])
    def test_future_onset_retained(self):
        self.assertEqual(len(normalize(collection(feature(onset='2026-11-01T12:30:00Z')), NOW)), 1)
    def test_test_alert_excluded(self):
        self.assertEqual(normalize(collection(feature(status='Test')), NOW), [])
    def test_duplicates(self):
        self.assertEqual(len(normalize(collection(feature(), feature()), NOW)), 1)
    def test_update_replaces_reference(self):
        update = feature('urn:alert:2', messageType='Update', references=[{'identifier': 'urn:alert:1'}])
        self.assertEqual([a['id'] for a in normalize(collection(feature(), update), NOW)], ['urn:alert:2'])
    def test_cancel_suppresses_referenced_alert(self):
        cancel = feature('urn:cancel', messageType='Cancel', references=[{'@id': feature()['id']}])
        self.assertEqual(normalize(collection(feature(), cancel), NOW), [])
    def test_out_of_order_update(self):
        update = feature('urn:alert:2', messageType='Update', references=[{'identifier': 'urn:alert:1'}])
        self.assertEqual(len(normalize(collection(update, feature()), NOW)), 1)
    def test_invalid_date_unavailable(self):
        self.assertEqual(service(collection(feature(expires='bad'))).get_alerts()['status'], 'unavailable')
    def test_partial_malformed_payload_not_no_alerts(self):
        self.assertEqual(service(collection(feature(), {'type':'Feature'})).get_alerts()['status'], 'unavailable')
    def test_pagination_unavailable(self):
        p = collection(); p['pagination'] = {'next': 'https://api.weather.gov/alerts?cursor=x'}
        self.assertEqual(service(p).get_alerts()['status'], 'unavailable')
    def test_county_not_centroid(self):
        r = service(collection()).get_alerts('miami_dade')
        self.assertIn('zone=FLC086', r['endpoint']); self.assertNotIn('point=', r['endpoint'])
    def test_point_separate(self):
        self.assertIn('point=', service(collection()).get_alerts('miami_point')['endpoint'])
    def test_invalid_input(self):
        for args in [('unknown', 'live'), ('miami_dade', 'demo')]:
            with self.assertRaises(ValueError): service(collection()).get_alerts(*args)
    def test_simulation_no_network(self):
        def fail(*args): raise AssertionError('Network called')
        s = GuardianService(transport=fail, clock=lambda: NOW)
        for scenario, expected in [('warning','alerts'), ('no_alerts','no_alerts'), ('unavailable','unavailable')]:
            r = s.get_alerts(mode='simulated', scenario=scenario)
            self.assertEqual(r['status'], expected); self.assertIn('SIMULATED', r['notice'])
            self.assertIsNone(r['endpoint'])
            self.assertTrue(all(a['simulated'] for a in r['alerts']))
    def test_outage_never_becomes_fixture(self):
        def fail(*args): raise TimeoutError('timeout')
        r = GuardianService(transport=fail, clock=lambda: NOW).get_alerts()
        self.assertEqual(r['mode'], 'live'); self.assertEqual(r['status'], 'unavailable')
        self.assertEqual(r['alerts'], [])
    def test_switch_does_not_reuse_previous(self):
        s = service(collection())
        self.assertEqual(s.get_alerts(mode='simulated')['status'], 'alerts')
        self.assertEqual(s.get_alerts(mode='live')['status'], 'no_alerts')
    def test_external_source_url_rejected(self):
        f = feature(); f['id'] = 'https://untrusted.example/phishing'
        self.assertEqual(normalize(collection(f), NOW)[0]['source_url'], 'https://www.weather.gov/')
    def test_future_sent_unavailable(self):
        r = service(collection(feature(sent='2026-11-02T01:00:00Z'))).get_alerts()
        self.assertEqual(r['status'], 'unavailable')

if __name__ == '__main__': unittest.main()
