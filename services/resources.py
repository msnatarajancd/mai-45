"""M3 directory boundary. These are official entry points, not verified resources."""
from domain.contracts import Resource


OFFICIAL_LINKS = [
    Resource(title='National Weather Service · South Florida', url='https://www.weather.gov/mfl/', category='Weather', caveat='Check official conditions and instructions. This app does not continuously monitor alerts.'),
    Resource(title='Miami-Dade · Weather Ready contacts', url='https://www.miamidade.gov/initiative/weather-ready/contact.page', category='Local assistance', caveat='Official contact directory. Service availability has not been verified by ReadyRelief.'),
    Resource(title='Miami-Dade · Evacuation assistance registration', url='https://www.miamidade.gov/apps/gis/eeap_publicregistration/', category='Transportation', caveat='Eligibility and advance registration requirements apply. No pickup, placement, or response is guaranteed.'),
    Resource(title='Miami-Dade · Text-to-911 information', url='https://www.miamidade.gov/global/release.page?Mduid_release=rel1748353190014356', category='Emergency access', caveat='County announcement; network/device availability is not verified. ReadyRelief cannot send messages.'),
]


def find_resources(needs: str, county: str = 'Miami-Dade') -> list[Resource]:
    # TODO(M3/M4): Return 5–8 human-verified records including reviewed date,
    # service geography, prerequisites, and availability caveats.
    return []
