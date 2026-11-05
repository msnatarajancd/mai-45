"""Static official pathways, separate from M3's reviewed evidence publication.

URL/purpose checks are dated snapshots, not checks of live service availability.
"""
import re
from domain.contracts import Resource


class OfficialPathway(Resource):
    organization: str
    purpose: str
    geography: str


# Independently checked official pages on this date; no M3 review is implied.
PATHWAYS = (
    OfficialPathway(title='Housing and shelter after a disaster', organization='USAGov',
        url='https://www.usa.gov/disaster-housing-shelter', category='Housing',
        purpose='Official information on temporary housing and shelter search pathways.', geography='US',
        last_checked='2026-11-04', caveat='Information only. No open shelter, room, placement or financial help is guaranteed; program conditions apply.'),
    OfficialPathway(title='How to apply for disaster assistance', organization='USAGov',
        url='https://www.usa.gov/disaster-assistance', category='Disaster assistance',
        purpose='Official information and links for FEMA applications and other disaster assistance.', geography='US',
        last_checked='2026-11-04', caveat='FEMA assistance depends on a qualifying declaration and program requirements. ReadyRelief determines no eligibility or outcome and submits nothing.'),
    OfficialPathway(title='Emergency evacuation and shelter information', organization='Miami-Dade County',
        url='https://www.miamidade.gov/global/service.page?Mduid_service=ser1477583540306215', category='Housing',
        purpose='County information about evacuation centers and where official opening information is announced.', geography='Miami-Dade',
        last_checked='2026-11-04', caveat='Not every center opens for every emergency. This link establishes no current evacuation order, open center, bed, transportation or post-disaster lodging availability.'),
    OfficialPathway(title='Find your utility service territories', organization='Florida Public Service Commission',
        url='https://www.psc.state.fl.us/find-utility-service', category='Electricity',
        purpose='Florida utility territory lookup to help identify a provider before contacting it about service.', geography='Florida',
        last_checked='2026-11-04', caveat='Confirm your provider using your bill or the utility. Territory information is a starting point, not household service verification, an outage report or a restoration estimate.'),
    OfficialPathway(title='Water and Sewer service contacts', organization='Miami-Dade County Water and Sewer Department',
        url='https://www.miamidade.gov/global/water/contact-water-sewer.page', category='Water',
        purpose='Department contact pathways for account questions, loss of service and water/sewer problems.', geography='Miami-Dade',
        last_checked='2026-11-04', caveat='Use only if this department is your provider; confirm using your bill. Other utilities may serve your address. No restoration time, water safety or financial assistance is established.'),
)


def find_resources(needs: str, county: str | None = None) -> list[OfficialPathway]:
    """Bounded category/keyword filter; unknown county never implies Miami-Dade.

    General US and Florida entry points support this Miami-Dade demo's unknown
    county flow. This is not nationwide discovery or reviewed guidance retrieval.
    """
    terms = set(re.findall(r'[a-z]+', needs.casefold()))
    categories = set()
    if terms & {'housing', 'shelter', 'shelters', 'lodging', 'accommodation'}:
        categories.add('Housing')
    if terms & {'disaster', 'fema', 'application', 'applications'}:
        categories.add('Disaster assistance')
    if terms & {'electricity', 'electric', 'power', 'outage', 'utility', 'utilities'}:
        categories.add('Electricity')
    if terms & {'water', 'sewer', 'utility', 'utilities'}:
        categories.add('Water')
    return [r.model_copy(deep=True) for r in PATHWAYS if r.category in categories
            and (r.geography != 'Miami-Dade' or county == 'Miami-Dade')]
