"""Explicit review/confirmation of optional saved fictional progress facts."""
from decimal import Decimal
import hashlib
import streamlit as st
from recovery.models import RecoveryCase
from recovery.progress.profiles import CONTRIBUTION_BANDS, ProgressProfile


def _paused(case):
    return (case.intake.immediate_danger is not False or st.session_state.get('rr_pending_danger')
            or st.session_state.get('rr_emergency'))


def _choice(label, value, key):
    options = ['Unknown', 'Yes', 'No']
    selected = st.selectbox(label, options, index={None: 0, True: 1, False: 2}[value], key=key)
    return {'Unknown': None, 'Yes': True, 'No': False}[selected]


def render_progress_profile(repo, case) -> None:
    """Profile side-table editor; no automatic save or plan mutation."""
    if _paused(case):
        st.warning('Household details are paused while safety requires attention.')
        return
    profile = repo.get_progress_profile(case.case_id)
    records = repo.get_recovery_records(case.case_id)
    counts = records.household
    if counts.adults is not None and counts.children is not None:
        suggested = counts.adults + counts.children
        if suggested > 0:
            st.caption(f'Saved adult and child counts suggest {suggested} people. Enter and confirm a total if correct; this suggestion is not saved.')
    if profile.version:
        st.caption('Changed needs can be reviewed through the existing recovery plan controls. Household details do not revise accepted tasks automatically.')
        if st.button('Review changed recovery needs', key='progress_needs_review:'+str(case.case_id)):
            st.session_state['rr_focus'] = 'Continue my recovery'
            st.session_state['rr_update_mode'] = True
            st.rerun()
    prefix = f'progress_profile:{case.case_id}:{profile.version}:'
    preview_key = 'progress_profile_review:'+str(case.case_id)
    st.caption('Optional fictional household details for Recovery Progress. Unknown values stay unknown. '
               'Use fictional information only. The exact address stays in local saved records and is hidden on the progress overview.')
    st.caption('Nightly housing budget and broad repair contribution are separate. Neither establishes available cash, benefits, or insurer payments.')
    with st.form(prefix+'form'):
        total = st.number_input('Confirmed household total (optional)', min_value=1, max_value=10000,
                                value=profile.total, step=1, key=prefix+'total')
        zip_code = st.text_input('Fictional ZIP code (optional)', value=profile.zip_code or '', key=prefix+'zip')
        address = st.text_input('Full fictional address (optional)', value=profile.address or '', max_chars=500, key=prefix+'address')
        started = st.date_input('Recovery start date (optional)', value=profile.recovery_started, key=prefix+'started')
        accessibility = _choice('Accessibility support needed', profile.accessibility, prefix+'accessibility')
        pets = _choice('Household has pets', profile.pets, prefix+'pets')
        vehicle = _choice('Household has transportation', profile.has_vehicle, prefix+'vehicle')
        budget = st.number_input('Nightly housing budget in USD (optional)', min_value=0.0,
                                 value=float(profile.housing_budget) if profile.housing_budget is not None else None,
                                 step=1.0, key=prefix+'budget')
        bands = ['Unknown', *CONTRIBUTION_BANDS]
        band = st.selectbox('Broad repair contribution band (optional)', bands,
                            index=bands.index(profile.contribution_band or 'Unknown'), key=prefix+'band')
        gas_applicable = _choice('Gas service applies to this home', profile.gas_applicable, prefix+'gas_applicable')
        gas_available = _choice('Gas reported available (only if applicable)', profile.gas_available, prefix+'gas_available')
        review = st.form_submit_button('Review household details')
    if review:
        st.session_state.pop(preview_key, None)
        if _paused(case):
            st.warning('Safety changed; household details were not saved.')
            return
        try:
            candidate = ProgressProfile(case_id=case.case_id, version=profile.version,
                updated_at=profile.updated_at, total=total, zip_code=zip_code.strip() or None,
                address=address.strip() or None, recovery_started=started,
                accessibility=accessibility, pets=pets, has_vehicle=vehicle,
                housing_budget=Decimal(str(budget)) if budget is not None else None,
                contribution_band=None if band == 'Unknown' else band,
                gas_applicable=gas_applicable, gas_available=gas_available)
        except ValueError:
            st.error('Review the ZIP code, optional amounts, and gas applicability. A gas report requires gas service to apply. Nothing was saved.')
            return
        st.session_state[preview_key] = {'profile': candidate.model_dump_json(), 'case': case.model_dump_json()}
    preview = st.session_state.get(preview_key)
    if not preview:
        return
    candidate = ProgressProfile.model_validate_json(preview['profile'])
    expected_case = RecoveryCase.model_validate_json(preview['case'])
    if candidate.version != profile.version or expected_case != case:
        st.session_state.pop(preview_key, None)
        st.warning('Saved household details changed. Review the current form again before confirming.')
        return
    st.markdown('**Household details awaiting confirmation**')
    st.caption('Confirmation applies to this displayed review. After changing the form, select Review household details again.')
    for name, value in candidate.model_dump(exclude={'case_id', 'version', 'updated_at'}).items():
        if isinstance(value, bool):
            value = 'Yes' if value else 'No'
        st.text(name.replace('_', ' ').capitalize()+': '+('Unknown' if value is None else str(value)))
    review_hash = hashlib.sha256(preview['profile'].encode()).hexdigest()[:16]
    confirmed = st.checkbox('I confirm the household details shown above', key=prefix+'confirm:'+review_hash)
    if st.button('Confirm and save household details', key=prefix+'save'):
        if _paused(case):
            st.warning('Safety changed; household details were not saved.')
            return
        if not confirmed:
            st.warning('Confirm the reviewed household details before saving. Nothing was saved.')
            return
        try:
            repo.save_progress_profile(candidate, expected_version=profile.version,
                                       expected_case=expected_case, explicitly_confirmed=True)
        except ValueError as error:
            st.warning(str(error))
            return
        st.session_state.pop(preview_key, None)
        st.session_state['rr_notice'] = 'Household details confirmed and saved. Recovery tasks were preserved.'
        st.rerun()
