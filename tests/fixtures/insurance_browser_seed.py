"""Seed ONLY the explicitly named, ignored synthetic browser database. No model calls."""
import base64
import io
import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image
from recovery.database import SQLiteRecoveryRepository
from recovery.models import RecoveryCase, RecoveryIntake, DamageRecord, TaskStatus
from recovery.demo_planner import create_demo_draft_plan
from recovery.insurance_models import InsuranceProfile
from recovery.attachments import validate_photo

path = Path(os.environ.get('READYRELIEF_DB_PATH', '')).resolve()
if path != (ROOT/'node_modules/insurance-browser.sqlite3').resolve():
    raise SystemExit('Set READYRELIEF_DB_PATH to node_modules/insurance-browser.sqlite3; production data is forbidden.')
repo = SQLiteRecoveryRepository(path)
cases = []
for populated in (False, True, 'returning'):
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Reported flood damage',
        utility_availability={'electricity':False,'water':None}, temporary_accommodation_status='Unknown',
        immediate_danger=False, household_recovery_needs=['Damage documentation']))
    repo.create_case(case)
    if populated:
        records = repo.get_recovery_records(case.case_id)
        records.damage_records = [DamageRecord(case_id=case.case_id,item_description=name,
            damage_description='Synthetic flood damage, for browser testing only')
            for name in (('Sofa',) if populated=='returning' else ('Refrigerator','Sofa'))]
        records = repo.save_recovery_records(records,expected_version=0,explicitly_confirmed=True)
        draft = create_demo_draft_plan(case, records)
        plan = repo.approve_plan(draft.plan_id,new_draft=draft,explicitly_approved=True)
        repo.update_task_status(plan.plan_id,plan.proposed_tasks[0].task_id,TaskStatus.COMPLETED,expected_progress_version=0)
        if populated=='returning':
            snapshot=repo.get_insurance_snapshot(case.case_id)
            workspace=snapshot.workspace.model_copy(deep=True)
            workspace.profile=InsuranceProfile(insurer_name='Returning Fictional Insurer')
            image=io.BytesIO();Image.new('RGB',(80,60),'green').save(image,'PNG')
            photo=validate_photo(image.getvalue(),'existing-sofa.png',case_id=case.case_id,damage_id=records.damage_records[0].damage_id)
            repo.save_insurance_workspace(workspace,expected_case=case,expected_records_version=records.version,
                expected_workspace_version=0,explicitly_confirmed=True,additions=[photo])
    cases.append(str(case.case_id))
photos = []
for color in ('red','blue'):
    output = io.BytesIO()
    Image.new('RGB',(80,60),color).save(output,'PNG')
    photos.append(base64.b64encode(output.getvalue()).decode())
print(json.dumps(dict(empty=cases[0],populated=cases[1],returning=cases[2],photos=photos)))
