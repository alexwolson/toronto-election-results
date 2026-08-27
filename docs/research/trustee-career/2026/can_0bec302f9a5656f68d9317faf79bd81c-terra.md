# Terra verification dossier: Frank D'Amico

## Review boundary

- Subject candidacy ID: `can_0bec302f9a5656f68d9317faf79bd81c`
- Certified 2026 ballot name: Frank D'Amico (acclaimed TCDSB Ward 6)
- Frozen Results release: `results-2026-08-27.1` (`ba5a660`)
- Verification date: 2026-08-27
- Scope: Toronto public elections from 2003 onward, across trustee, council, mayoral, provincial, and federal offices

## Independent identity anchors

The City certified feed and [2026 acclamation declaration](https://www.toronto.ca/wp-content/uploads/2026/08/8ed9-2026-Declaration-of-Acclamation.pdf) establish the Ward 6 candidate. The official [TCDSB board page](https://www.tcdsb.org/page/board-of-trustees) identifies Frank D'Amico as Ward 6 trustee; the board's public biography states he was first elected in 2010. The [2023 mayoral profile](https://thelocal.to/toronto-mayor-candidates-2023/) expressly identifies the mayoral candidate as that Ward 6 trustee.

## Independent Toronto election search

Searched canonical Results, City declarations, TCDSB sources, and exact/apostrophe-free/reversed forms before Luna. This produced two clusters: a single 2003 TDSB Ward 5 candidate (`per_d13ae…`) and a separate 2010–2023 TCDSB/mayoral cluster (`per_560f…`). No evidence permits their merger.

## Exact result verification

- `can_db651bb0672758849cf4f97fb3576823`: TDSB Ward 5, 2003-11-10; 3,790 / 13,939, 27.19%, rank 3 of 3, not elected. City source is the [2003 results ZIP](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/1ed53c9d-a316-465e-96ce-e72be74f8aa9/download/2003-results.zip); frozen Results verifies the facts.
- `can_643ef4ba05a85a99b80f35f11b217164`: TCDSB Ward 6, 2010-10-25; 3,759 / 11,717, 32.08%, rank 1 of 7, elected. The [2010 declaration](https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf) and frozen Results verify the facts.
- `can_d035d9ceab5c5838a266f98209ff2c3b`: TCDSB Ward 6, 2014-10-27; 8,757 / 11,622, 75.35%, rank 1 of 2, elected.
- `can_686a839bd2c459f3bd5974baaa8ed8de`: TCDSB Ward 6, 2018-10-22; 4,407 / 6,134, 71.85%, rank 1 of 3, elected. The [2018 City declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) confirms ballot candidate/votes.
- `can_a36063df8c4a52deb9d37ad8546619a2`: TCDSB Ward 6, 2022-10-24; 2,061 / 3,820, 53.95%, rank 1 of 4, elected.
- `can_6e420426261f5f3d9a66e8fdcc5b59e3`: Toronto mayoral by-election, 2023-06-26; 357 / 724,638, 0.049%, rank 24 of 102, not elected. Frozen Results verifies totals/rank; the Local bridge identifies this candidate as the Ward 6 trustee. The 2014/2022 vote facts are from City Clerk workbooks cited in frozen Results.

## Identity verification

TCDSB's first-elected-in-2010 statement links the Ward 6 trustee career; the 2023 profile directly joins the mayoral result to that officeholder; the current Board/City acclamation records establish continuation to 2026. These sources qualify the 2010–2023 occurrences. They do not identify the 2003 TDSB Ward 5 candidate.

## Collision and contradiction checks

The 2003 and 2010–2023 occurrences have different canonical persons, boards, and non-overlapping evidence chains. The TCDSB source says first elected in 2010, which is inconsistent with merging the 2003 TDSB candidate into this trustee's career. **Do not merge 2003.**

## Negative searches and inaccessible sources

Checked City/TCDSB archives and provincial/federal authority indexes under all name forms. No other Toronto occurrence was found. Older City workbooks are represented by direct locators in frozen Results.

## Luna comparison

Agreement: Luna's two-cluster analysis, five positive occurrence IDs/facts, and exclusion of 2003 are supported. Terra records the 2003 disposition as `reject` (rather than Luna's ambiguous “reject/split”) because the reviewed candidate has a separately evidenced TCDSB identity and no affirmative merger evidence.

## Limitations

The 2003 person's biography is unavailable; this does not weaken the affirmative non-merger conclusion.

## Verification conclusion

- `can_db651bb0672758849cf4f97fb3576823` — **reject** (separate same-name TDSB person).
- `can_643ef4ba05a85a99b80f35f11b217164` — **confirm**.
- `can_d035d9ceab5c5838a266f98209ff2c3b` — **confirm**.
- `can_686a839bd2c459f3bd5974baaa8ed8de` — **confirm**.
- `can_a36063df8c4a52deb9d37ad8546619a2` — **confirm**.
- `can_6e420426261f5f3d9a66e8fdcc5b59e3` — **confirm**.

Candidate status: **reviewed**.
