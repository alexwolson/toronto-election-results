# Terra independent verification: Toronto Star Editorial Board package census, 2003–2026

**Verification date/cutoff:** 2026-08-28
**Verifier:** Terra
**Input reviewed:** [Luna public discovery](endorsement-census-luna-star-public-2003-2026.md)
**Scope:** Toronto Star Editorial Board only; Toronto mayoral and City Council contests from the 2003 general election through the pending 2026 general election. This review used public sources and the checked-in Results records only. No institutional login was used.

## Decision

The Luna report is accepted as a **public-discovery and authenticated-retrieval
queue**, with the dispositions below. It is not an import instruction.

- The 70 existing confirmed Star assertions are retained: one 2003 mayoral,
  43 2010 council, 2010 mayoral, 2018 mayoral, 22 2022 council, 2022 mayoral,
  and 2023 mayoral-by-election fact.
- The existing 2022 council package and its `comprehensive_source_found`
  coverage state are confirmed. It is a three-item ward-range series that
  addresses all 25 wards, while yielding only 22 unambiguous positive edges.
- No new historical assertion clears the public-evidence gate in this review.
  In particular, the 2003 Adam Giambrone and 2006 David Miller/Ron Singer
  leads remain **HOLD**. A package title, candidate biography, election index,
  or an unrecovered partial transcription cannot be converted into a fact.
- The reported by-election search outcomes are accepted only as bounded,
  open-world `partially_searched` dispositions. They do not establish that the
  Star made no recommendation.
- The 2026 row is a valid as-of-2026-08-28 snapshot, not completed coverage.

The review found two targeting qualifications for the authenticated-access
work: the 2014 mayoral record needs a recovered catalogue result or original
article locator in addition to its title/date, and the 2014 council target must
first identify the full article sequence (the current record identifies the
general item and the Wards 22–44 continuation, but not every component).

## Evidence and identity checks

The established project rule is an exact positive edge from the **Toronto Star
Editorial Board** to one canonical Candidacy. It does not permit negative
inference from absent names or incomplete sources ([ADR 0008](../adr/0008-model-endorsements-as-open-world-facts.md)).

I checked the input against `endorsement_assertion_curations.csv`,
`endorsement_coverage_curations.csv`, their generated outputs, and the prior
editorial/recovery audits. Candidate and contest IDs in the existing assertions
already resolve through the Results build. The audit of the 2022 package also
cross-checked all 22 individual Candidate/Contest IDs against the City’s
certified declaration; the Wards 1–8, 9–16, and 17–25 editorials were preserved
before polling in the Internet Archive.

The public evidence independently supports these high-level facts:

- The recovered 2003 *Star* mayoral editorial is explicit that David Miller
  was its choice; the existing assertion is correctly retained.
- The preserved 2010 council reproduction explicitly attributes a complete
  ward-by-ward list to the *Star*. Its 43 positive rows and Ward 39 explicit
  no-choice statement are correctly represented without a negative edge.
- The existing 2018, 2022, and 2023 mayoral rows have dated, candidate-naming
  *Star* editorial titles published before their polls.
- The three 2022 council editorial URLs and dates form a bounded 1–25 series.
  The current 22 facts, explicit no-choice treatment in Wards 2 and 21, and
  non-selection treatment of Ward 16 are correct.

The current Star curation contains nine bounded historical/by-election searches
and one 2022 comprehensive council cell. Luna’s descriptions of those existing
states agree with the curation; nothing in this review warrants a negative
assertion or a broader completion claim.

## Package dispositions

| Event/package | Disposition | Terra verification and required treatment |
|---|---|---|
| 2003 mayor — David Miller | **CONFIRM (existing)** | Explicit recovered editorial reproduction; correct exact endorser, pre-poll date, mayoral contest, and canonical candidate. A page-image copy is desirable, not needed to retain the fact. |
| 2003 council — “Star’s selections for city council” | **HOLD / authenticated retrieval** | The title, 2003-11-07 date, A26 locator, and ProQuest `dids=648567571` are a precise, justified retrieval target. Do not turn the package citation into a complete slate until the text/page is inspected. |
| 2003 Ward 18 — Adam Giambrone | **HOLD** | The candidate is a valid canonical 2003 Ward 18 candidacy, but the current public attribution is secondary. The separately identified “Slate of six compete for Ward 18” is a useful companion search, not proof of an Editorial Board choice. |
| 2006 mayor — “Qualified support for David Miller” | **HOLD / authenticated retrieval** | Exact *Star* title, 2006-11-10 date, and A26 locator are strong. Public material reports a qualified endorsement, but without the editorial text or qualifying direct attribution it should not become a fact. |
| 2006 council — “Star’s selections for city council” | **HOLD / authenticated retrieval** | Exact title, 2006-11-08 date, and A26 locator are precise. Ron Singer’s Ward 15 attribution remains a lead only until the package is recovered and the named candidate is read against the canonical result. |
| 2010 mayor — George Smitherman | **CONFIRM (existing)** | The contemporaneous direct attribution is timely and exact; the existing fact is valid. |
| 2010 council | **CONFIRM (existing)** | 43 positive canonical edges, no negative Ward 39 edge. Original page/image retrieval is provenance improvement only. |
| 2014 mayor — “John Tory is the best choice to lead Toronto” | **HOLD / high-confidence target** | The exact title/date is widely preserved and unambiguously names a choice before the 2014-10-27 poll, but this pass could not recover a first-party URL, page locator, or independent direct attribution that meets the project’s source gate. Retrieve the original article or a catalogue record plus accessible text before import. |
| 2014 council | **HOLD / authenticated retrieval** | The October 20 broad article and Wards 22–44 continuation are credible leads. The package target is **not yet complete enough** to call a fully specified series: the library search must identify all remaining ward-range article(s) and retrieve them before any coverage or slate claim. |
| 2016 Ward 2 by-election | **CONFIRM bounded search state** | Retain `partially_searched`; no public positive was recovered. This is not an archive-wide no-endorsement conclusion. |
| 2017 Ward 42 by-election | **CONFIRM bounded search state** | Same treatment. |
| 2018 mayor — John Tory | **CONFIRM (existing)** | Dated, explicit first-party editorial title before the 2018-10-22 poll; existing canonical ID is correct. |
| 2018 council — Oct. 15–16 editorials | **HOLD / authenticated retrieval** | Exact two-title/date targets are justified. The public Wards 1–12 reproduction and later litigation citation corroborate discovery, including Lily Cheng, but do not establish an importable complete series under the present rule. Do not infer omissions or import a reconstructed slate. |
| 2021 Ward 22 by-election | **CONFIRM bounded search state** | Retain `partially_searched`; no fact or negative edge. |
| 2022 mayor — John Tory | **CONFIRM (existing)** | Timely, candidate-naming first-party editorial title; existing fact is valid. |
| 2022 council — Wards 1–25 editorial series | **CONFIRM (existing comprehensive package)** | The primary three-part package, archived copies, City-Hall-Watcher archival copy, and existing audit support 22 facts and comprehensive coverage only—not candidate-level negatives for Wards 2, 16, or 21. |
| 2023 mayoral by-election — Ana Bailão | **CONFIRM (existing)** | Timely, candidate-naming first-party editorial title. The canonical Bailão candidacy is correctly linked. |
| 2023 Ward 20, 2024 Ward 15, 2025 Ward 25 by-elections | **CONFIRM bounded search states** | Keep each `partially_searched`. The wording “no recoverable package” is acceptable only as the result of the documented public search, not as a conclusion that no Star package existed. |
| 2026 general | **CONFIRM as open snapshot** | The City’s current key-dates page records certification on August 24 and election day on October 26. At the August 28 cutoff, the absence of a located package supports an open `partially_searched` snapshot only. Do not close coverage or infer a no-endorsement result. |

## By-election search characterization

The six by-election rows are appropriately source-package-first, but library
retrieval should be more reproducible than a search for the ward and poll date.
For each, search the *Toronto Star* title/section fields and full text from
nomination close through election day, using the ward number/name, `by-election`,
`endorsement`, `editorial`, `choice`, and all leading candidates only as fallback.
Record the database, date window, query terms, result count, and any false
positive article IDs. A null result remains a search limitation, not a negative
fact.

## Prioritized authenticated-access queue

1. **2003 council package — required.** *Toronto Star*, “Star’s selections for
   city council,” 2003-11-07, A26, ProQuest `dids=648567571`. Recover the page
   or complete text, then enumerate only explicit choices.
2. **2006 mayor and council packages — required.** “Qualified support for David
   Miller,” 2006-11-10, A26; and “Star’s selections for city council,”
   2006-11-08, A26. These are exact, high-yield locators and can resolve the
   prominent Miller and Singer holds as well as any other explicit choices.
3. **2014 council series, then 2014 mayor — required.** Start with “The Star’s
   endorsements for Toronto city council,” 2014-10-20 and the identified Wards
   22–44 item. Establish the complete ward-range sequence before extracting.
   Then retrieve “John Tory is the best choice to lead Toronto,” 2014-10-21,
   recording its page/document ID and text.
4. **2018 council two-item package — required.** “These are the city builders
   that Toronto needs,” 2018-10-15, and “These are the council members Toronto
   needs,” 2018-10-16. Recover both, retain only explicit choices, and assess
   whether the titles/contents collectively cover all 25 wards.
5. **Six by-election event searches — required to improve coverage, lower
   expected yield.** Ward 2 (2016), Ward 42 (2017), Ward 22 (2021), Ward 20
   (2023), Ward 15 (2024), and Ward 25 (2025), using the reproducible windows
   above. Record a package found, partial evidence, or bounded no-recovery.
6. **2010 and 2022 originals — desirable provenance upgrades.** These cannot
   unlock new claims under the current records, so they rank below missing
   packages.
7. **2026 monitoring — not a historical retrieval task.** Search the Opinion /
   Editorial index and available databases periodically from late September to
   October 25. Preserve the assessed-through date with every rerun.

For any successful authenticated retrieval, record the original title,
publication date, page or document identifier, database/provider, retrieval
date, stable publisher/catalogue URL when available, and a concise permitted
evidence summary. Do not commit credentials, session URLs, database exports, or
full licensed article copies.

## Final validation outcome

**Accepted with two targeting qualifications.** Luna’s public report correctly
preserves the open-world model and gives a sound Star package census. It may
support search/coverage documentation immediately. It must not add historical
Star facts or declare new comprehensive packages until the authenticated targets
above are recovered and independently validated.
