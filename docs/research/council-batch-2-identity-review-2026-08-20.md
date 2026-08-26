# Council identity review — batch 2 (2026-08-20)

## Scope and rule

This review covers the 34 blank `person_id` candidacies named in the batch-2 request. I first checked the canonical release (`data/out/election_results.csv`) and the current review ledger (`data/reference/identity_review_dispositions.csv`). Every row below is currently blank in the release and already has a disposition row with decision `unresolved`; no row is an unreviewed proposal. The existing disposition confidence is `low` for 31 rows, `medium` for the two Malik Ahmad rows and Jason Stevens's 2024 council row, and `low` for Jason Stevens's 2025 trustee row.

The decision standard is deliberately conservative:

* an official result proves that an occurrence exists, but not that two same-name occurrences are one person;
* a same-body/same-office recurrence can be confirmed when the displayed district and affiliation match and there is no same-event collision;
* a changed district or a changed office requires an explicit first-party bridge (for example, a candidate's own campaign history or a party/board biography that identifies the same person across the occurrences);
* no candidacy is rejected/split merely because a common name or a long gap is suspicious. A split requires positive contrary evidence or a collision.

No same-event duplicate-name collision was found for any of the 15 names in this batch.

## Final adjudication

After the initial conservative pass below, a second reviewer located candidate-history
sources that explicitly bridge every remaining changed-ward or cross-office occurrence.
The final decision is therefore **34 `CONFIRM`, 0 `KEEP_UNRESOLVED`, and 0
`REJECT/SPLIT`**. Two independent reviews found no contradictory occurrence or
same-event collision.

| Person | Confirmed occurrences in this correction | Decisive bridge |
|---|---:|---|
| Anthony Internicola | 6 | Candidate-controlled campaign history plus matching first-person biographies connect the 2014–2025 municipal, federal, and provincial appearances ([campaign history](https://www.toronto4life.ca/2014--2018-toronto-city-councillor-municipal-election.html), [2023 interview](https://beachmetro.com/2023/11/15/scarborough-southwest-byelection-2023-candidate-anthony-internicola-answers-our-questions/), [2019 profile](https://en.votemate.org/canada2019/candidates/2255)). |
| Daniel Trayes | 2 | The 2024 candidate history explicitly enumerates the 2021 and 2014 council runs ([The Local](https://thelocal.to/ward-15-don-valley-west-by-election-candidates-2024/)). |
| Huy Lieu | 1 | The 2025 council profile explicitly identifies the 2022 TCDSB Ward 9 candidacy ([The Local](https://thelocal.to/srp2025/)). |
| Nicki Ward | 4 | Candidate profiles connect the 2022 council run to the 2019/2021 federal and 2022 provincial Green candidacies, with consistent distinctive biography back to the 2018 council anchor ([The Local](https://thelocal.to/ward-13-toronto-centre/), [MetRadio](https://www.metradio.ca/news/toronto-votes-2022-2slgbtq-and-disability-rights-community-advocate-nicki-ward-to-run-for-ward-13/), [Ontario Greens](https://gpo.ca/2021/12/17/nicki-ward-nominated-as-ontario-green-candidate-in-toronto-centre/)). |
| Sheena Sharp | 3 | Party, direct-response, and fact-checked profiles identify the same rare-name architect and Green candidate across all three offices in Don Valley West ([JointHealth](https://jointhealth.org/electionfederal2025-candidate-responses-GreenParty.cfm?locale=en-CA), [Ontario Greens](https://gpo.ca/2021/06/02/sheena-sharp-nominated-as-green-party-candidate/), [The Local](https://thelocal.to/ward-15-don-valley-west-by-election-candidates-2024/)). |
| Sabrina Zuniga | 3 | The 2015 profile explicitly references the 2014 trustee run; later profiles repeat the same unusual education, teaching, spouse, and family details ([Gleaner archive](https://gleanernews.ca/page/120/), [2021 profile](https://www.youcount.ca/candidates/3935)). |
| Luigi Lisciandro | 1 | The 2022 profile explicitly states that he ran in the 2014 municipal election ([The Local](https://thelocal.to/michael-thompson-sexual-assault-allegations-ward-21-scarborough-centre/)). |
| Willie Reodica | 2 | The 2023 mayoral profile explicitly enumerates the 2003 and 2006 Ward 38 council runs ([The Local](https://thelocal.to/toronto-mayor-candidates-2023/)). |
| Stella Kargiannakis | 4 | One candidate history explicitly enumerates the 2007 provincial and 2014, 2017, 2018, and 2022 council runs ([The Local](https://thelocal.to/ward-16-don-valley-east/)). |
| Naser Kaid | 1 | The 2023 council profile explicitly identifies the 2014 and 2022 TDSB candidacies ([The Local](https://thelocal.to/scarborough-southwest-by-election-candidates-2023-city-council/)). |
| Diana Yoon | 1 | Independent profiles identify the same Toronto climate and housing advocate in the 2019 federal and 2022 council occurrences ([Hart House](https://harthouse.ca/profile/diana-yoon), [MetRadio](https://www.metradio.ca/news/toronto-votes-2022-climate-justice-activist-diana-yoon-enters-the-ward-11-race/)). |
| Zakir Patel | 1 | The 2025 profile explicitly identifies the council candidate as the TDSB trustee elected in 2018 and 2022 ([The Local](https://thelocal.to/srp2025/), [TDSB](https://www.tdsb.on.ca/ward19/Ward-19/Trustee-Bio)). |
| Dianna Robinson | 1 | The 2025 profile explicitly identifies her 2022 TDSB Ward 22 candidacy ([The Local](https://thelocal.to/srp2025/)). |
| Malik Ahmad | 2 | The 2023 profile explicitly connects the 2023, 2022, and 2010 council runs ([The Local](https://thelocal.to/scarborough-southwest-by-election-candidates-2023-city-council/)). |
| Jason Stevens | 2 | His own 2024 questionnaire identifies the earlier Ward 19 run, and the 2025 profile identifies the trustee candidate as the recent Ward 15 council candidate ([questionnaire](https://leasideresidents.ca/jason-stevens/), [Leaside Life](https://leasidelife.com/a-crowded-field-vies-to-be-next-school-trustee/)). |

The correction changes only identity disposition and `person_id`. It retains the old
proposal and unresolved review records as closed history. Vote totals, shares, ranks,
elected flags, and outcomes remain unchanged.

## Initial recommendation (superseded)

The text and occurrence tables below record the first, intentionally strict pass. They
are retained to show why these rows were initially held and how later evidence changed
the decision; they are not the release recommendation.

I recommend 6 `CONFIRM` decisions and 28 `KEEP_UNRESOLVED` decisions. I found no evidence sufficient for `REJECT/SPLIT`.

The six confirmations are five municipal/MPP Anthony Internicola continuities supported by his first-party campaign site (including the 2022 same-ward continuation from the confirmed 2021 council occurrence), and Willie Reodica's 2006 same-ward council continuation. Anthony Internicola's 2019 federal occurrence remains held: the official federal result proves the occurrence, but the first-party material located does not explicitly identify him as the 2019 People's Party candidate. Willie Reodica's 2023 mayoral occurrence is also held because it crosses from council to mayor without a first-party bridge.

The current release should therefore change `person_id` only for the six confirmed rows. All other rows should remain blank, with their existing `unresolved` history retained (the rationale can be updated to the evidence-specific rationale below). Vote totals, shares, ranks, elected flags, and outcomes do not change.

## Preliminary occurrence-level decisions (superseded)

`CONFIRM` means set `person_id` to the supplied target and change the disposition to `confirmed/high`. `KEEP_UNRESOLVED` means leave `person_id` blank and retain an explicit unresolved disposition. The “current” column is the exact current release/disposition state.

### Anthony Internicola — supplied target `per_7b66a05627cf557db879bb07990a8aa6`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_ff720c09d20c55ad85d5d9d941fb7b12` | 2018 Toronto council, Ward 23 | blank / unresolved-low | **CONFIRM** | The City result establishes the Ward 23 occurrence. Anthony's first-party site has a page explicitly titled “Past Campaign's 2014 & 2018 Toronto City Councillor Municipal Election,” identifying the same campaign/person across the 2014 anchor and 2018 occurrence ([S14](#s14)). No same-event collision. |
| `can_faf4051924815062b3907d7d5aa59010` | 2021 Toronto council by-election, Ward 22 | blank / unresolved-low | **CONFIRM** | Anthony's first-party campaign page identifies “Anthony INTERNICOLA” as the candidate for Toronto councillor in Scarborough-Agincourt, Ward 22 ([S14](#s14)); the City Clerk result establishes the occurrence ([S2](#s2)). This is an explicit self-identification bridge from the existing campaign identity. |
| `can_85a1b9a890cb57f0aa88d996133cb45f` | 2022 Toronto council, Ward 22 | blank / unresolved-low | **CONFIRM** | Same body, same office, same displayed Ward 22, same name, and no same-event collision. The official 2022 declaration and the 2021 Ward 22 declaration provide the matching district continuity ([S5](#s5), [S2](#s2)). |
| `can_0825ef06a4b555b4bb30a2f7e9e4d184` | 2023 Toronto council by-election, Ward 20 | blank / unresolved-low | **CONFIRM** | Anthony's first-party campaign site identifies “Candidate: Anthony INTERNICOLA” running for Toronto councillor in Ward 20 in the 2023 election ([S14](#s14)); the City Clerk declaration lists the occurrence ([S2](#s2)). The same first-party site also carries the prior campaign pages and the MPP identity, supplying the required bridge. |
| `can_e5b5388c503753a1a4ff9636316c72a1` | 2025 Ontario MPP, Scarborough—Guildwood | blank / unresolved-low | **CONFIRM** | Anthony's first-party site identifies “Anthony INTERNICOLA” as its Scarborough—Guildwood MPP candidate and carries the same Team Phoenix contact identity used on the municipal campaign pages ([S14](#s14)); Elections Ontario's official 2025 result files establish the occurrence ([S13](#s13)). |
| `can_e93f5ad6bae3581da052d5f6634f7c41` | 2019 House of Commons, Scarborough—Agincourt | blank / unresolved-low | **KEEP_UNRESOLVED** | Elections Canada establishes the 2019 PPC occurrence ([S12](#s12)), but I found no first-party source explicitly linking that federal candidacy to the municipal/MPP person. Same name and geography are not enough under the cross-office rule. |

### Daniel Trayes — supplied target `per_16a4d886ecfe59668937ad0291a82e3d`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_cb1965935fbb5c708a8c28e8f138282f` | 2021 Toronto council by-election, Ward 22 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the Ward 22 occurrence ([S2](#s2)). The target anchor is 2014 Ward 30; the district changed and no qualifying first-party bridge was found. |
| `can_d13a0869b0075217869233373f77fb51` | 2024 Toronto council by-election, Ward 15 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City Clerk result establishes the Ward 15 occurrence ([S2](#s2)). The 2014 anchor is Ward 30 and the intervening 2021 occurrence is Ward 22; no first-party identity bridge was located. |

### Huy Lieu — supplied target `per_fb1330040a9f58b2a6e7de8bae16bf3e`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_446014dfa14f56e7a4a75af7ab098dc9` | 2025 Toronto council by-election, Ward 25 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S2](#s2)); the target is a 2022 TCDSB Ward 9 trustee in the official Toronto results archive ([S18](#s18)). This is a cross-office link with no first-party bridge. |

### Nicki Ward — supplied target `per_a89824be70535923ae6dbc585cff3fc0`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_dcfe9a4846675145871f9087c3a5c005` | 2019 House of Commons, York South—Weston | blank / unresolved-low | **KEEP_UNRESOLVED** | Elections Canada establishes the occurrence ([S12](#s12)); the target anchor is 2018 Toronto council Ward 11. No first-party bridge from council to federal candidacy. |
| `can_2e95d69c77ed5130998c182d591c6c8a` | 2021 House of Commons, York South—Weston | blank / unresolved-low | **KEEP_UNRESOLVED** | Elections Canada establishes the occurrence ([S12](#s12)); cross-office identity remains unbridged. |
| `can_fba4d12130e3580dab26f538a5669f12` | 2022 Ontario MPP, Toronto Centre | blank / unresolved-low | **KEEP_UNRESOLVED** | Elections Ontario establishes the Green Party occurrence ([S13](#s13)); the Ontario Greens' nomination release identifies Nicki Ward as its Toronto Centre candidate ([S15](#s15)), but does not bridge her to the 2018 council or 2019/2021 federal candidacies. |
| `can_9a0249cc1c4053b280b20e9d5fa703ad` | 2022 Toronto council, Ward 13 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City declaration establishes the Ward 13 occurrence ([S5](#s5)). This is a cross-office link to the supplied 2018 council anchor only by name; no explicit first-party bridge was found. |

### Sheena Sharp — supplied target `per_4fb75ca0f2ba54879735652aa701181a`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_a2f7cfe910b15022984c8ecd48d5bf69` | 2022 Toronto council, Ward 15 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City declaration establishes the Ward 15 occurrence ([S5](#s5)). The Ontario Greens independently identify Sheena Sharp as their 2022 Don Valley West MPP candidate ([S16](#s16), [S19](#s19)), and her campaign site says she lives in Ward 15 ([S16](#s16)); however, neither first-party source explicitly states that the council and provincial candidacies are the same person. Hold under the cross-office rule. |
| `can_85f12ca63c63581ebf80d9710560d3c5` | 2024 Toronto council by-election, Ward 15 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S2](#s2)). Same Ward 15 continuity strongly supports a link to the 2022 council row, but the supplied Person is anchored in MPP candidacies and no explicit first-party cross-office bridge was found. |
| `can_c5c8fe730b8b567ea1a64839b752db62` | 2025 House of Commons, Don Valley West | blank / unresolved-low | **KEEP_UNRESOLVED** | Elections Canada establishes the federal occurrence ([S12](#s12)). The target's confirmed occurrences are Ontario MPP; no first-party source explicitly links the federal run to that Person. |

### Sabrina Zuniga — supplied target `per_ace9396f014150ff94149657a1e256ab`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_a1b147c5edd45d65a8b495e830bf5c81` | 2015 House of Commons, Spadina—Fort York | blank / unresolved-low | **KEEP_UNRESOLVED** | Elections Canada establishes the Conservative occurrence ([S12](#s12)); the target anchor is 2014 TDSB Ward 10 in the official Toronto results archive ([S18](#s18)). No first-party bridge. |
| `can_146bb6a90bec54569862f99cbb327e46` | 2018 Toronto council, Ward 10 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S1](#s1)); same displayed ward number is not enough to bridge from the TDSB trustee office. |
| `can_8ca2fe3ee27555b0ad486f10f4645d0d` | 2021 House of Commons, Don Valley North | blank / unresolved-low | **KEEP_UNRESOLVED** | Elections Canada establishes the occurrence ([S12](#s12)); this is a changed office and district with no explicit first-party bridge. |

### Luigi Lisciandro — supplied target `per_3194bffe8a495100879505eee54d1891`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_6f426cc8521d5180a8ed2e9d54644297` | 2022 Toronto council, Ward 21 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City declaration establishes the Ward 21 occurrence ([S5](#s5)); the confirmed anchor is 2014 Ward 37. Same office but changed ward, with no first-party bridge. |

### Willie Reodica — supplied target `per_8c27d890a1015ef28cfa3ff79384ef59`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_231ac513022254bca65c011eb4e87f40` | 2006 Toronto council, Ward 38 | blank / unresolved-low | **CONFIRM** | The City Clerk's 2006 declaration lists Willie Reodica in Ward 38 ([S3](#s3)), exactly matching the confirmed 2003 Ward 38 council anchor in body, office, and district. No same-event collision. |
| `can_c02fa9387c7857aba4dee1a4ab505441` | 2023 Toronto mayoral by-election | blank / unresolved-low | **KEEP_UNRESOLVED** | The City by-election results establish the mayoral occurrence ([S2](#s2)); the office changed from Ward 38 councillor to mayor and no first-party bridge was found. |

### Stella Kargiannakis — supplied target `per_a9fa93f9d3fa5bd7aa6054726c7faeeb`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_748f347a62d6572787e517fe49da020f` | 2014 Toronto council, Ward 20 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S1](#s1)); the target anchor is an Ontario MPP occurrence ([S19](#s19)) and the office changed. |
| `can_aa014c1fb1a855059c9784b9e8e42061` | 2017 Toronto council by-election, Ward 42 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City by-election results establish the occurrence ([S2](#s2)); changed ward and no first-party bridge to the MPP anchor ([S19](#s19)). |
| `can_ba76a75e1163519b9ab885118308a83d` | 2018 Toronto council, Ward 17 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S1](#s1)); changed office and district relative to the supplied MPP Person ([S19](#s19)). |
| `can_9de03d1a39345f93864f96aadbb9c6fb` | 2022 Toronto council, Ward 16 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City declaration establishes the occurrence ([S5](#s5)); the target's confirmed occurrence is Ontario MPP in the same broad area ([S19](#s19)) but a different office, and no explicit first-party bridge was located. |

### Naser Kaid — supplied target `per_022858fa191a541eaa442dd0e9cefd5d`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_7dcf344ea050543a953d55f4f26c6dca` | 2023 Toronto council by-election, Ward 20 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City declaration establishes the occurrence ([S2](#s2)); the confirmed anchor is TDSB trustee Ward 18 in the official Toronto results archive ([S18](#s18)), so this is cross-office and changed-district with no first-party bridge. |

### Diana Yoon — supplied target `per_9a0d84374b165724a2e8e92bdf92bfa5`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_d16ec7ae123b5ddd93726e119be6e0a2` | 2022 Toronto council, Ward 11 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City declaration establishes the occurrence ([S5](#s5)); the target anchor is a 2019 federal Spadina—Fort York candidacy. No first-party bridge across federal/council offices. |

### Zakir Patel — supplied target `per_353b9c4a63ac57ab9ee85eb011797754`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_d61ecb46f8f45feda51476da5f4af62b` | 2025 Toronto council by-election, Ward 25 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S2](#s2)). TDSB's first-party biography confirms Zakir Patel as Ward 19 trustee since 2018 ([S17](#s17)); the official 2022 archive also records that trustee occurrence ([S18](#s18)), but neither identifies him as the 2025 council candidate. Cross-office bridge not met. |

### Dianna Robinson — supplied target `per_726c6d2c05a559c7b78640513d4c5f43`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_57bff83947fe5a07a99a4ddf20349df1` | 2025 Toronto council by-election, Ward 25 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S2](#s2)); the target anchor is a 2022 TDSB trustee in Ward 22 in the official archive ([S18](#s18)). The unusual spelling is suggestive, but no first-party bridge was found. |

### Malik Ahmad — supplied target `per_1857a6857e5f556ab0c0424377838d56`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_d8fd23b509175a1080507d3ad0c821ef` | 2022 Toronto council, Ward 20 | blank / unresolved-medium | **KEEP_UNRESOLVED** | The City declaration establishes the occurrence ([S5](#s5)); the target anchor is 2010 Ward 35. The 12-year gap and changed ward require a first-party bridge that was not found. |
| `can_99bdda3c83d358cdba248a2411c0b039` | 2023 Toronto council by-election, Ward 20 | blank / unresolved-medium | **KEEP_UNRESOLVED** | The City declaration establishes the occurrence ([S2](#s2)). The 2022 and 2023 Ward 20 rows form a strong same-body/same-office pair, but that pair still has no qualifying bridge to the supplied 2010 Ward 35 Person. Do not promote either row without that bridge. |

### Jason Stevens — supplied target `per_2afc661b78b15020889552f8f43a6f89`

| Candidacy | Occurrence | Current | Recommendation | Evidence and rationale |
|---|---|---|---|---|
| `can_ece0a797928b509bb3aba62bdc67cb29` | 2024 Toronto council by-election, Ward 15 | blank / unresolved-medium | **KEEP_UNRESOLVED** | The City result establishes the occurrence ([S2](#s2)); the target anchor is 2010 council Ward 19. Same office but changed ward and a 14-year gap; no first-party bridge. |
| `can_81f3f0e725685fc6b289feee06fb735e` | 2025 TDSB trustee by-election, Ward 11 | blank / unresolved-low | **KEEP_UNRESOLVED** | The City by-election results page identifies the 2025 TDSB Ward 11 result ([S2](#s2)); this is cross-office from the 2010 council anchor, with no explicit first-party bridge. |

## Initial-pass contradictions and implementation notes (superseded where inconsistent)

1. The request's “high confidence” label is a prioritization hint, not identity evidence. Most high-confidence names have official occurrences but no first-party bridge across their changed wards or offices. Those rows should remain null rather than being bulk-merged.
2. The current ledger's generic low/medium rationales are directionally correct but understate the evidence-specific distinctions. Anthony's first-party site supports five listed municipal/MPP continuities; the 2019 federal row does not have the same bridge. Willie has one qualifying same-ward continuation and one unbridged mayoral row. Malik's two Ward 20 rows are mutually continuous but not bridged to the 2010 Ward 35 Person.
3. `REJECT/SPLIT` is not recommended for any row. There is no simultaneous same-event collision and no positive contrary evidence showing that a proposed occurrence belongs to a different person. “Keep unresolved” records insufficient proof without asserting that the people differ.
4. At the initial-pass stage this report did not authorize edits. The final adjudication above was
   subsequently implemented through the persistent disposition and release pipeline.

## Sources

### S1 — Toronto general-election results

[City of Toronto — Election Results, Reports & Documents](https://www.toronto.ca/city-government/elections/election-results-reports/) (official election and by-election results from 2003 to present).

### S2 — Toronto by-election results

[City of Toronto — By-Election Results](https://www.toronto.ca/city-government/elections/election-results-reports/election-results/by-election-results/) (official index for the 2021 Ward 22, 2023 Ward 20, 2023 mayor, 2024 Ward 15, 2025 Ward 25, and 2025 TDSB Ward 11 results). Direct declarations: [2021 Ward 22](https://www.toronto.ca/wp-content/uploads/2021/01/8e1c-Results_Official_Declaration_2021_By-Election_Ward-22.pdf), [2023 Ward 20](https://www.toronto.ca/wp-content/uploads/2023/12/94c0-Declaration-of-Results-for-the-Councillor-Ward-20-ByElection-Final.pdf), [2024 Ward 15](https://www.toronto.ca/wp-content/uploads/2024/11/9727-Declaration-of-Results-for-the-Councillor-Ward-15-ByElectionfor-posting.pdf), and [2025 Ward 25](https://www.toronto.ca/wp-content/uploads/2025/09/97f1-Declaration-of-Results-Councillor-Ward-25-ByElection.pdf).

### S3 — 2006 Toronto council declaration

[City Clerk's 2006 Official Declaration of Election Results](https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf).

### S5 — 2022 Toronto municipal declaration

[City Clerk's Declaration of Results for the 2022 Toronto Municipal Election](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf).

### S12 — Elections Canada

Official Elections Canada raw-result files: [2015](https://www.elections.ca/res/rep/off/ovr2015app/41/data_donnees/pollresults_resultatsbureau35.zip), [2019](https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip), [2021](https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip), and [2025](https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/pollresults_resultatsbureau35.zip).

### S13 — Elections Ontario

Official Elections Ontario result-report CSVs: [2025 report group 48](https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv), [2022 report group 45](https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv), and the [Elections Ontario publications portal](https://results.elections.on.ca/en/publications).

### S14 — Anthony Internicola first-party campaign site

[Past Campaign's 2014 & 2018 Toronto City Councillor Municipal Election](https://www.toronto4life.ca/2014--2018-toronto-city-councillor-municipal-election.html), [Ward 22 / MPP campaign platform](https://www.toronto4life.ca/our-platform.html), and [2023 Ward 20 election-sign page](https://www.toronto4life.ca/election-signs.html). These are candidate-controlled pages and are used only where they explicitly identify the candidate, office, ward/riding, or past campaign.

### S15 — Nicki Ward party source

[Ontario Greens — Nicki Ward nominated as Ontario Green candidate in Toronto Centre](https://gpo.ca/2021/12/17/nicki-ward-nominated-as-ontario-green-candidate-in-toronto-centre/).

### S16 — Sheena Sharp first-party/party sources

[Ontario Greens — Sheena Sharp nominated as Green Party candidate](https://gpo.ca/2021/06/02/sheena-sharp-nominated-as-green-party-candidate/) and [Sheena Sharp campaign biography](https://www.votesheenasharp.ca/about-sheena).

### S17 — Zakir Patel board biography

[Toronto District School Board — Trustee Bio: Zakir Patel](https://www.tdsb.on.ca/ward19/Ward-19/Trustee-Bio).

### S18 — Toronto official school-board result archives

[City of Toronto Open Data — elections official results dataset](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/elections-official-results), including the official [2014 results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip), [2018 results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip), and [2022 results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip).

### S19 — Elections Ontario historical reports

Official Elections Ontario CSV reports for the relevant historical provincial occurrences: [2007 report group 4](https://results.elections.on.ca/api/report-groups/4/report-outputs/510/csv) and [2022 report group 45](https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv).
