from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
import unittest
from m2_guardian import GuardianService, get_alerts_by_point

class CoordinateTests(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        def transport(url, agent, timeout):
            self.calls.append(url)
            return {'type':'FeatureCollection','features':[]}
        self.service=GuardianService(transport=transport)
    def test_point_is_sent_to_nws_and_returned(self):
        r=self.service.get_alerts_by_point(25.7617,-80.1918)
        self.assertEqual(parse_qs(urlsplit(self.calls[0]).query),{'point':['25.761700,-80.191800']})
        self.assertEqual(r['location']['scope'],'point')
        self.assertEqual(r['location_id'],'custom_point')
        self.assertEqual(r['status'],'no_alerts')
    def test_invalid_numbers_rejected_before_network(self):
        for a,b in [(91,0),(-91,0),(0,181),(0,-181),(float('nan'),0),
                    (0,float('inf')),(True,0),(0,False),('25.7',-80),(None,0)]:
            with self.subTest(a=a,b=b), self.assertRaises(ValueError):
                self.service.get_alerts_by_point(a,b)
        self.assertEqual(self.calls,[])
    def test_valid_boundaries_and_zero(self):
        for a,b in [(0,0),(90,180),(-90,-180)]:
            self.assertEqual(self.service.get_alerts_by_point(a,b)['status'],'no_alerts')
    def test_changed_coordinates_new_query(self):
        a=self.service.get_alerts_by_point(25.7,-80.1)
        b=self.service.get_alerts_by_point(25.8,-80.2)
        self.assertNotEqual(a['endpoint'],b['endpoint'])
        self.assertNotEqual(a['location'],b['location'])
    def test_simulated_point_never_calls_nws(self):
        r=self.service.get_alerts_by_point(25,-80,mode='simulated')
        self.assertEqual(r['mode'],'simulated'); self.assertIsNone(r['endpoint'])
        self.assertEqual(self.calls,[])
    def test_county_backwards_compatible(self):
        r=self.service.get_alerts('miami_dade')
        self.assertEqual(parse_qs(urlsplit(r['endpoint']).query),{'zone':['FLC086']})
    def test_public_wrapper(self):
        r=get_alerts_by_point(25,-80,mode='simulated',scenario='no_alerts')
        self.assertEqual(r['status'],'no_alerts')
    def test_invalid_mode(self):
        with self.assertRaises(ValueError): self.service.get_alerts_by_point(25,-80,mode='unknown')
        self.assertEqual(self.calls,[])
