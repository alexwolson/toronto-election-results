# Terra independent verification: authenticated Star and Sun endorsement recovery

**Verification date:** 2026-08-28
**Verifier:** Terra
**Evidence reviewed:** the four authenticated U of T/ProQuest evidence and Luna
resolution reports dated 2026-08-28
**Scope:** Toronto Star Editorial Board (2003, 2006, 2014 and 2018 council;
2006 mayor; completed in-scope council by-elections) and Toronto Sun Editorial
Board (2018 council).

## Decision

**Accept all 178 proposed positive edges.** That is 151 Toronto Star edges
(150 council and David Miller for mayor in 2006) and 27 Toronto Sun council
edges in 2018. No proposed edge is rejected or held after this review.

| Endorser / package | Proposed | Accept | Reject | Hold |
|---|---:|---:|---:|---:|
| Star 2003 council | 40 | 40 | 0 | 0 |
| Star 2006 mayor | 1 | 1 | 0 | 0 |
| Star 2006 council | 41 | 41 | 0 | 0 |
| Star 2014 council | 44 | 44 | 0 | 0 |
| Star 2018 council | 25 | 25 | 0 | 0 |
| Sun 2018 council | 27 | 27 | 0 | 0 |
| **Total** | **178** | **178** | **0** | **0** |

This decision relies on the authenticated evidence summaries: each named row
comes from a full-text ProQuest article identified as an editorial-board
endorsement package, was published before the relevant poll, and has one exact
canonical Candidacy match. It does not reproduce licensed source text or turn
any unchosen candidate into a negative assertion.

## Independent canonical-ID audit

I independently joined every proposed `(contest_id, candidacy_id)` pair to the
current `data/out/election_results.csv`:

| Proposal set | Unique pairs | Invalid contest/candidacy joins | Event/office result |
|---|---:|---:|---|
| Star | 151 | 0 | 40 2003 council; 41 2006 council; 44 2014 council; 25 2018 council; 1 2006 mayor |
| Sun | 27 | 0 | 27 2018 council |

All candidates resolve within the stated election event, office and ward. The
only display differences are non-substantive: `Pam Mcconnell` and
`Mary-Margaret Mcmahon` capitalization in Results; the source’s `Lucy Trosi`
typo resolved to the unique Lucy Troisi candidacy; `Greb Christin Carmichael`
is the same uniquely matched person as source-order `Christin Carmichael Greb`;
and `Jennifer Mckelvie` is capitalization only. Evan Tummillo and Joyce
Rowlands lack a current `person_id`, but both have exact contest-specific
Candidacy IDs. That is sufficient at the endorsement table’s stated grain.

All package dates precede their polls: Star 2003 November 7–8 before November
10; 2006 November 8–10 before November 13; 2014 October 20–21 before October
27; and 2018 October 15–16 before October 22. The Sun’s primary ProQuest
record is dated October 20 (with duplicate records dated October 21), both
before the October 22 poll. Use October 20 as the authenticated primary
publication date.

## Star package and coverage decisions

| Package | Decision | Coverage/import treatment |
|---|---|---|
| 2003 council, Wards 1–21 and 22–44 | **Accept 40 edges** | The two dated pages cover all 44 wards. Wards 2 and 40 are explicit no-choice observations; Wards 7 and 24 are acclamations. Mark the 2003 Star council source package `comprehensive_source_found`, but create edges only for the 40 named choices. |
| 2006 mayor | **Accept David Miller** | “Qualified support” is an explicit qualified endorsement, with the exact mayoral Candidacy ID. It supplies complete coverage for the single mayoral contest. |
| 2006 council, two pages | **Accept 41 edges** | The Wards 1–22 and 23–44 pages together address all 44 wards. Wards 39, 40 and 42 are explicit no-choice observations. Mark 2006 Star council coverage comprehensive; add no negative edges. |
| 2014 council, two pages | **Accept 44 edges** | The authenticated “Looking for city-builders” and “Picking the best council” pages each provide one positive choice across their stated ward ranges. Mark 2014 Star council coverage comprehensive. |
| 2018 council, two pages | **Accept 25 edges** | The two authenticated pages cover Wards 1–12 and 13–25. Ward 7’s discussion of Tiffany Ford is praise, while Anthony Perruzza is the selected electoral choice; create only the Perruzza edge. Mark 2018 Star council coverage comprehensive. |

The authenticated archive did **not** recover the 2014 Star mayoral online
editorial. It remains a separate high-confidence **HOLD**, outside the 151-row
proposal, until a qualifying original/cached copy or direct attribution is
preserved.

The six authenticated Star by-election searches (2016 Ward 2, 2017 Ward 42,
2021 Ward 22, 2023 Ward 20, 2024 Ward 15, and 2025 Ward 25) are accepted as
bounded `partially_searched` coverage dispositions. Their stated publication,
pre-poll window, terms, result counts, and title/metadata review are sufficient
for that modest state. They do not support a "no Star endorsement" assertion or
any candidate-level negative.

## Sun 2018: multi-candidate decisions and coverage

**Accept both positive edges in Ward 15 and both in Ward 20.** The article is
explicitly an endorsement package, not a neutral profile:

- Ward 15’s heading names **“Jon Burnside or Jaye Robinson”** and the
  authenticated summary says the board regarded both incumbents as quality
  candidates and voters as well served by either. This is an expressly
  non-exclusive positive recommendation of both candidates.
- Ward 20’s heading names Michelle Holland-Berardinetti, and the body says
  voters cannot lose with **either** Holland-Berardinetti or Gary Crawford and
  that the board would keep **both**. In the context of the article’s stated
  endorsements, this is sufficient affirmative support for both, not a passing
  mention.

Consequently, the 2018 Sun council package has at least one explicit positive
selection in every Ward 1–25 and two in Wards 15 and 20. Retain or set its
coverage state to `comprehensive_source_found`; that means the source package
is complete, **not** that every other candidate is negatively coded.

Ward 10’s Karlene Nation praise is not an edge: Kevin Vuong is the named,
reasoned selection. The package’s John Tory mayoral cross-reference is
corroboration only, because the 2018 Sun mayoral fact already exists.

## Import rules

1. Create one confirmed `editorial_choice` assertion per accepted canonical
   pair, with `date_precision=day` and the package’s ProQuest document URL.
   Use a source type that identifies authenticated publisher-editorial access
   (for example, `publisher_editorial_authenticated_archive`) and retain the
   publisher URL as a secondary stable public locator where available.
2. Do not create rows for explicit no-choice, acclamation, praise, or
   narrative-context observations. Preserve those only in package research or
   coverage notes.
3. Add the 151 accepted Star facts; none duplicates a current Star assertion.
   Add only **14 new** Sun 2018 council facts. The other **13** accepted Sun
   rows already exist in the assertion curation and must be **updated in place**
   with the authenticated ProQuest provenance/date rather than inserted again.
4. The 14 new Sun candidacies are: Giorgio Mammoliti (W7), Ana Bailão (W9),
   Kevin Vuong (W10), Joyce Rowlands (W11), Joe Mihevc (W12), Lucy Troisi
   (W13), Mary Fragedakis (W14), Jon Burnside and Jaye Robinson (W15), Denzil
   Minnan-Wong (W16), Brad Bradford (W19), Michelle
   Holland-Berardinetti and Gary Crawford (W20), and Norm Kelly (W22).
5. Expand coverage only at the demonstrated package grain: Star council 2003,
   2006, 2014 and 2018; Star 2006 mayor; and Sun council 2018. Leave the Star
   2014 mayor and all bounded by-election cells in their appropriate open-world
   states.

## Final outcome

The authenticated phase clears the full Star 151-edge proposal and the full
Sun 27-edge package. The corresponding canonical curation change is now
authorized by this validation, subject to the normal CSV/output/release checks.
