# Independent verification: Toronto Star and Toronto Sun editorial-board coverage, 2003–2025

**Research date:** 2026-08-22  
**Verifier:** Terra  
**Scope:** Toronto Star Editorial Board and Toronto Sun Editorial Board; Toronto mayor and City Councillor contests; the 24 endorser × event × office batches reviewed in `endorsement-coverage-luna-editorial-2003-2025.md`.

## Decision

One Luna lead clears the fact-import gate: the **Toronto Sun's 2018 council editorial**. The publisher page is currently recoverable, is dated October 21 (before the October 22 poll), calls itself "Toronto Sun endorsements for city council," and says, "Here are the candidates running for city council who we endorse." It lists 13 candidates.

The two Star leads do **not** clear the gate:

- Adam Giambrone's 2003 Ward 18 attribution is only a Wikipedia biography/index. It is not a recovered Star item or reputable contemporaneous direct attribution.
- The identified 2006 Star title, *Qualified support for David Miller*, is a strong retrieval target, but the available bibliographic/index citation does not preserve the editorial or provide qualifying direct attribution. The title alone should not be imported.

The original Sun page also corrects a consequential extraction error in the Luna report: its secondary 26-name list is not the publisher's slate. The original page contains **13**, not 26, candidate choices. The other 13 listed in Luna's secondary transcription must not be imported; their absence from the recovered list is not a negative fact.

## Confirmed facts: Toronto Sun, 2018 council

**Endorser key:** `toronto_sun_editorial_board`  
**Election event:** 2018 general election, 2018-10-22, `evt_e4fe1909276b5fbd91057022b350fff3`  
**Assertion date:** 2018-10-21 (`day`)  
**Kind:** `editorial_choice`  
**Source type:** `publisher_editorial`  
**Primary source:** [Toronto Sun, “Toronto Sun endorsements for city council” (2018-10-21)](https://torontosun.com/news/local-news/toronto-sun-endorsements-for-city-council)

| Ward | Candidate as published | Candidate as stored | Contest ID | Candidacy ID |
|---:|---|---|---|---|
| 1 | Michael Ford | Michael Ford | `con_922d425132ad5243b459c0ca40a6dcd9` | `can_b52f6554caab5bc08b7deca203ffd5d5` |
| 2 | Stephen Holyday | Stephen Holyday | `con_3fc9df4b254c5eb6a2a7fb629a124bfb` | `can_02d0984005935af0b592f3ad185eff48` |
| 3 | Mark Grimes | Mark Grimes | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_881b56db387e50b19b0aa61d56b09724` |
| 4 | Evan Tummillo | Evan Tummillo | `con_f961284da53f5a38ba3a20e7e998ef4f` | `can_b6b790f30421564ca2e9c8263737a42e` |
| 5 | Frances Nunziata | Frances Nunziata | `con_ac347f98e5715159b3adecf8debcbde8` | `can_8c722fdcbad151f7a215974077dcdcbb` |
| 6 | James Pasternak | James Pasternak | `con_849867f583195ad38c77941612883bd9` | `can_56769676131c5f708884abdfea79deef` |
| 8 | Christin Carmichael Greb | Greb Christin Carmichael | `con_caa23fae586656b2bab11ee711073a2c` | `can_6f92d616fbc254aa87d1296422abbdae` |
| 17 | Christina Liu | Christina Liu | `con_7a4043e26d4256e78ee3861fb81e718a` | `can_a6628f45e8ae5f50a48d6645d8d8646f` |
| 18 | Sam Moini | Sam Moini | `con_4def6d4e85f85950babb9030e4eae0cb` | `can_fafe793aa442549aa62e15c5f44bc07f` |
| 21 | Michael Thompson | Michael Thompson | `con_16fad19349255393a28639cd62e83ae3` | `can_44edb32c95a155788c97ba51aab252a9` |
| 23 | Cynthia Lai | Cynthia Lai | `con_c85783d7c9a4550bae21b8e14f2ff992` | `can_736c4515a83c5c4d99d7bbb1acdd5f7a` |
| 24 | Paul Ainslie | Paul Ainslie | `con_7e6cf2fd75ba560a900bb024e72fe99c` | `can_a138036d836c5c8da46d76df542f931f` |
| 25 | Jennifer McKelvie | Jennifer Mckelvie | `con_eeda9883ca2d57148405d41f7f5a80a4` | `can_76a5898fec8b5e3983638f5c9354afe3` |

The source is an event-wide council endorsement list, so `toronto_sun_editorial_board` × 2018-10-22 × `councillor` may be marked `comprehensive_source_found`. This says a source that purports to list its endorsed council candidates was located. It does **not** create non-endorsement facts for other candidacies.

### Explicitly rejected secondary-transcription rows

The following rows appeared in Luna's 26-name secondary transcription but are not present in the recovered publisher list: Giorgio Mammoliti (Ward 7), Ana Bailão (9), Kevin Vuong (10), Joyce Rowlands (11), Joe Mihevc (12), Lucy Troisi (13), Mary Fragedakis (14), Jaye Robinson (15), Denzil Minnan-Wong (16), Brad Bradford (19), Gary Crawford and Michelle Holland-Berardinetti (20), and Norm Kelly (22). Do not import them. This is not evidence that the Sun opposed, or did not endorse, any of them outside the representation made by this recovered editorial.

## Holds

| Proposed fact | Decision | Reason | Retrieval source |
|---|---|---|---|
| Star → Adam Giambrone, 2003 Ward 18, `can_82808b3e4f6e57b893db83438007ba68` | **HOLD** | The surviving lead is an encyclopedia biography. It is neither a Star editorial nor reputable contemporaneous direct attribution. | [Adam Giambrone biography](https://en.wikipedia.org/wiki/Adam_Giambrone); recovery target described in [newspaper archive recovery](endorsement-newspaper-archive-recovery.md#toronto-star-2003-ward-18--adam-giambrone). |
| Star → David Miller, 2006 mayor, `can_60df17cf5ac95996aad15c760e40ee19` | **HOLD** | The bibliographic index identifies a Nov. 10 editorial title, but does not preserve the item or qualify as direct attribution under the project source gate. | [Index preserving the citation](https://en-academic.com/dic.nsf/enwiki/5061563/); recovery target in [newspaper archive recovery](endorsement-newspaper-archive-recovery.md#toronto-star-2006-mayor--david-miller). |

## Machine-actionable coverage decisions

All decisions below are at endorser × event × office grain. `partially_searched` records the bounded search work; it makes no negative candidate-level claim. No new `source_unavailable` decision is warranted because this verification either recovered the source (Sun 2018 council) or has a documented, bounded search log rather than an identified inaccessible source that is central to the decision.

| endorser_key | election_date | event_id | office_type | coverage_state | coverage_basis |
|---|---|---|---|---|---|
| `toronto_star_editorial_board` | 2003-11-10 | `evt_d89f777f34365c37b114ca39fb376591` | councillor | `partially_searched` | Ward 18 lead checked; only unqualified secondary attribution recovered. |
| `toronto_sun_editorial_board` | 2003-11-10 | `evt_d89f777f34365c37b114ca39fb376591` | mayor | `partially_searched` | Bounded publisher/index search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2003-11-10 | `evt_d89f777f34365c37b114ca39fb376591` | councillor | `partially_searched` | Bounded publisher/index search logged; no importable positive recovered. |
| `toronto_star_editorial_board` | 2006-11-13 | `evt_159f073fa6f15c23a840651723d3c3af` | mayor | `partially_searched` | Miller bibliographic lead checked; original/direct attribution not recovered. |
| `toronto_sun_editorial_board` | 2006-11-13 | `evt_159f073fa6f15c23a840651723d3c3af` | mayor | `partially_searched` | Bounded publisher/index search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2006-11-13 | `evt_159f073fa6f15c23a840651723d3c3af` | councillor | `partially_searched` | Bounded publisher/index search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2010-10-25 | `evt_5a786c1da7ec5e758036205f04351fc5` | councillor | `partially_searched` | Bounded publisher/archive search logged; no importable positive recovered. |
| `toronto_star_editorial_board` | 2014-10-27 | `evt_54673fd104ab5ef08eb865e162ac040c` | mayor | `partially_searched` | Bounded publisher/index search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2014-10-27 | `evt_54673fd104ab5ef08eb865e162ac040c` | councillor | `partially_searched` | Bounded publisher/archive search logged; no importable positive recovered. |
| `toronto_star_editorial_board` | 2016-07-25 | `evt_552c4874312956ae84afbbc5ee91b0f7` | councillor | `partially_searched` | Ward 2 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2016-07-25 | `evt_552c4874312956ae84afbbc5ee91b0f7` | councillor | `partially_searched` | Ward 2 by-election search logged; no importable positive recovered. |
| `toronto_star_editorial_board` | 2017-02-13 | `evt_b8284a5341635f79babdf7ddc512c2f6` | councillor | `partially_searched` | Ward 42 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2017-02-13 | `evt_b8284a5341635f79babdf7ddc512c2f6` | councillor | `partially_searched` | Ward 42 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2018-10-22 | `evt_e4fe1909276b5fbd91057022b350fff3` | councillor | `comprehensive_source_found` | Recovered publisher editorial lists its city-council choices. |
| `toronto_star_editorial_board` | 2021-01-15 | `evt_50c15fe55fa753fba75abfada8da3c38` | councillor | `partially_searched` | Ward 22 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2021-01-15 | `evt_50c15fe55fa753fba75abfada8da3c38` | councillor | `partially_searched` | Ward 22 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2022-10-24 | `evt_a52ef78967f05336bdb5d591fd50f122` | mayor | `partially_searched` | Bounded publisher/archive search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2022-10-24 | `evt_a52ef78967f05336bdb5d591fd50f122` | councillor | `partially_searched` | Bounded publisher/archive search logged; no importable positive recovered. |
| `toronto_star_editorial_board` | 2023-11-30 | `evt_ee5715a80b5a532c8b778d94f6b7c9b8` | councillor | `partially_searched` | Ward 20 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2023-11-30 | `evt_ee5715a80b5a532c8b778d94f6b7c9b8` | councillor | `partially_searched` | Ward 20 by-election search logged; no importable positive recovered. |
| `toronto_star_editorial_board` | 2024-11-04 | `evt_af73d490abf95ffdae38ca2c830e51f4` | councillor | `partially_searched` | Ward 15 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2024-11-04 | `evt_af73d490abf95ffdae38ca2c830e51f4` | councillor | `partially_searched` | Ward 15 by-election search logged; no importable positive recovered. |
| `toronto_star_editorial_board` | 2025-09-29 | `evt_ca435dada07f5ed9b041b7c3d24de732` | councillor | `partially_searched` | Ward 25 by-election search logged; no importable positive recovered. |
| `toronto_sun_editorial_board` | 2025-09-29 | `evt_ca435dada07f5ed9b041b7c3d24de732` | councillor | `partially_searched` | Ward 25 by-election search logged; no importable positive recovered. |

## Net handoff

- Import **13** confirmed `toronto_sun_editorial_board` assertions, all for 2018 council, using the source/date above.
- Set Sun 2018 councillor coverage to `comprehensive_source_found`.
- Set the other 23 listed batches to `partially_searched` with a reference to this verification and the Luna search certificate.
- Keep the two Star facts out of the assertion curation file. No negative facts should be generated.
