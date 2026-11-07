# Human coding of Person links, November 2026

The audit of Person links ([`link-audit-2026-11-03.md`](link-audit-2026-11-03.md)) was carried out
by AI agents. This coding has people check a sample of the same joins and of joins made since,
so that the agents' verdicts and the release's links can be compared with human judgement, and
uses newspaper archives to settle the joins the agents could not.

## Sample

[`scripts/draw_human_coding_sample.py`](../../scripts/draw_human_coding_sample.py), with seed
20261107, draws two sections into
[`human-coding-2026-11-07/coding_sheet.csv`](human-coding-2026-11-07/coding_sheet.csv).

- Section 1 has 50 joins in random order. Twenty-five are from the 64 joins that the audit's
  agents confirmed in its assertion, review and official-record strata (11, 11 and 3). The other
  25 are from the 135 joins whose two runs were in different Persons, or had none, in the release
  the audit sampled (commit `cf92e3b`): the audit's own fixes and the later reviews. The sheet
  does not say which is which.
- Section 2 has the 31 audit joins that the agents could not confirm (18 review, 7 assertion and
  6 official-record), each with the sources the release cites for it. Fifteen of them cite
  newspaper articles in ProQuest, 29 articles in all.

A join is two consecutive runs of one Person, as in the audit. All 81 are joins in the release on
`main` at the time of the draw. [`key.csv`](human-coding-2026-11-07/key.csv) gives each row's
origin and Candidacy IDs; coders should not open it until they have finished.

## Coding

Coders use the audit's verdicts and rule. A join is confirmed when a source names both runs, gives
a distinctive fact (occupation, employer, office held, organization or a stated earlier campaign)
for one run that another source gives for the other, or shows the later candidate as the sitting
holder of the seat the earlier run won. It is contradicted when a source shows two different
people, and not confirmed when nothing found ties or separates the runs. A shared name, party or
ward is not a distinctive fact.

Section 1 is coded before the coder consults the release's identity research, curations,
dispositions or the audit's results for those people. Any source that can be cited with a URL may
be used, ProQuest included. Each verdict records the coder, the sources, the quoted words that
settle it and the minutes taken.

## Comparison

When the coding is done, this report will give, for Section 1, the coders' agreement with the
agents' verdicts on the 25 audit joins and with the release's links on the 25 later joins, and
for Section 2, how many of the 31 joins the archive sources confirm or contradict. A contradicted
join will be held or split in the release.

[Results to be added when the coding is complete.]
