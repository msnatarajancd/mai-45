import json
import pytest
from domain.contracts import GuidanceResult
from services import generation

class FakeClient:
    """Explicit test double: never represents a real Nebius response."""
    def __init__(self, reply=None, verdict=True):
        self.calls=[]; self.reply=reply; self.verdict=verdict
    def complete(self,messages):
        self.calls.append(messages)
        if len(self.calls)==2: return json.dumps({'supported':self.verdict})
        evidence=json.loads(messages[1]['content'])['evidence'][0]
        return json.dumps(self.reply or {'claims':[{'text':'Use a qualified electrician to inspect electrical systems.', 'citation_id':evidence['citation_id'],'quote':evidence['passage']}]})

@pytest.fixture
def evidence():
    # Synthetic DTO from a trusted-adapter test double, not real approval evidence.
    from domain.contracts import GuidanceCitation
    citation=GuidanceCitation(citation_id='synthetic-citation',source_id='synthetic-source',
        parent_chunk_id='synthetic-parent',title='Synthetic test source',publisher='Test publisher',
        official_url='https://official.test/synthetic',original_content_hash='a'*64,
        section_heading='Synthetic electrical inspection',
        passage='Use a qualified electrician to inspect electrical systems.',
        passage_start=0,passage_end=61,jurisdiction='US-FL',hazards=['flood'],phases=['recover'],
        source_review={'test_only':True},candidate_review={'test_only':True},
        safety_caveats=['Synthetic evidence for automated tests only.'],source_limitations=['No operational use.'])
    return GuidanceResult(answer='Partial synthetic evidence',citations=[citation],
        retrieval_status='INSUFFICIENT_EVIDENCE',insufficient_evidence=True,
        limitations=['Synthetic test limitation.'])

def run(monkeypatch,evidence,client):
    monkeypatch.setattr(generation.knowledge,'retrieve_guidance',lambda *a,**k:evidence)
    return generation.explain('electrical hazards','recover',hazard='flood',jurisdiction='US-FL-MIAMI-DADE',client=client)

def test_partial_generation_keeps_status_and_public_only_prompt(monkeypatch,evidence):
    evidence.citations[0].source_review['private_note']='NEVER_SEND_ADMIN_NOTE'
    c=FakeClient(); result=run(monkeypatch,evidence,c)
    assert result.generation_status=='generated'
    assert result.retrieval.retrieval_status=='INSUFFICIENT_EVIDENCE'
    assert 'partial' in result.notice.lower()
    assert len(c.calls)==2
    prompt=json.dumps(c.calls)
    assert 'NEVER_SEND_ADMIN_NOTE' not in prompt and 'surrounding_context' not in prompt
    assert result.claims[0].citation_id==evidence.citations[0].citation_id

@pytest.mark.parametrize('status',['UNAVAILABLE','INSUFFICIENT_EVIDENCE','NO_RELEVANT_EVIDENCE'])
def test_no_evidence_never_calls_model(monkeypatch,status):
    c=FakeClient(); r=run(monkeypatch,GuidanceResult(answer='Unavailable',retrieval_status=status),c)
    assert not c.calls and not r.claims and r.generation_status=='not_requested'

def test_invented_citation_rejected(monkeypatch,evidence):
    c=FakeClient({'claims':[{'text':'Anything','citation_id':'invented','quote':'invented'}]})
    r=run(monkeypatch,evidence,c)
    assert r.generation_status=='unavailable' and not r.claims

def test_semantic_verification_failure_rejected(monkeypatch,evidence):
    r=run(monkeypatch,evidence,FakeClient(verdict=False))
    assert not r.claims and r.generation_status=='unavailable'

def test_provider_error_sanitized(monkeypatch,evidence):
    class Broken:
        def complete(self,messages):raise ValueError('secret provider body')
    r=run(monkeypatch,evidence,Broken())
    assert 'secret' not in r.model_dump_json() and not r.claims

def test_emergency_bypasses_retrieval(monkeypatch):
    def forbidden(*a,**k):raise AssertionError('retrieval must not run')
    monkeypatch.setattr(generation.knowledge,'retrieve_guidance',forbidden)
    r=generation.explain('We are trapped and water is rising','recover',hazard='flood',jurisdiction='US-FL-MIAMI-DADE')
    assert r.generation_status=='emergency'

def test_revocation_during_generation_suppresses_answer(monkeypatch,evidence):
    results=iter([evidence,GuidanceResult(answer='Revoked')])
    monkeypatch.setattr(generation.knowledge,'retrieve_guidance',lambda *a,**k:next(results))
    r=generation.explain('electrical hazards','recover',hazard='flood',jurisdiction='US-FL-MIAMI-DADE',client=FakeClient())
    assert not r.claims and not r.retrieval.citations


def test_success_status_is_preserved(monkeypatch,evidence):
    evidence.retrieval_status='SUCCESS'; evidence.insufficient_evidence=False
    result=run(monkeypatch,evidence,FakeClient())
    assert result.generation_status=='generated' and result.retrieval.retrieval_status=='SUCCESS'

def test_revocation_on_rerender_removes_generated_text(monkeypatch,evidence):
    result=run(monkeypatch,evidence,FakeClient())
    monkeypatch.setattr(generation.knowledge,'retrieve_guidance',lambda *a,**k:GuidanceResult(answer='Unavailable'))
    changed=generation.revalidate(result)
    assert not changed.claims and not changed.retrieval.citations

def test_invalid_support_quote_fails_closed(monkeypatch,evidence):
    client=FakeClient({'claims':[{'text':'Anything','citation_id':evidence.citations[0].citation_id,'quote':'not present'}]})
    result=run(monkeypatch,evidence,client)
    assert not result.claims and result.generation_status=='unavailable'
