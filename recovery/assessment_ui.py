"""Small optional controls shared by assessment and confirmed-detail editing."""
from datetime import date
import streamlit as st

from .assessment_summary import profile_suggestions


def optional_details(records, *, prefix, offer_profile=False, include_county=True):
    h = records.household
    with st.expander('Optional details for your recovery', expanded=False):
        st.caption('Share only what helps organize your next steps. Leave unknown details blank; no address, policy number or medical record is needed.')
        housing = list(dict.fromkeys(['Unknown', 'House', 'Apartment', 'Mobile home', 'Other'] + ([h.housing_type] if h.housing_type else [])))
        housing_type = st.selectbox('Housing type (optional)', housing,
            index=housing.index(h.housing_type or 'Unknown'), key=prefix+'housing_type')
        supports = list(dict.fromkeys(['Mobility assistance', 'Accessible communication', 'Transportation support',
                                      'Essential equipment support'] + h.accessibility_needs))
        accessibility = st.multiselect('Accessibility or support needs (optional)', supports,
            default=h.accessibility_needs, key=prefix+'accessibility')
        insurer = ['Unknown', 'Not contacted', 'Contacted', 'Follow-up requested']
        contact = st.selectbox('Have you contacted an insurer? (optional)', insurer,
            index=insurer.index(h.insurer_contact_status), key=prefix+'insurer')
        st.caption('Contacting an insurer does not establish coverage or an accepted claim.')
        county = (st.selectbox('County for your recovery (optional)', ['Unknown', 'Miami-Dade'],
            index=1 if records.reported_county else 0, key=prefix+'county') if include_county else records.reported_county or 'Unknown')
        reference = date.fromisoformat(st.session_state['rr_demo_selection']['as_of']) if st.session_state.get('rr_demo_active') else date.today()
        incident = st.date_input('Reported incident date (optional)', value=records.incident_date,
            max_value=max(reference, records.incident_date or reference), key=prefix+'incident')
        target = st.date_input('Your next check-in target (optional)', value=records.next_check_in_date, key=prefix+'target')
        st.caption('The check-in is your planning target. ReadyRelief does not predict how long recovery will take.')
        profile = profile_suggestions(st.session_state['household']) if offer_profile and 'household' in st.session_state else {}
        use_profile = False
        if any(profile.values()):
            st.caption('Your session profile suggests: '+', '.join(profile['accessibility_needs']+profile['recovery_needs'])+'. Confirm only if this describes your current situation.')
            use_profile = st.checkbox('These profile support needs still apply to this situation', key=prefix+'profile')
    if use_profile:
        accessibility = list(dict.fromkeys(accessibility + profile['accessibility_needs']))
    return dict(housing_type=None if housing_type == 'Unknown' else housing_type,
        accessibility_needs=accessibility, insurer_contact_status=contact,
        reported_county=None if county == 'Unknown' else county, incident_date=incident,
        next_check_in_date=target, profile_needs=profile.get('recovery_needs', []) if use_profile else [])


def apply_optional_details(records, values):
    result = records.model_copy(deep=True)
    for key in ('housing_type', 'accessibility_needs', 'insurer_contact_status'):
        setattr(result.household, key, values[key])
    for key in ('reported_county', 'incident_date', 'next_check_in_date'):
        setattr(result, key, values[key])
    return type(records).model_validate_json(result.model_dump_json())
