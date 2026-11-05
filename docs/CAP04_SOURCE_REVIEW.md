# CAP-04 directory source and listing review packet

**All eight directory listings are PENDING. No source, passage, or listing approval was performed for CAP-04.**

Prepared 2026-11-05T01:56:15.618976+00:00. This is an administrative review packet, not published emergency guidance. Review preparation and isolated tests do not constitute human signoff. Existing CDC and EEAP approval artifacts were preserved.

## Readiness

| Listing | Source | Evidence readiness |
|---|---|---|
| `fcc-text-911-guidance` | `fcc-text-911` | Acquisition blocked; no original hash or publishable evidence |
| `miami-dade-311` | `miami-dade-weather-contacts` | Exact acquired passages; source, passage and listing review outstanding |
| `miami-dade-eeap-inquiry` | `miami-dade-eeap` | Exact acquired passages; source, passage and listing review outstanding |
| `miami-dade-eeap-planning` | `miami-dade-eeap` | Exact acquired passages; source, passage and listing review outstanding |
| `miami-dade-emergency-management` | `miami-dade-weather-contacts` | Exact acquired passages; source, passage and listing review outstanding |
| `miami-dade-sheriff-nonemergency` | `miami-dade-weather-contacts` | Exact acquired passages; source, passage and listing review outstanding |
| `miami-dade-text-911` | `miami-dade-text-911` | Exact acquired passages; source, passage and listing review outstanding |
| `miami-dade-water-sewer` | `miami-dade-weather-contacts` | Exact acquired passages; source, passage and listing review outstanding |

Seven listings have original-byte provenance and exact candidate passages. FCC is the eighth, blocked record. The official FCC page was readable through Tavily on November 4, 2026, but direct M3 acquisition returned an HTTP error. Tavily extraction is not substituted for original HTTP bytes. No FCC candidate or source hash was invented. The 911.gov FAQ extraction also failed; it remains an official entry link, not a verified directory record.

The EEAP planning and inquiry entries are scoped to **hurricane**, because the existing supporting candidates have that scope. No flood or unknown-hazard context is manufactured to make them match. PREPARE-only registration evidence is absent from the RESPOND inquiry entry. The Text 911 and general county contact listings propose hazard-independent applicability; that designation becomes usable only after listing approval.

## User-visible behavior before review

The emergency actions remain available. Directory results distinguish `matches`, `no_match`, `review_required`, and `unavailable`. At present there are zero verified directory listings. EEAP service and registration FAQ links are shown as official entry links with directory review pending; the app does not publish pending registration timing, contact values, eligibility, or pickup assertions as verified information. Cannot-call entry links point to the current MDSO and FCC sources. Clicking a link never confirms a connection or successful service outcome.

## Source acquisition and extraction

New captures were acquired through the existing allowlisted M3 transport. Initial MDSO extraction failed because its actual H1 is in the hero before main; county contact extraction failed on breadcrumbs before H1. A source-specific extractor requires the actual unique page H1, reads main only, and excludes navigation, scripts and footer content. It does not seed a title from model knowledge. Original bytes and HTTP retrieval timestamps are unchanged by re-extraction. Every published passage is re-extracted and revalidated against those bytes.

The EEAP introductory candidate is new and pending. Its original source bytes, existing candidates and source review state were not overwritten. MDSO text includes language, multimedia, location and message-length constraints for reviewer inspection; no app-operated SMS sender was added.

## Review procedure

Review the source first, then each standalone candidate, then each directory listing. Inspect all listed original bytes, complete context sections, exact displayed fields and conditional language. Source approval alone does not approve any listing. All phone values require their specific supporting candidate; internal matching tags are separate from exact official display text. Provider and service area must match authoritative source metadata. Directory limitations are explicit project caveats, not quoted official eligibility guarantees.

The project policy expires a listing at its review deadline, no more than 30 days after its approval. This is a project freshness policy, not an official accuracy guarantee. Pending deadlines are proposed dates; if a review occurs later, edit `review.review_due_at` in the draft before inspection. Future deadlines are allowed; actual review and retrieval times cannot be future. Recheck official links before each demonstration.

Use your actual reviewer identity. Do not approve all records by executing a loop. The commands below are manual templates; replace the placeholders only after completing the corresponding review. No approval command in this packet has been executed against production records.

```sh
python -m knowledge.review inspect --source-id SOURCE_ID
python -m knowledge.review approve --source-id SOURCE_ID --reviewer "ACTUAL REVIEWER" --expected-content-hash CONTENT_HASH --expected-context-hash CONTEXT_HASH --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review inspect --source-id SOURCE_ID --chunk-id CANDIDATE_ID
python -m knowledge.review approve --source-id SOURCE_ID --chunk-id CANDIDATE_ID --reviewer "ACTUAL REVIEWER" --expected-content-hash CONTENT_HASH --expected-context-hash CONTEXT_HASH --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved --standalone-passage-checked
python -m knowledge.resources inspect --resource-id RESOURCE_ID
python -m knowledge.resources approve --resource-id RESOURCE_ID --reviewer "ACTUAL REVIEWER" --expected-fingerprint FINGERPRINT
python -m knowledge.resources revoke --resource-id RESOURCE_ID --reviewer "ACTUAL REVIEWER" --reason "WHY IT IS REVOKED"
```

Inspection returns publication blockers and the current listing fingerprint. Fingerprints bind displayed fields, matching tags, purposes, county/phase/hazard scope, source content/context, candidate context/evidence mappings, review deadline and limitations. Any changed bound value invalidates prior approval. Source/candidate revocation, missing bytes, phase mismatch, expiration or storage failure removes the verified card on the next lookup. Inspection, approval, revocation and runtime validation each use one store lock; no nested admin locks.

## Source records

### `fcc-text-911`

- Official source: [Text to 911: What You Need to Know](https://www.fcc.gov/consumers/guides/what-you-need-know-about-text-911)
- State: `UNAVAILABLE`; failure: `HTTP_ERROR`.
- Retrieved at: `not acquired`.
- Actual review: `none`; reviewer: `none`.
- Original SHA-256: `none`.
- Source context hash: `e969d3466b0ee574de6bf63660158d0dde6e82cfc670d7ba6f0b2d241303f1e5`.
- Extracted sections: 0.

### `miami-dade-eeap`

- Official source: [Emergency & Evacuation Assistance Program (EEAP)](https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672)
- State: `REVIEW_REQUIRED`; failure: `none`.
- Retrieved at: `2026-11-03T03:05:30.655165+00:00`.
- Actual review: `none`; reviewer: `none`.
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`.
- Source context hash: `c80018b9167ce93db50b52333dc17bf1dcace183c578cfbbcc1855313832e805`.
- Extracted sections: 7.

### `miami-dade-text-911`

- Official source: [Text 911](https://www.mdso.com/text-911)
- State: `REVIEW_REQUIRED`; failure: `none`.
- Retrieved at: `2026-11-05T01:48:39.944738+00:00`.
- Actual review: `none`; reviewer: `none`.
- Original SHA-256: `ef11e602d4f208a62445f4ff20c4d0b000a193066fd5e41f6692d66fd7692be8`.
- Source context hash: `fdf523ef448741e27215b480e74caf440200e958c0c5a7daba02e872cac26fdb`.
- Extracted sections: 1.

### `miami-dade-weather-contacts`

- Official source: [Resources and Contact Information](https://www.miamidade.gov/initiative/weather-ready/contact.page)
- State: `REVIEW_REQUIRED`; failure: `none`.
- Retrieved at: `2026-11-05T01:48:40.329790+00:00`.
- Actual review: `none`; reviewer: `none`.
- Original SHA-256: `9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87`.
- Source context hash: `5f803bdc2530f071c5de346ddd367ef7b2c0a9471cb712bdf830c12d418557d1`.
- Extracted sections: 3.

## Directory drafts

### `fcc-text-911-guidance`

- Record: `data/official_sources/resources/fcc-text-911-guidance.json`.
- Current fingerprint: `772e7676aa18718849208a09a99b4f4c0753c834bbfe6b8041e8ff2e5d664481`.
- Current blocker: listing has no individually approved evidence.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['prepare', 'respond']; purposes ['communication_access']; hazards []; hazard-independent `True`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "fcc-text-911-guidance",
    "source_id": "fcc-text-911",
    "official_name": "Text-to-911",
    "service_category": "911",
    "service_area": "US",
    "official_contact": null,
    "contact_evidence_chunk_id": null,
    "official_url": "https://www.fcc.gov/consumers/guides/what-you-need-know-about-text-911",
    "prerequisites": [],
    "limitations": [
      "Current availability not verified.",
      "This record is not publishable without original acquisition and human review."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Federal Communications Commission",
  "description": "Text-to-911",
  "enrollment_timing": null,
  "matching_tags": [
    "communication_access",
    "cannot_call"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "prepare",
    "respond"
  ],
  "purposes": [
    "communication_access"
  ],
  "hazards": [],
  "hazard_independent": true,
  "supporting_candidate_ids": [],
  "field_evidence": {},
  "source_content_hash": null,
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "Direct official HTTP acquisition failed. No original hash or candidate evidence is available.",
    "Tavily read the official URL on 2026-11-04; this does not substitute for M3 original-byte provenance.",
    "Acquire the official original, prepare exact standalone candidates, then inspect and review."
  ]
}
```

### `miami-dade-311`

- Record: `data/official_sources/resources/miami-dade-311.json`.
- Current fingerprint: `d63ca3e83c9f8120874f56a02a0bb608e5adf8319b31c3a28648581882c5de88`.
- Current blocker: only human-reviewed sources and chunks may be published.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['prepare', 'respond', 'recover']; purposes ['planning', 'urgent_assistance']; hazards []; hazard-independent `True`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "miami-dade-311",
    "source_id": "miami-dade-weather-contacts",
    "official_name": "Miami-Dade County Contact Center",
    "service_category": "Contact Center",
    "service_area": "US-FL-MIAMI-DADE",
    "official_contact": "311",
    "contact_evidence_chunk_id": "735cc29cc0ce6e6a001968f2fcc18a8f04c7015c3bb91fbef59b4f3729391f90",
    "official_url": "https://www.miamidade.gov/initiative/weather-ready/contact.page",
    "prerequisites": [],
    "limitations": [
      "Current availability not verified.",
      "No connection, enrollment, dispatch, rescue, or transportation is confirmed.",
      "For immediate danger, call 911."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Miami-Dade County",
  "description": "Miami-Dade County Contact Center\n311 or 305-468-5900\nTTY/TDD: 711",
  "enrollment_timing": null,
  "matching_tags": [
    "local_assistance",
    "transportation",
    "evacuation_support"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "prepare",
    "respond",
    "recover"
  ],
  "purposes": [
    "planning",
    "urgent_assistance"
  ],
  "hazards": [],
  "hazard_independent": true,
  "supporting_candidate_ids": [
    "735cc29cc0ce6e6a001968f2fcc18a8f04c7015c3bb91fbef59b4f3729391f90"
  ],
  "field_evidence": {
    "official_name": [
      "735cc29cc0ce6e6a001968f2fcc18a8f04c7015c3bb91fbef59b4f3729391f90"
    ],
    "service_category": [
      "735cc29cc0ce6e6a001968f2fcc18a8f04c7015c3bb91fbef59b4f3729391f90"
    ],
    "description": [
      "735cc29cc0ce6e6a001968f2fcc18a8f04c7015c3bb91fbef59b4f3729391f90"
    ],
    "official_contact": [
      "735cc29cc0ce6e6a001968f2fcc18a8f04c7015c3bb91fbef59b4f3729391f90"
    ]
  },
  "source_content_hash": "9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87",
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "Source and passage reviews pending; service category is an exact source string.",
    "General directory scope does not establish a specific service outcome or eligibility."
  ]
}
```

### `miami-dade-eeap-inquiry`

- Record: `data/official_sources/resources/miami-dade-eeap-inquiry.json`.
- Current fingerprint: `302359929aadb1074cc44dc934b696d119b50ca8f9e834e375032a3cca7a3616`.
- Current blocker: only human-reviewed sources and chunks may be published.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['respond']; purposes ['urgent_assistance']; hazards ['hurricane']; hazard-independent `False`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "miami-dade-eeap-inquiry",
    "source_id": "miami-dade-eeap",
    "official_name": "Emergency & Evacuation Assistance Program (EEAP)",
    "service_category": "evacuation",
    "service_area": "US-FL-MIAMI-DADE",
    "official_contact": "311",
    "contact_evidence_chunk_id": "1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549",
    "official_url": "https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672",
    "prerequisites": [],
    "limitations": [
      "Current availability not verified.",
      "No connection, enrollment, dispatch, rescue, or transportation is confirmed.",
      "For immediate danger, call 911."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Miami-Dade County",
  "description": "When an emergency arises, pre-registered residents will have priority over those\n who have not registered for the program.\nResidents not currently enrolled in the EEAP, who need emergency and evacuation\n assistance, should call 311 to request assistance. Contacting the 311 Contact Center\n does not guarantee that a resident will receive assistance in the event of an emergency\n or are enrolled in the EEAP. Residents who have not pre-registered with the EEAP are\n encouraged to seek alternate transportation and sheltering arrangements with family\n and friends.",
  "enrollment_timing": null,
  "matching_tags": [
    "transportation",
    "evacuation_support",
    "accessible_transport"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "respond"
  ],
  "purposes": [
    "urgent_assistance"
  ],
  "hazards": [
    "hurricane"
  ],
  "hazard_independent": false,
  "supporting_candidate_ids": [
    "9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1",
    "1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549"
  ],
  "field_evidence": {
    "official_name": [
      "9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1"
    ],
    "service_category": [
      "9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1"
    ],
    "description": [
      "1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549"
    ],
    "official_contact": [
      "1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549"
    ]
  },
  "source_content_hash": "4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2",
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "311 is an evacuation-assistance inquiry, not a substitute for 911 during immediate danger.",
    "Source and standalone candidates require human review before directory approval."
  ]
}
```

### `miami-dade-eeap-planning`

- Record: `data/official_sources/resources/miami-dade-eeap-planning.json`.
- Current fingerprint: `e728d6928e4c92df3bc992b93ffcc37e5cff21bc1653a358d91feea06e7f311b`.
- Current blocker: only human-reviewed sources and chunks may be published.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['prepare']; purposes ['planning']; hazards ['hurricane']; hazard-independent `False`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "miami-dade-eeap-planning",
    "source_id": "miami-dade-eeap",
    "official_name": "Emergency & Evacuation Assistance Program (EEAP)",
    "service_category": "evacuation",
    "service_area": "US-FL-MIAMI-DADE",
    "official_contact": null,
    "contact_evidence_chunk_id": null,
    "official_url": "https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672",
    "prerequisites": [],
    "limitations": [
      "Current availability not verified.",
      "No connection, enrollment, dispatch, rescue, or transportation is confirmed.",
      "For immediate danger, call 911."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Miami-Dade County",
  "description": "The Emergency & Evacuation Assistance Program (EEAP) provides free evacuation\n assistance to eligible residents living in Miami-Dade County who need specialized\n transportation and/or sheltering or who would like to receive a wellness call after\n a disaster.\nPrior to an emergency, residents who may require medical monitoring, assistance\n with daily living or have life-saving medical equipment dependent on electricity should\n register for the EEAP to ensure help is available when needed. Pre-registered residents\n will receive priority during an emergency. It may also be utilized post-disaster to\n provide other assistance.\nThis program is for individuals who live alone or with families and may have access/functional\n needs. Residents living in long-term care facilities such as nursing homes, assisted\n living facilities or group homes are not eligible for this program as these facilities\n are required by law to develop an emergency plan and provide emergency assistance\n for their clients.\nWhen an emergency arises, pre-registered residents will have priority over those\n who have not registered for the program.",
  "enrollment_timing": "If more than one eligible person living in the same household requires assistance\n during evacuations, each person must complete and submit a separate application.\nIf you require a higher level of medical care, your primary care physician should\n complete and sign the application before submission.\nRegistration (online and paper application) for the EEAP closes before an evacuation\n order is pronounced. Do not wait until an evacuation order is issued to request to\n be added to the EEAP Registry.",
  "matching_tags": [
    "transportation",
    "evacuation_support",
    "accessible_transport"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "prepare"
  ],
  "purposes": [
    "planning"
  ],
  "hazards": [
    "hurricane"
  ],
  "hazard_independent": false,
  "supporting_candidate_ids": [
    "9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1",
    "7d79b4586449195f46f7ef80385dde00241df006f892674b0c39a627013e9349",
    "15627d254d98b3cdb0d95737ba7177031d4a0c9067cbc3de1a4b6c00db45e017",
    "f8a045039bb7ab2b702116a082a43dd1b1ae83e8aa3140c3c2f2424f8ce34a5c"
  ],
  "field_evidence": {
    "official_name": [
      "9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1"
    ],
    "service_category": [
      "9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1"
    ],
    "description": [
      "9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1"
    ],
    "enrollment_timing": [
      "f8a045039bb7ab2b702116a082a43dd1b1ae83e8aa3140c3c2f2424f8ce34a5c"
    ]
  },
  "source_content_hash": "4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2",
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "Existing source and all supporting passages remain pending; no human approval recorded.",
    "Reviewer must assess complete eligibility exclusions, caregiver conditions and advance enrollment timing."
  ]
}
```

### `miami-dade-emergency-management`

- Record: `data/official_sources/resources/miami-dade-emergency-management.json`.
- Current fingerprint: `1fe8c5c25e9a59f36b9715f32543ba2e5df68b3688a9d5ba097eecfd3b0647f6`.
- Current blocker: only human-reviewed sources and chunks may be published.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['prepare', 'respond', 'recover']; purposes ['planning', 'urgent_assistance']; hazards []; hazard-independent `True`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "miami-dade-emergency-management",
    "source_id": "miami-dade-weather-contacts",
    "official_name": "Department of Emergency Management",
    "service_category": "Emergency Management",
    "service_area": "US-FL-MIAMI-DADE",
    "official_contact": "305-468-5400",
    "contact_evidence_chunk_id": "e8c96ee87dcb6d4687e6f84fd0fe4221104ed9c5ffba25dca53bb37cbc2b6ef1",
    "official_url": "https://www.miamidade.gov/initiative/weather-ready/contact.page",
    "prerequisites": [],
    "limitations": [
      "Current availability not verified.",
      "No connection, enrollment, dispatch, rescue, or transportation is confirmed.",
      "For immediate danger, call 911."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Miami-Dade County",
  "description": "Department of Emergency Management\n305-468-5400",
  "enrollment_timing": null,
  "matching_tags": [
    "local_assistance",
    "evacuation_support"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "prepare",
    "respond",
    "recover"
  ],
  "purposes": [
    "planning",
    "urgent_assistance"
  ],
  "hazards": [],
  "hazard_independent": true,
  "supporting_candidate_ids": [
    "e8c96ee87dcb6d4687e6f84fd0fe4221104ed9c5ffba25dca53bb37cbc2b6ef1"
  ],
  "field_evidence": {
    "official_name": [
      "e8c96ee87dcb6d4687e6f84fd0fe4221104ed9c5ffba25dca53bb37cbc2b6ef1"
    ],
    "service_category": [
      "e8c96ee87dcb6d4687e6f84fd0fe4221104ed9c5ffba25dca53bb37cbc2b6ef1"
    ],
    "description": [
      "e8c96ee87dcb6d4687e6f84fd0fe4221104ed9c5ffba25dca53bb37cbc2b6ef1"
    ],
    "official_contact": [
      "e8c96ee87dcb6d4687e6f84fd0fe4221104ed9c5ffba25dca53bb37cbc2b6ef1"
    ]
  },
  "source_content_hash": "9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87",
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "Source and passage reviews pending; service category is an exact source string.",
    "General directory scope does not establish a specific service outcome or eligibility."
  ]
}
```

### `miami-dade-sheriff-nonemergency`

- Record: `data/official_sources/resources/miami-dade-sheriff-nonemergency.json`.
- Current fingerprint: `871ee96776a08403fbfef4bc1a3bbecfa5c849bd8b6af26a32586a4a2ee3cbae`.
- Current blocker: only human-reviewed sources and chunks may be published.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['prepare', 'respond', 'recover']; purposes ['planning', 'urgent_assistance']; hazards []; hazard-independent `True`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "miami-dade-sheriff-nonemergency",
    "source_id": "miami-dade-weather-contacts",
    "official_name": "Miami-Dade Sheriff's Office",
    "service_category": "Non-Emergencies",
    "service_area": "US-FL-MIAMI-DADE",
    "official_contact": null,
    "contact_evidence_chunk_id": null,
    "official_url": "https://www.miamidade.gov/initiative/weather-ready/contact.page",
    "prerequisites": [],
    "limitations": [
      "Current availability not verified.",
      "No connection, enrollment, dispatch, rescue, or transportation is confirmed.",
      "For immediate danger, call 911."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Miami-Dade County",
  "description": "Miami-Dade Sheriff's Office\nEmergencies: 911\nNon-Emergencies: 305-Sheriff (743-7433)",
  "enrollment_timing": null,
  "matching_tags": [
    "nonemergency_assistance",
    "local_assistance"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "prepare",
    "respond",
    "recover"
  ],
  "purposes": [
    "planning",
    "urgent_assistance"
  ],
  "hazards": [],
  "hazard_independent": true,
  "supporting_candidate_ids": [
    "470b6feed8ee8310acbb8f3d287bb66c52f7fb078f30eeff1e0fe27cca5ebfe6"
  ],
  "field_evidence": {
    "official_name": [
      "470b6feed8ee8310acbb8f3d287bb66c52f7fb078f30eeff1e0fe27cca5ebfe6"
    ],
    "service_category": [
      "470b6feed8ee8310acbb8f3d287bb66c52f7fb078f30eeff1e0fe27cca5ebfe6"
    ],
    "description": [
      "470b6feed8ee8310acbb8f3d287bb66c52f7fb078f30eeff1e0fe27cca5ebfe6"
    ]
  },
  "source_content_hash": "9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87",
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "Source and passage reviews pending; service category is an exact source string.",
    "General directory scope does not establish a specific service outcome or eligibility."
  ]
}
```

### `miami-dade-text-911`

- Record: `data/official_sources/resources/miami-dade-text-911.json`.
- Current fingerprint: `2e3df291b0c5c74f3b94872b814fe8d0bc236c530b8376dda31d1f97dcbb095a`.
- Current blocker: only human-reviewed sources and chunks may be published.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['prepare', 'respond']; purposes ['communication_access']; hazards []; hazard-independent `True`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "miami-dade-text-911",
    "source_id": "miami-dade-text-911",
    "official_name": "Text-to-911",
    "service_category": "emergency services",
    "service_area": "US-FL-MIAMI-DADE",
    "official_contact": null,
    "contact_evidence_chunk_id": null,
    "official_url": "https://www.mdso.com/text-911",
    "prerequisites": [
      "Communication over text message is only available in English at this time",
      "Photo and video sharing over text is not available. Some 911 Centers may message you separately to share multimedia",
      "Wireless phone carriers have set a 160-character count limitation for texts"
    ],
    "limitations": [
      "Current availability not verified.",
      "No connection, enrollment, dispatch, rescue, or transportation is confirmed.",
      "For immediate danger, call 911."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Miami-Dade Sheriff's Office",
  "description": "This new service allows residents to send a text message to 911 in situations where calling may not be possible or safe.",
  "enrollment_timing": null,
  "matching_tags": [
    "communication_access",
    "cannot_call",
    "hearing_speech_access"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "prepare",
    "respond"
  ],
  "purposes": [
    "communication_access"
  ],
  "hazards": [],
  "hazard_independent": true,
  "supporting_candidate_ids": [
    "c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80"
  ],
  "field_evidence": {
    "official_name": [
      "c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80"
    ],
    "service_category": [
      "c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80"
    ],
    "description": [
      "c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80"
    ],
    "prerequisites.0": [
      "c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80"
    ],
    "prerequisites.1": [
      "c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80"
    ],
    "prerequisites.2": [
      "c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80"
    ]
  },
  "source_content_hash": "ef11e602d4f208a62445f4ff20c4d0b000a193066fd5e41f6692d66fd7692be8",
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "Hazard-independent applicability is a proposal requiring explicit directory approval.",
    "The original H1 is outside main; extraction uses that actual H1 and main text only."
  ]
}
```

### `miami-dade-water-sewer`

- Record: `data/official_sources/resources/miami-dade-water-sewer.json`.
- Current fingerprint: `46f597c587c3b8d2ad536f5a4f69086bb97622c895a34a692ad4ccd0b1e90036`.
- Current blocker: only human-reviewed sources and chunks may be published.
- Proposed applicability: counties ['US-FL-MIAMI-DADE']; phases ['prepare', 'respond', 'recover']; purposes ['planning', 'urgent_assistance']; hazards []; hazard-independent `True`.
- Proposed deadline: `2026-12-04T01:53:38.339858+00:00`; no actual listing review exists.

```json
{
  "resource": {
    "resource_id": "miami-dade-water-sewer",
    "source_id": "miami-dade-weather-contacts",
    "official_name": "Miami-Dade Water and Sewer Department",
    "service_category": "Emergency Communications Center",
    "service_area": "US-FL-MIAMI-DADE",
    "official_contact": "305-274-9272",
    "contact_evidence_chunk_id": "0f3b908381e3ffc771f6687a06c7a755ae7fa670f723076b990d2238b5b40c0d",
    "official_url": "https://www.miamidade.gov/initiative/weather-ready/contact.page",
    "prerequisites": [],
    "limitations": [
      "Current availability not verified.",
      "No connection, enrollment, dispatch, rescue, or transportation is confirmed.",
      "For immediate danger, call 911."
    ],
    "availability_status": "UNKNOWN"
  },
  "provider": "Miami-Dade County",
  "description": "Miami-Dade Water and Sewer Department\nEmergency Communications Center\n305-274-9272",
  "enrollment_timing": null,
  "matching_tags": [
    "utility_hazard",
    "water_sewer"
  ],
  "counties": [
    "US-FL-MIAMI-DADE"
  ],
  "phases": [
    "prepare",
    "respond",
    "recover"
  ],
  "purposes": [
    "planning",
    "urgent_assistance"
  ],
  "hazards": [],
  "hazard_independent": true,
  "supporting_candidate_ids": [
    "0f3b908381e3ffc771f6687a06c7a755ae7fa670f723076b990d2238b5b40c0d"
  ],
  "field_evidence": {
    "official_name": [
      "0f3b908381e3ffc771f6687a06c7a755ae7fa670f723076b990d2238b5b40c0d"
    ],
    "service_category": [
      "0f3b908381e3ffc771f6687a06c7a755ae7fa670f723076b990d2238b5b40c0d"
    ],
    "description": [
      "0f3b908381e3ffc771f6687a06c7a755ae7fa670f723076b990d2238b5b40c0d"
    ],
    "official_contact": [
      "0f3b908381e3ffc771f6687a06c7a755ae7fa670f723076b990d2238b5b40c0d"
    ]
  },
  "source_content_hash": "9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87",
  "review": {
    "status": "PENDING",
    "reviewer": null,
    "reviewed_at": null,
    "review_due_at": "2026-12-04T01:53:38.339858Z",
    "fingerprint": null,
    "revoked_at": null,
    "revoked_by": null,
    "revocation_reason": null
  },
  "preparation_notes": [
    "Source and passage reviews pending; service category is an exact source string.",
    "General directory scope does not establish a specific service outcome or eligibility."
  ]
}
```

## Exact candidate passages for review

These quotations remain unpublished. Their complete source context is available in each candidate JSON under `surrounding_context`, and through `python -m knowledge.review inspect`. Context is administrative only; it is not added to a verified listing or sent to a model.

### `735cc29cc0ce6e6a001968f2fcc18a8f04c7015c3bb91fbef59b4f3729391f90`

- Source: `miami-dade-weather-contacts`; parent section: `8f258167af83a52d17db52370b853ad8611f618c510f4e797e73c4c809925bfc`.
- State: `PENDING`; candidate context hash: `7626023798adfe8044331c6bf4521424c1add2ca6f58e7284b36c5037d643471`.
- Original SHA-256: `9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87`; character span [0, 65).
- Section: Resources and Contact Information > Miami-Dade County
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond', 'recover']; hazards ['flood', 'hurricane'].

```text
Miami-Dade County Contact Center
311 or 305-468-5900
TTY/TDD: 711
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- This is a static county directory entry, not current service availability.
- Use 911 for immediate danger. This entry does not establish emergency dispatch.

### `9bcb64480708d821a9b0b0d8373af13064420537a9fc99c3068ead8dc31852d1`

- Source: `miami-dade-eeap`; parent section: `1f1086b2b14e0d28ba209f1d6a64dc1940a30a82978d1ccc0abd52a68504e8ca`.
- State: `PENDING`; candidate context hash: `89c31995bbd2cb27681fa6f6fe1d530c9070c4406d9c8735a7a4bbcf39dcddf6`.
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`; character span [0, 1123).
- Section: Emergency & Evacuation Assistance Program (EEAP) > longDescription
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond']; hazards ['flood', 'hurricane'].

```text
The Emergency & Evacuation Assistance Program (EEAP) provides free evacuation
 assistance to eligible residents living in Miami-Dade County who need specialized
 transportation and/or sheltering or who would like to receive a wellness call after
 a disaster.
Prior to an emergency, residents who may require medical monitoring, assistance
 with daily living or have life-saving medical equipment dependent on electricity should
 register for the EEAP to ensure help is available when needed. Pre-registered residents
 will receive priority during an emergency. It may also be utilized post-disaster to
 provide other assistance.
This program is for individuals who live alone or with families and may have access/functional
 needs. Residents living in long-term care facilities such as nursing homes, assisted
 living facilities or group homes are not eligible for this program as these facilities
 are required by law to develop an emergency plan and provide emergency assistance
 for their clients.
When an emergency arises, pre-registered residents will have priority over those
 who have not registered for the program.
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- No current eligibility, enrollment, placement, pickup or transport availability is established.
- Read eligibility exclusions and registration timing with the separate approved supporting passages.

### `1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549`

- Source: `miami-dade-eeap`; parent section: `6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b`.
- State: `PENDING`; candidate context hash: `dbd14b0ab97fb981138c08c154cac84abcdcb66d3abc09d975ca8b70fe39639f`.
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`; character span [0, 562).
- Section: Emergency & Evacuation Assistance Program (EEAP) > Can I get assistance if I am not enrolled in the event of an emergency?
- Scope: `US-FL-MIAMI-DADE`; phases ['respond']; hazards ['hurricane'].

```text
When an emergency arises, pre-registered residents will have priority over those
 who have not registered for the program.
Residents not currently enrolled in the EEAP, who need emergency and evacuation
 assistance, should call 311 to request assistance. Contacting the 311 Contact Center
 does not guarantee that a resident will receive assistance in the event of an emergency
 or are enrolled in the EEAP. Residents who have not pre-registered with the EEAP are
 encouraged to seek alternate transportation and sheltering arrangements with family
 and friends.
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.

### `7d79b4586449195f46f7ef80385dde00241df006f892674b0c39a627013e9349`

- Source: `miami-dade-eeap`; parent section: `16920ae167aca6c18f25b02f1f352277ca8dfeaee15c98c1bfcca176bad5683b`.
- State: `PENDING`; candidate context hash: `d4340ae59aa91a1ada2f978447ad1298d2a6c80032a777d00534537e8606eba7`.
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`; character span [0, 793).
- Section: Emergency & Evacuation Assistance Program (EEAP) > What does the EEAP offer and when is it used?
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond']; hazards ['hurricane'].

```text
The program offers:
Specialized transportation
Safe shelter
Medical monitoring
Wellness checks
A caregiver or companion is required to accompany the evacuee throughout the emergency
 period to ensure the evacuee’s needs are met in a timely manner.
The EEAP may be used for emergencies that occur in Miami-Dade County, such
 as:
Hurricanes or tornadoes
Chemical or Hazardous material releases (e.g., industrial accident or act of terrorism)
Wildfires
Prolonged widespread power outages
Radiological  releases (e.g., from a nuclear power plant incident or act
 of terrorism)
Emergency evacuation centers are intended as a refuge of last resort for those
 who do not have an alternate safe location for evacuation. They do not offer the same
 level of care or equipment as health care facilities.
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.
- Retain the caregiver requirement and refuge-of-last-resort / health-care-level limitations.

### `15627d254d98b3cdb0d95737ba7177031d4a0c9067cbc3de1a4b6c00db45e017`

- Source: `miami-dade-eeap`; parent section: `9c7e52a128185b463037aabbc651ff167458f05694ff296cf0e8f8093e5d4bbb`.
- State: `PENDING`; candidate context hash: `86d8e13a09aabeff88157620698c1419d24bd07f392f0512bb3f098f21f2d15c`.
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`; character span [0, 760).
- Section: Emergency & Evacuation Assistance Program (EEAP) > Am I eligible for the EEAP?
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond']; hazards ['hurricane'].

```text
You are eligible for this program if any of the following conditions
 apply:
You are unable to evacuate on your own due to a specialized transportation need.
You are homebound and unable to walk to a bus pickup point and do not have anyone
 who can provide transportation.
You have medical needs that prevent you from evacuating on your own.
You are bedbound.
You are on life-sustaining medical equipment that requires electricity.
You require assistance with daily living activities.
Residents living in residential health care facilities such as nursing
 homes, assisted living facilities or group homes do not qualify for this program as
 these facilities are required by law to develop an emergency plan and provide emergency
 assistance for their clients.
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.
- Criteria are quoted for human review, not an eligibility determination; retain the residential-facility exclusion.

### `f8a045039bb7ab2b702116a082a43dd1b1ae83e8aa3140c3c2f2424f8ce34a5c`

- Source: `miami-dade-eeap`; parent section: `029d9ddadbf85022bb5c9a90f1c6bb1561ac15deb26335624a9b401aa80c7bbb`.
- State: `PENDING`; candidate context hash: `781db7d5d8cfb7884176ac8569512826558111393717f1b00e22d3be22923263`.
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`; character span [520, 1020).
- Section: Emergency & Evacuation Assistance Program (EEAP) > How do I register for the EEAP?
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare']; hazards ['hurricane'].

```text
If more than one eligible person living in the same household requires assistance
 during evacuations, each person must complete and submit a separate application.
If you require a higher level of medical care, your primary care physician should
 complete and sign the application before submission.
Registration (online and paper application) for the EEAP closes before an evacuation
 order is pronounced. Do not wait until an evacuation order is issued to request to
 be added to the EEAP Registry.
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.
- Preserve separate-application, physician-signature and Do not wait conditions; this is not a current enrollment window or evacuation notice.

### `e8c96ee87dcb6d4687e6f84fd0fe4221104ed9c5ffba25dca53bb37cbc2b6ef1`

- Source: `miami-dade-weather-contacts`; parent section: `8f258167af83a52d17db52370b853ad8611f618c510f4e797e73c4c809925bfc`.
- State: `PENDING`; candidate context hash: `38482b89474ace23db50775cd12d18d16a929ecc552164d6495df9ecb7a5e98d`.
- Original SHA-256: `9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87`; character span [115, 162).
- Section: Resources and Contact Information > Miami-Dade County
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond', 'recover']; hazards ['flood', 'hurricane'].

```text
Department of Emergency Management
305-468-5400
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- This is a static county directory entry, not current service availability.
- Use 911 for immediate danger. This entry does not establish emergency dispatch.

### `470b6feed8ee8310acbb8f3d287bb66c52f7fb078f30eeff1e0fe27cca5ebfe6`

- Source: `miami-dade-weather-contacts`; parent section: `8f258167af83a52d17db52370b853ad8611f618c510f4e797e73c4c809925bfc`.
- State: `PENDING`; candidate context hash: `daf23ce86e006c013cd8dad72de9b45b06c86d344f08a51994d47295adefa076`.
- Original SHA-256: `9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87`; character span [369, 453).
- Section: Resources and Contact Information > Miami-Dade County
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond', 'recover']; hazards ['flood', 'hurricane'].

```text
Miami-Dade Sheriff's Office
Emergencies: 911
Non-Emergencies: 305-Sheriff (743-7433)
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- This is a static county directory entry, not current service availability.
- Use 911 for immediate danger. This entry does not establish emergency dispatch.

### `c9052df8db4490a789062c2a2525f17d41e9680c6c36f7d689a39253d28afa80`

- Source: `miami-dade-text-911`; parent section: `38a4dc13841d331f9bcb6bb9984e619862820001efe0fc39ed5d11a906c5cd11`.
- State: `PENDING`; candidate context hash: `5a03c978ca3c3821587f41d6a1361917ae8e23426a3d6c366b12d694116e8fa6`.
- Original SHA-256: `ef11e602d4f208a62445f4ff20c4d0b000a193066fd5e41f6692d66fd7692be8`; character span [0, 1233).
- Section: Text 911
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond']; hazards ['flood', 'hurricane'].

```text
This new service allows residents to send a text message to 911 in situations where calling may not be possible or safe. This initiative is part of our commitment to leveraging technology to enhance public safety and ensure that all members of our community have access to emergency assistance when they need it most.
Whether you're deaf, hard of hearing, have a speech disability, or find yourself in a scenario where speaking could put you in danger, Text-to-911 ensures you can still reach emergency services.
 Please remember, voice calls to 911 are still the fastest and most efficient way to reach emergency services. Text-to-911 should only be used in emergency situations when calling is not an option.
General Public
Deaf, hard of hearing, or individuals with speech disabilities
Domestic violence advocates
Individuals unable to speak due to medical or other conditions
Calling 911 provides enhanced location information that may be limited when texting 911
Communication over text message is only available in English at this time
Photo and video sharing over text is not available. Some 911 Centers may message you separately to share multimedia
Wireless phone carriers have set a 160-character count limitation for texts
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- Local applicability is Miami-Dade; no support is inferred for another county.
- Calling is preferred when possible. Connectivity, device support and message delivery are not verified.
- No app-operated SMS sender, relay connection, or dispatch is provided.

### `0f3b908381e3ffc771f6687a06c7a755ae7fa670f723076b990d2238b5b40c0d`

- Source: `miami-dade-weather-contacts`; parent section: `8f258167af83a52d17db52370b853ad8611f618c510f4e797e73c4c809925bfc`.
- State: `PENDING`; candidate context hash: `fd56812f4c000e3e1f50d792a186ac6af9ffa0dac0aa6e10e0a45b525b0cfc94`.
- Original SHA-256: `9f300a0e02258db8dfd6e23ac56ff467af943958171f24384f18ee3ed4186f87`; character span [252, 334).
- Section: Resources and Contact Information > Miami-Dade County
- Scope: `US-FL-MIAMI-DADE`; phases ['prepare', 'respond', 'recover']; hazards ['flood', 'hurricane'].

```text
Miami-Dade Water and Sewer Department
Emergency Communications Center
305-274-9272
```

Candidate caveats:
- PENDING human review; not operational guidance or household safety verification.
- This is a static county directory entry, not current service availability.
- Use 911 for immediate danger. This entry does not establish emergency dispatch.

## Validation evidence

The directory tests use isolated stores and identities explicitly labeled TEST ONLY. They cover approved matching, pending/revoked/expired evidence, source/candidate mutation, field-specific contacts, exact phase/county/purpose scope, unknown hazard handling, deadline integrity, authoritative timestamps, storage failure, and a non-reentrant store lock. A copied packet is approved only in a temporary test store to prove all seven captured listings are structurally reviewable. Those temporary approvals are not copied to production and make no claim of editorial or operational reliability.

Run: `python -m pytest tests/test_emergency_resources.py tests/test_knowledge_review_gate.py tests/test_knowledge_review_candidates.py tests/test_knowledge_retrieval.py -q`. The coordinated project verification report records the actual final totals.
