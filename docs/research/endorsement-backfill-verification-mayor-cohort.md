# Verification audit: individual mayor cohort endorsement backfill

**Audit date:** 2026-08-21  
**Scope:** personal endorsements by David Miller (from 2003-12-01), John Tory (from 2014-12-01), and Olivia Chow (from 2023-07-12), of Toronto Mayor or City Councillor candidates only.

## Result

This audit confirms sixteen importable facts and holds one otherwise well-supported fact because the current release has no Candidacy to receive it. No newly verified positive Chow endorsement, no qualifying 2026 endorsement, and no missed Tory council endorsement outside the reported 2018 and 2022 sets were located.

The test here is explicit electoral support, public before polls close, by the named person, for an in-scope candidate. It accepts a direct first-party source or reputable contemporaneous direct attribution. Absence of a result is not a negative endorsement.

## Candidate-key validation

Every **CONFIRM** target below has a completed Toronto Mayor/Council Candidacy in `data/out/election_results.csv`, sourced to the Toronto City Clerk. The listed IDs are the intended `(Contest, Candidate)` keys. No Campaign entity is needed.

**Cynthia Lai exception.** Contemporaneous reporting says Lai died on October 21, remained printed on the ballot, and votes for her were not counted. The released results file consequently has no 2022 Lai row. The historical support assertion is valid, but cannot currently be imported without a Candidacy key. This is a **HOLD** on mapping, not a rejection of the historical fact.

## Discovered positive assertions

### David Miller

| Decision | Assertion | Target key | Verification |
| --- | --- | --- | --- |
| **CONFIRM** | Miller endorsed Joe Pantalone for mayor in 2010. | `can_d37ad909fb1c5173be971d0fb7fa193a` | On October 6, before the October 25 poll, contemporaneous reporting said Miller had endorsed Pantalone and described Miller's reasons. [Toronto Life](https://torontolife.com/city/mayor-shocks-no-one-by-endorsing-his-deputy-mayor-joe-pantalone/); [CityNews](https://toronto.citynews.ca/2010/10/06/miller-endorses-pantalone-in-race-for-mayor-mihevc-endorses-smitherman/). |

### John Tory — 2018 general election

| Decision | Assertion | Target key | Verification |
| --- | --- | --- | --- |
| **CONFIRM** | Tory endorsed Mark Grimes in Ward 3. | `can_881b56db387e50b19b0aa61d56b09724` | A contemporary *Toronto Star* report is titled “Tory endorses Mark Grimes in Etobicoke council race” and dated October 20, before the poll. Its original URL is robots-restricted, but later accounts directly describe the decision and Tory robocalls. [Original Star URL](https://www.thestar.com/news/city_hall/2018/10/20/tory-endorses-mark-grimes-in-etobicoke-council-race.html); [The Local](https://thelocal.to/ward-3-etobicoke-lakeshore/); [Spacing](https://spacing.ca/toronto/2022/11/21/election-how-toronto-voted/). |
| **CONFIRM** | Tory endorsed Joe Mihevc in Ward 12. | `can_daba066aa91d57bb8ac1116dacf2f2bc` | Contemporary coverage reports Tory “threw his support behind Mihevc” October 12. A separate October 15 report records Tory's own statement that he had made endorsements, naming Mihevc as the example. [CityNews](https://toronto.citynews.ca/2018/10/12/matlow-vs-mihevc-when-council-friends-become-foes/); [Global News](https://globalnews.ca/news/4551754/council-endorsements-2018-municipal-election/). |
| **CONFIRM** | Tory endorsed Brad Bradford in Ward 19. | `can_aeb469c9e30b5f37a4f25f6a757d2ca4` | Reporting immediately after the election says Bradford had Tory's backing, that Tory campaigned with him several times, and quotes Bradford thanking him. [Global News](https://globalnews.ca/news/4584494/toronto-election-2018-new-councillors/). |

The October 15 Global report is a useful timing checkpoint but not a negative edge: it records that Tory then expected no further endorsements, while the Grimes source documents a later pre-poll endorsement.

### John Tory — 2022 general election

Spacing's October 21 report explicitly calls this a 12-candidate Tory slate and identifies the targets before the October 24 vote. That is contemporaneous direct attribution to **John Tory**, not merely to an office or generic campaign. [Spacing](https://spacing.ca/toronto/2022/10/21/election-map-duelling-campaign-endorsements/).

| Decision | Target and contest | Target key | Notes |
| --- | --- | --- | --- |
| **CONFIRM** | Mark Grimes — Ward 3 | `can_0683e747d16658ccbd08215379bddc50` | Named in slate. |
| **CONFIRM** | Siri Agrell — Ward 4 | `can_79eaa51713b25cf5912773588f7cb884` | Named in slate; independently attributed in [Skedline](https://skedline.com/2022/10/siri-agrell-running-for-ward-4/). |
| **CONFIRM** | Frances Nunziata — Ward 5 | `can_c4e145ff6e765e0082c90ea1a07ae943` | Named in slate. |
| **CONFIRM** | James Pasternak — Ward 6 | `can_86b4a8b96048544897930f1f1cd40336` | Named in slate. |
| **CONFIRM** | Mike Colle — Ward 8 | `can_1c713059ec0357ccb3294d4ec433ba51` | Named in slate. |
| **CONFIRM** | Grant Gonzales — Ward 9 | `can_088b3c28f70f5a1397b937c55ecb3a65` | Named in slate; independently attributed in [The Local](https://thelocal.to/ward-9-davenport/). |
| **CONFIRM** | Jon Burnside — Ward 16 | `can_03d6f16490885a9bb430aa263793788d` | Named in slate. |
| **CONFIRM** | Markus O’Brien Fehr — Ward 18 | `can_95396b48533f50499d760d4eefdf569e` | Named in slate. |
| **CONFIRM** | Brad Bradford — Ward 19 | `can_8a8622ea6deb5fc893af017dd09e6cb6` | Named in slate. |
| **CONFIRM** | Gary Crawford — Ward 20 | `can_4be13ddaed1f5fd69bb23af3743ef443` | Named in slate. Spacing says Ward 21 once; the Clerk result key establishes Ward 20. |
| **CONFIRM** | Nick Mantas — Ward 22 | `can_933ed8a454ba5127a1f53e6f4b508546` | Named in slate. |
| **HOLD — mapping only** | Cynthia Lai — Ward 23 | *No released 2022 Candidacy* | The pre-election slate supports Tory → Lai. Lai died October 21; ballots could not be changed and her votes were not counted. Do not fabricate a target or add a Campaign entity. [Spacing](https://spacing.ca/toronto/2022/10/21/election-map-duelling-campaign-endorsements/); [CityNews](https://toronto.citynews.ca/2022/10/21/city-councillor-cythia-lai-dies/). |

### John Tory — 2023 mayoral by-election

| Decision | Assertion | Target key | Verification |
| --- | --- | --- | --- |
| **CONFIRM** | Tory endorsed Ana Bailão for mayor. | `can_f9c65b5f49305573ac4de1d27b1e8fca` | CityNews published the announcement June 21, five days before the June 26 poll, and reproduces Tory's explicit endorsement statement. [CityNews](https://toronto.citynews.ca/2023/06/21/john-tory-endorse-ana-bailao-toronto-byelection/); [Global News corroboration](https://globalnews.ca/news/9783181/john-tory-ana-bailao-endorsement-expected/). |

## Non-qualifying discovered lead

| Decision | Lead | Reason |
| --- | --- | --- |
| **REJECT** | Tory congratulated Nick Mantas after the 2021 Ward 22 by-election. | It is post-result congratulations, not a public pre-close endorsement, so creates no edge. [CityNews](https://toronto.citynews.ca/2021/01/16/former-karygiannis-chief-of-staff-mantas-wins-ward-22-by-election/). |

## Coverage recommendations

| Endorser / events | Recommended state | Reason |
| --- | --- | --- |
| Miller — all eligible general elections and by-elections | `partially_searched` | The 2010 fact is solid, but there is no auditable event-by-event search establishing all Miller endorsements. |
| Tory — 2016 Ward 2 and 2017 Ward 42 by-elections | `partially_searched` | A post-election Shan congratulations was found, but not a qualifying endorsement or a complete pre-poll audit. |
| Tory — 2018 general | `partially_searched` | Three facts are confirmed; no complete final slate was found. |
| Tory — 2021 Ward 22 | `partially_searched` | The known Mantas lead is rejected, but a complete search certificate does not exist. |
| Tory — 2022 general | `comprehensive_source_found` | The October 21 source declares and enumerates a 12-target slate. |
| Tory — 2023 mayoral by-election | `partially_searched` | Bailão is confirmed; a report of one endorsement is not evidence of no other support. |
| Tory — 2023 Ward 20, 2024 Ward 15, and 2025 Ward 25 by-elections | `partially_searched` | No qualifying target was located, but no auditable negative search log exists. |
| Tory — 2026 through 2026-08-21 | `partially_searched` | His March non-commitment is not a negative fact. Continue monitoring to polls close; no later qualifying edge was verified. |
| Chow — 2023 Ward 20, 2024 Ward 15, 2025 Ward 25, and 2026 through 2026-08-21 | `partially_searched` | No qualifying personal Chow edge was verified. Her own 2026 candidacy is self-endorsement territory and excluded; institutional support is not hers. |

## Import recommendation

Import the sixteen **CONFIRM** rows as positive facts with the cited sources. Preserve the Lai assertion as a mapping hold rather than silently treating it as absent. Do not infer negative endorsements, do not treat a mayor's office or campaign label as the person without attribution, and keep 2026 collection open through polling day.
