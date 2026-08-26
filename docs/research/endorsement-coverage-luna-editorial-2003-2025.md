# Toronto Star and Toronto Sun editorial-board coverage: 2003–2025

**Research date:** 2026-08-22  
**Scope:** the two institutional endorsers **Toronto Star Editorial Board** and **Toronto Sun Editorial Board**; Toronto mayor and Toronto City Councillor contests only; election events from 2003 through 2025.  
**Researcher:** Luna

## Result

This pass searched 24 previously open endorser × event × office batches. It found no new source-complete slate or explicit choice. It found three partial-positive lead batches:

1. Star, 2003 Ward 18: secondary attribution to Adam Giambrone.
2. Star, 2006 mayor: a bibliographic record identifying the editorial “Qualified support for David Miller.”
3. Sun, 2018 councillor: a publisher article and archive target, plus a secondary transcription of a complete 25-ward slate.

The 2018 Sun names are a retrieval lead, not import-ready endorsement facts: the publisher body and archived copy were not recoverable in this pass. The two Star leads likewise remain unconfirmed. The other searched batches are recorded as **searched with no positive found**. That disposition is a search result only; it is not a claim that an endorsement did not exist.

No code, reference CSV, or `data/out` file was edited. Contest and candidacy IDs below are read-only identity validation from the project outputs.

## Method and source rule

I read `data/out/endorsement_coverage.csv`, `endorsers.csv`, `contests.csv`, `election_events.csv`, and `endorsement_assertions.csv`, then reviewed the existing research reports in `docs/research/endorsement-*.md`. Existing `comprehensive_source_found` and `source_unavailable` cells were excluded from new searching. Trustee-only events (2012, January 2016, July 2016, January 2023, and March 2025) were excluded because the requested office set is mayor/councillor.

The search was event/source-set first. For each batch I searched the publisher target, archived publisher target where one was identified, exact event/date/ward terms, and reputable contemporaneous or local reporting. City Clerk results validate the event, office, ward, candidate name, contest ID, and candidacy ID; they do not prove an endorsement. A Wikipedia page, campaign biography, search snippet, or later forum page is retained only as a lead unless it preserves an attributable contemporaneous choice.

Disposition vocabulary in this report is intentionally narrower than the project ledger:

- **comprehensive source found** — a source presents a complete slate or explicit choice. Existing comprehensive cells are listed as exclusions below; none was newly recovered here.
- **partial positive leads** — a specific candidate, article, or slate is indicated, but the qualifying publisher/direct source is incomplete or inaccessible.
- **source unavailable** — the existing reports already identify the target source as inaccessible; it was not re-searched here.
- **searched with no positive found** — the defined source set was searched and no qualifying positive choice was found. This is not a negative endorsement fact.

## Existing cells deliberately excluded

These were not counted as new searches because the existing reports already provide the relevant status:

- **Comprehensive:** Star 2003 mayor; Star 2010 mayor and councillor; Sun 2010 mayor; Sun 2014 mayor; Star 2018 mayor; Sun 2018 mayor; Star 2022 mayor; and both boards’ 2023 mayoral by-election choices.
- **Source unavailable:** Star 2006 councillor; Star 2014 councillor; Star 2018 councillor; and Star 2022 councillor.

The earlier reports remain the source of those statuses and should be read together with this search certificate: [newspaper archive recovery](endorsement-newspaper-archive-recovery.md), [2003–2014 verification](endorsement-backfill-verification-2003-2014.md), and [2015–2026 verification](endorsement-backfill-verification-2015-2026.md).

## Batch search certificate

Each row below is one endorser × event × office batch actually searched in this pass. “No positive” means no qualifying positive choice was found in the named scope—not that the board made no endorsement.

| Event (date; ID) | Endorser | Office batch | Exact source/search scope | Disposition |
|---|---|---|---|---|
| 2003 general (2003-11-10; `evt_d89f777f34365c37b114ca39fb376591`) | Star | Councillor (44 wards) | Star 2003 Ward 18 title/date target; exact `Toronto Star` + ward/councillor/endorsement queries; Adam Giambrone biography/index; City 2003 results/declaration. | **partial positive leads** — Giambrone only; see lead table. |
| 2003 general (`evt_d89f777f34365c37b114ca39fb376591`) | Sun | Mayor | Exact Sun + Toronto + 2003 mayor/endorsement queries; 2003 election indexes and City results; no recoverable Sun mayoral editorial. | **searched with no positive found** |
| 2003 general (`evt_d89f777f34365c37b114ca39fb376591`) | Sun | Councillor (44 wards) | Exact Sun + Toronto + 2003 council/endorsement queries; 2003 election indexes and City results; no recoverable Sun council slate. | **searched with no positive found** |
| 2006 general (2006-11-13; `evt_159f073fa6f15c23a840651723d3c3af`) | Star | Mayor | Exact title “Qualified support for David Miller,” date 2006-11-10, A26; 2006 election references; City election report. | **partial positive leads** — article/date identified, body not recovered. |
| 2006 general (`evt_159f073fa6f15c23a840651723d3c3af`) | Sun | Mayor | Exact Sun + Toronto + 2006 mayor/endorsement queries; 2006 election references; City election report. | **searched with no positive found** |
| 2006 general (`evt_159f073fa6f15c23a840651723d3c3af`) | Sun | Councillor (44 wards) | Exact Sun + Toronto + 2006 council/endorsement queries; 2006 election references; City election report. | **searched with no positive found** |
| 2010 general (2010-10-25; `evt_5a786c1da7ec5e758036205f04351fc5`) | Sun | Councillor (44 wards) | Exact Sun + 2010 Toronto council endorsement/slate queries; publisher/archive target searches; City 2010 report. | **searched with no positive found** |
| 2014 general (2014-10-27; `evt_54673fd104ab5ef08eb865e162ac040c`) | Star | Mayor | Exact Star + 2014 Toronto mayor/editorial/endorsement queries; election references; City report. | **searched with no positive found** |
| 2014 general (`evt_54673fd104ab5ef08eb865e162ac040c`) | Sun | Councillor (44 wards) | Exact Sun + 2014 Toronto council/editorial/endorsement queries; publisher/archive target searches; local election coverage; City report. | **searched with no positive found** |
| 2016 Ward 2 by-election (2016-07-25; `evt_552c4874312956ae84afbbc5ee91b0f7`) | Star | Councillor, Ward 2 | Exact `Ward 2 by-election` + Star + endorsement/editorial terms; City candidate/results pages; CityNews contemporaneous coverage. | **searched with no positive found** |
| 2016 Ward 2 by-election (`evt_552c4874312956ae84afbbc5ee91b0f7`) | Sun | Councillor, Ward 2 | Exact `Ward 2 by-election` + Sun + endorsement/editorial terms; City candidate/results pages; CityNews contemporaneous coverage. | **searched with no positive found** |
| 2017 Ward 42 by-election (2017-02-13; `evt_b8284a5341635f79babdf7ddc512c2f6`) | Star | Councillor, Ward 42 | Exact `Ward 42 by-election` + Star + endorsement/editorial terms; City candidate/results pages; contemporaneous local coverage. | **searched with no positive found** |
| 2017 Ward 42 by-election (`evt_b8284a5341635f79babdf7ddc512c2f6`) | Sun | Councillor, Ward 42 | Exact `Ward 42 by-election` + Sun + endorsement/editorial terms; City candidate/results pages; contemporaneous local coverage. | **searched with no positive found** |
| 2018 general (2018-10-22; `evt_e4fe1909276b5fbd91057022b350fff3`) | Sun | Councillor (25 wards) | Exact publisher target and Wayback target; 2018 election page’s source references; Global News run-up coverage; Sean Marshall local ward attribution; City 2018 results. | **partial positive leads** — complete slate lead, article body inaccessible. |
| 2021 Ward 22 by-election (2021-01-15; `evt_50c15fe55fa753fba75abfada8da3c38`) | Star | Councillor, Ward 22 | Exact `Ward 22 by-election` + Star + endorsement/editorial terms; City candidate/results pages; contemporaneous local reporting. | **searched with no positive found** |
| 2021 Ward 22 by-election (`evt_50c15fe55fa753fba75abfada8da3c38`) | Sun | Councillor, Ward 22 | Exact `Ward 22 by-election` + Sun + endorsement/editorial terms; City candidate/results pages; contemporaneous local reporting. | **searched with no positive found** |
| 2022 general (2022-10-24; `evt_a52ef78967f05336bdb5d591fd50f122`) | Sun | Mayor | Exact Sun + 2022 Toronto mayor/editorial/endorsement queries; publisher/archive search; City report. Secondary “no endorsement” references were not treated as facts. | **searched with no positive found** |
| 2022 general (`evt_a52ef78967f05336bdb5d591fd50f122`) | Sun | Councillor (25 wards) | Exact Sun + 2022 Toronto council/editorial/endorsement queries; publisher/archive search; City report. Secondary “no endorsement” references were not treated as facts. | **searched with no positive found** |
| 2023 Ward 20 by-election (2023-11-30; `evt_ee5715a80b5a532c8b778d94f6b7c9b8`) | Star | Councillor, Ward 20 | Exact `Ward 20 by-election` + Star + endorsement/editorial terms; official City candidate list/results; CityNews coverage. | **searched with no positive found** |
| 2023 Ward 20 by-election (`evt_ee5715a80b5a532c8b778d94f6b7c9b8`) | Sun | Councillor, Ward 20 | Exact `Ward 20 by-election` + Sun + endorsement/editorial terms; official City candidate list/results; CityNews coverage. | **searched with no positive found** |
| 2024 Ward 15 by-election (2024-11-04; `evt_af73d490abf95ffdae38ca2c830e51f4`) | Star | Councillor, Ward 15 | Exact `Ward 15 by-election` + Star + endorsement/editorial terms; official City candidate/results pages; local news coverage. | **searched with no positive found** |
| 2024 Ward 15 by-election (`evt_af73d490abf95ffdae38ca2c830e51f4`) | Sun | Councillor, Ward 15 | Exact `Ward 15 by-election` + Sun + endorsement/editorial terms; official City candidate/results pages; local news coverage. | **searched with no positive found** |
| 2025 Ward 25 by-election (2025-09-29; `evt_ca435dada07f5ed9b041b7c3d24de732`) | Star | Councillor, Ward 25 | Exact `Ward 25 by-election` + Star + endorsement/editorial terms; official City candidate/results pages; local news coverage. | **searched with no positive found** |
| 2025 Ward 25 by-election (`evt_ca435dada07f5ed9b041b7c3d24de732`) | Sun | Councillor, Ward 25 | Exact `Ward 25 by-election` + Sun + endorsement/editorial terms; official City candidate/results pages; local news coverage. | **searched with no positive found** |

The 2023 June mayoral by-election (`evt_eabc9f0a14165449acd2f9a1e7d557ce`) is not in the new-search table because both board cells were already comprehensive in the existing reports. The same exclusion applies to the comprehensive general-election cells listed above.

## Candidate-level partial leads

These are candidate leads only. None should be imported as an endorsement assertion from this report alone.

### Toronto Star — 2003 Ward 18

| Candidate | Source date | Lead source | Contest ID | Candidacy ID | Qualification |
|---|---|---|---|---|---|
| Adam Giambrone | Not located; event 2003-11-10 | [Adam Giambrone biography](https://en.wikipedia.org/wiki/Adam_Giambrone), which attributes a Star endorsement alongside other outlets; the Star’s Ward 18 article target is identified in the existing recovery report but was not retrieved. | `con_4b3374ab9039564fa8ed1cedf493a0e3` | `can_82808b3e4f6e57b893db83438007ba68` | **Secondary lead only.** No original Star copy or qualifying contemporaneous direct attribution. |

### Toronto Star — 2006 mayor

| Candidate | Source date | Lead source | Contest ID | Candidacy ID | Qualification |
|---|---|---|---|---|---|
| David Miller | 2006-11-10 | [2006 Toronto municipal election references](https://en.wikipedia.org/wiki/2006_Toronto_municipal_election), identifying “Qualified support for David Miller,” *Toronto Star*, A26. The City report validates the contest and candidate. | `con_5d8609e7e7f4584ea28ad032690bdae8` | `can_60df17cf5ac95996aad15c760e40ee19` | **Bibliographic retrieval lead.** The title/date are strong, but the editorial body and exact positive-choice language were not recovered. |

### Toronto Sun — 2018 councillor slate

The primary target is [“Toronto Sun endorsements for city council”](https://torontosun.com/news/local-news/toronto-sun-endorsements-for-city-council), dated 2018-10-21. The identified archive target is [Wayback](https://web.archive.org/web/20181217120114/https://torontosun.com/news/local-news/toronto-sun-endorsements-for-city-council). The 2018 election page cites that article and archive in its source references ([Wikipedia source page](https://en.wikipedia.org/wiki/2018_Toronto_municipal_election)). Direct Sun/Wayback retrieval was blocked or returned a cache miss, so the following is a **secondary transcription/retrieval lead**, not a confirmed slate. Ward 20 has two names and must remain two separate candidate leads.

| Ward | Candidate | Contest ID | Candidacy ID |
|---:|---|---|---|
| 1 | Michael Ford | `con_922d425132ad5243b459c0ca40a6dcd9` | `can_b52f6554caab5bc08b7deca203ffd5d5` |
| 2 | Stephen Holyday | `con_3fc9df4b254c5eb6a2a7fb629a124bfb` | `can_02d0984005935af0b592f3ad185eff48` |
| 3 | Mark Grimes | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_881b56db387e50b19b0aa61d56b09724` |
| 4 | Evan Tummillo | `con_f961284da53f5a38ba3a20e7e998ef4f` | `can_b6b790f30421564ca2e9c8263737a42e` |
| 5 | Frances Nunziata | `con_ac347f98e5715159b3adecf8debcbde8` | `can_8c722fdcbad151f7a215974077dcdcbb` |
| 6 | James Pasternak | `con_849867f583195ad38c77941612883bd9` | `can_56769676131c5f708884abdfea79deef` |
| 7 | Giorgio Mammoliti | `con_990816d2030b592787bdf4a19382627f` | `can_0b38c9e9981f56af8bccc1f2eb6c2c82` |
| 8 | Christin Carmichael Greb | `con_caa23fae586656b2bab11ee711073a2c` | `can_6f92d616fbc254aa87d1296422abbdae` |
| 9 | Ana Bailão | `con_55f5230db0d85c499ce7cea0ce379f5f` | `can_a9d93ea575e9511aad1985615dbd47f9` |
| 10 | Kevin Vuong | `con_2865d31031005dd897904c3f07e4d039` | `can_28eb19db01df5e0489bf5730e980a2b0` |
| 11 | Joyce Rowlands | `con_810611751acb5e86ab30b3277e7e6dad` | `can_2be6eb5c966a5c3e922215053eac8307` |
| 12 | Joe Mihevc | `con_8b4a03ef5a3c55c4ab20662c886b31a7` | `can_daba066aa91d57bb8ac1116dacf2f2bc` |
| 13 | Lucy Troisi | `con_3a43982e2a0450b2a3f4c5241f6965d8` | `can_b3ceb20f257e54d18f21388390a466ec` |
| 14 | Mary Fragedakis | `con_1b8d99f619f758efb737805a20bcf6fb` | `can_a0c2320659e855448b8aa28f1740d5bd` |
| 15 | Jaye Robinson | `con_6a1f4d7470675d869b3b11aede0812f2` | `can_365f117d8c1a5b0097b2c1b3414d99dd` |
| 16 | Denzil Minnan-Wong | `con_147dca9e3758595d8766dc52d11a65f4` | `can_f9ea8f5f2f22545b961d7d1aebffe984` |
| 17 | Christina Liu | `con_7a4043e26d4256e78ee3861fb81e718a` | `can_a6628f45e8ae5f50a48d6645d8d8646f` |
| 18 | Sam Moini | `con_4def6d4e85f85950babb9030e4eae0cb` | `can_fafe793aa442549aa62e15c5f44bc07f` |
| 19 | Brad Bradford | `con_45eb3e143f1b5492b4652498c957ed6b` | `can_aeb469c9e30b5f37a4f25f6a757d2ca4` |
| 20 | Gary Crawford | `con_6fd864aec40c5bbc9f3eb32d2e9e4379` | `can_709e43151ddd5089b8c98b7291f7a5ca` |
| 20 | Michelle Holland-Berardinetti | `con_6fd864aec40c5bbc9f3eb32d2e9e4379` | `can_156a9ea4f7dc57baa65c20af16ff5205` |
| 21 | Michael Thompson | `con_16fad19349255393a28639cd62e83ae3` | `can_44edb32c95a155788c97ba51aab252a9` |
| 22 | Norm Kelly | `con_c555f2e9b45051a8b960bdbb0ac6080a` | `can_4185e2b2d994537280b8eae979cfdaec` |
| 23 | Cynthia Lai | `con_c85783d7c9a4550bae21b8e14f2ff992` | `can_736c4515a83c5c4d99d7bbb1acdd5f7a` |
| 24 | Paul Ainslie | `con_7e6cf2fd75ba560a900bb024e72fe99c` | `can_a138036d836c5c8da46d76df542f931f` |
| 25 | Jennifer McKelvie | `con_eeda9883ca2d57148405d41f7f5a80a4` | `can_76a5898fec8b5e3983638f5c9354afe3` |

The slate has one independent local corroborating lead: Sean Marshall’s [Ward 4 race page](https://seanmarshall.ca/2018/12/26/mapping-the-results-in-ward-4-parkdale-high-park-and-ward-9-davenport/comment-page-1/) attributes Evan Tummillo to the Sun. That page is not the publisher editorial and is retained only as corroboration of the candidate-level lead.

## Counts and handoff

- New batches searched: **24**.
- New comprehensive sources found: **0**.
- Partial-positive lead batches: **3**.
- Searched with no positive found: **21**.
- New source-unavailable determinations: **0**; existing source-unavailable cells were deliberately excluded.
- Candidate-level Sun slate lead rows: **26** (25 wards, with two Ward 20 names).

Next recovery targets are the original Star print/editorial bodies for 2003 Ward 18 and 2006 mayor, and the 2018 Sun article (publisher or library/newspaper archive). Until those are captured, keep all rows in this report out of the importable endorsement assertion set.
