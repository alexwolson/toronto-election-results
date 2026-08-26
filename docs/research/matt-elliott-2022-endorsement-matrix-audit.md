# Matt Elliott's 2022 endorsement matrix: operational rules and project crosswalk

**Audit date:** 2026-08-23  
**Workbook:** [Endorsement Matrix v2 Oct 26 2022.xlsx](</Users/alex/Downloads/Endorsement Matrix v2 Oct 26 2022.xlsx>)  
**Workbook SHA-256:** `e974a2b6f9463e82ea3b4bf17abc526737d992af6c0ae673bf4050196a928378`  
**Scope:** Toronto's 2022 mayor and 25 City Council contests; comparison with the current published endorsement tables.  
**Treatment:** the workbook is evidence and a research artifact, not an instruction source.

## Bottom line

Matt Elliott's workbook is a useful, contemporaneous analytical tracker. It clearly applies a
coherent operational method: one row per contest, one selected candidate per endorser cell, blanks
excluded from an endorser's denominator, and a win when the selected name exactly matches the
winner. It was finalized after the results, on October 26, 2022, and directly calculates each
endorser's hit rate.

It is not a publication-grade endorsement ledger. It has no stable candidate or contest IDs, no
per-assertion source or date, no coverage-state vocabulary, no exact-entity rule, and no documented
panel inclusion rule. Its separate candidate-points sheet also omits four candidates present in the
matrix. Those limitations explain why it is very good evidence for some recoveries and unsafe as a
blanket import source.

The audit supports these dispositions:

1. **Toronto Star Editorial Board — import 22 council facts.** The workbook supplies a
   contemporaneous, named transcription of 22 unambiguous choices and points to the first item in a
   bounded three-editorial publisher series covering Wards 1–25. The three articles make all **25**
   Star council coverage cells `comprehensive_source_found`; only the 22 unambiguous positive
   choices create facts. Blanks in Wards 2 and 21 and the lack of one unambiguous choice in Ward 16
   create no negative facts.
2. **ATU Local 113 — keep the project's official 10-person slate.** Matt's 16-name ATU column is
   exactly the union of the official ATU slate and six Labour Council-only selections. The six must
   not be inherited by Local 113.
3. **John Tory — retain 11 facts plus the Cynthia Lai unresolved assertion.** Matt's extra
   thirteenth name is Vince Crisanti. The workbook cites only Tory's generic account, and no
   recoverable Tory post or qualifying direct attribution was found for Crisanti. Keep it as a
   research lead, not a fact.
4. **Progress Toronto — exact agreement.** Matt's nine choices and the project's nine 2022 facts
   match exactly.
5. **Do not add Matt's other five organizations to the canonical panel.** Their 2022 activity does
   not satisfy the approved 2023-anchored institutional eligibility rule.

No code, curation CSV, or `data/out` file was changed in this audit.

## Evidence inspected

The workbook contains two sheets:

- `Endorsement Matrix!A1:W34`: 26 contest rows (25 council wards and mayor), an incumbent
  comparator, nine endorsers, results, binary scoring cells, summary rates, totals, and one source
  link per endorser.
- `Endorsement Totals!A1:B42`: a manually enumerated candidate list with formula-derived counts of
  appearances in the nine endorsement columns.

The workbook identifies itself as maintained by Matt Elliott at `Endorsement Matrix!A34`. Its
attribution is independently consistent with Sean Marshall's contemporaneous October 21 article,
which says these endorsements were tracked by freelance journalist Matt Elliott and links the
tracker. That article also provides a direct contemporaneous cross-check for the Tory and Progress
Toronto slates ([Spacing](https://spacing.ca/toronto/2022/10/21/election-map-duelling-campaign-endorsements/)).

Candidate/contest identity and outcomes were cross-checked against the published
[`election_results.csv`](../../data/out/election_results.csv) and the City's official
[2022 declaration of results](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf).
The project-side comparison uses [`endorsers.csv`](../../data/out/endorsers.csv),
[`endorsements.csv`](../../data/out/endorsements.csv),
[`endorsement_assertions.csv`](../../data/out/endorsement_assertions.csv), and
[`endorsement_coverage.csv`](../../data/out/endorsement_coverage.csv).

## Matt's inferred operational rules

These are rules demonstrable from the workbook's structure and formulas. Where motive is not stated,
the description is explicitly an inference from the implementation.

| Dimension | Workbook rule | Evidence and consequence |
| --- | --- | --- |
| Grain | One row per 2022 Toronto mayor/councillor contest; one column per comparator or endorser. | `Endorsement Matrix!A2:L27`. The dataset is election-specific rather than historical. |
| Endorsement cell | At most one named candidate per endorser × contest cell. | `C2:K27` has one scalar value per cell. It cannot represent two separately supported candidates in one contest. |
| Blank | Blank means “not counted as an endorsement attempt” in the hit-rate denominator. It does not reveal *why* the cell is blank. | `C29:K29` uses `COUNTA` over each endorsement column. Blanks therefore contribute neither a win nor an attempt. The workbook cannot distinguish no choice, missed evidence, unavailable source, or inapplicability. |
| Win scoring | A choice scores 1 when its text exactly equals the result text, otherwise 0. | The shared row formula begins `COUNTIF(C2,$L2)` for the Tory column and shifts across the other endorser columns. This is exact-name comparison, not an ID join. |
| Record | `Seats Won / Endorsements Made`. | `C28:K28` divides the corresponding binary-win sum by `COUNTA`; `C29:K29` counts choices and `C30:K30` sums wins. |
| Incumbent comparator | Every contest is in the denominator. An open seat is stored as `Open (outgoing officeholder)` and necessarily scores 0. | `B2:B27` is fully populated, and `B28` is `SUM(M2:M27)/COUNTA(B2:B27)`. The resulting 65.38% is “an incumbent remained in the role in 17 of 26 contests,” not the re-election rate among incumbents who ran. |
| Candidate points | One point per appearance across the nine endorsement columns. | `Endorsement Totals!B2:B42` counts each listed name across `C:K`. The candidate-name list is manual, not generated from the matrix. |
| Endorser selection | A practical 2022 comparison set: the incumbent mayor, advocacy groups, unions/labour bodies, a newspaper editorial board, and a strategic-voting group that published multi-contest choices. | Inference from the nine headers and 8–25 choices per column. The workbook states no reproducible inclusion threshold, historical eligibility date, or future-election relevance rule. |
| Sources | One link per endorser column, not per assertion. | `C31:K31` includes account homepages, campaign/slate pages, one specific ATU tweet, and one of the three Star ward editorials. Individual choice/date provenance is not retained. |
| Timing | The tracker uses pre-poll endorsement material but stores no announcement dates; results were filled in after polling. | The source series includes October 2022 material; `A32` says the workbook was last updated October 26, two days after the October 24 vote. This is not a preregistered model input table. |

The workbook records 130 endorsement cells. Its candidate-points sheet lists 41 of the 45 unique
endorsed names and omits **Jennifer McKelvie, John Tory, Mike Colle, and Vince Crisanti**. The count
formulas are sound for names that are listed, but the manual candidate index is not complete.

## Comparison with this project's model

| Concern | Matt's workbook | Current project model |
| --- | --- | --- |
| Positive fact | Candidate name in one matrix cell. | One ID-backed `(endorser_id, contest_id, candidacy_id)` edge. |
| Multiple choices in one contest | Structurally unavailable. | Permitted as separate positive edges if evidence explicitly supports each one. |
| Missingness | One undifferentiated blank. | Separate `not_applicable`, `not_searched`, `partially_searched`, `searched_no_endorsement_found`, `comprehensive_source_found`, and `source_unavailable` coverage states. |
| Negative inference | Blanks are excluded from the hit-rate denominator, but their meaning is unstated. | Absence of a fact never creates a candidate-level negative; even completed coverage does not manufacture negative edges. |
| Provenance | One URL per endorser column; no assertion dates or review state. | Source-specific assertions with review state, source type, source URL, announcement date, and precision, separated from adjudicated facts. |
| Entity identity | Display label only; affiliate/coalition boundaries are undocumented. | Parent bodies, locals, affiliates, editorial boards, owners, coalitions, and members are distinct endorsers; no inheritance. |
| Candidate/contest identity | Display names and ward labels. | Stable Candidacy and Contest IDs joined to canonical results. |
| Panel | A practical, 2022-specific set with no written gate. | A frozen nine-endorser historical panel. Institutions require a qualifying 2023 mayoral choice plus approved structural evidence (with the named Progress Toronto exception); the individual cohort is living mayors of amalgamated Toronto, eligible from first assuming office. Every panel endorser applies to both mayor and council contests. |
| Outcome scoring | Embedded directly in the evidence workbook. | Downstream concern; the canonical release publishes evidence-backed facts and coverage, not hit-rate analysis. |

The project model is therefore a generalization of the good part of Matt's approach—positive
contest-specific choices—while preserving the distinctions his compact analytical matrix cannot.
The workbook's most important compatible feature is that its blanks are not included in an
endorser's record. Its largest incompatibilities are source granularity and exact-entity control.

## Four overlapping endorsers

| Endorser | Matt 2022 choices | Current project | Exact reconciliation |
| --- | ---: | ---: | --- |
| John Tory | 13 | 11 facts + 1 unresolved assertion | The shared 12 are Matt's list except Vince Crisanti. Eleven map to released Candidacies; Cynthia Lai is historically supported but unmappable because the City excluded her from certified results after her death. Crisanti is workbook-only and remains a hold. |
| Progress Toronto | 9 | 9 facts | Exact name-and-contest match; no difference. |
| ATU Local 113 | 16 | 10 facts | All 10 official ATU choices match. Matt has six additional Labour Council-only names that must not be inherited by ATU. |
| Toronto Star Editorial Board | 23 (22 council + mayor) | 1 mayor fact | The existing mayor fact matches. The workbook supports adding the 22 council choices below and completing coverage across all 25 council contests. |

### John Tory: why 13 versus 11 facts plus Cynthia Lai

Matt lists: Vince Crisanti, Mark Grimes, Siri Agrell, Frances Nunziata, James Pasternak, Mike Colle,
Grant Gonzales, Jon Burnside, Markus O'Brien Fehr, Brad Bradford, Gary Crawford, Nick Mantas, and
Cynthia Lai (`C2:C26`; count 13 at `C29`).

The contemporaneous Spacing account explicitly describes a **12-person** Tory slate and enumerates
the latter 12—everyone except Crisanti. It is the source for the project's 11 mapped facts and the
Lai hold ([Spacing](https://spacing.ca/toronto/2022/10/21/election-map-duelling-campaign-endorsements/)).
Several choices also survive as Tory's own campaign posts, including
[Gary Crawford](https://x.com/JohnTory/status/1565458029738328069),
[Jon Burnside](https://x.com/JohnTory/status/1566823593018884104),
[Brad Bradford](https://x.com/JohnTory/status/1567642418668871680),
[James Pasternak](https://x.com/JohnTory/status/1569097133210406916),
[Grant Gonzales](https://x.com/JohnTory/status/1574895875188563973),
[Nick Mantas](https://x.com/JohnTory/status/1574548655838621696),
[Mike Colle](https://x.com/JohnTory/status/1576665955249270785),
[Frances Nunziata](https://x.com/JohnTory/status/1576681783252307970),
[Siri Agrell](https://x.com/JohnTory/status/1584241199652646913), and
[Mark Grimes](https://x.com/JohnTory/status/1584188926910078982).

Matt's source cell is only `http://twitter.com/JohnTory`, not a post permalink. No recoverable Tory
post or qualifying contemporaneous direct attribution for Crisanti was found. The workbook makes
Crisanti a credible discovery lead, but not an auditable fact under the project's gate. It should
remain **HOLD**, not rejected: an incomplete archive cannot prove the endorsement did not occur.

Lai is different. The Spacing source positively names her, but the City states that after her
October 21 death the Ward 23 election proceeded as if she had not been nominated and votes for her
were not counted ([City notice](https://www.toronto.ca/news/impact-of-the-passing-of-councillor-cynthia-lai-on-the-scarborough-north-ward-23-election/)).
The project is correct to preserve an unresolved source assertion rather than invent a Candidacy.

### ATU Local 113: why 16 versus the official 10

ATU Local 113's dated October 6 first-party announcement calls the poster its candidate
endorsements and urges readers to vote for “these transit champions”
([ATU announcement](https://wemovetoronto.ca/atu-local-113-endorses-candidates-for-the-2022-ontario-municipal-election/);
[poster](https://wemovetoronto.ca/wp-content/uploads/2022/10/ATU_MunicipalElection2022_Poster-scaled-1.jpg)).
The poster's exact 10 are Amber Morley, Gord Perks, Chiara Padovani, Anthony Perruzza, Alejandra
Bravo, Ausma Malik, Shelley Carroll, Kevin Rupasinghe, Nick Mantas, and Jamaal Myers. ATU's
post-election notice names the eight winners from that set and no workbook-only additions
([ATU follow-up](https://wemovetoronto.ca/atu-local-113-congratulates-the-newly-elected-city-councillors/)).

Matt's ATU column contains those 10 plus six more:

| Ward | Workbook-only ATU name | Also in Matt's Labour Council column | Official ATU poster |
| ---: | --- | --- | --- |
| 1 | Charles Ozzoude | Yes | Absent |
| 11 | Norm Di Pasquale | Yes | Absent |
| 13 | Chris Moise | Yes | Absent |
| 14 | Paula Fletcher | Yes | Absent |
| 15 | David Ricci | Yes | Absent |
| 16 | Stephen Ksiazek | Yes | Absent |

The set relationship is exact:

`Matt ATU (16) = Matt Labour Council (14) ∪ {Nick Mantas, Jamaal Myers}`.

Equivalently, the six additions are precisely Matt's Labour Council choices not present on ATU's
poster. This strongly indicates cross-column inheritance or copy/merge contamination. The workbook
does not document which. Either interpretation violates the project's exact-entity rule, so the
official 10-person ATU slate is the defensible canonical set. This is analytically consequential:
Matt reports 10 wins from 16 (62.5%), while the official 10-person slate had eight winners (80%).

### Progress Toronto: exact match

Both sources identify Charles Ozzoude, Amber Morley, Chiara Padovani, Alejandra Bravo, Ausma Malik,
Norm Di Pasquale, Chris Moise, Kevin Rupasinghe, and Jamaal Myers. Progress Toronto's September 22
announcement says it picked local races where it would work to elect progressive champions
([first-party announcement](https://www.progresstoronto.ca/updates/2022/9/22/progressive-champions));
Spacing contemporaneously enumerates the nine candidates
([direct attribution](https://spacing.ca/toronto/2022/10/21/election-map-duelling-campaign-endorsements/)).
Matt's five wins from nine and the project's nine facts are consistent.

## Toronto Star 2022 council recovery

### Evidence disposition

The workbook's Star column identifies 22 single-candidate council choices, reports 23 total Star
choices including John Tory for mayor, and calculates 18 winners (`J2:J30`). It cites the first
publisher-owned article in a three-part ward series. The other two article titles, URLs, and dates
are independently preserved in the contemporaneous election bibliography:

1. [Wards 1–8, October 19](https://www.thestar.com/opinion/editorials/2022/10/19/the-stars-endorsements-for-toronto-council-in-wards-1-to-8.html)
2. [Wards 9–16, October 20](https://www.thestar.com/opinion/editorials/2022/10/20/the-stars-endorsements-for-toronto-council-in-wards-9-to-16.html)
3. [Wards 17–25, October 21](https://www.thestar.com/opinion/editorials/2022/10/21/the-stars-endorsements-for-toronto-council-in-wards-17-to-25.html)

The live publisher pages are now retrieval-restricted, but pre-election Internet Archive captures
preserve the complete article bodies for [Wards 1–8](https://web.archive.org/web/20221019105703/https://www.thestar.com/opinion/editorials/2022/10/19/the-stars-endorsements-for-toronto-council-in-wards-1-to-8.html),
[Wards 9–16](https://web.archive.org/web/20221020112036/https://www.thestar.com/opinion/editorials/2022/10/20/the-stars-endorsements-for-toronto-council-in-wards-9-to-16.html),
and [Wards 17–25](https://web.archive.org/web/20221021111327/https://www.thestar.com/opinion/editorials/2022/10/21/the-stars-endorsements-for-toronto-council-in-wards-17-to-25.html).
Those first-party captures independently confirm Matt's 22-name transcription and explain all
three blanks: Ward 2 says there is no strong challenger the board can recommend; Ward 16 calls the
choice between Jon Burnside and Stephen Ksiazek a tough call without selecting one; and Ward 21
does not recommend a candidate. The workbook is therefore a contemporaneous cross-check, not the
sole evidence bridge.

Coverage and facts must remain distinct:

- The three editorials are a bounded source set expressly partitioning **all 25 wards**, so all 25
  Star 2022 council cells can move from `source_unavailable` to
  `comprehensive_source_found`.
- The workbook supplies **22** unambiguous positive choices, so it supports 22 new assertions/facts.
- Ward 2 and Ward 21 are blank in the source-complete matrix. Ward 16 has no single choice in Matt's
  matrix; a surviving secondary transcription is ambiguous between Jon Burnside and Stephen
  Ksiazek. These three contests produce **no positive fact**, but this is not a candidate-level
  non-endorsement claim.

### Exact 22 council choices

| Ward | Candidate as attributed by Matt | Contest ID | Candidacy ID | Editorial date | Result |
| ---: | --- | --- | --- | --- | --- |
| 1 | Charles Ozzoude | `con_0d314382ba1a5d62b399c1eefc717cc1` | `can_4bf69fdd28d25a3cafce07961bdc56ea` | 2022-10-19 | Lost |
| 3 | Amber Morley | `con_bcc3da3d377f5fd3bb1d8a0c3ad7160b` | `can_65ba2cff1113567da004dd917ba8ef28` | 2022-10-19 | Won |
| 4 | Gord Perks | `con_2c0ca30fc75e51a3acf50c4693b1cc1b` | `can_5d3cda342f5d5ce9a7bcb18578d4c2b7` | 2022-10-19 | Won |
| 5 | Chiara Padovani | `con_52f50431db92559f8d4391fb2e932f16` | `can_6c6ffe1b743357a5b7e74c8e511ea2d9` | 2022-10-19 | Lost |
| 6 | James Pasternak | `con_bab4f35c5b9a51da935131d5c790bddf` | `can_86b4a8b96048544897930f1f1cd40336` | 2022-10-19 | Won |
| 7 | Anthony Perruzza | `con_43f8a49a6b095ee8a38c2a1aa0477382` | `can_75961c4df15e5d8c85f6a63ffa59f246` | 2022-10-19 | Won |
| 8 | Mike Colle | `con_27e80d547d0256149213a7e90956055b` | `can_1c713059ec0357ccb3294d4ec433ba51` | 2022-10-19 | Won |
| 9 | Alejandra Bravo | `con_6821258c9f7f598e829c8617b8765c25` | `can_73ec5ac31ba8585b9b52e77fce07bc31` | 2022-10-20 | Won |
| 10 | Ausma Malik | `con_c44af6fcb9ff527e8974217b3d633af1` | `can_45aad11df89c511b88aed431e1b1be4e` | 2022-10-20 | Won |
| 11 | Robin Buxton Potts | `con_037ae72c455f558590ca04bc929df4cb` | `can_f1bfda454f1a55febe96be2c77bc773d` | 2022-10-20 | Lost |
| 12 | Josh Matlow | `con_91f80636385c5df5b2d409f9c9b389ed` | `can_a5a51a39a0825accaf1a1112adefeedf` | 2022-10-20 | Won |
| 13 | Chris Moise | `con_9476d4c41a7d5fa48b97b47e28f9305d` | `can_4b78f4587dab5e69b879563516563791` | 2022-10-20 | Won |
| 14 | Paula Fletcher | `con_ac0a746327ea57b39ba13add8456bbd3` | `can_0e66b13370375a32876db67694e0ddbd` | 2022-10-20 | Won |
| 15 | Jaye Robinson | `con_f8a855ebf8c250bda4eeed75246305b5` | `can_3c3d60402ebe53679b24342c577cb4f6` | 2022-10-20 | Won |
| 17 | Shelley Carroll | `con_a548943febc15683bb34e547001ee6e7` | `can_ce7185de10085eaaaedc1b064810f59d` | 2022-10-21 | Won |
| 18 | Markus O'Brien Fehr | `con_8d2d5f08a1095a14abbcb526483a3aa0` | `can_95396b48533f50499d760d4eefdf569e` | 2022-10-21 | Lost |
| 19 | Brad Bradford | `con_b7158aa7285c513f8255b4f87166c723` | `can_8a8622ea6deb5fc893af017dd09e6cb6` | 2022-10-21 | Won |
| 20 | Kevin Rupasinghe | `con_9e0a04dcf1245155b6f1fd50c6a83e99` | `can_0c187005e2eb558c9e79766553461816` | 2022-10-21 | Lost |
| 22 | Nick Mantas | `con_db6acf978ec15e2c9ac0230649ef0609` | `can_933ed8a454ba5127a1f53e6f4b508546` | 2022-10-21 | Won |
| 23 | Jamaal Myers | `con_c686b3ad3bd059d78db8cc44229817a0` | `can_19bbe15fc35c514cab23e1672f721659` | 2022-10-21 | Won |
| 24 | Paul Ainslie | `con_98fc649f10ee5100a44520c1500dfac9` | `can_765f141c853a5c22bec6091dfb398cef` | 2022-10-21 | Won |
| 25 | Jennifer McKelvie | `con_e3987d425526548a844f6d73b662eac3` | `can_2e4aa5191b76594f88dbe6b8af5e48be` | 2022-10-21 | Won |

The crosswalk yields 17 council winners from 22 choices; adding the already-published Star → John
Tory mayoral fact reproduces Matt's 18 wins from 23 choices (78.26%). That exact reconciliation is
an additional internal integrity check.

## Should Matt's other five organizations join the canonical panel?

No. A strong 2022 slate is useful historical evidence but does not replace the approved
2023-anchored institutional gate. Panel exclusion does not mean their 2022 choices are false or
uninteresting; it means the project will not claim systematic historical completeness for them.

| Organization in Matt's workbook | Matt 2022 choices | 2023 gate assessment | Panel disposition |
| --- | ---: | --- | --- |
| More Neighbours Toronto | 12 | It demonstrably produced a 2023 mayoral scorecard and co-sponsored a housing debate, but no qualifying organizational candidate endorsement was recovered. A scorecard/debate is not a choice. | **Do not add.** Missing required 2023 candidate choice. |
| Toronto & York Region Labour Council | 14 | Its own post-election account says the election planning committee had not reached consensus on a mayoral candidate; its anti-hate pledge named several candidates rather than selecting one ([pledge](https://www.labourcouncil.ca/pledge-to-stand-up-against-hate/); [Labour Action, pp. 2 and 6](https://www.labourcouncil.ca/wp-content/uploads/2024/11/126617-1_LabourAction-Summer2023.pdf)). | **Do not add.** Explicitly fails the 2023 choice gate despite strong historic slate infrastructure. |
| Toronto Community Bikeways Coalition | 8 | The first-party 2022 page mixes “candidate endorsements” language with candidate sign-ons and lists multiple signers in some contests ([2022 page](https://www.communitybikewaysto.ca/municipal-vote-2022)). No qualifying 2023 mayoral choice was recovered; later material records congratulations to Mayor Chow, which is post-result and not an endorsement ([correspondence index](https://www.communitybikewaysto.ca/the-right-to-safe-roads)). | **Do not add.** Missing required 2023 candidate choice; its source semantics also need careful adjudication. |
| Toronto ACORN PAC | 10 | Toronto ACORN published a broad 2022 slate, but its 2023 campaign asked voters to support an affordable-city platform and named no mayoral candidate ([2022 slate](https://acorncanada.org/message-from-the-toronto-acorn-political-action-committee/); [2023 campaign](https://acorncanada.org/news/count-on-me-to-vote-for-an-affordable-city/)). | **Do not add.** Strong 2022 structure does not repair the missing 2023 choice. |
| Stop The Split Ontario | 25 | Its current page preserves a near-citywide 2022 slate ([2022 endorsements](https://www.stopthesplit.ca/endorsements)), but no qualifying 2023 mayoral choice or other approved 2023 evidence was recovered. | **Do not add.** Missing required 2023 candidate choice. |

## Recommended implementation handoff

1. Add 22 Toronto Star Editorial Board assertions/facts using the exact IDs above,
   `editorial_choice`, and the applicable editorial's publication date.
2. Record the supplied workbook and this audit as the contemporaneous retrieval/transcription
   bridge; retain the three publisher URLs as the owned source series.
3. Change **all 25** Toronto Star 2022 council coverage cells to
   `comprehensive_source_found`. Do not create facts for Wards 2, 16, or 21, and do not express
   their missing single-candidate choice as a negative edge.
4. Leave ATU Local 113 at the exact official 10-person slate. Do not import its six workbook-only
   rows.
5. Keep Tory → Vince Crisanti as a discovery hold unless a Tory post or qualifying contemporary
   direct attribution is recovered. Keep Cynthia Lai unresolved until the schema has a legitimate
   in-scope Candidacy target; do not synthesize one.
6. Do not expand the frozen canonical panel based on the other five workbook organizations.
