"""Standalone M2 integration preview; not the shared M1 application."""
import streamlit as st
from m2_guardian.service import GuardianService, LOCATIONS
from m2_guardian.explanation import explain_alert

def render_guardian(*, retrieve_guidance=None, llm_client=None):
    st.title('ReadyRelief | Guardian')
    st.caption('Course prototype. On-demand lookup; no background monitoring or dispatch.')
    st.info('For a life-threatening emergency in the U.S., call 911. Do not wait for this prototype.')
    st.link_button('Official NWS information', 'https://www.weather.gov/')
    location = st.selectbox('Watch area', list(LOCATIONS) + ['custom_point'],
                            format_func=lambda k: 'Enter coordinates' if k == 'custom_point' else LOCATIONS[k]['label'])
    latitude, longitude = None, None
    if location == 'custom_point':
        st.caption('Enter coordinates manually. Live checks send them to NWS; no device location is collected. Coverage is limited to NWS-served areas.')
        latitude = st.number_input('Latitude', min_value=-90.0, max_value=90.0, value=25.7617, format='%.6f')
        longitude = st.number_input('Longitude', min_value=-180.0, max_value=180.0, value=-80.1918, format='%.6f')
    mode_label = st.radio('Data mode', ['SIMULATED DEMO', 'LIVE CHECK'], horizontal=True)
    mode = 'simulated' if mode_label == 'SIMULATED DEMO' else 'live'
    scenario = st.selectbox('Fictional scenario', ['warning', 'no_alerts', 'unavailable']) if mode == 'simulated' else 'warning'
    key = (location, mode, scenario, latitude, longitude)
    # Never retain another location/mode's result under the new selection.
    if st.session_state.get('guardian_selection') != key:
        st.session_state.pop('guardian_result', None)
        st.session_state.pop('guardian_explanation', None)
    st.session_state['guardian_selection'] = key
    if st.button('Check alerts', type='primary'):
        st.session_state.pop('guardian_explanation', None)
        with st.spinner('Checking selected source…'):
            service = GuardianService()
            if location == 'custom_point':
                st.session_state['guardian_result'] = service.get_alerts_by_point(latitude, longitude, mode, scenario)
            else:
                st.session_state['guardian_result'] = service.get_alerts(location, mode, scenario)
    r = st.session_state.get('guardian_result')
    if r:
        st.warning(r['notice'])
        st.caption('Checked at: ' + r['checked_at'] + ' | Scope: ' + r['location']['scope'])
        st.caption('Result is a snapshot; check again for updates.')
        if r['location']['scope'] == 'county':
            st.caption('County coverage is not address-specific.')
        for alert in r['alerts']:
            st.subheader(alert['event'])
            # Plain text prevents upstream content being treated as HTML or instructions.
            st.text(alert['headline'] or alert['event'])
            st.text('Area: ' + alert['area'])
            st.text('Issued by: ' + alert['sender'])
            st.text('Expires: ' + alert['expires'])
            st.text(alert['description'])
            st.text(alert['instruction'] or 'No instructions supplied in this record.')
            st.link_button('Official source', alert['source_url'])
            if st.button('Understand this alert', key='explain_' + alert['id']):
                st.session_state['guardian_explanation'] = explain_alert(
                    r, alert['id'], retrieve_guidance=retrieve_guidance, llm_client=llm_client)
            explanation = st.session_state.get('guardian_explanation')
            if explanation and explanation['alert_id'] == alert['id']:
                st.caption(explanation['label'])
                st.text(explanation['notice'])
                if explanation['status'] == 'available':
                    details = explanation['official_details']
                    st.text('Official classifications: severity=' + str(details['severity']) +
                            '; urgency=' + str(details['urgency']) + '; certainty=' + str(details['certainty']))
                    if explanation['guidance']:
                        st.caption('Supporting guidance excerpts — relevance requires review; not a safety determination.')
                        for excerpt in explanation['guidance']:
                            st.text(excerpt['guidance_text'])
                            st.link_button(excerpt['source_title'], excerpt['source_url'],
                                           key='source_' + excerpt['source_id'])
                    else:
                        st.caption('Additional reviewed guidance is not available. Official alert text remains above.')

        with st.expander('Integration details'):
            st.json(r)
    st.divider()
    st.write('For a life-threatening emergency in the U.S., call 911. Do not wait for this prototype.')


if __name__ == "__main__":
    st.set_page_config(page_title="ReadyRelief Guardian", layout="centered")
    render_guardian()
