"""Browser-only synthetic provider; never imported by the production entry point."""
import json,runpy,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import streamlit as st
from services import assistant
class SyntheticClient:
 def __init__(self,**kwargs):pass
 def complete(self,messages):
  st.session_state['fixture_model_calls']=st.session_state.get('fixture_model_calls',0)+1
  if messages[0]['content'].startswith('Verify proposed recovery facts'):
   return json.dumps({'assessment':'SYNTHETIC browser fixture audit','unsupported_fields':[],'ambiguous_fields':[]})
  message=json.loads(messages[1]['content'])['message']
  fields={};damage=[]
  def fact(value,quote):return {'state':'PROPOSED','value':value,'source_quote':quote}
  if 'Our home is flooded' in message:
   fields={'disaster_type':fact('Flood','Our home is flooded'),'housing_condition':fact('Flooded','Our home is flooded')}
  if 'Electricity is back' in message:fields['electricity']=fact('Available','Electricity is back')
  for item in ['furniture','refrigerator']:
   quote=('our '+item+' is damaged')
   if quote in message:damage.append(fact(item,quote))
  return json.dumps({'fields':fields,'new_damage':damage,'clarification_fields':['adults','children'] if '5 members' in message else []})
assistant.NebiusClient=SyntheticClient
os.environ['NEBIUS_API_KEY']='synthetic-browser-fixture-not-a-credential'
try:runpy.run_path(str(ROOT/'app.py'),run_name='__main__')
finally:
 summary={k:st.session_state.get(k) for k in ['page','rr_emergency','rr_pending_danger','rr_emergency_epoch','rr_emergency_decision','rr_case_id','fixture_model_calls']}
 st.caption('SYNTHETIC MODEL FIXTURE / no live Qwen calls')
 st.code(json.dumps(summary),language='json')
