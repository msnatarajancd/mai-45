# Official assistance pathways

The integrated Recover → Find assistance action uses services.resources.find_resources(needs, county=None).
It returns OfficialPathway objects extending the existing Resource display contract
with organization, purpose and geography. Existing title, url, category, caveat and
last_checked fields are retained. No model, database writes or external submissions
are involved. Housing, disaster assistance, electricity and water filters are independent.
Only saved RecoveryRecords.reported_county supplies county context. Unknown county
shows general US and Florida entry points, not local providers. No approved plan is required.

## Independent link checks: November 4, 2026

| Organization | Official page | Purpose / limitation |
|---|---|---|
| USAGov | https://www.usa.gov/disaster-housing-shelter | Temporary housing and shelter information; no placement or open facility guaranteed. |
| USAGov | https://www.usa.gov/disaster-assistance | FEMA application information and official onward links; declarations and individual program requirements apply. No eligibility determination or submission. |
| Miami-Dade County | https://www.miamidade.gov/global/service.page?Mduid_service=ser1477583540306215 | Evacuation-center information; not all centers open. No current order, center opening or transportation inferred. Includes older material; no instructions extracted. |
| Florida Public Service Commission | https://www.psc.state.fl.us/find-utility-service | Utility territory lookup; identify provider, then confirm with bill/utility. Not outage reporting or a restoration estimate. Search-index text verified; direct fetch produced no readable text (interactive page). |
| Miami-Dade Water and Sewer | https://www.miamidade.gov/global/water/contact-water-sewer.page | Service contacts including loss of service. Only applicable if this is the household's provider; no water safety, restoration or financial assistance guaranteed. |

These are dated official-link/purpose checks, not monitoring of live services.
DisasterAssistance.gov direct retrieval returned HTTP 403 to the research tool;
it is not included as a directly verified directory entry. USAGov's successfully
read page provides the application pathway instead. No phone numbers are copied.

## M3 trust boundary

None of these five URLs is in the current M3 source manifest. Its reviewed CDC
reentry source and pending CDC floodwater/EEAP sources are separate. This directory
does not acquire, approve, publish or export evidence. It never feeds directory
descriptions into Qwen or M5 evidence objects. Existing separately reviewed guidance
continues below the directory with its existing gates. Human review records and
government captures remain untouched.

## Safety and limitations

Existing pending-danger guards and persisted-danger restrictions precede the Finder.
Global Call 911 / I Can't Call 911 controls remain unchanged and independent of storage,
retrieval and models. Directory errors produce an unavailable message; zero matches
do not imply no assistance exists. Provider, opening, eligibility, availability and
restoration must be confirmed externally. Static links can change and need periodic
manual rechecking; last_checked is not refreshed automatically.

Run offline tests:

```powershell
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_assistance_finder.py tests/test_recovery_landing.py tests/test_pending_danger.py
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
..\.venv\Scripts\python.exe -m streamlit run app.py
```
