"""M3 directory boundary. These are official entry points, not verified resources."""
from domain.contracts import Resource


OFFICIAL_LINKS = [
    Resource(title='National Weather Service · South Florida', url='https://www.weather.gov/mfl/', category='Weather', caveat='Check official conditions and instructions. This app does not continuously monitor alerts.'),
    Resource(title='Miami-Dade · Weather Ready contacts', url='https://www.miamidade.gov/initiative/weather-ready/contact.page', category='Local assistance', caveat='Official contact directory. Service availability has not been verified by ReadyRelief.'),
    Resource(title='Miami-Dade · Evacuation assistance registration', url='https://www.miamidade.gov/apps/gis/eeap_publicregistration/', category='Transportation', caveat='Eligibility and advance registration requirements apply. No pickup, placement, or response is guaranteed.'),
    Resource(title='Miami-Dade · Text-to-911 information', url='https://www.mdso.com/text-911', category='Emergency access', caveat='Official entry link; network/device availability is not verified. ReadyRelief cannot send messages.'),
]


def find_resources(needs: str, county: str | None = None) -> list[Resource]:
    """Compatibility view. County is explicit; verified results still use the gate."""
    from domain.resources import ResourceQuery
    result = lookup_resources(ResourceQuery(needs=needs, county=county))
    return [Resource(title=record.official_name, url=record.official_url,
        category=record.service_category, caveat=' '.join(record.limitations),
        last_checked=record.reviewed_at.isoformat()) for record in result.records]


OFFICIAL_EEAP_LINKS = [
    Resource(title='Miami-Dade · EEAP official program information',
        url='https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672',
        category='Transportation', caveat='Official entry link; directory review pending. Current availability not verified.'),
    Resource(title='Miami-Dade · EEAP registration FAQ',
        url='https://www.miamidade.gov/global/faq.page?Mduid_faq=faq1598023863344518',
        category='Transportation', caveat='Read the county’s current application and timing requirements. This link does not enroll or book transportation.'),
]
GENERAL_EMERGENCY_LINKS = [
    Resource(title='FCC · Text-to-911 guidance',
        url='https://www.fcc.gov/consumers/guides/what-you-need-know-about-text-911',
        category='Emergency access', caveat='Official entry link. Local coverage, device connectivity, and delivery are not verified.'),
    Resource(title='911.gov · Frequently asked questions',
        url='https://www.911.gov/calling-911/frequently-asked-questions/',
        category='Emergency access', caveat='Official entry link; ReadyRelief cannot place calls or send messages.'),
]
MIAMI_DADE_EMERGENCY_LINKS = [
    Resource(title="Miami-Dade Sheriff’s Office · Text 911 information",
        url='https://www.mdso.com/text-911', category='Emergency access',
        caveat='Official entry link; directory review pending. Device connectivity and delivery are not verified.'),
]


def lookup_resources(request, now=None, *, store=None):
    """Load directory dependencies lazily so entry links survive storage failures."""
    from pathlib import Path
    from knowledge.resources import lookup_resources as lookup
    from knowledge.store import SourceStore
    return lookup(store if store is not None else SourceStore(Path(__file__).resolve().parents[1]/'data/official_sources'), request, now)
