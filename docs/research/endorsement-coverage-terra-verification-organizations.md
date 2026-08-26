# Verification of organizational endorsement coverage, 2003–2025

**Verification date:** 2026-08-22  
**Scope:** Luna's ETT, ATU Local 113, Progress Toronto, and CUPE Ontario historical research report.  
**Rule applied:** an Endorsement is a positive, pre-poll electoral choice by the *exact* approved entity. Absence of a fact is never a negative. A direct choice supplies `comprehensive_source_found` for that one Contest; it does not make an event-wide slate comprehensive unless the source itself establishes the slate.

## Verdict

The two Progress Toronto leads are confirmed, not merely plausible:

| Import recommendation | Exact fact | Evidence and reason |
|---|---|---|
| **CONFIRM** | Progress Toronto → Amber Morley, 2018 Ward 3 (`con_612115bf42b450d3aeb63bb430d3aec9`; `can_a4e55da62ed2509cb497ad0bfd65c11f`) | Progress Toronto's dated **October 4, 2018** [Campaign Action Plan](https://www.progresstoronto.ca/updates/2018/11/7/campaign-action-plan) says volunteers told voters Morley was the best candidate and prepared supporters to “vote Morley” on October 22. This is direct, pre-poll, first-party support. Suggested curation: `progress_2018_w03_morley`; `endorsement`; `2018-10-04`; `day`; `first_party_campaign`. |
| **CONFIRM** | Progress Toronto → Manna Wong, 2021 Ward 22 (`con_53468b4ee3c7510aba4d708f584951a9`; `can_f9f7d971b99c52cf9a48edf7b1dd38ba`) | The dated **December 15, 2020** [Progress Toronto announcement](https://www.progresstoronto.ca/updates/2020/12/15/by-election-update-manna-wong-is-our-progressive-champion) calls Wong its “Progressive Champion” and says it will work hard to elect her. The related [volunteer page](https://www.progresstoronto.ca/byelection-volunteer) independently says Progress Toronto was campaigning to elect her in the January 15, 2021 by-election. Suggested curation: `progress_2021_w22_wong`; `progressive_champion`; `2020-12-15`; `day`; `first_party_campaign`. |
| **KEEP UNRESOLVED** | claimed CUPE Ontario → David Miller, 2003 mayor (`con_945161409a0450f29e351ff3f263f815`; `can_63e1ea224f9a5132ae24d181a6bd7ca2`) | The material found only identifies “CUPE” or labour support. It does not establish the approved entity **CUPE Ontario**. The first-party [2006 CUPE Ontario item](https://cupe.on.ca/d307/gloves-off-jane-mayoral) attacks Jane Pitfield but names no positive mayoral choice; it cannot bridge the 2003 entity ambiguity. Do not load a fact. |

## Materially new recovery: ATU Local 113's 2018 council list

Luna's report missed a first-party Local 113 PDF, [**Endorsed Municipal Candidate Contacts**](https://wemovetoronto.ca/wp-content/uploads/2018/10/ATU-Local-113_Endorsed-Candidates.pdf). Its first-party host, title, `2018/10` path, and pre-poll candidate contact/mobilization content establish a Local 113 2018 municipal endorsement list. The document explicitly labels itself an endorsed-candidate list. The ward-20 note explicitly says Suman Roy was **not** officially endorsed, so he is excluded rather than converted into a negative fact.

The following 16 direct facts are ready to import, with an October 2018 announcement date at **month** precision (use `2018-10-01`, `month`, and `first_party_slate` unless a day-specific capture is recovered):

| Ward | Candidate | Contest ID | Candidacy ID |
|---:|---|---|---|
| 3 | Amber Morley | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_a4e55da62ed2509cb497ad0bfd65c11f` |
| 4 | Gord Perks | `con_f961284da53f5a38ba3a20e7e998ef4f` | `can_f016d26c42dc5073b6e91d974223d0a7` |
| 5 | Lekan Olawoye | `con_ac347f98e5715159b3adecf8debcbde8` | `can_467ce1971c8b595a88cebb67edda463a` |
| 6 | Maria Augimeri | `con_849867f583195ad38c77941612883bd9` | `can_4eec1f4fc03c5c2192fa031a86b3420d` |
| 7 | Anthony Perruzza | `con_990816d2030b592787bdf4a19382627f` | `can_6dfeac63c0665cf483c6ac6a4934541e` |
| 9 | Ana Bailão | `con_55f5230db0d85c499ce7cea0ce379f5f` | `can_a9d93ea575e9511aad1985615dbd47f9` |
| 10 | Joe Cressy | `con_2865d31031005dd897904c3f07e4d039` | `can_c17e828fbf045e0087095cfa28321105` |
| 11 | Mike Layton (listed as “Michael Layton”) | `con_810611751acb5e86ab30b3277e7e6dad` | `can_aa928563d472570d901401bff637b922` |
| 12 | Joe Mihevc | `con_8b4a03ef5a3c55c4ab20662c886b31a7` | `can_daba066aa91d57bb8ac1116dacf2f2bc` |
| 13 | Kristyn Wong-Tam | `con_3a43982e2a0450b2a3f4c5241f6965d8` | `can_c370bbf8fd765d9694fd4f089ba3d462` |
| 14 | Paula Fletcher | `con_1b8d99f619f758efb737805a20bcf6fb` | `can_d7591ea7a10b549e97f6a6ec33e194d6` |
| 17 | Shelley Carroll | `con_7a4043e26d4256e78ee3861fb81e718a` | `can_577ddf8125b85bf18e731f150dca4600` |
| 18 | Saman Tabasi Nejad | `con_4def6d4e85f85950babb9030e4eae0cb` | `can_bd1df746d51c51459c672d68456dc7e6` |
| 19 | Matthew Kellway | `con_45eb3e143f1b5492b4652498c957ed6b` | `can_8702c409b44c56869788d0fcb7ee8999` |
| 23 | Felicia Samuel | `con_c85783d7c9a4550bae21b8e14f2ff992` | `can_cd24b1b0a226537e8e6a4cc6ad03981a` |
| 25 | Neethan Shan | `con_c8883aeeac29529eada91aebc451242b` | `can_2a0745629be0507080db6d72f4a6719b` |

One identity normalization needs no fuzzy match: the Local 113 PDF says **Saman Tabasinejad**; the City's [2018 financial-disclosure record](https://secure.toronto.ca/EFD/jsf/candidate2018/candidate_campaign_status.xhtml?campaign=15) gives the Ward 18 candidate as **Tabasi Nejad, Saman**, which is the same name order/spelling represented by the cited Candidacy.

This source is sufficient for `comprehensive_source_found` for each listed contest under the project's one-endorsement-per-Contest rule. It is *not* sufficiently explicit to turn the other nine 2018 council Contests into negatives; retain those as `partially_searched`.

## Machine-actionable batch decisions

`C` means the full council source set named in the row. A `C [wards]` row is a necessary contest-level split, because coverage is published at Endorser × Contest grain. “Excluded/current” means that a source batch was already made comprehensive by an earlier curation and is not changed by this verification.

### Progress Toronto

| Event | Office / Contest split | Coverage state | Action |
|---|---|---|---|
| 2003-11-10 | Mayor | `not_applicable` | No organization/process before 2018. |
| 2003-11-10 | C, 44 wards | `not_applicable` | Same. |
| 2006-11-13 | Mayor | `not_applicable` | Same. |
| 2006-11-13 | C, 44 wards | `not_applicable` | Same. |
| 2010-10-25 | Mayor | `not_applicable` | Same. |
| 2010-10-25 | C, 44 wards | `not_applicable` | Same. |
| 2014-10-27 | Mayor | `not_applicable` | Same. |
| 2014-10-27 | C, 44 wards | `not_applicable` | Same. |
| 2016-07-25 | C, Ward 2 | `not_applicable` | Same. |
| 2017-02-13 | C, Ward 42 | `not_applicable` | Same. |
| 2018-10-22 | Mayor | `partially_searched` | Exact-entity campaign pages checked; no direct mayoral choice recovered. |
| 2018-10-22 | C, Ward 3 | `comprehensive_source_found` | Import Morley fact above. |
| 2018-10-22 | C, Wards 1–2 and 4–25 | `partially_searched` | Action-plan search is not a complete named slate. |
| 2021-01-15 | C, Ward 22 | `comprehensive_source_found` | Import Wong fact above. |
| 2023-11-30 | C, Ward 20 | `partially_searched` | Exact-entity search logged; recovered training material is not an endorsement. |

The pre-2018 determination is independently supported by Progress Toronto's own [2023 process account](https://www.progresstoronto.ca/media-release-may10-progressive-mayoral-champions), which says its public champion process has run in every election since 2018, and by its [2022 account](https://www.progresstoronto.ca/2022-election-results-history), which says the organization was founded in 2018.

### Elementary Teachers of Toronto (ETT)

All 15 logged ETT batches are `partially_searched`, **not** `source_unavailable`. Luna recorded real exact-entity/site and archive work, but neither that report nor this verification establishes that a known, bounded ETT municipal source set is unavailable. This is the honest middle state: work happened; a complete slate/choice source was not recovered.

| Event | Office / source set | State |
|---|---|---|
| 2003-11-10 | Mayor; C, 44 wards | `partially_searched`; `partially_searched` |
| 2006-11-13 | Mayor; C, 44 wards | `partially_searched`; `partially_searched` |
| 2010-10-25 | Mayor; C, 44 wards | `partially_searched`; `partially_searched` |
| 2014-10-27 | C, 44 wards | `partially_searched` |
| 2016-07-25 | C, Ward 2 | `partially_searched` |
| 2017-02-13 | C, Ward 42 | `partially_searched` |
| 2018-10-22 | C, 25 wards | `partially_searched` |
| 2022-10-24 | Mayor; C, 25 wards | `partially_searched`; `partially_searched` |
| 2023-11-30 | C, Ward 20 | `partially_searched` |
| 2024-11-04 | C, Ward 15 | `partially_searched` |
| 2025-09-29 | C, Ward 25 | `partially_searched` |

The excluded ETT 2014 mayor, 2018 mayor, 2021 Ward 22, and 2023 mayor facts remain as previously curated; the 2021 result is independently first-party corroborated by [ETT's dated Wong endorsement](https://ett.ca/ett-endorses-manna-wong-in-scarborough-agincourt-city-council-by-election/).

### ATU Local 113

| Event | Office / Contest split | Coverage state | Action |
|---|---|---|---|
| 2003-11-10 | Mayor; C, 44 wards | `partially_searched`; `partially_searched` | Archive search logged, without a bounded unavailable source set. |
| 2006-11-13 | Mayor; C, 44 wards | `partially_searched`; `partially_searched` | Same. |
| 2010-10-25 | Mayor; C, 44 wards | `partially_searched`; `partially_searched` | Same. |
| 2014-10-27 | Mayor; C, 44 wards | `partially_searched`; `partially_searched` | Same; post-poll policy material is not a choice. |
| 2016-07-25 | C, Ward 2 | `partially_searched` | No qualifying choice recovered. |
| 2017-02-13 | C, Ward 42 | `partially_searched` | No qualifying choice recovered. |
| 2018-10-22 | Mayor | `partially_searched` | No mayoral choice in the recovered council document. |
| 2018-10-22 | C, Wards 3, 4, 5, 6, 7, 9–14, 17–19, 23, 25 | `comprehensive_source_found` | Import the 16 facts above. |
| 2018-10-22 | C, Wards 1, 2, 8, 15, 16, 20–22, 24 | `partially_searched` | Do not derive negatives from omitted names or the explicit Suman Roy near-miss. |
| 2021-01-15 | C, Ward 22 | `partially_searched` | No qualifying choice recovered. |
| 2022-10-24 | Mayor | `partially_searched` | Existing Council slate is not mayoral evidence. |
| 2024-11-04 | C, Ward 15 | `partially_searched` | No qualifying choice recovered. |
| 2025-09-29 | C, Ward 25 | `partially_searched` | No qualifying choice recovered in this pass. |

The existing 2022 council, 2023 mayor, and 2023 Ward 20 comprehensive cells remain unchanged.

### CUPE Ontario

**Implementation update (2026-08-22):** the user clarified that every approved panel Endorser is
applicable to both Mayor and City Councillor Contests. That scope decision does not infer any
positive choice or completed search. The audited Council work below is therefore recorded as
`partially_searched`, except the independently verified 2025 Ward 25 choice, which is
`comprehensive_source_found` for that single Contest.

| Event | Office / source set | State | Action |
|---|---|---|---|
| 2003-11-10 | Mayor | `partially_searched` | Miller remains unresolved; no exact-entity fact. |
| 2003-11-10 | C, 44 wards | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2006-11-13 | Mayor | `partially_searched` | Pitfield opposition is not a positive choice. |
| 2006-11-13 | C, 44 wards | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2010-10-25 | C, 44 wards | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2014-10-27 | Mayor | `partially_searched` | No direct CUPE Ontario choice recovered. |
| 2014-10-27 | C, 44 wards | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2016-07-25 | C, Ward 2 | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2017-02-13 | C, Ward 42 | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2018-10-22 | Mayor | `partially_searched` | Bill 5 advocacy is not a candidate choice. |
| 2018-10-22 | C, 25 wards | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2021-01-15 | C, Ward 22 | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2022-10-24 | Mayor | `partially_searched` | No direct CUPE Ontario choice recovered. |
| 2022-10-24 | C, 25 wards | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2023-11-30 | C, Ward 20 | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2024-11-04 | C, Ward 15 | `partially_searched` | Audited exact-entity Council search; no complete slate or choice source recovered. |
| 2025-09-29 | C, Ward 25 | `comprehensive_source_found` | Exact first-party CUPE Ontario choice verified in the hold-recovery pass. |

### CUPE Ontario Ward 25 evidence recovery

CUPE Ontario's own [Ward 25 page](https://cupe.on.ca/shanforscarborough/) explicitly says it is proud to endorse Neethan Shan for Toronto City Council. The independently verified hold-recovery pass corrected the stale 2018 locator and established a pre-poll first-party publication date. The import uses `con_c8883aeeac29529eada91aebc451242b` / `can_2a0745629be0507080db6d72f4a6719b`, not the 2018 keys shown in the original discovery memo.

## Summary for implementation

- Import **18** verified positive facts: two Progress Toronto facts and sixteen ATU Local 113 facts.
- Keep CUPE Ontario → David Miller **unresolved**; do not turn generic CUPE/labour references into CUPE Ontario.
- Do **not** use `source_unavailable` for the early ETT/ATU rows solely because no source was recovered. The auditable result is `partially_searched`.
- Record the audited CUPE Council search work as partial coverage, and record the verified Ward 25 Shan choice as a single-contest comprehensive source; neither conclusion creates candidate-level negatives.
