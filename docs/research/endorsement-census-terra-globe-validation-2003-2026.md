# Terra independent validation: Globe and Mail Editorial Board endorsement spike

**Verification date/cutoff:** 2026-08-28
**Verifier:** Terra
**Inputs reviewed:** [Luna public discovery](endorsement-census-luna-globe-public-2003-2026.md) and [authenticated U of T / ProQuest evidence](endorsement-census-globe-utoronto-proquest-evidence-2026-08-28.md)
**Scope:** The Globe and Mail Editorial Board; Toronto mayoral and City Council
events from 2003 through the pending 2026 election. This is a research and
methodology validation only. It does not change the approved panel, assertions,
curations, or release outputs.

## Decision

The authenticated evidence supports **three importable positive mayoral
assertions**, all attributable to the exact entity **The Globe and Mail Editorial
Board**:

| Election | Candidate | Canonical contest | Canonical candidacy | Disposition |
|---|---|---|---|---|
| 2003-11-10 general | John Tory | `con_945161409a0450f29e351ff3f263f815` | `can_1179f79bea135e8d82289930ed974496` | **CONFIRM** |
| 2010-10-25 general | George Smitherman | `con_099fbf24dd655a0e8b1720fbe2215a6a` | `can_3d13fbd9fab452a5b347fb048574b6c4` | **CONFIRM** |
| 2014-10-27 general | John Tory | `con_9250eb2b2609550597520e68352ac56a` | `can_b3ecaef663ba56adbab70efbcb5004da` | **CONFIRM** |

Each ID resolves uniquely in the current canonical results, and all three
editorials predate their respective polls. The evidence is sufficient under the
approved authenticated-source standard. The facts should nevertheless remain
**outside the frozen systematic panel** unless the owner explicitly changes its
eligibility rule.

## Source, entity, and timing audit

| Item | Source-quality finding | Endorser identity and timing | Terra outcome |
|---|---|---|---|
| 2003, *Choosing the next mayor of Toronto*, 2003-11-01, A24, ProQuest `383973430` | Authenticated original full text; a stable provider target and editorial-page metadata are recorded. The public reproduction independently preserves the same dated conclusion. | The item compares the mayoral field and explicitly selects Tory. November 1 is before the November 10 poll. | **CONFIRM** — the conditional formulation (“if marking one ballot”) is still an explicit board choice, not neutral analysis. |
| 2010, *The Globe’s endorsement for Mayor of Toronto*, 2010-10-21, ProQuest `2385373871` | Authenticated original full text. The public record’s one-day date discrepancy is resolved by the ProQuest record. | The title and text explicitly present the Globe’s guarded choice of Smitherman. October 21 is before the October 25 poll. | **CONFIRM** — “guarded” describes qualification, not absence of an endorsement. |
| 2014, *Globe editorial board endorsement: John Tory is Toronto’s best bet*, 2014-10-17, ProQuest `2383842806` | Authenticated original full text and exact title. A contemporaneous CityNews report and the Globe public editor independently identify the choice. | The title expressly names the editorial board and Tory. October 17 is before the October 27 poll. The public editor distinguishes the board’s institutional view from Marcus Gee’s individual municipal-columnist view. | **CONFIRM** — this is the clearest exact-entity record. |

The three records are editorial-board choices, not news reporting, personal
columns, campaign claims, or endorsements by another organization. The Globe
public editor describes the editorial-board view as the newspaper’s institutional
view, which supports the precise Endorser identity used here. No full licensed
text, credentials, or session material should be stored in the repository.

## Bounded gaps and over-reading controls

The authenticated searches materially improve the research record, but they do
not establish that the Globe did not endorse candidates in any other event.

- **2006, 2018, 2022, and 2023 mayor:** the described election-window searches
  found reporting, commentary, policy editorials, and title false positives but
  no qualifying Globe Editorial Board choice. Retain only a bounded
  `partially_searched`/archive-gap disposition; do not create a no-endorsement
  observation or negative candidate edge.
- **Council:** no authenticated ward-by-ward or single-ward Globe package was
  recovered. The all-period title-term search is useful evidence that mayoral
  editorials were the only explicit board-election titles found, but it is not
  proof that no council package ever existed. Do not construct a council slate
  from candidate biographies, campaign claims, newspaper reporting, or named
  columnist views.
- **By-elections:** public discovery listed seven event-level gaps. The
  authenticated packet folds council packages and by-elections into a broader
  search rather than giving seven independently reproducible result logs. That
  supports a general research limitation only; it does **not** yet justify a
  separate completed-search or source-unavailable coverage row for each event.
- **2026:** the August 28 result is necessarily an open snapshot. Polling is on
  October 26, so no absence finding can close current-cycle collection.

The packet’s exclusion of the 2022 *Vote Ford for mayor of Toronto* policy
editorial is correct: it concerns provincial strong-mayor legislation, not a
Toronto municipal election choice. The same caution applies to every
favourable Globe political column or post-election policy editorial.

## Panel recommendation

**Keep the current 2023-anchored frozen-panel rule for this census.** The Globe
does not meet it because no pre-close 2023 Toronto mayoral Editorial Board
choice was recovered. The existing rule was deliberately chosen to make the
institutional panel current-cycle grounded and comparable; relaxing it just for
one newly recovered historic record would be an after-the-fact exception.

The three verified items are still valuable. ADR 0008 already permits verified
facts outside the approved panel without a completeness claim. If the project
wants to retain them before any rule change, create the exact Globe Editorial
Board endorser as **outside the systematic panel**, applicable only to the
three verified mayoral facts; do not generate an expected coverage census for
Globe council or mayoral events.

A historical-practice rule could be defensible in a future explicit methodology
revision, but only if it is general rather than Globe-specific. A workable
version would require all of the following:

1. an exact, independently operated newspaper editorial board;
2. at least three authenticated, pre-poll Toronto mayoral choices across at
   least three general-election events and at least ten years;
3. **mayor-only** applicability unless separate authenticated council-package
   evidence establishes a council practice; and
4. open-world coverage thereafter: verified facts are published, while events
   with no recovered package remain gaps rather than no-endorsement findings.

The Globe satisfies the evidentiary portion of that proposed historical
mayor-only threshold (2003, 2010, 2014), but adoption should follow a comparable
review of all plausible editorial boards—especially the National Post—so the
rule does not single out the Globe because its archive happened to be recovered
first. It would also be a material change to ADR 0008 and the approved panel,
requiring owner approval before implementation.

## Import conditions if separately authorized

For each of the three confirmed facts, use one `editorial_choice` assertion with
`review_state=confirmed`, `date_precision=day`, the applicable ProQuest URL,
and authenticated-editorial source metadata. Keep the publication dates as
2003-11-01, 2010-10-21, and 2014-10-17. Do not add a 2006, 2018, 2022, 2023, or
2026 Globe fact; do not derive any council fact; and do not infer non-endorsement
from any gap.
