"""Inspect actual browser downloads, not mocked package bytes."""
import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from pypdf import PdfReader

root=Path(sys.argv[1]);hashes=json.loads(sys.argv[2])
reader=PdfReader(root/'preparation.pdf')
text='\n'.join(page.extract_text() for page in reader.pages)
assert 'Fictional Demonstration Mutual' in text and 'SYNTHETIC-POLICY-42' in text
assert 'SYNTHETIC-CALL-42' in text and 'NOT A SUBMITTED CLAIM' in text
assert 'Synthetic repair estimate unavailable' in text
assert 'Optional information to add' in text and '123.45' in text
rows=list(csv.DictReader((root/'inventory.csv').read_text(encoding='utf-8-sig').splitlines()))
assert {row['item_description'] for row in rows}=={'Refrigerator','Sofa'}
with zipfile.ZipFile(root/'evidence.zip') as archive:
    assert archive.testzip() is None
    assert archive.read('insurance-preparation.pdf')==(root/'preparation.pdf').read_bytes()
    manifest=json.loads(archive.read('evidence-manifest.json'))
    assert len(manifest['attachments'])==2
    assert any(e['evidence_type']=='Receipt' and e['status']=='Reported available, not uploaded' and e['attachment_id'] is None for e in manifest['evidence'])
    assert any(e['evidence_type']=='Estimate' and e['status']=='Unavailable' for e in manifest['evidence'])
    for entry,expected in zip(manifest['attachments'],hashes):
        assert entry['damage_id']==next(row['damage_id'] for row in rows if row['item_description']=='Refrigerator')
        assert hashlib.sha256(archive.read(entry['safe_filename'])).hexdigest()==entry['sha256']==expected
print('Actual PDF, CSV and ZIP downloads inspected: PASS; both original saved photograph hashes match.')
