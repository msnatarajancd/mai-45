from datetime import datetime, timedelta, timezone
import json
import unittest
from m2_guardian.service import GuardianService
from m2_guardian.explanation import explain_alert

NOW = datetime(2026,11,2,12,tzinfo=timezone.utc)
def result():
    r = GuardianService(clock=lambda:NOW).get_alerts(mode='simulated')
    r['mode'] = 'live'  # Synthetic live-mode record for offline tests only.
    r['alerts'][0]['simulated'] = False
    return r

def evidence(**changes):
    r = dict(source_id='official-1', source_title='Example reviewed guidance',
             source_url='https://www.weather.gov/safety/flood',
             guidance_text='Synthetic test excerpt. Not reviewed production guidance.',
             geographic_scope='United States', verified=True, reviewed=True,
             reviewed_at=NOW.isoformat())
    r.update(changes)
    return r

class Client:
    def __init__(self, output): self.output=output; self.calls=0
    def complete(self, messages): self.calls+=1; return self.output

class ExplanationTests(unittest.TestCase):
    def explain(self, records=None, client=None, **kwargs):
        r=result()
        retrieve = lambda **args: {'snippets': records if records is not None else [evidence()],
                                   'insufficient_evidence': False}
        return explain_alert(r,r['alerts'][0]['id'],retrieve_guidance=retrieve,llm_client=client,now=NOW,**kwargs)
    def test_no_m3_keeps_official_details(self):
        r=result(); a=explain_alert(r,r['alerts'][0]['id'],now=NOW)
        self.assertEqual(a['guidance_status'],'not_connected')
        self.assertEqual(a['official_details']['instruction'],r['alerts'][0]['instruction'])
    def test_excerpts_are_verbatim(self):
        a=self.explain();self.assertEqual(a['guidance'][0]['guidance_text'],evidence()['guidance_text'])
    def test_ai_selects_only_existing_ids(self):
        c=Client(json.dumps({'source_ids':['official-1']}))
        self.assertEqual(self.explain(client=c)['guidance_status'],'ai_selected_excerpts')
        self.assertEqual(c.calls,1)
    def test_fabricated_citation_rejected(self):
        a=self.explain(client=Client('{"source_ids":["fake"]}'))
        self.assertEqual(a['guidance_status'],'unavailable');self.assertIsNotNone(a['official_details'])
    def test_freeform_advice_rejected(self):
        a=self.explain(client=Client('{"source_ids":[],"summary":"You are safe"}'))
        self.assertEqual(a['guidance_status'],'unavailable')
    def test_unreviewed_excluded(self):
        self.assertEqual(self.explain([evidence(reviewed=False)])['guidance_status'],'insufficient_evidence')
    def test_old_review_excluded(self):
        self.assertEqual(self.explain([evidence(reviewed_at=(NOW-timedelta(days=31)).isoformat())])['guidance_status'],'insufficient_evidence')
    def test_url_allowlist(self):
        for url in ['https://weather.gov.evil.example/x','http://weather.gov/x','https://a:b@weather.gov/x']:
            self.assertEqual(self.explain([evidence(source_url=url)])['guidance_status'],'unavailable')
    def test_stale_alert_requires_recheck(self):
        r=result();r['checked_at']=(NOW-timedelta(minutes=6)).isoformat()
        self.assertEqual(explain_alert(r,r['alerts'][0]['id'],now=NOW)['status'],'unavailable')
    def test_expired_alert_requires_recheck(self):
        r=result();r['alerts'][0]['expires']=NOW.isoformat()
        self.assertEqual(explain_alert(r,r['alerts'][0]['id'],now=NOW)['status'],'unavailable')
    def test_simulation_never_calls_model_or_retrieval(self):
        r=GuardianService(clock=lambda:NOW).get_alerts(mode='simulated')
        def fail(**args): raise AssertionError('Retrieval must not run')
        c=Client('{}');a=explain_alert(r,r['alerts'][0]['id'],now=NOW,retrieve_guidance=fail,llm_client=c)
        self.assertEqual(a['guidance_status'],'simulation_only');self.assertEqual(c.calls,0)
    def test_no_alert_cannot_be_explained(self):
        r=result();r['status']='no_alerts'
        self.assertEqual(explain_alert(r,'unknown',now=NOW)['status'],'unavailable')
    def test_provider_error_sanitized(self):
        class Fail:
            def complete(self, messages): raise RuntimeError('SECRET')
        a=self.explain(client=Fail());self.assertNotIn('SECRET',json.dumps(a))
    def test_duplicate_ids_rejected(self):
        self.assertEqual(self.explain([evidence(),evidence()])['guidance_status'],'unavailable')
