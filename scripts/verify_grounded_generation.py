"""Explicit live acceptance probe; never reads or prints credentials.
Run from repository root: python scripts/verify_grounded_generation.py --live
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.generation import explain,public_payload
from recovery.llm_client import NebiusClient
import os

class RecordedClient(NebiusClient):
    def __init__(self):
        super().__init__(model=os.getenv('NEBIUS_CHAT_MODEL') or os.getenv('NEBIUS_MODEL') or 'Qwen/Qwen3-235B-A22B-Instruct-2507',timeout=25)
        self.calls=[]
    def complete(self,messages):
        # Public prompt content only. HTTP headers and credentials are never captured.
        answer=super().complete(messages)
        self.calls.append({'messages':messages,'response':json.loads(answer)})
        return answer

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Explicitly authorize real Nebius requests')
    parser.add_argument('--output',default='.local/grounded-acceptance.json')
    args=parser.parse_args()
    if not args.live:parser.error('Use --live to request actual model generation; tests use labeled doubles.')
    client=RecordedClient()
    result=explain('electrical hazards','recover',hazard='flood',jurisdiction='US-FL-MIAMI-DADE',client=client)
    no_evidence=explain('Am I eligible for FEMA assistance?','recover',hazard='flood',jurisdiction='US-FL-MIAMI-DADE',client=client)
    record={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'kind':'REAL NEBIUS CALLS' if client.calls else 'LIVE ACCESS FAILED; NO VERIFIED GENERATION',
        'generation_status':result.generation_status,'provider':result.provider,
        'evidence':public_payload(result.retrieval),'notice':result.notice,
        'claims':[c.model_dump() for c in result.claims],
        'sources':[{'citation_id':c.citation_id,'url':c.official_url,'original_content_hash':c.original_content_hash} for c in result.retrieval.citations],
        'calls':client.calls,
        'unsupported_question':{'retrieval_status':no_evidence.retrieval.retrieval_status,'generation_status':no_evidence.generation_status,'notice':no_evidence.notice}}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('recorded_at_utc','kind','generation_status','provider','unsupported_question')},indent=2))
    return 0 if result.generation_status=='generated' else 1

if __name__=='__main__':raise SystemExit(main())
