# Verification audit: Toronto mayor and councillor endorsement discoveries, 2003–2014

**Audit date:** 2026-08-21  
**Scope:** the approved exact institutional endorsers — Progress Toronto; Toronto Star Editorial Board; Toronto Sun Editorial Board; CUPE Ontario; Elementary Teachers of Toronto (ETT); and ATU Local 113 — in completed City of Toronto mayor and city-councillor contests from 2003 through 2014.

This is an adjudication audit of [the discovery report](endorsement-backfill-discovery-2003-2014.md), not a claim that a search found every historical endorsement. A missing item remains open-world missingness, never a negative edge.

## Evidence rule used

An imported fact needs explicit public electoral support by the **exact approved entity**, public before polling closed, and a qualifying source: the endorser's own material or reputable contemporaneous reporting that directly attributes the choice. A copied newspaper text in a later discussion forum is a useful retrieval lead, but is not sufficient for a `confirmed` import. A parent, local, labour council, columnist, candidate biography, issue position, or uncorroborated campaign statement is not substituted for the approved entity.

`CONFIRM` below means that the endorsement may be imported once the production schema is available. `HOLD` means the evidence is useful but does not yet meet that gate. `REJECT` means the proposed edge is outside the exact-entity rule or otherwise fails it; it should not be imported on the cited basis.

## Official target validation

The City Clerk's official declarations validate every target and ward in the discovery report, except for a spelling/display-name correction: the 2010 Ward 12 candidate is **Richard Gosling**, not “Rick Gosling.” Do not create a separate candidate or an endorsement edge under “Rick.” The declarations are the authoritative target records, rather than evidence of endorsement:

- [2003 declaration](https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf)
- [2006 declaration](https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf)
- [2010 declaration](https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf)
- [2014 declaration](https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf)

The [City's general-election-results index](https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/) links those official results. There was no completed City of Toronto mayoral or councillor by-election in this period; the purported coverage column for such contests is therefore `not_applicable`, not `searched_no_endorsement_found`.

## Adjudicated discovery assertions

| Exact endorser | Event and target(s) | Decision | Audit finding and qualifying evidence |
|---|---|---|---|
| Toronto Star Editorial Board | 2003 mayor — David Miller | **HOLD** | The discovery source reproduces wording identifying Miller as the Star's choice, but it is an archival forum copy rather than an endorser-owned page or reputable contemporaneous direct attribution. The original Star editorial is precisely identified as Nov. 6, 2003, but needs a Star/library archive capture before import. [Reproduction](https://urbantoronto.ca/forum/threads/2003-municipal-election-editorial-david-miller-best-to-lead-toronto.399/) |
| Toronto Star Editorial Board | 2003 Ward 18 — Adam Giambrone | **HOLD** | The claim rests on a secondary biography/index; no qualifying Star material or contemporaneous direct attribution was retrieved. The City declaration confirms Giambrone's Ward 18 candidacy, not the endorsement. |
| Toronto Star Editorial Board | 2006 mayor — David Miller | **HOLD** | A secondary index identifies a Nov. 10 Star editorial, “Qualified support for David Miller,” but the editorial itself was not retrieved. This is a strong retrieval target, not an import-ready fact. |
| Toronto Star Editorial Board | 2006 Ward 15 — Ron Singer | **HOLD** | The only discovery support is a secondary election index. No qualifying board source or contemporaneous direct attribution was retrieved. |
| Toronto Star Editorial Board | 2010 mayor — George Smitherman | **CONFIRM** | A contemporaneous reputable report says the Star made its official mayoral endorsement for Smitherman on Oct. 18, seven days before polling. It links the original editorial as “Star's choice: Smitherman for mayor.” [Toronto Life, Oct. 18, 2010](https://torontolife.com/city/torontos-weekend-of-entirely-unsurprising-mayoral-endorsements/) |
| Toronto Star Editorial Board | 2010 council, Wards 1–21 — Suzan Hall; Cadigia Ali; Doug Holyday; John Campbell; Peter Milczyn; Mark Grimes; Larry Perlman; Anthony Perruzza; Maria Augimeri; Brian Shifman; Fulvio Sansone; **Richard** Gosling; Sarah Doucette; Gord Perks; Josh Colle; Karen Stintz; Jonah Schein; Ana Bailão; Karen Sun; Adam Vaughan; Joe Mihevc | **HOLD** | The complete choices are reproduced with unambiguous endorsement language, but only in a later forum post pointing to dead Star URLs. This is excellent extraction/retrieval evidence but fails the final source gate. [Reproduction](https://skyrisecities.com/forum/threads/2014-municipal-election-toronto-council-races.20318/page-26) |
| Toronto Star Editorial Board | 2010 council, Wards 22–44 — Josh Matlow; John Filion; Sonny Cho; Jaye Robinson; Mohamed Dhanani; Ken Chan; Pam McConnell; Jennifer Wood; Paula Fletcher; Janet Davis; Mary-Margaret McMahon; Shelley Carroll; Denzil Minnan-Wong; Michelle Berardinetti; Robert Spencer; Michael Thompson; Glenn De Baeremaeker; Bryan Heal; Chin Lee; Neethan Shan; Paul Ainslie; Diana Hall | **HOLD** | Same evidence limitation as Wards 1–21. The forum reproduction explicitly records **no endorsement** in Ward 39; that is not an endorsement assertion or a negative edge. [Reproduction](https://skyrisecities.com/forum/threads/2014-municipal-election-toronto-council-races.20318/page-26) |
| Toronto Star Editorial Board | 2014 council — named discovery examples, including James Pasternak, Gord Perks, Alex Mazer, Joe Mihevc, Josh Matlow, John Filion, Ishrath Velshi, Mary Fragedakis, Denzil Minnan-Wong, Robert Spencer, Michael Thompson, Glenn De Baeremaeker, Chin Lee, and Paul Ainslie | **HOLD** | The original Star editorial URL and date establish a strong recovery target, but its full contents were not captured. Candidate-controlled quotation of the Star (including the Velshi example) is insufficient without independent corroboration. Do not infer a complete slate from secondary indexes. [Original editorial target](https://www.thestar.com/news/toronto-election/2014/10/20/the-stars-endorsements-for-toronto-city-council-editorial.html) |
| Toronto Sun Editorial Board | 2010 mayor — Rob Ford | **CONFIRM** | Contemporary reporting explicitly says the Sun made its official mayoral endorsement for Ford on Oct. 18, before the Oct. 25 poll. [Toronto Life, Oct. 18, 2010](https://torontolife.com/city/torontos-weekend-of-entirely-unsurprising-mayoral-endorsements/) |
| Toronto Sun Editorial Board | 2014 mayor — John Tory | **CONFIRM** | Contemporary CityNews reports the Sun's Sunday editorial endorsed Tory and quotes its rationale; publication was eight days before polling. [CityNews, Oct. 19, 2014](https://toronto.citynews.ca/2014/10/19/john-tory-endorsed-by-toronto-sun-globe-and-mail/) |
| CUPE Ontario | 2003 mayor — David Miller | **REJECT** | The lead supports only generic “CUPE”/union support. It does not establish that **CUPE Ontario** made the choice. Do not inherit an endorsement from CUPE national, a local, or an unspecified CUPE body. |
| CUPE Ontario | 2010 mayor — Joe Pantalone | **CONFIRM** | CUPE Ontario's own Oct. 19 release says President Fred Hahn announced the decision to back Pantalone for mayor and urged Toronto CUPE members to vote for him. It is exact-entity, explicit, and pre-close. [CUPE Ontario release](https://cupe.on.ca/archivedoc1288/) |
| Elementary Teachers of Toronto (ETT) | 2014 mayor — Olivia Chow | **CONFIRM** | CityNews contemporaneously and directly attributes ETT's endorsement of Chow, quotes the ETT statement, and published it six days before the poll. This is direct attribution to the exact local, not ETFO. [CityNews, Oct. 21, 2014](https://toronto.citynews.ca/2014/10/21/elementary-teachers-of-toronto-union-endorses-olivia-chow/) |
| ATU Local 113 | 2003–2014 mayor/council discoveries | **REJECT (none proposed)** | No candidate-level ATU Local 113 endorsement was discovered. The 2014 transit-advocacy material is policy advocacy, not an electoral choice; it produces no edge. |

The confirmed targets are all present in the cited Clerk declarations: Smitherman and Ford were 2010 mayoral candidates; Pantalone was a 2010 mayoral candidate; Tory and Chow were 2014 mayoral candidates. All 43 named 2010 Star council targets and all named 2014 Star examples likewise match their stated ward and election date, with the Gosling correction above.

## Coverage-state audit

The following assesses the discovery report's existing coverage semantics, not whether an endorser failed to endorse anyone. “Comprehensive source found” only means that a source purporting to make a full slate or explicit choice was located; it never turns absent rows into no-endorsement observations.

| Endorser | 2003 | 2006 | 2010 | 2014 | Auditor determination |
|---|---|---|---|---|---|
| Progress Toronto | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | **Defensible.** Its own account places its public champion-selection process from 2018 onward. [Progress Toronto](https://www.progresstoronto.ca/media-release-may10-progressive-mayoral-champions) |
| Toronto Star Editorial Board | `partially_searched` | `partially_searched` | `comprehensive_source_found` | `comprehensive_source_found` | **Defensible as discovery coverage, with an important limit.** Complete 2010 and 2014 Star council-editorial targets were located, but the surviving evidence has not cleared the fact-import source gate. Keep every individual row above on `HOLD` until primary/reputable preservation is captured. |
| Toronto Sun Editorial Board | `partially_searched` | `partially_searched` | `partially_searched` | `partially_searched` | **Defensible.** The two confirmed mayoral editorials do not establish source-complete council coverage. |
| CUPE Ontario | `partially_searched` | `partially_searched` | `comprehensive_source_found` | `partially_searched` | **Defensible.** The exact-entity 2010 release is an explicit choice; other events have no source-complete negative. |
| Elementary Teachers of Toronto | `partially_searched` | `partially_searched` | `partially_searched` | `partially_searched` | **Defensible.** A contemporaneous 2014 direct attribution is enough to confirm Chow but no endorser-owned archive or full slate establishes event completeness. |
| ATU Local 113 | `partially_searched` | `partially_searched` | `partially_searched` | `partially_searched` | **Defensible.** No source-complete archive was located; absence remains open-world missingness. |

For all six endorsers, replace the report's 2003–2014 mayor/councillor-by-election cell of `searched_no_endorsement_found` with **`not_applicable`**: the official inventory contains no in-scope completed contest in that interval. This is a scope statement, not a negative endorsement finding.

## Missed-item screen and next work

No additional high-confidence, import-ready endorsement by one of the six exact entities was found in this audit. The key retrieval work is narrow and consequential:

1. Obtain publisher/library/archive copies of the Star 2003, 2006, 2010, and 2014 editorials. That would convert the grouped Star holds to individual confirmed facts without creating negative edges for omitted wards.
2. Preserve the direct CUPE Ontario 2010 release and the CityNews ETT 2014 story as evidence assertions when the ledger is implemented.
3. Retain the target correction as **Richard Gosling, Ward 12 (2010)** throughout extraction and future evidence work.

