"""Fictional, offline Insurance acceptance. No real household files or model calls."""
import csv
import hashlib
import io
import json
import sqlite3
import zipfile
from datetime import date
from uuid import uuid4
import pytest
from PIL import Image
from pypdf import PdfReader
from recovery.database import SQLiteRecoveryRepository
from recovery.models import DamageRecord
from recovery.insurance_models import (InsuranceProfile, ItemPreparation, EvidenceRecord, EvidenceType,
    EvidenceStatus, InsuranceCommunication)
from recovery.attachments import validate_photo, thumbnail, MAX_CASE_BYTES, MAX_PHOTO_BYTES
from recovery.insurance_exports import build_preparation_package, PACKAGE_LABEL
from test_recovery_records import saved, dump


def image_bytes(color='red', format='PNG', size=(16, 12)):
    stream = io.BytesIO()
    Image.new('RGB', size, color).save(stream, format)
    return stream.getvalue()


@pytest.fixture
def insurance(saved):
    path, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    records.damage_records = [DamageRecord(case_id=case.case_id, item_description=name,
        damage_description='Synthetic flood damage') for name in ['Refrigerator', 'Sofa']]
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    return path, repo, case


def save(repo, snapshot, workspace=None, **kwargs):
    return repo.save_insurance_workspace(workspace or snapshot.workspace,
        expected_case=snapshot.case, expected_records_version=snapshot.records.version,
        expected_workspace_version=snapshot.workspace.version, explicitly_confirmed=True, **kwargs)


def photo(snapshot, color='red', name='synthetic.png'):
    return validate_photo(image_bytes(color), name, case_id=snapshot.case.case_id,
        damage_id=snapshot.records.damage_records[0].damage_id)


def test_legacy_empty_workspace_is_read_only_and_plan_unchanged(saved):
    path, repo, case = saved
    before = dump(path)
    snapshot = repo.get_insurance_snapshot(case.case_id)
    assert snapshot.workspace.version == 0 and snapshot.workspace.profile.insurer_name is None
    assert snapshot.attachments == []
    assert dump(path) == before


def test_profile_inventory_evidence_communications_and_original_photos_reopen(insurance):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    plan = repo.get_active_plan(case.case_id)
    workspace = snapshot.workspace.model_copy(deep=True)
    workspace.profile = InsuranceProfile(insurer_name='Fictional Mutual', policy_reference='DEMO-42', insurer_contacted=True)
    workspace.items = [ItemPreparation(damage_id=snapshot.records.damage_records[0].damage_id,
        quantity=1, brand='Synthetic brand', estimated_cost='123.45', currency='USD')]
    workspace.evidence = [EvidenceRecord(case_id=case.case_id, evidence_type=EvidenceType.RECEIPT,
        status=EvidenceStatus.REPORTED_AVAILABLE, description='Paper receipt available, not uploaded'),
        EvidenceRecord(case_id=case.case_id, evidence_type=EvidenceType.ESTIMATE,
        status=EvidenceStatus.UNAVAILABLE, description='No estimate received')]
    workspace.communications = [InsuranceCommunication(contact_date=date(2026,11,5), method='Phone',
        reference='SYN-CALL-7', summary='User reports asking about documentation; no submission accepted.')]
    first, second = photo(snapshot), photo(snapshot, 'blue')
    save(repo, snapshot, workspace, additions=[first, second])
    reopened = SQLiteRecoveryRepository(path).get_insurance_snapshot(case.case_id)
    assert reopened.workspace.profile.insurer_name == 'Fictional Mutual'
    assert reopened.workspace.profile.insurance_type is None
    assert [p.content for p in reopened.attachments] == [first.content, second.content]
    assert [d.damage_id for d in reopened.records.damage_records] == [d.damage_id for d in snapshot.records.damage_records]
    assert repo.get_active_plan(case.case_id) == plan
    assert thumbnail(reopened.attachments[0])
    save(repo, reopened, removals=[first.metadata.attachment_id])
    after = repo.get_insurance_snapshot(case.case_id)
    assert [p.metadata.attachment_id for p in after.attachments] == [second.metadata.attachment_id]
    assert next(e for e in after.workspace.evidence if e.description.startswith('Paper')).attachment_id is None
    assert sum(e.status is EvidenceStatus.FILE_SAVED for e in after.workspace.evidence) == 1
    assert sum(e.status is EvidenceStatus.NOT_COLLECTED for e in after.workspace.evidence) == 1


def test_unconfirmed_save_and_stale_case_records_workspace_rejected(insurance):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    with pytest.raises(ValueError, match='confirmation'):
        repo.save_insurance_workspace(snapshot.workspace, expected_case=case,
            expected_records_version=snapshot.records.version, expected_workspace_version=0)
    save(repo, snapshot)
    before = dump(path)
    with pytest.raises(ValueError, match='Stale'):
        save(repo, snapshot, additions=[photo(snapshot)])
    assert dump(path) == before
    fresh = repo.get_insurance_snapshot(case.case_id)
    repo.save_recovery_records(fresh.records, expected_version=fresh.records.version, explicitly_confirmed=True)
    before = dump(path)
    with pytest.raises(ValueError, match='Stale'):
        save(repo, fresh)
    assert dump(path) == before


@pytest.mark.parametrize('danger', [True, None])
def test_danger_added_after_snapshot_blocks_all_writes_and_exports(insurance, danger):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    if danger:
        repo.report_immediate_danger(case.case_id)
    else:
        case.intake.immediate_danger = None
        with sqlite3.connect(path) as connection:
            connection.execute('UPDATE recovery_cases SET case_json=? WHERE case_id=?', (case.model_dump_json(), str(case.case_id)))
    before = dump(path)
    with pytest.raises(ValueError, match='safety'):
        save(repo, snapshot, additions=[photo(snapshot)])
    with pytest.raises(ValueError, match='safety'):
        build_preparation_package(repo, case.case_id)
    assert dump(path) == before


@pytest.mark.parametrize('defect', ['foreign_item', 'foreign_attachment', 'false_file_status', 'duplicate_photo', 'foreign_removal'])
def test_case_and_evidence_integrity_fail_closed_without_partial_updates(insurance, defect):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    workspace = snapshot.workspace.model_copy(deep=True)
    additions, removals = [], []
    if defect == 'foreign_item':
        workspace.items = [ItemPreparation(damage_id=uuid4())]
    elif defect == 'foreign_attachment':
        p = photo(snapshot);p.metadata.case_id = uuid4(); additions = [p]
    elif defect == 'false_file_status':
        workspace.evidence = [EvidenceRecord(case_id=case.case_id, evidence_type=EvidenceType.RECEIPT,
            status=EvidenceStatus.FILE_SAVED, attachment_id=uuid4())]
    elif defect == 'duplicate_photo':
        additions = [photo(snapshot), photo(snapshot)]
    else:
        removals = [uuid4()]
    before = dump(path)
    with pytest.raises(ValueError):
        save(repo, snapshot, workspace, additions=additions, removals=removals)
    assert dump(path) == before


def test_database_failure_rolls_back_inserted_blob_and_workspace(insurance):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_insurance BEFORE INSERT ON recovery_insurance_workspaces BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    before = dump(path)
    with pytest.raises(sqlite3.IntegrityError):
        save(repo, snapshot, additions=[photo(snapshot)])
    assert dump(path) == before


@pytest.mark.parametrize('filename,content', [('lie.jpg', image_bytes()), ('../escape.png', image_bytes()),
    ('C:\\fake.png', image_bytes()), ('broken.png', b'not an image'), ('unsupported.png', image_bytes(format='GIF')),
    ('huge.png', b'x'*(MAX_PHOTO_BYTES+1)), ('empty.png', b''), ('truncated.png', image_bytes()[:25])])
def test_invalid_uploads_are_rejected(filename, content):
    with pytest.raises(ValueError):
        validate_photo(content, filename, case_id=uuid4())


def test_animated_and_excessive_dimension_images_rejected():
    output = io.BytesIO()
    first = Image.new('RGB',(2,2),'red');second = Image.new('RGB',(2,2),'blue')
    first.save(output,'PNG',save_all=True,append_images=[second],duration=100,loop=0)
    with pytest.raises(ValueError, match='animated'):
        validate_photo(output.getvalue(),'animated.png',case_id=uuid4())
    with pytest.raises(ValueError, match='dimensions'):
        validate_photo(image_bytes(size=(10001,1)),'wide.png',case_id=uuid4())


def test_case_attachment_limits_are_atomic(insurance, monkeypatch):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    before = dump(path)
    with pytest.raises(ValueError, match='20-attachment'):
        save(repo, snapshot, additions=[photo(snapshot, f'#{index:06x}') for index in range(21)])
    assert dump(path) == before
    # Exercise the exact aggregate branch without allocating 50 MiB of fixtures.
    monkeypatch.setattr('recovery.attachments.MAX_CASE_BYTES', 1)
    with pytest.raises(ValueError, match='50 MiB'):
        save(repo, snapshot, additions=[photo(snapshot)])
    assert dump(path) == before


def test_pdf_csv_zip_parse_original_hashes_long_text_and_saved_only(insurance):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    workspace = snapshot.workspace.model_copy(deep=True)
    workspace.profile = InsuranceProfile(insurer_name='Synthetic <Mutual> & Co', policy_reference='DEMO-POLICY',
        notes=('Long synthetic description <script> & details. '*80)+' \U0001f30a')
    workspace.communications = [InsuranceCommunication(contact_date=date(2026,11,5), method='Phone',
        reference='DEMO-CALL', summary='Discussed documentation. No claim submitted.')]
    photos = [photo(snapshot), photo(snapshot,'blue')]
    save(repo,snapshot,workspace,additions=photos)
    # Unsaved model edits must not appear in an export loaded from the repository.
    workspace.profile.insurer_name = 'UNSAVED-DO-NOT-EXPORT'
    pdf, inventory, archive = build_preparation_package(repo,case.case_id)
    assert build_preparation_package(repo,case.case_id)[0] == pdf
    reader = PdfReader(io.BytesIO(pdf))
    text = '\n'.join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) > 1
    assert 'Synthetic <Mutual> & Co' in text and 'DEMO-CALL' in text
    assert '2026-11-05' in text and '[U+1F30A]' in text
    assert 'UNSAVED-DO-NOT-EXPORT' not in text
    assert 'NOT A SUBMITTED CLAIM' in text and 'Optional information to add' in text
    rows = list(csv.DictReader(io.StringIO(inventory.decode('utf-8-sig'))))
    assert [row['item_description'] for row in rows] == ['Refrigerator','Sofa']
    assert all(row['package_label'] == PACKAGE_LABEL for row in rows)
    with zipfile.ZipFile(io.BytesIO(archive)) as archive_file:
        assert archive_file.testzip() is None
        assert archive_file.read('insurance-preparation.pdf') == pdf
        assert archive_file.read('damage-inventory.csv') == inventory
        manifest = json.loads(archive_file.read('evidence-manifest.json'))
        assert manifest['label'] == PACKAGE_LABEL
        for entry, original in zip(manifest['attachments'], photos):
            assert archive_file.read(entry['safe_filename']) == original.content
            assert hashlib.sha256(archive_file.read(entry['safe_filename'])).hexdigest() == entry['sha256']


def test_corrupted_attachment_is_not_exported(insurance):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    save(repo,snapshot,additions=[photo(snapshot)])
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE recovery_insurance_attachments SET content=?', (image_bytes('green'),))
    with pytest.raises(ValueError, match='hash'):
        build_preparation_package(repo,case.case_id)


def test_csv_formula_injection_is_neutralized(insurance):
    _, repo, case = insurance
    records = repo.get_recovery_records(case.case_id)
    records.damage_records[0].item_description = '  =HYPERLINK("bad")'
    repo.save_recovery_records(records,expected_version=records.version,explicitly_confirmed=True)
    _, inventory, _ = build_preparation_package(repo,case.case_id)
    rows = list(csv.DictReader(io.StringIO(inventory.decode('utf-8-sig'))))
    assert rows[0]['item_description'].startswith("'")


def test_returning_recovery_damage_addition_preserves_workspace_photos_and_progress(insurance):
    _, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    save(repo,snapshot,additions=[photo(snapshot)])
    before = repo.get_insurance_snapshot(case.case_id)
    plan = repo.get_active_plan(case.case_id)
    records = repo.get_recovery_records(case.case_id)
    records.damage_records.append(DamageRecord(case_id=case.case_id,item_description='Furniture',damage_description='Additional confirmed synthetic damage'))
    repo.save_recovery_records(records,expected_version=records.version,explicitly_confirmed=True)
    after = repo.get_insurance_snapshot(case.case_id)
    assert len(after.records.damage_records)==3
    assert after.workspace == before.workspace and after.attachments == before.attachments
    assert repo.get_active_plan(case.case_id)==plan


def test_other_case_cannot_read_remove_or_reuse_attachment_identity(insurance):
    path,repo,case=insurance
    first=repo.get_insurance_snapshot(case.case_id)
    original=photo(first)
    save(repo,first,additions=[original])
    other=case.model_copy(update={'case_id':uuid4()})
    repo.create_case(other)
    second=repo.get_insurance_snapshot(other.case_id)
    assert second.attachments==[]
    before=dump(path)
    with pytest.raises(ValueError,match='outside this case'):
        save(repo,second,removals=[original.metadata.attachment_id])
    forged=original.model_copy(deep=True)
    forged.metadata.case_id=other.case_id;forged.metadata.damage_id=None
    with pytest.raises(ValueError,match='cannot be overwritten'):
        save(repo,second,additions=[forged])
    assert dump(path)==before


def test_exact_photo_and_attachment_count_boundaries(insurance):
    path,repo,case=insurance
    snapshot=repo.get_insurance_snapshot(case.case_id)
    raw=image_bytes();raw+=b'\x00'*(MAX_PHOTO_BYTES-len(raw))
    assert validate_photo(raw,'boundary.png',case_id=case.case_id).metadata.byte_count==MAX_PHOTO_BYTES
    save(repo,snapshot,additions=[photo(snapshot,f'#{i:06x}') for i in range(20)])
    fresh=repo.get_insurance_snapshot(case.case_id)
    assert len(fresh.attachments)==20
    before=dump(path)
    with pytest.raises(ValueError,match='20-attachment'):
        save(repo,fresh,additions=[photo(snapshot,'white')])
    assert dump(path)==before


def test_confirmed_communication_history_cannot_be_rewritten(insurance):
    path,repo,case=insurance
    snapshot=repo.get_insurance_snapshot(case.case_id)
    workspace=snapshot.workspace.model_copy(deep=True)
    workspace.communications=[InsuranceCommunication(method='Phone',summary='Original user-reported call')]
    save(repo,snapshot,workspace)
    snapshot=repo.get_insurance_snapshot(case.case_id)
    proposal=snapshot.workspace.model_copy(deep=True);proposal.communications[0].summary='Silently overwritten'
    before=dump(path)
    with pytest.raises(ValueError,match='historical communication'):
        save(repo,snapshot,proposal)
    assert dump(path)==before


def test_pdf_household_layout_evidence_traceability_and_item_pagination(insurance):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    workspace = snapshot.workspace.model_copy(deep=True)
    workspace.profile = InsuranceProfile(insurer_name='Fictional Mutual', notes='???????? ?????????')
    workspace.items = [ItemPreparation(damage_id=snapshot.records.damage_records[0].damage_id,
        brand='Fictional refrigerator brand', estimated_cost='123.45', currency='USD')]
    workspace.evidence = [EvidenceRecord(case_id=case.case_id, evidence_type=EvidenceType.RECEIPT,
        status=EvidenceStatus.REPORTED_AVAILABLE, description='Paper receipt available, not uploaded')]
    save(repo, snapshot, workspace, additions=[photo(snapshot, name='refrigerator.png')])
    before = dump(path)
    pdf, _, zipped = build_preparation_package(repo, case.case_id)
    assert dump(path) == before
    pages = [page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages]
    text = '\n'.join(pages)
    for heading in ('Insurance Preparation Package', 'Incident overview', 'Insurance information',
        'Itemized damage inventory', 'Supporting evidence', 'Insurer communication history',
        'Questions and next steps', 'Optional information to add'):
        assert heading in text
    assert '???????? ?????????' in text
    assert any('Fictional refrigerator brand' in page and '123.45 USD' in page for page in pages)
    assert 'independently verified official channel' in text
    assert 'Paper receipt available, not uploaded' in text
    assert 'No file included in companion ZIP' in text
    assert 'Saved versions' not in text and str(case.case_id) not in text
    assert 'Unknown / not supplied' not in text
    with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
        manifest = json.loads(archive.read('evidence-manifest.json'))
        attachment = manifest['attachments'][0]
        assert attachment['original_name'] in text
        assert attachment['safe_filename'] in text.replace('\n', '')
        assert hashlib.sha256(archive.read(attachment['safe_filename'])).hexdigest() == attachment['sha256']


def test_pdf_long_item_narrative_can_span_pages_without_losing_cost_or_text(insurance):
    _, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    workspace = snapshot.workspace.model_copy(deep=True)
    workspace.items = [ItemPreparation(damage_id=snapshot.records.damage_records[0].damage_id,
        estimated_cost='123.45', currency='USD', notes=('Detailed fictional observation. ' * 120) + 'END-OF-ITEM')]
    save(repo, snapshot, workspace)
    pdf, _, _ = build_preparation_package(repo, case.case_id)
    pages = [page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages]
    assert len(pages) > 1
    assert any('Refrigerator - reported item details' in page and '123.45 USD' in page for page in pages)
    assert 'END-OF-ITEM' in '\n'.join(pages)
