"""Integrated Insurance presentation. All durable writes use the Recovery repository."""
from uuid import UUID
import streamlit as st
from recovery.insurance_models import (InsuranceWorkspace, InsuranceProfile, ItemPreparation,
    EvidenceRecord, EvidenceType, EvidenceStatus, InsuranceCommunication)
from recovery.models import RecoveryCase
from recovery.attachments import validate_photo, thumbnail
from recovery.insurance_exports import PACKAGE_LABEL, LIMITATIONS, known, missing_information, build_preparation_package

STAGES = ['Insurance Details', 'Damage Inventory', 'Evidence & Documents', 'Review & Download']


def optional_input(label, value=None):
    return st.text_input(label + ' (optional)', value='' if value is None else str(value), max_chars=200).strip() or None


def render(repo, case):
    from ui.recovery_page import guard_pending_danger
    guard_pending_danger()
    current = repo.get_insurance_snapshot(case.case_id)
    key = 'insurance_base:'+str(case.case_id)
    if key not in st.session_state:
        st.session_state[key] = dict(case=current.case.model_dump_json(), records_version=current.records.version,
                                    workspace=current.workspace.model_dump_json())
    base = st.session_state[key]
    workspace = InsuranceWorkspace.model_validate_json(base['workspace'])
    expected_case = RecoveryCase.model_validate_json(base['case'])
    prefix = f'insurance:{case.case_id}:{workspace.version}:{base["records_version"]}:'
    stale = (expected_case != current.case or base['records_version'] != current.records.version or workspace.version != current.workspace.version)
    if stale:
        st.warning('Saved information changed. Reload before saving; your outdated draft cannot overwrite newer information.')
    if st.button('Reload saved Insurance information'):
        st.session_state.pop(key, None)
        st.rerun()
    stage = st.radio('Insurance workspace stage', STAGES, horizontal=True, key='insurance_stage:'+str(case.case_id))
    notice = st.session_state.pop('insurance_notice', None)
    if notice:
        st.success(notice)

    def save(proposal, confirmed, *, additions=(), removals=()):
        guard_pending_danger()
        if not confirmed:
            raise ValueError('Confirm these Insurance changes first. Nothing was saved.')
        repo.save_insurance_workspace(proposal, expected_case=expected_case,
            expected_records_version=base['records_version'], expected_workspace_version=workspace.version,
            explicitly_confirmed=True, additions=additions, removals=removals)
        st.session_state.pop(key, None)
        st.session_state['insurance_notice'] = 'Insurance changes saved locally. No insurer was contacted and no claim was submitted.'
        st.rerun()

    with st.container(key='insurance_workspace'):
        if stage == STAGES[0]:
            if not current.records.damage_records:
                st.info('No confirmed damaged items have been recorded. You can save optional Insurance details now or document damage first.')
                damage_action()
            profile = workspace.profile
            st.write('Enter what you know. Optional fields may remain Unknown.')
            with st.form(prefix+'profile'):
                a, b = st.columns(2)
                with a:
                    insurer = optional_input('Insurer name', profile.insurer_name)
                    kind = optional_input('Insurance type', profile.insurance_type)
                    policy = optional_input('Policy reference', profile.policy_reference)
                    contacted = st.selectbox('Insurer contacted', ['Unknown', 'Yes', 'No'], index={None:0, True:1, False:2}[profile.insurer_contacted])
                with b:
                    claim = optional_input('Claim reference', profile.claim_reference)
                    incident = st.date_input('Incident date (optional)', value=profile.incident_date)
                    property = st.text_area('Affected-property description (optional)', profile.property_description or '', max_chars=2000)
                notes = st.text_area('Insurance notes (optional)', profile.notes or '', max_chars=4000)
                confirmed = st.checkbox('I confirm these Insurance details')
                submitted = st.form_submit_button('Save Insurance Details', type='primary')
            if submitted:
                proposal = workspace.model_copy(deep=True)
                proposal.profile = InsuranceProfile(insurer_name=insurer, insurance_type=kind,
                    policy_reference=policy, claim_reference=claim, insurer_contacted={'Unknown':None,'Yes':True,'No':False}[contacted],
                    incident_date=incident, property_description=property.strip() or None, notes=notes.strip() or None)
                save(proposal, confirmed)

        elif stage == STAGES[1]:
            st.write('Confirmed Recovery items are reused automatically. Estimates below are user-reported, not valuations or coverage decisions.')
            damage_action()
            if not current.records.damage_records:
                st.info('No confirmed damaged items yet. Use Document damage to add and explicitly confirm an item, then return here.')
            selected_id = st.session_state.get('insurance_edit:'+str(case.case_id))
            for item in current.records.damage_records:
                with st.container(border=True, key='insurance_item_'+str(item.damage_id)):
                    st.markdown('**'+item.item_description+'**')
                    st.text(item.damage_description)
                    st.caption('Item reference: '+str(item.damage_id))
                    photos = [p for p in current.attachments if p.metadata.damage_id == item.damage_id]
                    count = sum(e.damage_id == item.damage_id for e in workspace.evidence)
                    st.caption(f'{len(photos)} saved file(s) / {count} evidence record(s)')
                    if photos:
                        st.image(thumbnail(photos[0]), caption='Saved image preview', width=180)
                    if st.button('Edit Details', key='insurance_edit_button:'+str(item.damage_id)):
                        st.session_state['insurance_edit:'+str(case.case_id)] = str(item.damage_id)
                        st.rerun()
            item = next((d for d in current.records.damage_records if str(d.damage_id) == selected_id), None)
            if item:
                detail = next((d for d in workspace.items if d.damage_id == item.damage_id), ItemPreparation(damage_id=item.damage_id))
                st.subheader('Edit Details: '+item.item_description)
                with st.form(prefix+'item:'+str(item.damage_id)):
                    a, b = st.columns(2)
                    with a:
                        category = optional_input('Item category', detail.category)
                        location = optional_input('Room / location', detail.location)
                        quantity = optional_input('Quantity', detail.quantity)
                        brand = optional_input('Brand', detail.brand)
                        model = optional_input('Model', detail.model)
                    with b:
                        serial = optional_input('Serial / reference', detail.serial_reference)
                        purchase = st.date_input('Approximate purchase date (optional)', value=detail.purchase_date)
                        price = optional_input('Original purchase price', detail.purchase_price)
                        cost = optional_input('User-estimated repair / replacement cost', detail.estimated_cost)
                        currency = optional_input('Currency (three-letter code)', detail.currency)
                    additional = st.text_area('Additional damage description (optional)', detail.additional_damage or '', max_chars=4000)
                    notes = st.text_area('Item preparation notes (optional)', detail.notes or '', max_chars=4000)
                    confirmed = st.checkbox('I confirm these item details')
                    submitted = st.form_submit_button('Save Item Details', type='primary')
                if submitted:
                    updated = ItemPreparation(damage_id=item.damage_id, category=category, location=location,
                        quantity=int(quantity) if quantity else None, brand=brand, model=model,
                        serial_reference=serial, purchase_date=purchase, purchase_price=price,
                        estimated_cost=cost, currency=currency.upper() if currency else None,
                        additional_damage=additional.strip() or None, notes=notes.strip() or None)
                    proposal = workspace.model_copy(deep=True)
                    proposal.items = [d for d in proposal.items if d.damage_id != item.damage_id] + [updated]
                    save(proposal, confirmed)

        elif stage == STAGES[2]:
            evidence_editor(current, workspace, prefix, save)

        else:
            review_download(repo, current)


def damage_action():
    if st.button('Document damage for insurance'):
        st.session_state['rr_focus'] = 'Document damage'
        st.rerun()


def evidence_editor(current, workspace, prefix, save):
    st.caption('Upload existing files only when safe. Do not enter unsafe premises to gather evidence. JPEG/PNG only; PDF, video and photo analysis are not supported.')
    st.warning('Original files may contain EXIF/GPS metadata. Fictional data only; this local course prototype has no authenticated document access or production-grade document security.')
    st.caption(f'{len(current.attachments)} / 20 saved attachments; maximum 5 MiB each and 50 MiB per case.')
    labels = {None:'General case evidence', **{str(d.damage_id):d.item_description for d in current.records.damage_records}}
    association = st.selectbox('Associate new evidence with', list(labels), format_func=labels.get, key=prefix+'association')
    damage_id = UUID(association) if association else None
    category = st.selectbox('File evidence category', list(EvidenceType), key=prefix+'category')
    description = st.text_input('File description (optional)', max_chars=2000, key=prefix+'description')
    uploads = st.file_uploader('Photographs or receipt / estimate scans (JPEG/PNG)', type=['jpg','jpeg','png'],
        accept_multiple_files=True, max_upload_size=5, key=prefix+'uploads')
    pending = []
    if len(uploads) > 20:
        raise ValueError('Select no more than 20 attachments.')
    for upload in uploads:
        photo = validate_photo(upload.getvalue(), upload.name, case_id=workspace.case_id,
                               damage_id=damage_id, evidence_type=category, description=description)
        pending.append(photo)
        st.image(thumbnail(photo), caption='Unsaved preview: '+upload.name, width=200)
    confirmed = st.checkbox('I confirm saving these attachments', key=prefix+'confirm_upload')
    if st.button('Save Attachments', type='primary', disabled=not pending):
        save(workspace, confirmed, additions=pending)
    for photo in current.attachments:
        meta = photo.metadata
        with st.container(border=True, key='insurance_photo_'+str(meta.attachment_id)):
            st.image(thumbnail(photo), caption=meta.original_name+' / '+meta.evidence_type.value, width=200)
            st.caption('File saved / '+labels.get(str(meta.damage_id) if meta.damage_id else None, 'Unknown item')+' / SHA-256 '+meta.sha256)
            st.download_button('Download saved photograph', photo.content, file_name=meta.safe_filename,
                               mime=meta.media_type, key='insurance_download:'+str(meta.attachment_id))
            remove = st.checkbox('I confirm removing this file', key=prefix+'remove:'+str(meta.attachment_id))
            if st.button('Remove saved photograph', key='insurance_remove:'+str(meta.attachment_id)):
                save(workspace, remove, removals=[meta.attachment_id])
    st.subheader('Other evidence')
    st.caption('Reporting an available receipt does not attach a file. Save its JPEG/PNG scan above to record File saved.')
    for evidence in workspace.evidence:
        st.text(evidence.evidence_type.value+' / '+evidence.status.value+' / '+evidence.description)
    with st.form(prefix+'evidence'):
        kind = st.selectbox('Evidence type', list(EvidenceType))
        status = st.selectbox('Evidence status', [v for v in EvidenceStatus if v is not EvidenceStatus.FILE_SAVED])
        text = st.text_area('Evidence description', max_chars=2000)
        when = st.date_input('Evidence date (optional)', value=None)
        confirmed = st.checkbox('I confirm this evidence record')
        submitted = st.form_submit_button('Save Evidence Record', type='secondary')
    if submitted:
        proposal = workspace.model_copy(deep=True)
        proposal.evidence.append(EvidenceRecord(case_id=workspace.case_id, damage_id=damage_id,
            evidence_type=kind, status=status, description=text, relevant_date=when))
        save(proposal, confirmed)
    st.subheader('User-reported insurer communications')
    for entry in workspace.communications:
        st.text(f'{known(entry.contact_date)} / {entry.method} / {known(entry.representative)} / {known(entry.reference)}\n{entry.summary}\nFollow-up: {known(entry.next_follow_up)}')
    with st.form(prefix+'communication'):
        when = st.date_input('Contact date (optional)', value=None)
        method = st.selectbox('Contact method', ['Phone', 'Email', 'Letter', 'In person', 'Other'])
        who = optional_input('Representative / organization')
        reference = optional_input('Communication reference')
        text = st.text_area('Communication summary', max_chars=4000)
        follow = st.text_area('Next follow-up (optional)', max_chars=2000)
        confirmed = st.checkbox('I confirm this user-reported communication')
        submitted = st.form_submit_button('Save Communication', type='secondary')
    if submitted:
        proposal = workspace.model_copy(deep=True)
        proposal.communications.append(InsuranceCommunication(contact_date=when, method=method,
            representative=who, reference=reference, summary=text, next_follow_up=follow.strip() or None))
        save(proposal, confirmed)


def review_download(repo, current):
    from ui.recovery_page import guard_pending_danger
    st.markdown('**'+PACKAGE_LABEL+'**')
    st.caption('Only saved confirmed information is included. Unsaved edits are excluded. This is not an insurer-specific submission checklist.')
    st.subheader('Insurance and incident')
    with st.container(border=True):
        for name,value in current.workspace.profile.model_dump().items():
            if value is not None and value != '':
                st.text(name.replace('_',' ').title()+': '+known(value))
    st.caption('Reported incident: '+current.case.intake.disaster_type+' / '+current.case.intake.housing_condition)
    st.text('Children: '+known(current.records.household.children)+' / Adults: '+known(current.records.household.adults))
    st.subheader('Confirmed damage inventory')
    details = {item.damage_id:item for item in current.workspace.items}
    if not current.records.damage_records:
        st.info('No confirmed damaged items have been recorded. Add and confirm items through Recovery.')
        damage_action()
    st.text('Confirmed items: '+('; '.join(item.item_description for item in current.records.damage_records) or 'None recorded'))
    for item in current.records.damage_records:
        st.markdown('**'+item.item_description+'**')
        st.text('Item / area: '+item.item_description+'\n'+item.damage_description)
        if item.damage_id in details:
            for name,value in details[item.damage_id].model_dump().items():
                if name!='damage_id' and value is not None and value != '':
                    st.text(name.replace('_',' ').title()+': '+known(value))
    st.subheader('Saved evidence and communications')
    st.caption(f'{len(current.attachments)} actual saved file(s) / {len(current.workspace.evidence)} evidence record(s) / {len(current.workspace.communications)} user-reported communication(s)')
    for evidence in current.workspace.evidence:
        st.text(evidence.evidence_type.value+' / '+evidence.status.value+' / '+evidence.description)
    for entry in current.workspace.communications:
        st.text(f'{known(entry.contact_date)} / {entry.method} / {entry.summary}')
    st.subheader('Optional information not yet supplied')
    missing = missing_information(current)
    for stage in STAGES[:3]:
        fields = [field for target,field in missing if target==stage]
        if fields:
            st.write(stage+': '+ '; '.join(fields))
            st.caption('Open '+stage+' using the stage selector above to enter these details. Policy information and applicable procedures must be obtained from your own records or insurer; no deadline or coverage is inferred.')
    if not missing:
        st.caption('No tracked optional fields are missing. Insurer-specific requirements remain unverified.')
    st.info(LIMITATIONS)
    guard_pending_danger()
    pdf, inventory, archive = build_preparation_package(repo, current.case.case_id)
    guard_pending_danger()
    # Recheck persisted danger and versions after potentially lengthy PDF work.
    latest = repo.get_insurance_snapshot(current.case.case_id)
    if latest.case != current.case or latest.records.version != current.records.version or latest.workspace.version != current.workspace.version:
        st.warning('Saved information changed while preparing exports. Reload before downloading.')
        return
    st.download_button('Download Preparation PDF', pdf, file_name='insurance-preparation.pdf', mime='application/pdf', type='primary')
    st.download_button('Download Damage Inventory CSV', inventory, file_name='damage-inventory.csv', mime='text/csv')
    st.download_button('Download Evidence ZIP', archive, file_name='insurance-evidence.zip', mime='application/zip')
