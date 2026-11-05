# Final recovery-source review preparation

No formal approval has occurred. Conversation decisions are provisional only. This document supersedes all approval examples in M3_RECOVERY_COVERAGE_REVIEW.md.

## Decision summary
- NFIP parent: HOLD. Integrity passed, but the full-source content/applicability attestation is unresolved. No NFIP approval commands are provided. Candidates 1 and 2 remain conditionally acceptable excerpts, blocked by their parent; Candidate 3 stays HOLD/PENDING.
- USAGov parent: ready for the human source-level inspection and decision below for static information. This is an audit recommendation, not an approval record. Candidate 5 alone is conditionally ready for human approval; Candidates 4 and 6 stay HOLD/PENDING.
- Receipts replacement: new PENDING candidate, requiring its own review and the NFIP parent gate. No approval command provided.

## NFIP full-capture findings
- Official URL: https://www.floodsmart.gov/recover/document-damage
- Retrieved UTC: 2026-11-04T18:37:55.105232+00:00; HTTP 200; 84025 bytes; 11 extracted sections.
- SHA-256: `fc9693d31c3fbbb1353a9365ff328e770de53e91800978b1dbfdb3145a0f2f9f`; bundle context: `7222f918fd52bb81651adb88da15099c4ce6d1210e881d063f2e9fdc07fe0f62`.
- Preserved bytes, strict UTF-8 decoding, fresh extraction, spans and candidate context hashes pass. The previous failed TLS attempt remains separate history; no capture or review history was rewritten.
- Entire visible capture inspected: navigation/marketing, safe-return introduction, photographs, samples/receipts, repair contractors, mold paragraph, all five FAQs, related pages, and footer. Embedded scripts were read as inert source, not executed. Linked documents/images were not acquired or verified. No publication/update date could be established in this NFIP HTML; retrieval time is not a source publication date.

### Safety mismatch (not a claim that all electrical advice is logically contradictory)
```text
NFIP: Turning off electricity and gas before going inside to avoid fire or injury.
CDC approved: NEVER turn power on or off yourself or use an electric tool or appliance while standing in water.
CDC approved: Have an electrician check the house's electrical system before turning the power on again.
CDC approved: If your home has damage, do not reenter until it has been examined by a building inspector for safety.
```
NFIP also says a qualified expert should inspect before power is turned back on, which aligns with part of CDC advice. Its broad shutdown instruction does not specify dry access/qualified assistance and could be unsafe if generalized to a flooded home. Its introductory safe-return condition does not supply the missing standing-water restriction. No advice to operate a switch or valve is selected.
The blanket mold exclusion paragraph is followed by conditional mold-coverage exception language. This is not sufficient to decide anyone's insurance coverage. Neither section is selected. Exact coverage and applicability are not independently settled by this audit.

### Why parent approval is on HOLD despite safe excerpt separation
Technically, parent approval alone does NOT publish all sections: retrieval, M1 adaptation, M5 export and Qwen public_payload use individually approved candidate passages and permitted caveats only. Pending candidates and raw surrounding_context are excluded; direct parent-section IDs cannot export. Resource validation also requires approved candidate support. SourceStore/CLI full context remains administrative only.
However, review_source marks every extracted source section REVIEWED with one source-level content/applicability/caveat decision. The model has no recorded per-section exclusion or qualified parent-scope approval. I cannot justify that blanket attestation for the unresolved electrical/coverage material. Do not use candidate gating as permission to assert an inspection check that the human cannot truthfully complete.
To release NFIP, the human must resolve the full-source interpretation/applicability issue and personally justify the existing checks, or request a separately scoped review-contract change/alternative source. No architecture or policy change is implemented here.

## USAGov full-capture findings
- Official URL: https://www.usa.gov/disaster-housing-shelter
- Retrieved UTC: 2026-11-04T18:37:15.431013+00:00; HTTP 200; 40906 bytes; 8 extracted sections.
- SHA-256: `44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2`; bundle context: `99ff6d7727a153ba8f66f2f44db83a7d38cdca31178d36e1339e9eb402235f03`.
- Preserved HTML explicitly says LAST UPDATED November 3, 2026. Earlier search-index dates are not the captured page date. Hash, UTF-8, fresh extraction and candidate trace checks pass. No re-download occurred.
- Entire visible capture inspected: government banner, navigation/footer, housing introduction, declared-disaster condition, FEMA shelter-search pathways, transitional hotel section, Red Cross referral, 211 description, and LIHEAP office-specific conditions. Outbound destinations were inspected in the capture, not tested for live availability or program activation.
- Captured hotel paragraph first conditions the discussion on registering and learning whether one qualifies; later sentences describe TSA hotel payment and contacting participating hotels for reservations. Candidate 5 contains ONLY the conditional first sentence. Its signed-for-review caveats expressly exclude qualification, approved hotel payment and room reservation.
- Candidate 5 exact passage:
```text
After you register for disaster assistance with FEMA, you will find out if you qualify for transitional housing.
```
This can support only general information about an assessment after registration. It supplies no active Miami-Dade program, declaration, FEMA approval, room, eligibility decision or assurance that registration produces assistance. Candidate scope is US / flood / recover. Source scope US / flood,hurricane / recover is generic disaster information, not a claim of active disaster assistance.
No unresolved provenance or standalone-excerpt discrepancy was found for USAGov. Human must still assess substantive accuracy, scope and all conditions personally before checking the flags. The stronger neighboring hotel text and held Candidates 4/6 stay excluded from publication.

## Candidate 3 replacement (new, not a mutation)
- New candidate ID: `b7cd7908f13feabf79bc5bb21fb9446b3b5cb7d7b013973102e038c12cc34f13`
- Original source hash: `fc9693d31c3fbbb1353a9365ff328e770de53e91800978b1dbfdb3145a0f2f9f`
- Parent section ID: `b27b8679965b7426166595fb344c35e2daf467a81c659aa7586bb1e859ac0457`
- Exact span: [152, 253); length 101 characters.
- Candidate/context hash: `3008216ba2b29073d1822589533851054069210febbdd1f0e8a74ec353eab471`
- Original Candidate 3 remains PENDING and byte-for-byte unchanged; its context hash is `3d461fbeedd74f638655f7dc279dba62db4b4997bbac8c0616830bacd1c0c525`.
- Source-exact contiguous passage (no edits, no inserted heading):
```text
Receipts for repairs and replacement items.
Warranty or manufacturer details for replaced appliances.
```
**Editorial review limitations:**
- PENDING human review; not operational guidance or household safety verification.
- Receipts and warranty/manufacturer records only; material samples are excluded from this passage.
- The source conditions documentation on safe return. This is not permission to enter, handle hazards or retain contaminated items.
- NFIP documentation information only; no insurance coverage, reimbursement or claim outcome is established.
**Complete administrative context remains in the new candidate record:**
### How to document flood damage > FAQs about documenting flood damage and mold / b27b8679965b7426166595fb344c35e2daf467a81c659aa7586bb1e859ac0457
```text
Keeping samples and receipts helps prove flood damage and supports your claim. Save things like:
Small pieces of damaged carpet, drywall or insulation.
Receipts for repairs and replacement items.
Warranty or manufacturer details for replaced appliances.
```
### How to document flood damage / 2aab798d4f6894db8be6dfadb5eba6475664833fcf562c5b428d384a9400d62d
```text
Recovery begins once floodwaters recede. If you have flood insurance, you don’t have to go through it alone.
When it’s safe to return home, act quickly to document flood damage. Early action can support your flood insurance claim and gets you on the road to recovery.
```
### How to document flood damage > FAQs about documenting flood damage and mold / 5004880fe006404b5bc5298e8d9256da9d6452a587bf29b092ae8cafe345b1ce
```text
Photos and videos are key for your flood insurance claim. Be sure to capture:
Water levels on walls, furniture and appliances.
Structural damage to floors, ceilings and foundations.
Serial numbers on damaged electronics and appliances.
After taking photos, immediately throw away anything that could be a health risk, like spoiled food or moldy clothing, cushions and pillows.
```

## Human checklist and exact permitted commands
1. Work from repository root with the existing virtual environment. Enter your OWN reviewer identity at the placeholder; no identity or signoff has been invented.
2. Inspect the USAGov preserved original and every extracted section. Check the date, official origin, source/context hashes, all conditions, geography and hazard/phase scope. The commands do not replace reading.
3. Inspect Candidate 5 separately, including full administrative context and every safety caveat. Check that its standalone published passage cannot imply payment, a room or eligibility.
4. Approve only if each flag can truthfully be attested. Otherwise STOP and leave PENDING. Source approval is optional until this human decision.
5. Source-first sequence below is safe because pending candidates cannot publish; the second approval makes Candidate 5 eligible for retrieval. No additional automatic publish step exists. Leave every other new candidate PENDING.
6. Reinspect after any content/context change. Do not modify hashes or substitute freshly downloaded bytes.

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id usagov-disaster-housing
python -m knowledge.review inspect --root data/official_sources --source-id usagov-disaster-housing --chunk-id 8630330fbd12aabc3c31bff38cd811d234bc3e214e05021a322d6f082d9f2b48
python -m knowledge.review approve --root data/official_sources --source-id usagov-disaster-housing --reviewer "<YOUR_OWN_REVIEWER_IDENTITY>" --expected-content-hash 44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2 --expected-context-hash 99ff6d7727a153ba8f66f2f44db83a7d38cdca31178d36e1339e9eb402235f03 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review approve --root data/official_sources --source-id usagov-disaster-housing --chunk-id 8630330fbd12aabc3c31bff38cd811d234bc3e214e05021a322d6f082d9f2b48 --reviewer "<YOUR_OWN_REVIEWER_IDENTITY>" --expected-content-hash 44e8213b5d20875cc9b4c8773150f60f38f9af9efa8683853f1a2adcc9d1c6f2 --expected-context-hash 3034b531f7dcb800f4473cef6de4867826f8c888c384cb3a5c7665a33d219cc4 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved --standalone-passage-checked
```

No commands for NFIP parent/Candidates 1/2 are supplied because the parent is on HOLD. No approval commands for held Candidates 3/4/6 or the replacement are supplied. None of the displayed commands was executed.

## Retrieval verification after the human decision
Use the existing FoundationKnowledgeService with flood / recover / US-FL-MIAMI-DADE and requested_evidence_count=1; a bounded topic such as "transitional housing" should be tested for Candidate 5 with its exact citation. Then try all held IDs via export and confirm rejection. The larger default count can yield partial/insufficient evidence.
The original question "Where can I learn about temporary housing assistance after flooding?" triggers the existing can ... assistance operational guard even after approval. That guard/ranking is unchanged. Current pending evidence returns zero passages from these sources.
Do not claim household safety, coverage, live availability, eligibility, an active local program or automatic submissions. No M1/M5 workflow, model client, government capture or legitimate human approval record was changed.
