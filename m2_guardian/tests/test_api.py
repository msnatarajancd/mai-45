"""HTTP acceptance checks use injected responses; no NWS/model calls."""
from datetime import datetime, timezone
import unittest
try:
    from fastapi.testclient import TestClient
    from m2_guardian.api import create_app
except ModuleNotFoundError as error:
    if error.name not in {'fastapi', 'httpx'}:
        raise
    TestClient = None
from m2_guardian.service import GuardianService

@unittest.skipIf(TestClient is None, 'Install requirements-m2-api.txt for HTTP tests')
class APITests(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        def fetch(url, agent, timeout):
            self.calls.append(url)
            return {'type':'FeatureCollection','features':[]}
        self.service=GuardianService(transport=fetch)
        self.client=TestClient(create_app(service=self.service,api_key=''))
    def test_health_does_not_call_nws(self):
        r=self.client.get('/health')
        self.assertEqual(r.status_code,200)
        self.assertFalse(r.json()['upstream_checked']);self.assertEqual(self.calls,[])
    def test_default_county(self):
        r=self.client.get('/v1/alerts')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['location_id'],'miami_dade')
        self.assertIn('zone=FLC086',self.calls[0])
    def test_point(self):
        r=self.client.get('/v1/alerts',params={'latitude':25.7617,'longitude':-80.1918})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['location']['scope'],'point')
        self.assertIn('point=',self.calls[0])
    def test_no_match_not_safe(self):
        r=self.client.get('/v1/alerts')
        self.assertEqual(r.json()['status'],'no_alerts')
        self.assertIn('does not mean',r.json()['notice'])
    def test_bad_queries_do_not_call_nws(self):
        for query in ['latitude=91&longitude=0','latitude=nan&longitude=0',
                      'latitude=0&longitude=inf','latitude=25', 'longitude=-80',
                      'location_id=miami_dade&latitude=25&longitude=-80',
                      'mode=unknown','location_id=unknown','latitude=true&longitude=0',
                      'latitude=1&latitude=2&longitude=0','mode=live&scenario=warning',
                      'unexpected=abc','location_id=']:
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/v1/alerts?'+query).status_code,422)
        self.assertEqual(self.calls,[])
    def test_simulation_explicit(self):
        r=self.client.get('/v1/alerts?mode=simulated')
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.json()['alerts'][0]['simulated'])
        self.assertIsNone(r.json()['endpoint']); self.assertEqual(self.calls,[])
    def test_simulated_outage_503(self):
        r=self.client.get('/v1/alerts?mode=simulated&scenario=unavailable')
        self.assertEqual(r.status_code,503)
        self.assertEqual(r.json()['mode'],'simulated')
    def test_real_outage_not_demo(self):
        def fail(*args): raise TimeoutError('SECRET')
        c=TestClient(create_app(service=GuardianService(transport=fail),api_key=''))
        r=c.get('/v1/alerts')
        self.assertEqual(r.status_code,503);self.assertEqual(r.json()['mode'],'live')
        self.assertNotIn('SECRET',r.text)
    def test_auth(self):
        c=TestClient(create_app(service=self.service,api_key='test-only-secret'))
        for headers in [{},{'X-API-Key':'wrong'}]:
            self.assertEqual(c.get('/v1/alerts',headers=headers).status_code,401)
        self.assertEqual(self.calls,[])
        self.assertEqual(c.get('/v1/alerts',headers={'X-API-Key':'test-only-secret'}).status_code,200)
    def test_no_store_and_no_wildcard_cors(self):
        r=self.client.get('/v1/alerts',headers={'Origin':'https://external.example'})
        self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertNotIn('access-control-allow-origin',r.headers)
    def test_openapi_documents_errors(self):
        r=self.client.get('/openapi.json')
        self.assertEqual(r.status_code,200)
        responses=r.json()['paths']['/v1/alerts']['get']['responses']
        self.assertTrue({'200','401','422','503'}.issubset(responses))
