# M3-2A human review packet

**All candidates: PENDING. No approval or rejection command has been run.**
Source quotations are acquired historical text, not current service availability or safety verification.
Editorial safety caveats below are review annotations, not quotations or official orders.
Packet prepared at: 2026-11-03T12:53:42.740423+00:00

## Extraction repair and provenance

The preserved EEAP response contains program text in main/div#service-data/service: an escaped longDescription and six related-faq name/answer pairs. The old generic extractor failed on metadata before a usable heading. A source-scoped static parser decodes only those fields without executing scripts.
Actual section counts: CDC flood reentry 13; CDC floodwater 17; Miami-Dade EEAP 7. The original HTTP timestamps, URLs, byte counts and SHA-256 values are unchanged. Re-extraction is recorded separately in extraction metadata/history; no new download occurred.
Obfuscated contact markup remains source context only. No hidden email address is reconstructed and no contact availability is verified. All original acquisition history is retained.

## Review procedure

Read each exact passage and every linked context section against the preserved original hash. Check geography, hazard/phase scope and ALL conditional/negative language.
The proposed chunk is verbatim; no generated paraphrase fills coverage gaps. Source authority and accuracy still require human judgment.
Use the existing knowledge.review CLI commands shown below. Replace the reviewer/reason placeholders yourself. Do not approve by copying commands without inspection.
Candidate approval records only that candidate decision. It does not mark the source REVIEWED, publish guidance, or enable retrieval. Existing export still requires source-level review.
If hashes/context change, inspect again and prepare a new packet. Rejected candidates remain non-publishable. No live acquisition is needed for these commands.

## Coverage gaps

- No substantive acquired instruction supporting safe damage documentation was selected; a Damage Reporting link label is not guidance.
- No live resource availability, personal eligibility or county evacuation order is evidenced.
- PROTECT phase tags are proposals grounded in Before / Recognize Flood Risk text, not approved source scope.

## Candidate 1: 3f99a870c42b339f7b2816bb8aec2734480954062abe56ef9073246d7c6c30ae

**Review status: PENDING**
- Source: `cdc-flood-reentry` — https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html
- Original SHA-256: `61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85`
- Parent section: `00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558`; character span [54, 375).
- Intended hazards: hurricane; phases: prepare; geography: `US`.
- Source section heading: Safety Guidelines: Reentering Your Flooded Home > When you first reenter your home > Take these steps when you first reenter your flooded home.

**Original passage from acquired content:**

```text
Before
Cover windows with storm shutters or plywood.
Tune in for local information.
Know how to turn off your gas, electricity, and water in case you need to evacuate.
Secure outdoor items by moving them to the garage.
Make an emergency kit.
Designate a shelter area if you can't evacuate. Rooms without windows are best.
```

**Surrounding context:** [Context 00c7f0e0a7de](#context-00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558), [Context 40d20e9ce3a5](#context-40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Before
Cover windows with storm shutters or plywood.
Tune in for local information.
Know how to turn off your gas, electricity, and water in case you need to evacuate.
Secure outdoor items by moving them to the garage.
Make an emergency kit.
Designate a shelter area if you can't evacuate. Rooms without windows are best.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- The source labels this infographic Before; PREPARE is a proposed phase beyond the current source-level RECOVER tag. Human scope review is required.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-flood-reentry --chunk-id 3f99a870c42b339f7b2816bb8aec2734480954062abe56ef9073246d7c6c30ae
python -m knowledge.review approve --root data/official_sources --source-id cdc-flood-reentry --chunk-id 3f99a870c42b339f7b2816bb8aec2734480954062abe56ef9073246d7c6c30ae --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash 8015185fbd1a5a043acd8055ba770c4a29ee1f88c3acfc848f2db4ebdc7a202a --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-flood-reentry --chunk-id 3f99a870c42b339f7b2816bb8aec2734480954062abe56ef9073246d7c6c30ae --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash 8015185fbd1a5a043acd8055ba770c4a29ee1f88c3acfc848f2db4ebdc7a202a --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 2: 0a803dca33e55c0c5dea445f1db7f8bde62474553fc53314f8b933bf229b2ce8

**Review status: PENDING**
- Source: `cdc-flood-reentry` — https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html
- Original SHA-256: `61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85`
- Parent section: `00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558`; character span [382, 484).
- Intended hazards: flood, hurricane; phases: recover; geography: `US`.
- Source section heading: Safety Guidelines: Reentering Your Flooded Home > When you first reenter your home > Take these steps when you first reenter your flooded home.

**Original passage from acquired content:**

```text
If your home has damage, do not reenter until it has been examined by a building inspector for safety.
```

**Surrounding context:** [Context 00c7f0e0a7de](#context-00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558), [Context 40d20e9ce3a5](#context-40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
If your home has damage, do not reenter until it has been examined by a building inspector for safety.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-flood-reentry --chunk-id 0a803dca33e55c0c5dea445f1db7f8bde62474553fc53314f8b933bf229b2ce8
python -m knowledge.review approve --root data/official_sources --source-id cdc-flood-reentry --chunk-id 0a803dca33e55c0c5dea445f1db7f8bde62474553fc53314f8b933bf229b2ce8 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash 484339b07cfd15ac25bb1edb68f974dedbc2b3d78151355f18dfff8c2efee83f --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-flood-reentry --chunk-id 0a803dca33e55c0c5dea445f1db7f8bde62474553fc53314f8b933bf229b2ce8 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash 484339b07cfd15ac25bb1edb68f974dedbc2b3d78151355f18dfff8c2efee83f --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 3: 988c9fcd1da54e741fcd265c007f7388a9cfa52efc4b6c74d99796e1cb5a3fb1

**Review status: PENDING**
- Source: `cdc-flood-reentry` — https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html
- Original SHA-256: `61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85`
- Parent section: `40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e`; character span [0, 97).
- Intended hazards: flood, hurricane; phases: recover; geography: `US`.
- Source section heading: Safety Guidelines: Reentering Your Flooded Home > When you first reenter your home > Warning!

**Original passage from acquired content:**

```text
NEVER turn power on or off yourself or use an electric tool or appliance while standing in water.
```

**Surrounding context:** [Context 40d20e9ce3a5](#context-40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e), [Context 00c7f0e0a7de](#context-00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
NEVER turn power on or off yourself or use an electric tool or appliance while standing in water.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Preserve NEVER and while standing in water; this is not electrical-repair permission.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-flood-reentry --chunk-id 988c9fcd1da54e741fcd265c007f7388a9cfa52efc4b6c74d99796e1cb5a3fb1
python -m knowledge.review approve --root data/official_sources --source-id cdc-flood-reentry --chunk-id 988c9fcd1da54e741fcd265c007f7388a9cfa52efc4b6c74d99796e1cb5a3fb1 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash a5bf10b7492cb21885da1ba44fe3bfdcb8cc16e1119d85edf1e0b59f8a68915c --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-flood-reentry --chunk-id 988c9fcd1da54e741fcd265c007f7388a9cfa52efc4b6c74d99796e1cb5a3fb1 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash a5bf10b7492cb21885da1ba44fe3bfdcb8cc16e1119d85edf1e0b59f8a68915c --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 4: ffa4fe9ae4c8f85d1030c5907c403b265370c503fefd6ab9f87e097ccf620465

**Review status: PENDING**
- Source: `cdc-flood-reentry` — https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html
- Original SHA-256: `61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85`
- Parent section: `00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558`; character span [1342, 1432).
- Intended hazards: flood, hurricane; phases: recover; geography: `US`.
- Source section heading: Safety Guidelines: Reentering Your Flooded Home > When you first reenter your home > Take these steps when you first reenter your flooded home.

**Original passage from acquired content:**

```text
Have an electrician check the house's electrical system before turning the power on again.
```

**Surrounding context:** [Context 00c7f0e0a7de](#context-00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558), [Context 40d20e9ce3a5](#context-40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Have an electrician check the house's electrical system before turning the power on again.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Electricity availability does not establish general household safety.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-flood-reentry --chunk-id ffa4fe9ae4c8f85d1030c5907c403b265370c503fefd6ab9f87e097ccf620465
python -m knowledge.review approve --root data/official_sources --source-id cdc-flood-reentry --chunk-id ffa4fe9ae4c8f85d1030c5907c403b265370c503fefd6ab9f87e097ccf620465 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash d0495e060dc44a35380c5a0801a8035fb03e779e333fc56c5426d78b68498d16 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-flood-reentry --chunk-id ffa4fe9ae4c8f85d1030c5907c403b265370c503fefd6ab9f87e097ccf620465 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash d0495e060dc44a35380c5a0801a8035fb03e779e333fc56c5426d78b68498d16 --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 5: a60f54160bbb2ce43a813d4ad0a83e72e8212aec8492956a7dd56b4e89c532c7

**Review status: PENDING**
- Source: `cdc-flood-reentry` — https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html
- Original SHA-256: `61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85`
- Parent section: `00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558`; character span [543, 604).
- Intended hazards: flood, hurricane; phases: recover; geography: `US`.
- Source section heading: Safety Guidelines: Reentering Your Flooded Home > When you first reenter your home > Take these steps when you first reenter your flooded home.

**Original passage from acquired content:**

```text
Tap water may not be safe to drink. Listen to local warnings.
```

**Surrounding context:** [Context 00c7f0e0a7de](#context-00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558), [Context 40d20e9ce3a5](#context-40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Tap water may not be safe to drink. Listen to local warnings.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-flood-reentry --chunk-id a60f54160bbb2ce43a813d4ad0a83e72e8212aec8492956a7dd56b4e89c532c7
python -m knowledge.review approve --root data/official_sources --source-id cdc-flood-reentry --chunk-id a60f54160bbb2ce43a813d4ad0a83e72e8212aec8492956a7dd56b4e89c532c7 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash 63ecfa40fa72e170a0046771970b1a06400cd516cdea572fe4e64f60eaa6acc2 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-flood-reentry --chunk-id a60f54160bbb2ce43a813d4ad0a83e72e8212aec8492956a7dd56b4e89c532c7 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash 63ecfa40fa72e170a0046771970b1a06400cd516cdea572fe4e64f60eaa6acc2 --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 6: ab2bd10259fd31091cacb80da02f5e8e042eeef7fb9d88b6f37ff01d23622498

**Review status: PENDING**
- Source: `cdc-flood-reentry` — https://www.cdc.gov/floods/safety/reentering-your-flooded-home-safety.html
- Original SHA-256: `61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85`
- Parent section: `2273ed119c944e0858145c0aedf349de599ee60bf06cf3bf428905e8ec5fe1b0`; character span [0, 231).
- Intended hazards: flood, hurricane; phases: recover; geography: `US`.
- Source section heading: Safety Guidelines: Reentering Your Flooded Home > Key points

**Original passage from acquired content:**

```text
When returning to a flooded home after a natural disaster, be aware that your house may be contaminated with mold or sewage, which can make you sick.
Take steps to protect your health and safety when returning to your flooded home.
```

**Surrounding context:** [Context 2273ed119c94](#context-2273ed119c944e0858145c0aedf349de599ee60bf06cf3bf428905e8ec5fe1b0), [Context 00c7f0e0a7de](#context-00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558), [Context 40d20e9ce3a5](#context-40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
When returning to a flooded home after a natural disaster, be aware that your house may be contaminated with mold or sewage, which can make you sick.
Take steps to protect your health and safety when returning to your flooded home.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-flood-reentry --chunk-id ab2bd10259fd31091cacb80da02f5e8e042eeef7fb9d88b6f37ff01d23622498
python -m knowledge.review approve --root data/official_sources --source-id cdc-flood-reentry --chunk-id ab2bd10259fd31091cacb80da02f5e8e042eeef7fb9d88b6f37ff01d23622498 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash a58eea1396059bcd050a525654b08da5160ff61204e200f2cc054ee628b0be46 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-flood-reentry --chunk-id ab2bd10259fd31091cacb80da02f5e8e042eeef7fb9d88b6f37ff01d23622498 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 61ee0c0add7e00bf7295b316e4edaffdd55b5612b8706f7dff3710aa18abba85 --expected-context-hash a58eea1396059bcd050a525654b08da5160ff61204e200f2cc054ee628b0be46 --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 7: f343d8888f2404484e62b2a2cf8a94838c6b01f18709920cc4052d220a435260

**Review status: PENDING**
- Source: `cdc-floodwater` — https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- Original SHA-256: `19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8`
- Parent section: `0d7bafd14b5d20adf424397f3b3afa737a14a39c4231c47b93c2feef9ad1cf0c`; character span [0, 140).
- Intended hazards: flood, hurricane; phases: respond; geography: `US`.
- Source section heading: Safety Guidelines: Floodwater > Key points

**Original passage from acquired content:**

```text
Never drive in flooded areas—turn around, don't drown!
Stay out of floodwater—it can contain many things that can hurt you or make you sick.
```

**Surrounding context:** [Context 0d7bafd14b5d](#context-0d7bafd14b5d20adf424397f3b3afa737a14a39c4231c47b93c2feef9ad1cf0c), [Context fb7c68740691](#context-fb7c68740691c5415cf046ef7cf33c371987a032efa5349c24bd0344f50b7352)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Never drive in flooded areas—turn around, don't drown!
Stay out of floodwater—it can contain many things that can hurt you or make you sick.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-floodwater --chunk-id f343d8888f2404484e62b2a2cf8a94838c6b01f18709920cc4052d220a435260
python -m knowledge.review approve --root data/official_sources --source-id cdc-floodwater --chunk-id f343d8888f2404484e62b2a2cf8a94838c6b01f18709920cc4052d220a435260 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 23ebd894daa6b6b75ed1b75f331d8be0662e7af2ded8838fac90755068efcaae --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-floodwater --chunk-id f343d8888f2404484e62b2a2cf8a94838c6b01f18709920cc4052d220a435260 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 23ebd894daa6b6b75ed1b75f331d8be0662e7af2ded8838fac90755068efcaae --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 8: f8940b5b922259594b525596f654ee3d975d3f020077d671f73f4dbc62b01b86

**Review status: PENDING**
- Source: `cdc-floodwater` — https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- Original SHA-256: `19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8`
- Parent section: `028c2d0201eba657665949e814362ba0d7d2693321c217a9d325a0b31a61e49d`; character span [0, 184).
- Intended hazards: flood, hurricane; phases: respond; geography: `US`.
- Source section heading: Safety Guidelines: Floodwater > Overview > Don't drive in flooded areas.

**Original passage from acquired content:**

```text
Always follow warnings about flooded roads.
Don't drive in flooded areas—cars or other vehicles won't protect you from floodwaters. They can be swept away or may stall in moving water.
```

**Surrounding context:** [Context 028c2d0201eb](#context-028c2d0201eba657665949e814362ba0d7d2693321c217a9d325a0b31a61e49d), [Context fb7c68740691](#context-fb7c68740691c5415cf046ef7cf33c371987a032efa5349c24bd0344f50b7352)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Always follow warnings about flooded roads.
Don't drive in flooded areas—cars or other vehicles won't protect you from floodwaters. They can be swept away or may stall in moving water.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-floodwater --chunk-id f8940b5b922259594b525596f654ee3d975d3f020077d671f73f4dbc62b01b86
python -m knowledge.review approve --root data/official_sources --source-id cdc-floodwater --chunk-id f8940b5b922259594b525596f654ee3d975d3f020077d671f73f4dbc62b01b86 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 08fcd4743d3a6d842e17cf947454015d6d64e246ffb691cb61ae45725090bc97 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-floodwater --chunk-id f8940b5b922259594b525596f654ee3d975d3f020077d671f73f4dbc62b01b86 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 08fcd4743d3a6d842e17cf947454015d6d64e246ffb691cb61ae45725090bc97 --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 9: ee1b186d50f72b4fa2d5b4b8919c5c41d10f521349df1b2e4ef5fdcf1859d5ec

**Review status: PENDING**
- Source: `cdc-floodwater` — https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- Original SHA-256: `19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8`
- Parent section: `054a6163a645840b22edd3daf3e5565b477c4490471aeb09b197844cf85a32f1`; character span [0, 199).
- Intended hazards: flood, hurricane; phases: respond; geography: `US`.
- Source section heading: Safety Guidelines: Floodwater > Overview > Turn around, don't drown!

**Original passage from acquired content:**

```text
Floodwater can pose a drowning risk for everyone— regardless of their ability to swim. Swiftly moving shallow water can be deadly, and even shallow standing water can be dangerous for small children.
```

**Surrounding context:** [Context 054a6163a645](#context-054a6163a645840b22edd3daf3e5565b477c4490471aeb09b197844cf85a32f1), [Context fb7c68740691](#context-fb7c68740691c5415cf046ef7cf33c371987a032efa5349c24bd0344f50b7352)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Floodwater can pose a drowning risk for everyone— regardless of their ability to swim. Swiftly moving shallow water can be deadly, and even shallow standing water can be dangerous for small children.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-floodwater --chunk-id ee1b186d50f72b4fa2d5b4b8919c5c41d10f521349df1b2e4ef5fdcf1859d5ec
python -m knowledge.review approve --root data/official_sources --source-id cdc-floodwater --chunk-id ee1b186d50f72b4fa2d5b4b8919c5c41d10f521349df1b2e4ef5fdcf1859d5ec --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash af27144d9fe707fc152cefcd114fb3b7a577e1ff21640c738a3b9eac773470da --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-floodwater --chunk-id ee1b186d50f72b4fa2d5b4b8919c5c41d10f521349df1b2e4ef5fdcf1859d5ec --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash af27144d9fe707fc152cefcd114fb3b7a577e1ff21640c738a3b9eac773470da --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 10: 583e722d5f070eea7913bb10aa1c6f3c189b9cdcd4105807cb81f5df4f135e8c

**Review status: PENDING**
- Source: `cdc-floodwater` — https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- Original SHA-256: `19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8`
- Parent section: `5a6739b4103ae566940edbd93627230a7423334ba321a3a63af4e16d4fc930ac`; character span [413, 619).
- Intended hazards: flood, hurricane; phases: prepare; geography: `US`.
- Source section heading: Safety Guidelines: Floodwater > Stay out of floodwater > Floodwaters contain many things that may harm health.

**Original passage from acquired content:**

```text
Recognize Flood Risk
Identify flood-prone or landslide-prone areas near you.
Know your community's warning signals, evacuation routes, and emergency shelter locations.
Know flood evacuation routes near you.
```

**Surrounding context:** [Context 5a6739b4103a](#context-5a6739b4103ae566940edbd93627230a7423334ba321a3a63af4e16d4fc930ac)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Recognize Flood Risk
Identify flood-prone or landslide-prone areas near you.
Know your community's warning signals, evacuation routes, and emergency shelter locations.
Know flood evacuation routes near you.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Hazard-awareness text only. Shelter names, capacity, evacuation orders and route availability are not established.
- PREPARE is proposed from the infographic context; current source-level tags do not yet include PREPARE.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-floodwater --chunk-id 583e722d5f070eea7913bb10aa1c6f3c189b9cdcd4105807cb81f5df4f135e8c
python -m knowledge.review approve --root data/official_sources --source-id cdc-floodwater --chunk-id 583e722d5f070eea7913bb10aa1c6f3c189b9cdcd4105807cb81f5df4f135e8c --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash bd62bfd7de184ce6ac3fdaf5831391aad5329e277942f561df49ac3429670b3d --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-floodwater --chunk-id 583e722d5f070eea7913bb10aa1c6f3c189b9cdcd4105807cb81f5df4f135e8c --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash bd62bfd7de184ce6ac3fdaf5831391aad5329e277942f561df49ac3429670b3d --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 11: c8cc634ab6e6efec6cbe6c76f280563dcdb58d2126b42efdda8baed2b052cb62

**Review status: PENDING**
- Source: `cdc-floodwater` — https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- Original SHA-256: `19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8`
- Parent section: `0b26baf60b774893e1239f8b31e9d960abb4d4e335e60538dd7d06d8d7c0a555`; character span [252, 598).
- Intended hazards: flood, hurricane; phases: respond, recover; geography: `US`.
- Source section heading: Safety Guidelines: Floodwater > Protect yourself from illness and injuries > Avoid electrical hazards inside or outside your home.

**Original passage from acquired content:**

```text
NEVER touch a fallen power line. Call the power company to report fallen power lines. Avoid contact with overhead power lines during cleanup and other activities.
Do not drive through standing water if downed power lines are in the water.
If you believe someone has been electrocuted, call or have someone else call 911 or emergency medical help.
```

**Surrounding context:** [Context 0b26baf60b77](#context-0b26baf60b774893e1239f8b31e9d960abb4d4e335e60538dd7d06d8d7c0a555)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
NEVER touch a fallen power line. Call the power company to report fallen power lines. Avoid contact with overhead power lines during cleanup and other activities.
Do not drive through standing water if downed power lines are in the water.
If you believe someone has been electrocuted, call or have someone else call 911 or emergency medical help.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Preserve the negative instructions and conditional emergency-help sentence. No responder contact is made by this application.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-floodwater --chunk-id c8cc634ab6e6efec6cbe6c76f280563dcdb58d2126b42efdda8baed2b052cb62
python -m knowledge.review approve --root data/official_sources --source-id cdc-floodwater --chunk-id c8cc634ab6e6efec6cbe6c76f280563dcdb58d2126b42efdda8baed2b052cb62 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 18f8a20819ad25c5aae8d6f27e2f1271024cb9e24e4e4369fefeda54fa097aff --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-floodwater --chunk-id c8cc634ab6e6efec6cbe6c76f280563dcdb58d2126b42efdda8baed2b052cb62 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 18f8a20819ad25c5aae8d6f27e2f1271024cb9e24e4e4369fefeda54fa097aff --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 12: 2b547640ce57007af7be5598028fb9fa2f4026d67c6262a31a196a307180fa91

**Review status: PENDING**
- Source: `cdc-floodwater` — https://www.cdc.gov/floods/safety/floodwater-after-a-disaster-or-emergency-safety.html
- Original SHA-256: `19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8`
- Parent section: `29ee34e3fccd7fc859fe228e8ddb03b95613b3c99d0c871fbf14babf9fef5417`; character span [348, 667).
- Intended hazards: flood, hurricane; phases: respond; geography: `US`.
- Source section heading: Safety Guidelines: Floodwater > Protect yourself from illness and injuries > Protect yourself and your loved ones from diarrheal diseases.

**Original passage from acquired content:**

```text
Do not allow children to play in floodwater areas.
Do not allow children to play with toys that have been contaminated by floodwater and have not been disinfected.
Do not bathe in water that may be contaminated with sewage or toxic chemicals. This includes rivers, streams, or lakes that are contaminated by floodwater.
```

**Surrounding context:** [Context 29ee34e3fccd](#context-29ee34e3fccd7fc859fe228e8ddb03b95613b3c99d0c871fbf14babf9fef5417)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
Do not allow children to play in floodwater areas.
Do not allow children to play with toys that have been contaminated by floodwater and have not been disinfected.
Do not bathe in water that may be contaminated with sewage or toxic chemicals. This includes rivers, streams, or lakes that are contaminated by floodwater.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id cdc-floodwater --chunk-id 2b547640ce57007af7be5598028fb9fa2f4026d67c6262a31a196a307180fa91
python -m knowledge.review approve --root data/official_sources --source-id cdc-floodwater --chunk-id 2b547640ce57007af7be5598028fb9fa2f4026d67c6262a31a196a307180fa91 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 4fec7b9116dc718ab28eb7d96378b7e9b957fe1993c98f0798137c542bcfcc3d --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id cdc-floodwater --chunk-id 2b547640ce57007af7be5598028fb9fa2f4026d67c6262a31a196a307180fa91 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 19ff095397e4369d1937673322c1a27e9d5bfea970d96f57af64fdcf912020b8 --expected-context-hash 4fec7b9116dc718ab28eb7d96378b7e9b957fe1993c98f0798137c542bcfcc3d --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 13: 1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549

**Review status: PENDING**
- Source: `miami-dade-eeap` — https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`
- Parent section: `6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b`; character span [0, 562).
- Intended hazards: hurricane; phases: respond; geography: `US-FL-MIAMI-DADE`.
- Source section heading: Emergency & Evacuation Assistance Program (EEAP) > Can I get assistance if I am not enrolled in the event of an emergency?

**Original passage from acquired content:**

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

**Surrounding context:** [Context 6a709297db55](#context-6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b), [Context 1f1086b2b14e](#context-1f1086b2b14e0d28ba209f1d6a64dc1940a30a82978d1ccc0abd52a68504e8ca)

**Proposed short retrieval chunk (verbatim, pending review):**

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

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id miami-dade-eeap --chunk-id 1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549
python -m knowledge.review approve --root data/official_sources --source-id miami-dade-eeap --chunk-id 1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash dbd14b0ab97fb981138c08c154cac84abcdcb66d3abc09d975ca8b70fe39639f --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id miami-dade-eeap --chunk-id 1dceb9df1efd2dc78c44c34dc7d315c66d945f52bdd0ffe3959aaf9e13909549 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash dbd14b0ab97fb981138c08c154cac84abcdcb66d3abc09d975ca8b70fe39639f --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 14: 15627d254d98b3cdb0d95737ba7177031d4a0c9067cbc3de1a4b6c00db45e017

**Review status: PENDING**
- Source: `miami-dade-eeap` — https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`
- Parent section: `9c7e52a128185b463037aabbc651ff167458f05694ff296cf0e8f8093e5d4bbb`; character span [0, 760).
- Intended hazards: hurricane; phases: prepare, respond; geography: `US-FL-MIAMI-DADE`.
- Source section heading: Emergency & Evacuation Assistance Program (EEAP) > Am I eligible for the EEAP?

**Original passage from acquired content:**

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

**Surrounding context:** [Context 9c7e52a12818](#context-9c7e52a128185b463037aabbc651ff167458f05694ff296cf0e8f8093e5d4bbb), [Context 1f1086b2b14e](#context-1f1086b2b14e0d28ba209f1d6a64dc1940a30a82978d1ccc0abd52a68504e8ca), [Context 6a709297db55](#context-6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b)

**Proposed short retrieval chunk (verbatim, pending review):**

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

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.
- Criteria are quoted for human review, not an eligibility determination; retain the residential-facility exclusion.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id miami-dade-eeap --chunk-id 15627d254d98b3cdb0d95737ba7177031d4a0c9067cbc3de1a4b6c00db45e017
python -m knowledge.review approve --root data/official_sources --source-id miami-dade-eeap --chunk-id 15627d254d98b3cdb0d95737ba7177031d4a0c9067cbc3de1a4b6c00db45e017 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash 86d8e13a09aabeff88157620698c1419d24bd07f392f0512bb3f098f21f2d15c --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id miami-dade-eeap --chunk-id 15627d254d98b3cdb0d95737ba7177031d4a0c9067cbc3de1a4b6c00db45e017 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash 86d8e13a09aabeff88157620698c1419d24bd07f392f0512bb3f098f21f2d15c --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 15: 7d79b4586449195f46f7ef80385dde00241df006f892674b0c39a627013e9349

**Review status: PENDING**
- Source: `miami-dade-eeap` — https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`
- Parent section: `16920ae167aca6c18f25b02f1f352277ca8dfeaee15c98c1bfcca176bad5683b`; character span [0, 793).
- Intended hazards: hurricane; phases: prepare, respond; geography: `US-FL-MIAMI-DADE`.
- Source section heading: Emergency & Evacuation Assistance Program (EEAP) > What does the EEAP offer and when is it used?

**Original passage from acquired content:**

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

**Surrounding context:** [Context 16920ae167ac](#context-16920ae167aca6c18f25b02f1f352277ca8dfeaee15c98c1bfcca176bad5683b), [Context 1f1086b2b14e](#context-1f1086b2b14e0d28ba209f1d6a64dc1940a30a82978d1ccc0abd52a68504e8ca), [Context 6a709297db55](#context-6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b)

**Proposed short retrieval chunk (verbatim, pending review):**

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

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.
- Retain the caregiver requirement and refuge-of-last-resort / health-care-level limitations.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id miami-dade-eeap --chunk-id 7d79b4586449195f46f7ef80385dde00241df006f892674b0c39a627013e9349
python -m knowledge.review approve --root data/official_sources --source-id miami-dade-eeap --chunk-id 7d79b4586449195f46f7ef80385dde00241df006f892674b0c39a627013e9349 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash d4340ae59aa91a1ada2f978447ad1298d2a6c80032a777d00534537e8606eba7 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id miami-dade-eeap --chunk-id 7d79b4586449195f46f7ef80385dde00241df006f892674b0c39a627013e9349 --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash d4340ae59aa91a1ada2f978447ad1298d2a6c80032a777d00534537e8606eba7 --reason "<HUMAN_REJECTION_REASON>"
```

## Candidate 16: f8a045039bb7ab2b702116a082a43dd1b1ae83e8aa3140c3c2f2424f8ce34a5c

**Review status: PENDING**
- Source: `miami-dade-eeap` — https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672
- Original SHA-256: `4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2`
- Parent section: `029d9ddadbf85022bb5c9a90f1c6bb1561ac15deb26335624a9b401aa80c7bbb`; character span [520, 1020).
- Intended hazards: hurricane; phases: prepare; geography: `US-FL-MIAMI-DADE`.
- Source section heading: Emergency & Evacuation Assistance Program (EEAP) > How do I register for the EEAP?

**Original passage from acquired content:**

```text
If more than one eligible person living in the same household requires assistance
 during evacuations, each person must complete and submit a separate application.
If you require a higher level of medical care, your primary care physician should
 complete and sign the application before submission.
Registration (online and paper application) for the EEAP closes before an evacuation
 order is pronounced. Do not wait until an evacuation order is issued to request to
 be added to the EEAP Registry.
```

**Surrounding context:** [Context 029d9ddadbf8](#context-029d9ddadbf85022bb5c9a90f1c6bb1561ac15deb26335624a9b401aa80c7bbb), [Context 1f1086b2b14e](#context-1f1086b2b14e0d28ba209f1d6a64dc1940a30a82978d1ccc0abd52a68504e8ca), [Context 6a709297db55](#context-6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b)

**Proposed short retrieval chunk (verbatim, pending review):**

```text
If more than one eligible person living in the same household requires assistance
 during evacuations, each person must complete and submit a separate application.
If you require a higher level of medical care, your primary care physician should
 complete and sign the application before submission.
Registration (online and paper application) for the EEAP closes before an evacuation
 order is pronounced. Do not wait until an evacuation order is issued to request to
 be added to the EEAP Registry.
```

**Safety caveats (editorial review annotations):**

- PENDING human review; not operational guidance or household safety verification.
- Static program description is not live shelter, enrollment, transport or pickup availability.
- No individual eligibility, enrollment, assistance or evacuation order is established; preserve the non-guarantee FAQ.
- Preserve separate-application, physician-signature and Do not wait conditions; this is not a current enrollment window or evacuation notice.

**Inspect / approve / reject this candidate:**

```powershell
python -m knowledge.review inspect --root data/official_sources --source-id miami-dade-eeap --chunk-id f8a045039bb7ab2b702116a082a43dd1b1ae83e8aa3140c3c2f2424f8ce34a5c
python -m knowledge.review approve --root data/official_sources --source-id miami-dade-eeap --chunk-id f8a045039bb7ab2b702116a082a43dd1b1ae83e8aa3140c3c2f2424f8ce34a5c --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash 781db7d5d8cfb7884176ac8569512826558111393717f1b00e22d3be22923263 --provenance-checked --content-checked --geographic-scope-checked --applicability-checked --caveats-preserved
python -m knowledge.review reject --root data/official_sources --source-id miami-dade-eeap --chunk-id f8a045039bb7ab2b702116a082a43dd1b1ae83e8aa3140c3c2f2424f8ce34a5c --reviewer "<HUMAN_REVIEWER>" --expected-content-hash 4829fd8bd62991c0ce9276d9bc45d08578cb9a35a05e6f15d8c72633048ad3e2 --expected-context-hash 781db7d5d8cfb7884176ac8569512826558111393717f1b00e22d3be22923263 --reason "<HUMAN_REJECTION_REASON>"
```

## Acquired surrounding context

Text is decoded from the preserved HTML; HTML tags and layout whitespace are normalized. Guidance wording is not rewritten. Heading paths retain parent conditions.

<a id="context-00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558"></a>
### Context 00c7f0e0a7de
Source `cdc-flood-reentry`; extracted section `00c7f0e0a7de3a0992eb142574ba75d93dd473b504adc196e13c9033bcf3e558`.
Safety Guidelines: Reentering Your Flooded Home > When you first reenter your home > Take these steps when you first reenter your flooded home.

```text
Be Ready! Hurricanes Infographic
Be Ready! Hurricanes
Before
Cover windows with storm shutters or plywood.
Tune in for local information.
Know how to turn off your gas, electricity, and water in case you need to evacuate.
Secure outdoor items by moving them to the garage.
Make an emergency kit.
Designate a shelter area if you can't evacuate. Rooms without windows are best.
After
If your home has damage, do not reenter until it has been examined by a building inspector for safety.
Prevent mold growth by airing out rooms and disinfecting.
Tap water may not be safe to drink. Listen to local warnings.
Throw away food that may be unsafe.
Prevent carbon monoxide poisoning. Use generators, stoves, and grills outside and away from windows and doors. 20 feet
Footer
Public Health Preparedness and Response/Centers for Disease Control and Prevention
Download Infographic PDF: English | Español
Try to return to your home during the daytime so that you do not have to use any lights. Use battery-powered flashlights and lanterns, rather than candles, gas lanterns, or torches.
If you have standing water in your home and can turn off the main power from a dry location, then go ahead and turn off the power, even if it delays cleaning. If you must enter standing water to access the main power switch, then call an electrician to turn it off.
Have an electrician check the house's electrical system before turning the power on again.
If you smell gas or suspect a leak, turn off the main gas valve, open all windows, and leave your house immediately. Notify the gas company or the police or fire departments or State Fire Marshal's office, and do not turn on the lights or do anything that could cause a spark. Do not return until you are told it is safe to do so.
If the house has been closed up for several days, enter briefly to open doors and windows to let the house air out for a while (at least 30 minutes) before you stay for any length of time.
If your home has been flooded and has been closed up for several days, assume your home has mold.
If your home has been flooded, it also may be contaminated with sewage. See Floodwater After a Disaster or Emergency.
```

<a id="context-40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e"></a>
### Context 40d20e9ce3a5
Source `cdc-flood-reentry`; extracted section `40d20e9ce3a5c19070064a2701e6b7ee1a164e150c32c59a8405ad2ca12cad0e`.
Safety Guidelines: Reentering Your Flooded Home > When you first reenter your home > Warning!

```text
NEVER turn power on or off yourself or use an electric tool or appliance while standing in water.
```

<a id="context-2273ed119c944e0858145c0aedf349de599ee60bf06cf3bf428905e8ec5fe1b0"></a>
### Context 2273ed119c94
Source `cdc-flood-reentry`; extracted section `2273ed119c944e0858145c0aedf349de599ee60bf06cf3bf428905e8ec5fe1b0`.
Safety Guidelines: Reentering Your Flooded Home > Key points

```text
When returning to a flooded home after a natural disaster, be aware that your house may be contaminated with mold or sewage, which can make you sick.
Take steps to protect your health and safety when returning to your flooded home.
```

<a id="context-0d7bafd14b5d20adf424397f3b3afa737a14a39c4231c47b93c2feef9ad1cf0c"></a>
### Context 0d7bafd14b5d
Source `cdc-floodwater`; extracted section `0d7bafd14b5d20adf424397f3b3afa737a14a39c4231c47b93c2feef9ad1cf0c`.
Safety Guidelines: Floodwater > Key points

```text
Never drive in flooded areas—turn around, don't drown!
Stay out of floodwater—it can contain many things that can hurt you or make you sick.
```

<a id="context-fb7c68740691c5415cf046ef7cf33c371987a032efa5349c24bd0344f50b7352"></a>
### Context fb7c68740691
Source `cdc-floodwater`; extracted section `fb7c68740691c5415cf046ef7cf33c371987a032efa5349c24bd0344f50b7352`.
Safety Guidelines: Floodwater > Overview

```text
Never drive in flooded areas—turn around, don't drown!
Floodwater and standing water can be dangerous and can make you vulnerable to infectious diseases, chemical hazards, and injuries. Protect yourself and your loved ones from the risks brought by floodwater by following these steps.
```

<a id="context-028c2d0201eba657665949e814362ba0d7d2693321c217a9d325a0b31a61e49d"></a>
### Context 028c2d0201eb
Source `cdc-floodwater`; extracted section `028c2d0201eba657665949e814362ba0d7d2693321c217a9d325a0b31a61e49d`.
Safety Guidelines: Floodwater > Overview > Don't drive in flooded areas.

```text
Always follow warnings about flooded roads.
Don't drive in flooded areas—cars or other vehicles won't protect you from floodwaters. They can be swept away or may stall in moving water.
```

<a id="context-054a6163a645840b22edd3daf3e5565b477c4490471aeb09b197844cf85a32f1"></a>
### Context 054a6163a645
Source `cdc-floodwater`; extracted section `054a6163a645840b22edd3daf3e5565b477c4490471aeb09b197844cf85a32f1`.
Safety Guidelines: Floodwater > Overview > Turn around, don't drown!

```text
Floodwater can pose a drowning risk for everyone— regardless of their ability to swim. Swiftly moving shallow water can be deadly, and even shallow standing water can be dangerous for small children.
```

<a id="context-5a6739b4103ae566940edbd93627230a7423334ba321a3a63af4e16d4fc930ac"></a>
### Context 5a6739b4103a
Source `cdc-floodwater`; extracted section `5a6739b4103ae566940edbd93627230a7423334ba321a3a63af4e16d4fc930ac`.
Safety Guidelines: Floodwater > Stay out of floodwater > Floodwaters contain many things that may harm health.

```text
Be Ready! Floods Infographic
Be Ready! Floods
During
Gather emergency supplies and follow local radio or TV updates.
Unplug appliances to prevent electrical shock when power comes back on.
Do NOT drive or walk across flooded roads. Cars and people can be swept away.
When power lines are down, water is in your home, or before you evacuate, TURN OFF gas, power, and water.
Tie down or bring outdoor items inside.
Recognize Flood Risk
Identify flood-prone or landslide-prone areas near you.
Know your community's warning signals, evacuation routes, and emergency shelter locations.
Know flood evacuation routes near you.
After 
Throw away items that cannot be disinfected, like wall coverings, cloth, rugs, and drywall.
Use fans, air conditioning units, and dehumidifiers for drying.
For cleanup, wear rubber boots and plastic gloves.
Clean walls, hard floors, and other surfaces with soap and water. Use a mixture of 1 cup of bleach and 1 gallon of water to disinfect.
Caution! Flood water may contain trash.
Practice safe hygiene
Wash hands with soap and water to help prevent germs.
Listen for information from your local officials on how to safely use water to drink, cook, or clean.
Download Infographic PDF: English | Español
We don't know exactly what is in floodwater at any given point in time. Floodwater can contain:
Downed power lines
Human and livestock waste
Household, medical, and industrial hazardous waste (chemical, biological, and radiological)
Coal ash waste that can contain carcinogenic compounds such as arsenic, chromium, and mercury
Other germs and contaminants that can lead to illness
Physical objects such as lumber, vehicles, and debris
Wild or stray animals such as rodents and snakes
```

<a id="context-0b26baf60b774893e1239f8b31e9d960abb4d4e335e60538dd7d06d8d7c0a555"></a>
### Context 0b26baf60b77
Source `cdc-floodwater`; extracted section `0b26baf60b774893e1239f8b31e9d960abb4d4e335e60538dd7d06d8d7c0a555`.
Safety Guidelines: Floodwater > Protect yourself from illness and injuries > Avoid electrical hazards inside or outside your home.

```text
After a hurricane, flood or other natural disaster you need to be careful to avoid electrical hazards both in your home and elsewhere.
Shut off electrical power and natural gas or propane tanks in your home to avoid fire, electrocution, or explosions.
NEVER touch a fallen power line. Call the power company to report fallen power lines. Avoid contact with overhead power lines during cleanup and other activities.
Do not drive through standing water if downed power lines are in the water.
If you believe someone has been electrocuted, call or have someone else call 911 or emergency medical help.
Keep Reading 
What to Do to Protect Yourself From Electrical Hazards
```

<a id="context-29ee34e3fccd7fc859fe228e8ddb03b95613b3c99d0c871fbf14babf9fef5417"></a>
### Context 29ee34e3fccd
Source `cdc-floodwater`; extracted section `29ee34e3fccd7fc859fe228e8ddb03b95613b3c99d0c871fbf14babf9fef5417`.
Safety Guidelines: Floodwater > Protect yourself from illness and injuries > Protect yourself and your loved ones from diarrheal diseases.

```text
Be aware that floodwater may contain sewage, and eating or drinking anything contaminated by floodwater can cause diarrheal disease (such as E. coli or Salmonella infection). To protect yourself and your family:
Wash your hands after contact with floodwater. Also be sure to wash children's hands with soap and water often and always before meals.
Do not allow children to play in floodwater areas.
Do not allow children to play with toys that have been contaminated by floodwater and have not been disinfected.
Do not bathe in water that may be contaminated with sewage or toxic chemicals. This includes rivers, streams, or lakes that are contaminated by floodwater.
Keep Reading 
Water, Sanitation, and Hygiene (WASH)-related Emergencies and Outbreaks
```

<a id="context-6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b"></a>
### Context 6a709297db55
Source `miami-dade-eeap`; extracted section `6a709297db559f157a7b7f4eff8cdbecca07b789ab49fd6b5edec3b616c5032b`.
Emergency & Evacuation Assistance Program (EEAP) > Can I get assistance if I am not enrolled in the event of an emergency?

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

<a id="context-1f1086b2b14e0d28ba209f1d6a64dc1940a30a82978d1ccc0abd52a68504e8ca"></a>
### Context 1f1086b2b14e
Source `miami-dade-eeap`; extracted section `1f1086b2b14e0d28ba209f1d6a64dc1940a30a82978d1ccc0abd52a68504e8ca`.
Emergency & Evacuation Assistance Program (EEAP) > longDescription

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

<a id="context-9c7e52a128185b463037aabbc651ff167458f05694ff296cf0e8f8093e5d4bbb"></a>
### Context 9c7e52a12818
Source `miami-dade-eeap`; extracted section `9c7e52a128185b463037aabbc651ff167458f05694ff296cf0e8f8093e5d4bbb`.
Emergency & Evacuation Assistance Program (EEAP) > Am I eligible for the EEAP?

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

<a id="context-16920ae167aca6c18f25b02f1f352277ca8dfeaee15c98c1bfcca176bad5683b"></a>
### Context 16920ae167ac
Source `miami-dade-eeap`; extracted section `16920ae167aca6c18f25b02f1f352277ca8dfeaee15c98c1bfcca176bad5683b`.
Emergency & Evacuation Assistance Program (EEAP) > What does the EEAP offer and when is it used?

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

<a id="context-029d9ddadbf85022bb5c9a90f1c6bb1561ac15deb26335624a9b401aa80c7bbb"></a>
### Context 029d9ddadbf8
Source `miami-dade-eeap`; extracted section `029d9ddadbf85022bb5c9a90f1c6bb1561ac15deb26335624a9b401aa80c7bbb`.
Emergency & Evacuation Assistance Program (EEAP) > How do I register for the EEAP?

```text
How to apply
Individuals may apply throughout the year to become enrolled in the
 EEAP. Residents only need to apply once to be a life-long member of the program.
Register online or download an application
 below, completely fill it out and mail it. You can also call 311 to have an application
 sent to you in English, Spanish, and Haitian Creole or in an alternate format such
 as Braille or large print.
The EEAP application is available in:
EEAP Application English
EEAP Application Spanish
EEAP
 Application Creole
If more than one eligible person living in the same household requires assistance
 during evacuations, each person must complete and submit a separate application.
If you require a higher level of medical care, your primary care physician should
 complete and sign the application before submission.
Registration (online and paper application) for the EEAP closes before an evacuation
 order is pronounced. Do not wait until an evacuation order is issued to request to
 be added to the EEAP Registry.
After you apply:
The Emergency Management Department or support personnel may contact you to verify
 your registration information.
You will receive a letter letting you know if you have been accepted
 into the program. This letter will include the evacuation assistance you are eligible
 to receive and your responsibilities.
You will be contacted throughout the year to update your personal contact and
 medical information. You do not need to complete an application every year, but it
 is the responsibility of you or your caregiver to report any changes. If your contact
 or medical information changes or you would like to be removed from the EEAP, please
 email [email protected] or call the support
 line at (305) 513-7700.
```
