# Recovery knowledge coverage: human review packet

**Superseded approval procedure:** see M3_RECOVERY_FINAL_APPROVAL_PREPARATION.md. All earlier blanket approval examples have been removed. NFIP parent is on HOLD; only USAGov parent/Candidate 5 have prepared conditional human commands. Original six candidate records remain unchanged. A separate replacement candidate is documented in the final preparation packet.

All six candidates are PENDING. No approval or publication action was executed.
Prepared: 2026-11-04T18:39:09.719362+00:00

## Existing coverage
Three original sources were inspected: five CDC reentry candidates pass the full publication gate; one reentry, six floodwater and four EEAP candidates remain pending. No other approved sources were found. All three preserved original hashes verified.

## Acquisition and source review blockers
NFIP: the first urllib request failed TLS certificate validation. That failed attempt remains in history. A separate successful acquisition used Windows curl certificate validation through the existing M3 transport boundary; TLS verification was not disabled.
USAGov: acquired with the existing default transport. These are new captures, independent of the Assistance Finder directory check.
HTML text is extracted from preserved bytes with normalized layout whitespace. Browser search results are not substituted for acquired content. Some headings/images may be omitted by static extraction.
NFIP full-source context contains broad electrical shutdown advice that must be reconciled with CDC standing-water warnings during parent review. That advice is not selected for publication. Mold-coverage statements also require source-level inspection. Strict UTF-8 decoding found zero Unicode replacement characters in either capture; console apostrophe rendering is not a source-text defect.
USAGov hotel-program context includes stronger payment language than the selected conditional first sentence. Do not publish neighboring context or infer eligibility, reservations, or available rooms.
No auto-freshness interval exists. Approval covers the captured version, not live conditions.

## Required human procedure
Inspect preserved HTML and all extracted sections. Approve each eligible standalone candidate and its caveats individually using your own reviewer identity. Approve the parent only after full source-level inspection; source approval alone never publishes pending candidates. Leave any unresolved item pending.
Commands below are for a human, not recorded signoffs. Replace <HUMAN_REVIEWER> yourself. Hash changes require fresh inspection; do not copy stale commands.
Candidate approval may precede parent approval; retrieval requires both. No additional publish command bypasses these gates.

## Source: nfip-document-flood-damage
- Official URL: https://www.floodsmart.gov/recover/document-damage
- Captured UTC: 2026-11-04T18:37:55.105232+00:00
- HTTP: 200; bytes: 84025; sections: 11
- Original SHA-256: `fc9693d31c3fbbb1353a9365ff328e770de53e91800978b1dbfdb3145a0f2f9f`
- Original: `data/official_sources/originals/fc9693d31c3fbbb1353a9365ff328e770de53e91800978b1dbfdb3145a0f2f9f.bin`
- Status: REVIEW_REQUIRED; no reviewer or review timestamp.
- Scope: US; source hazards flood/hurricane; phase recover. Proposed candidates are flood/recover only.

```powershell
python -m knowledge.review inspect --source-id nfip-document-flood-damage
```

## Source: usagov-disaster-housing
- Official URL: https://www.usa.gov/disaster-housing-shelter
- Captured UTC: 2026-11-04T18:37:15.431013+00:00
- HTTP: 200; bytes: 40906; sections: 8
- Original SHA-256: `44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2`
- Original: `data/official_sources/originals/44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2.bin`
- Status: DOWNLOADED_UNREVIEWED; no reviewer or review timestamp.
- Scope: US; source hazards flood/hurricane; phase recover. Proposed candidates are flood/recover only.

```powershell
python -m knowledge.review inspect --source-id usagov-disaster-housing
```

## Candidate 1: fe4096112e28365974239d4f78f6b6039dd07c8953cc272c0477fcf6caefb916
**Status: PENDING**
- Supports question A: document flood-damaged furniture for insurance.
- Source: nfip-document-flood-damage; https://www.floodsmart.gov/recover/document-damage
- Scope: US / flood / recover; source SHA-256 `fc9693d31c3fbbb1353a9365ff328e770de53e91800978b1dbfdb3145a0f2f9f`.
- Parent: `36f62ce1160c79cd5d42fcf37bc80bee44aec9e80629959fa7f42a0fb1dad3a6`; span [0, 247); length 247.
- Candidate/context SHA-256: `fc353cd3dd9b2914ffb5c81b4e7a26b1d217acc2e4100682a0118e39b2378212`

**Exact original passage / proposed retrieval text (identical):**
```text
Take clear pictures and videos of damaged items before cleaning, fixing or throwing them out. Capture wide shots and close-ups of walls, floors and furniture. Remember to record serial numbers from electronics and appliances to support your claim.
```

**Editorial safety caveats (must be reviewed):**
- PENDING human review; not operational guidance or household safety verification.
- The source conditions documentation on safe return. This passage is not permission to enter or handle hazards; preserve existing reentry and electrical warnings.
- NFIP documentation information only; no insurance coverage, reimbursement or claim outcome is established.
- The source separately instructs disposal of health-risk items after photographs; do not retain hazardous items to document them.

```powershell
python -m knowledge.review inspect --source-id nfip-document-flood-damage --chunk-id fe4096112e28365974239d4f78f6b6039dd07c8953cc272c0477fcf6caefb916
```

**Full administrative context ? must NOT be published or sent to Qwen:**
### How to document flood damage > Document everything before you start cleanup (36f62ce1160c79cd5d42fcf37bc80bee44aec9e80629959fa7f42a0fb1dad3a6)
```text
Take clear pictures and videos of damaged items before cleaning, fixing or throwing them out. Capture wide shots and close-ups of walls, floors and furniture. Remember to record serial numbers from electronics and appliances to support your claim.
```
### How to document flood damage (2aab798d4f6894db8be6dfadb5eba6475664833fcf562c5b428d384a9400d62d)
```text
Recovery begins once floodwaters recede. If you have flood insurance, you don’t have to go through it alone.
When it’s safe to return home, act quickly to document flood damage. Early action can support your flood insurance claim and gets you on the road to recovery.
```
### How to document flood damage > FAQs about documenting flood damage and mold (5004880fe006404b5bc5298e8d9256da9d6452a587bf29b092ae8cafe345b1ce)
```text
Photos and videos are key for your flood insurance claim. Be sure to capture:
Water levels on walls, furniture and appliances.
Structural damage to floors, ceilings and foundations.
Serial numbers on damaged electronics and appliances.
After taking photos, immediately throw away anything that could be a health risk, like spoiled food or moldy clothing, cushions and pillows.
```

## Candidate 2: a84e865690a511e23ecb8fe1eeba0b083ae674a039090f8c478f732700dde983
**Status: PENDING**
- Supports question A: document flood-damaged furniture for insurance.
- Source: nfip-document-flood-damage; https://www.floodsmart.gov/recover/document-damage
- Scope: US / flood / recover; source SHA-256 `fc9693d31c3fbbb1353a9365ff328e770de53e91800978b1dbfdb3145a0f2f9f`.
- Parent: `5004880fe006404b5bc5298e8d9256da9d6452a587bf29b092ae8cafe345b1ce`; span [0, 376); length 376.
- Candidate/context SHA-256: `46fca8e3676e088419b72b38fe5fab231c081b869ceccc6885ea491ee1dbc406`

**Exact original passage / proposed retrieval text (identical):**
```text
Photos and videos are key for your flood insurance claim. Be sure to capture:
Water levels on walls, furniture and appliances.
Structural damage to floors, ceilings and foundations.
Serial numbers on damaged electronics and appliances.
After taking photos, immediately throw away anything that could be a health risk, like spoiled food or moldy clothing, cushions and pillows.
```

**Editorial safety caveats (must be reviewed):**
- PENDING human review; not operational guidance or household safety verification.
- The source conditions documentation on safe return. This passage is not permission to enter or handle hazards; preserve existing reentry and electrical warnings.
- NFIP documentation information only; no insurance coverage, reimbursement or claim outcome is established.

```powershell
python -m knowledge.review inspect --source-id nfip-document-flood-damage --chunk-id a84e865690a511e23ecb8fe1eeba0b083ae674a039090f8c478f732700dde983
```

**Full administrative context ? must NOT be published or sent to Qwen:**
### How to document flood damage > FAQs about documenting flood damage and mold (5004880fe006404b5bc5298e8d9256da9d6452a587bf29b092ae8cafe345b1ce)
```text
Photos and videos are key for your flood insurance claim. Be sure to capture:
Water levels on walls, furniture and appliances.
Structural damage to floors, ceilings and foundations.
Serial numbers on damaged electronics and appliances.
After taking photos, immediately throw away anything that could be a health risk, like spoiled food or moldy clothing, cushions and pillows.
```
### How to document flood damage (2aab798d4f6894db8be6dfadb5eba6475664833fcf562c5b428d384a9400d62d)
```text
Recovery begins once floodwaters recede. If you have flood insurance, you don’t have to go through it alone.
When it’s safe to return home, act quickly to document flood damage. Early action can support your flood insurance claim and gets you on the road to recovery.
```

## Candidate 3: fc072448ce3bcea4ad83400947fae856e01af8c604f986fd866bcc026bb5605f
**Status: PENDING**
- Supports question A: document flood-damaged furniture for insurance.
- Source: nfip-document-flood-damage; https://www.floodsmart.gov/recover/document-damage
- Scope: US / flood / recover; source SHA-256 `fc9693d31c3fbbb1353a9365ff328e770de53e91800978b1dbfdb3145a0f2f9f`.
- Parent: `b27b8679965b7426166595fb344c35e2daf467a81c659aa7586bb1e859ac0457`; span [0, 253); length 253.
- Candidate/context SHA-256: `3d461fbeedd74f638655f7dc279dba62db4b4997bbac8c0616830bacd1c0c525`

**Exact original passage / proposed retrieval text (identical):**
```text
Keeping samples and receipts helps prove flood damage and supports your claim. Save things like:
Small pieces of damaged carpet, drywall or insulation.
Receipts for repairs and replacement items.
Warranty or manufacturer details for replaced appliances.
```

**Editorial safety caveats (must be reviewed):**
- PENDING human review; not operational guidance or household safety verification.
- The source conditions documentation on safe return. This passage is not permission to enter or handle hazards; preserve existing reentry and electrical warnings.
- NFIP documentation information only; no insurance coverage, reimbursement or claim outcome is established.
- Keep only small material samples when safe; this is not an instruction to retain contaminated or health-risk items.

```powershell
python -m knowledge.review inspect --source-id nfip-document-flood-damage --chunk-id fc072448ce3bcea4ad83400947fae856e01af8c604f986fd866bcc026bb5605f
```

**Full administrative context ? must NOT be published or sent to Qwen:**
### How to document flood damage > FAQs about documenting flood damage and mold (b27b8679965b7426166595fb344c35e2daf467a81c659aa7586bb1e859ac0457)
```text
Keeping samples and receipts helps prove flood damage and supports your claim. Save things like:
Small pieces of damaged carpet, drywall or insulation.
Receipts for repairs and replacement items.
Warranty or manufacturer details for replaced appliances.
```
### How to document flood damage (2aab798d4f6894db8be6dfadb5eba6475664833fcf562c5b428d384a9400d62d)
```text
Recovery begins once floodwaters recede. If you have flood insurance, you don’t have to go through it alone.
When it’s safe to return home, act quickly to document flood damage. Early action can support your flood insurance claim and gets you on the road to recovery.
```
### How to document flood damage > FAQs about documenting flood damage and mold (5004880fe006404b5bc5298e8d9256da9d6452a587bf29b092ae8cafe345b1ce)
```text
Photos and videos are key for your flood insurance claim. Be sure to capture:
Water levels on walls, furniture and appliances.
Structural damage to floors, ceilings and foundations.
Serial numbers on damaged electronics and appliances.
After taking photos, immediately throw away anything that could be a health risk, like spoiled food or moldy clothing, cushions and pillows.
```

## Candidate 4: bb5d9e9af1c354b8e87f39b4ee6bd48aaa069f41ef83917b9245d344675af199
**Status: PENDING**
- Supports question B: learn about temporary housing assistance after flooding.
- Source: usagov-disaster-housing; https://www.usa.gov/disaster-housing-shelter
- Scope: US / flood / recover; source SHA-256 `44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2`.
- Parent: `41425b779ac21c95d361155dfaec59ed299314b800993f182272dd03c2ae541e`; span [0, 66); length 66.
- Candidate/context SHA-256: `c76a1f2e334dbae02f54b5f84c9298d933c5a21c3acb9b846a23e2060b8bbe1a`

**Exact original passage / proposed retrieval text (identical):**
```text
Learn where to search for temporary housing or a shelter near you.
```

**Editorial safety caveats (must be reviewed):**
- PENDING human review; not operational guidance or household safety verification.
- Static information pathway only: no current housing, shelter opening, room, placement, transportation, funding or personal eligibility is established.
- Program registration, geographic declaration and individual requirements must be confirmed with the official program; no application is submitted here.

```powershell
python -m knowledge.review inspect --source-id usagov-disaster-housing --chunk-id bb5d9e9af1c354b8e87f39b4ee6bd48aaa069f41ef83917b9245d344675af199
```

**Full administrative context ? must NOT be published or sent to Qwen:**
### How to find housing after a disaster (41425b779ac21c95d361155dfaec59ed299314b800993f182272dd03c2ae541e)
```text
Learn where to search for temporary housing or a shelter near you. Find out if you qualify for financial help to pay for housing after a disaster.
```
### How to find housing after a disaster > Find a shelter (86aed4193867b4912bf96474c9e9c24f494465bec49093c38eebcdf1bf427728)
```text
If you live in a presidentially declared disaster area, there are programs and organizations that can help you find shelter.
```
### How to find housing after a disaster > Find a shelter > Find transitional shelter in a hotel (f16fe9aef5adb826d7f27e44ccf457ce570facfdc1fd42344d7e18454199b562)
```text
After you register for disaster assistance with FEMA, you will find out if you qualify for transitional housing. The Transitional Sheltering Assistance (TSA) program will pay for your hotel stay while you are displaced. 
Enter your FEMA registration number to find a hotel that participates in the TSA program and contact them to reserve a room.
```

## Candidate 5: 8630330fbd12aabc3c31bff38cd811d234bc3e214e05021a322d6f082d9f2b48
**Status: PENDING**
- Supports question B: learn about temporary housing assistance after flooding.
- Source: usagov-disaster-housing; https://www.usa.gov/disaster-housing-shelter
- Scope: US / flood / recover; source SHA-256 `44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2`.
- Parent: `f16fe9aef5adb826d7f27e44ccf457ce570facfdc1fd42344d7e18454199b562`; span [0, 112); length 112.
- Candidate/context SHA-256: `3034b531f7dcb800f4473cef6de4867826f8c888c384cb3a5c7665a33d219cc4`

**Exact original passage / proposed retrieval text (identical):**
```text
After you register for disaster assistance with FEMA, you will find out if you qualify for transitional housing.
```

**Editorial safety caveats (must be reviewed):**
- PENDING human review; not operational guidance or household safety verification.
- Static information pathway only: no current housing, shelter opening, room, placement, transportation, funding or personal eligibility is established.
- Program registration, geographic declaration and individual requirements must be confirmed with the official program; no application is submitted here.
- Registration does not establish qualification, an approved hotel payment or a room reservation. The remaining hotel-program description stays administrative context only.

```powershell
python -m knowledge.review inspect --source-id usagov-disaster-housing --chunk-id 8630330fbd12aabc3c31bff38cd811d234bc3e214e05021a322d6f082d9f2b48
```

**Full administrative context ? must NOT be published or sent to Qwen:**
### How to find housing after a disaster > Find a shelter > Find transitional shelter in a hotel (f16fe9aef5adb826d7f27e44ccf457ce570facfdc1fd42344d7e18454199b562)
```text
After you register for disaster assistance with FEMA, you will find out if you qualify for transitional housing. The Transitional Sheltering Assistance (TSA) program will pay for your hotel stay while you are displaced. 
Enter your FEMA registration number to find a hotel that participates in the TSA program and contact them to reserve a room.
```
### How to find housing after a disaster > Find a shelter (86aed4193867b4912bf96474c9e9c24f494465bec49093c38eebcdf1bf427728)
```text
If you live in a presidentially declared disaster area, there are programs and organizations that can help you find shelter.
```

## Candidate 6: 4cc704dacf6262548e1c5818b316aab6f0aec53578bc0630cede57afc72a3b48
**Status: PENDING**
- Supports question B: learn about temporary housing assistance after flooding.
- Source: usagov-disaster-housing; https://www.usa.gov/disaster-housing-shelter
- Scope: US / flood / recover; source SHA-256 `44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2`.
- Parent: `1c32796ebf8758580ee46eeee4ca39845fb7e3913596338ac6e000ae90ec8913`; span [0, 287); length 287.
- Candidate/context SHA-256: `bc63b78b163847e7e289e177e69671fe74e4291b5fd11aee55208b8923923f6a`

**Exact original passage / proposed retrieval text (identical):**
```text
Some Low Income Home Energy Assistance Programs (LIHEAPs) set aside money to help people get shelter after a natural disaster. Each office sets its own criteria for who can receive funds. Contact the LIHEAP office that serves your state. Or contact the LIHEAP office in your tribal area.
```

**Editorial safety caveats (must be reviewed):**
- PENDING human review; not operational guidance or household safety verification.
- Static information pathway only: no current housing, shelter opening, room, placement, transportation, funding or personal eligibility is established.
- Program registration, geographic declaration and individual requirements must be confirmed with the official program; no application is submitted here.
- Each office sets its own funding criteria; no local office, contact details or funds are verified by this candidate.

```powershell
python -m knowledge.review inspect --source-id usagov-disaster-housing --chunk-id 4cc704dacf6262548e1c5818b316aab6f0aec53578bc0630cede57afc72a3b48
```

**Full administrative context ? must NOT be published or sent to Qwen:**
### How to find housing after a disaster > Get help paying for housing (1c32796ebf8758580ee46eeee4ca39845fb7e3913596338ac6e000ae90ec8913)
```text
Some Low Income Home Energy Assistance Programs (LIHEAPs) set aside money to help people get shelter after a natural disaster. Each office sets its own criteria for who can receive funds. Contact the LIHEAP office that serves your state. Or contact the LIHEAP office in your tribal area.
Image
Find more programs and services to help with life after a disaster.
LAST UPDATED:
 November 3, 2026
 SHARE THIS PAGE:
```
### How to find housing after a disaster (41425b779ac21c95d361155dfaec59ed299314b800993f182272dd03c2ae541e)
```text
Learn where to search for temporary housing or a shelter near you. Find out if you qualify for financial help to pay for housing after a disaster.
```

## Retrieval verification after human decisions
Use FoundationKnowledgeService(SourceStore("data/official_sources")).retrieve_guidance(KnowledgeRequest(hazard=Hazard.FLOOD, disaster_phase=DisasterPhase.RECOVER, jurisdiction="US-FL-MIAMI-DADE", safety_topic=topic, requested_evidence_count=1)).
Test both full demo questions and bounded topics ("pictures videos furniture", "temporary housing", "transitional housing", "housing funds"). Check returned candidate IDs, original hashes and public caveats. Do not treat SUCCESS as an eligibility or coverage decision.
Before approval these sources must contribute zero evidence and M5 export must reject all six candidates. Existing CDC matches may still appear; no approved evidence was revoked.

## Retrieval blockers and offline lexical sanity check (not publication)
Both full demo questions currently return zero evidence: A is NO_RELEVANT_EVIDENCE; B is INSUFFICIENT_EVIDENCE. Neither pending source contributes published guidance.

Important: B is blocked before lexical search by the existing conservative operational-question detector: `can ... assistance` matches "Where can I learn about temporary housing assistance after flooding?". Formal evidence approval alone will not make that exact wording retrievable. Use the supported static topic "temporary housing" for a later demo, or request a separately reviewed M3 change; no detector/ranking change was made here.

Ignoring gates only to inspect lexical overlap, question A has two proposed NFIP matches (token coverage 0.75 and 0.50); question B has one USAGov introduction match (0.571), but that does NOT bypass its earlier operational abstention. With the default requested count of three, bounded static topics may still produce INSUFFICIENT_EVIDENCE after human review. An explicitly single-excerpt request can test a narrower static topic after both gates; SUCCESS is not completeness, safety clearance, coverage or eligibility.
