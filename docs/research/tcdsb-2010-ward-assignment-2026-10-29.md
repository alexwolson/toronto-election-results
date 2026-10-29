# 2010 TCDSB ward assignment correction (2026-10-29)

## Defect

The published 2010 Toronto Catholic District School Board results listed eight candidates in two
wards each. In every pair one row held most of the candidate's votes and the other a few hundred.

The City's poll-by-poll workbook for the board
(`2010_Toronto_Poll_by_Poll_Toronto_Catholic_District_School_Board.xls`) has one worksheet per
trustee ward. Each sheet opens with a heading such as "Poll By Poll report for: TORONTO CATHOLIC
DISTRICT SCHOOL BOARD Ward: 5" and then has one block per City ward, each ending in a
"Ward N Totals" row. Three sheets also carry one block from another trustee ward's Contest:

| Sheet | Block | Candidates listed in the block | Contest the votes belong to |
|---|---|---|---|
| Ward5 | City Ward 24 | John Del Grande, Michael Issa | Ward 7 |
| Ward6 | City Ward 21 | Jo-Ann Davis, Catherine LeBlanc-Miller | Ward 9 |
| Ward9 | City Ward 26 | Angela Kennedy, Brad McCabe, Kevin Morrison, Ryan Ward | Ward 11 |

`_parse_workbook` in `trustees.py` gave every block on a sheet the ward named by the sheet. Each of
these three blocks therefore became spurious Candidacies in the sheet's ward, and its votes were
missing from the Contest they were cast in. Each of the 44 City wards appears in exactly one block
of the workbook, so nothing was counted twice.

## Fix

General-election blocks are now assigned by the candidate roster they list
(`_assign_trustee_wards`). The first block on each sheet sits under the sheet's heading and gives
that ward's roster, and every block goes to the ward whose roster it lists. The parser fails if one
ward's heading blocks list different rosters, if two wards list the same roster, or if a block lists
a roster that heads no ward. In all 21 general-election workbooks from 2003 to 2022 every block
lists exactly one ward's roster, and the three blocks above are the only ones on another ward's
sheet, so no other row changed.

By-election files keep their existing path. Each covers one Contest, apart from the 2012 TDSB
Wards 17 and 20 file, where each sheet lists only its own ward's candidates.

`_year_for` now takes the election year from the file name or the nearest directory that names a
year. It used to search the whole path, so a checkout directory with a year in its name (such as
`tcdsb2010`) gave every workbook that year and broke the tests that use absolute paths. The
pipeline passes a relative path, so release outputs were not affected.

A new release gate, `trustee_ward_collision_issues` in `release_validation.py`, rejects a candidate
name that appears in two trustee wards of one School Board at one Election event. The release has
no genuine exception. The same query finds no candidate name in two districts of one body at one
event for any other office either.

## Check against the Clerk's declarations

Affected Contests in 2010:

| Ward | Candidacies before | after | Valid votes before | after |
|---|---|---|---|---|
| 5 | 11 | 9 | 15,091 | 12,685 |
| 6 | 7 | 5 | 11,717 | 10,009 |
| 7 | 2 | 2 | 11,481 | 13,887 |
| 9 | 6 | 2 | 12,945 | 12,890 |
| 11 | 4 | 4 | 10,692 | 12,455 |

Candidacies whose votes changed (after the fix each equals the declaration):

| Ward | Candidate | Before | After |
|---|---|---|---|
| 7 | John Del Grande (elected) | 8,183 | 9,654 |
| 7 | Michael Issa | 3,298 | 4,233 |
| 9 | Jo-Ann Davis (elected) | 6,294 | 7,254 |
| 9 | Catherine LeBlanc-Miller | 4,888 | 5,636 |
| 11 | Angela Kennedy (elected) | 5,068 | 5,904 |
| 11 | Kevin Morrison | 3,546 | 4,104 |
| 11 | Brad McCabe | 1,204 | 1,424 |
| 11 | Ryan Ward | 874 | 1,023 |

The remaining Ward 5 and Ward 6 candidates already matched the declaration, and no elected outcome
changed. The trustee pages of the declarations for 2003, 2006, 2010, 2014, 2018 and 2022 were then
parsed with a scratch script (the package reads no PDFs) and compared with the release ward by
ward. All 232 general-election trustee Contests in
those years match by candidate and vote count, and the two 2022 Contests the declaration marks void
have no Candidacy rows. Before the fix the only mismatches were the five 2010 TCDSB wards above.

## Retired Candidacies

These eight rows were votes from the Contest in the last column. Their ledger rows were deleted and
their rows stripped from `election_results.csv` and `candidacy_person_links.csv` before the
rebuild. The eight real Candidacies kept their IDs.

| Candidacy | Candidate | Ward shown | Votes | Contest |
|---|---|---|---|---|
| `can_7c93d3db7ee35456bd409f180cb3796c` | John Del Grande | 5 | 1,471 | Ward 7 |
| `can_a61df2c6674759f8980ba3ebe9d62e27` | Michael Issa | 5 | 935 | Ward 7 |
| `can_46733f134e7052788d0fe7e6b14b41ff` | Jo-Ann Davis | 6 | 960 | Ward 9 |
| `can_708733b1951f5dfea952d00789d95e74` | Catherine LeBlanc-Miller | 6 | 748 | Ward 9 |
| `can_bdebbc1bc209571bb822180ba1c83abe` | Angela Kennedy | 9 | 836 | Ward 11 |
| `can_ed0b6688e386591fa61a6ba45f49b644` | Brad McCabe | 9 | 220 | Ward 11 |
| `can_27eeec08461051ba9207daf09935b243` | Kevin Morrison | 9 | 558 | Ward 11 |
| `can_c570b62122c656c896e38110b62cdef4` | Ryan Ward | 9 | 149 | Ward 11 |

## Identity records

- `identity_review_dispositions.csv`: the seven decisions on retired Candidacies were removed
  (three unresolved, four rejected). The four rejections cited the same-name collision that this
  defect created.
- Catherine LeBlanc-Miller, 2010 Ward 9 (`can_bfb4251aac145441b5ec9fd4ac7c75ac`): the earlier
  decision rejected `per_1532e26a4057567c93e20e166067edcc`, the Person holding her 2003 and 2006
  Ward 9 wins, because the same name also appeared in Ward 6. The Globe and Mail's 2010 election
  report says she "was unseated in Ward 9 (Toronto) by Jo-Ann Davis", and The Catholic Register's
  report says Davis "defeated long-time trustee and former chair Catherine LeBlanc-Miller". The
  Register had named her TCDSB chair for 2008. The decision is now confirmed with high confidence
  under reviewer `tcdsb-2010-ward-assignment-review-2026-10-29`. Structural continuity also holds:
  same board and ward, a four-year gap, an uncommon name and, after the fix, no namesake.
- Kevin Morrison: the bootstrap had created `per_0f6b3c990ec85336a61dcdf54c43dfd6` for the spurious
  Ward 9 row, which sorted ahead of his Ward 11 row, and his five real Candidacies were curated onto
  `per_5f4f8c32ad01536bb991d193fb1b4b9e`. The declaration lists one Kevin Morrison in 2010, in
  Ward 11, and his 4,104 votes there include the 558 that had been filed under Ward 9. The
  `kevin-morrison-tcdsb-ward11-to-ward9-continuity` assertion now names both records with
  `per_5f4f8c32...` as canonical, so `per_0f6b3c99...` is a deprecated redirect. A separate merge
  assertion was not possible because that assertion already pins every Morrison Candidacy. The
  pending 2026 council proposal for a Kevin Morrison (`can_0d98ec79ea1f5994b1be5f4299a9f756`) that
  pointed at the old record was re-homed to `per_5f4f8c32...` and is still only a proposal.
- Angela Kennedy: the 2026 trustee career review held a `reject` decision on the spurious Ward 9 row.
  It was removed from `trustee_career_decisions.csv`, and the review's `rejected_count` in
  `trustee_career_reviews.csv` went from 1 to 0. The `angela-kennedy-tcdsb-and-ontario-continuity`
  rationale no longer mentions a separate 2010 Ward 9 namesake. Correction notes were added to the
  Luna and Terra reports for that review and to `identity-linkage-review-2026-08-20.md`.
- The other spurious rows (Davis, Del Grande, Issa, McCabe, Ryan Ward) had no Person of their own,
  so only their review decisions were removed.

## Counts

| | Before | After |
|---|---|---|
| Candidacies | 7,566 | 7,558 |
| Final Candidacies | 7,209 | 7,201 |
| Trustee Candidacies | 1,342 | 1,334 |
| Candidacies with a null Person ID | 958 | 950 |
| Disposition rows (unresolved / confirmed / rejected) | 1,406 (937 / 463 / 6) | 1,399 (934 / 464 / 1) |
| Deprecated People | 101 | 102 |

Contests (1,259), Election events (80) and People (4,963) are unchanged.

## Sources

- City Clerk's official declarations of results:
  [2003](https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf),
  [2006](https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf),
  [2010](https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf),
  [2014](https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf),
  [2018](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf),
  [2022](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf).
- [The Globe and Mail, "Voters choose at least 12 new school trustees"](https://www.theglobeandmail.com/news/toronto/voters-choose-at-least-12-new-school-trustees/article1215614/).
- [The Catholic Register, "Six incumbents re-elected to Toronto Catholic board" (October 27, 2010)](https://catholicregister.org/item/9389-six-incumbents-re-elected-to-toronto-catholic-board).
- [The Catholic Register, "Toronto area school boards choose 2008 leaders" (December 13, 2007)](https://catholicregister.org/features/catholic-education/item/11715-toronto-area-school-boards-choose-2008-leaders).
