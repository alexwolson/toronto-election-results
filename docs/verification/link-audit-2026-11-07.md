# Census of the joins made after the November audit, November 2026

The audit of Person links ([`link-audit-2026-11-03.md`](link-audit-2026-11-03.md)) sampled the
joins of the release at commit `cf92e3b`. The fixes that audit made, the same-name and near-name
reviews and the later identity work have since made 135 joins whose two runs were not joined at
`cf92e3b`. This census checks every one of them. Combined with the November sample, it bounds
the share of false merges among all 2,613 joins in the release.

The census was run on the link set whose `candidacy_person_links.csv` has SHA-256
`1d3b2e4655207bc0611ac07eb69afdb1e6e68f83fe0aa361d609af4d8d6dd6f9` and whose
`election_results.csv` has SHA-256
`fddd99d03c237162f0866fc425ce5e05b765d5bdd1c9cede3febf781c0572c1c`, as built at commit
`2be19d9`. Any later change to the links needs the same check before these figures apply to it.

No join was found to tie two different people. After a second check of the evidence, 51 of the
135 joins were confirmed from sources the auditors found themselves, and 84 could be neither
confirmed nor refuted. Across the 2,613 joins, with the older joins weighted by the November
sample, the share of false merges is 0.0%, with a one-sided 95% upper bound of 3.7%. The weighted
share confirmed is 71.3% (95% interval 63.0% to 77.3%).

## Design

[`scripts/draw_post_audit_frame.py`](../../scripts/draw_post_audit_frame.py) lists the joins. As
in November, a join is a pair of consecutive Candidacies (by election date) within one Person. A
join is new when its two runs were in different Persons, or one had no Person, at `cf92e3b`. The
script writes the frame the auditors saw
([`link-audit-2026-11-07/joins_frame.csv`](link-audit-2026-11-07/joins_frame.csv)), a key with
the Person, Candidacies and links behind each join, which they did not see
([`joins_key.csv`](link-audit-2026-11-07/joins_key.csv)), and the size of each stratum of the
release's joins ([`frame_strata.csv`](link-audit-2026-11-07/frame_strata.csv)).

The later Candidacy of 104 of the 135 joins is linked by a curated identity assertion, 12 by a
review disposition and one by a person-record redirect. In the other 18 the later Candidacy is its
Person's own record, so the earlier Candidacy's link made the join. 62 joins are for the same
office and 73 for different offices.

The joins were split at random into four packets of 34, 34, 34 and 33, one for each of four
agents. None had made or reviewed any of the links, and they were told not to read the release's
repository, so each verdict rests on sources the agent found for itself. The rules were those of
November: web search and pages found through it, a limit of 35 searches each, no ProQuest,
LinkedIn or pages behind a login, no web archives or mirrors, and no name-matched databases as
evidence. A join was rated confirmed when a source names both runs, gives a distinctive fact
(occupation, employer, office held, organization or a stated earlier campaign) for one run that
another source gives for the other, or shows the later candidate as the sitting holder of the seat
the earlier run won. It was rated contradicted when a source shows two different people, and not
confirmed when nothing found ties or separates the runs. A shared party label is not a distinctive
fact.

Every join rated confirmed went to one of two further agents, which had not audited any join. They
opened each cited page, checked that the quotations were on it and matched the runs, and judged
the evidence against the same standard. A user-editable wiki page without references, or an
anonymous reader comment, did not confirm a join on its own. A join counts as confirmed only if
this second check accepted it. The November sample's confirmed verdicts had no such check. No
join was rated contradicted, so none needed one.

The 135 new joins are a census, so their shares are known without sampling error. The 2,478 older
joins are estimated from the November sample, each stratum weighted by its size in the release
now. Each sampled stratum's rate has a Jeffreys posterior, and the release-wide interval comes from
200,000 Monte Carlo draws.
[`scripts/summarize_post_audit.py`](../../scripts/summarize_post_audit.py) produces the tables
below from [`joins_results.csv`](link-audit-2026-11-07/joins_results.csv), which holds each
verdict with the auditor's sources, quotations and notes, and the second check's decision and
notes.

## Results

| Verdict | Auditor | After second check |
|---|---:|---:|
| Confirmed | 54 | 51 |
| Contradicted | 0 | 0 |
| Not confirmed | 81 | 84 |

| Stratum | Joins in release | Checked | Confirmed | Contradicted | Not confirmed |
|---|---:|---:|---:|---:|---:|
| Made after the November sample (census) | 135 | 135 | 51 | 0 | 84 |
| Curated assertion | 1,023 | 40 | 33 | 0 | 7 |
| Review disposition | 889 | 40 | 22 | 0 | 18 |
| Reported incumbency | 221 | 15 | 15 | 0 | 0 |
| Official record | 214 | 15 | 9 | 0 | 6 |
| Council roster | 131 | 10 | 10 | 0 | 0 |

The older strata hold 2,478 joins against 2,502 in November. Of the November joins, 12 lost a run
that was later held and 14 now have another run between their two, while two older joins are of
runs that had a run between them at `cf92e3b` that has since been removed. The weighted share of
joins that tie two different people is 0.0%, with a one-sided 95% upper bound of 3.7%. The
weighted share confirmed from the auditors' own sources is 71.3% (95% interval 63.0% to 77.3%).

The second check rejected three of the auditors' 54 confirmations. Two joins of Hassan Husseini's
runs in York South—Weston (federal 1997, Ontario 1999, federal 2000) rested only on an
EverybodyWiki page with no references. A join of Costas Manios's 1999 and 2003 runs in
Scarborough Centre rested only on reader comments on an election-prediction site.

Of the 84 joins not confirmed, 27 rest on the release's structural rules, which by design join
runs that no source about the person ties. The other 57 rest on a source about the person, and 35
of those cite Toronto Star articles read through ProQuest, which the auditors could not use. For
the rest, the auditors found only result listings, could not open a page they needed (several of
Wikipedia's lists of party candidates), or, for nine joins, ran out of searches. A join that was
not confirmed is not evidence of an error. Twenty-five of the 135 joins are also in the human
coding sample ([`human-coding-2026-11-07.md`](human-coding-2026-11-07.md)).

## Other findings

Five accepted confirmations rest on sources weaker than the rest, and the second check said so.
Terry Parker's (2000 and 2004), Ellery Hollingsworth's and Fred Johnston's rest on Wikipedia
sentences without a citation. The last of these is one sentence in Gerry Altobello's article
calling the third-place finisher in the 1997 Ward 13 race a fellow Scarborough councillor. Paul
McKeever's rests on the Freedom Party's own archive, and Unblind Tibbin's on a blog post by a
named author that quotes him.

Five cited pages give a vote count that differs from the release's. For Danny Red Goldstick in
York South—Weston in 1993 (Wikipedia 119, release 62), Terry Parker in Parkdale—High Park in 2000
(711 against 775) and Paul Figueiras in Trinity—Spadina in 2014 (308 against 307), the release's
contest agrees with Sevi's dataset (see
[`external-reconciliation-2026-11-07.md`](external-reconciliation-2026-11-07.md)). John Turmel's
2006 Parkdale—High Park count (77 against 78) follows Elections Ontario, and Catherine Habus's
2022 Ward 2 count (2,218 against 2,318) follows the City's results. Wikipedia places David
Gershuny's 1999 Ontario run in Beaches—East York, but its vote count, placing and winner are those
of York South—Weston, where the release has it.

## Reproduce

```
git show cf92e3b:data/out/election_results.csv > /tmp/results-cf92e3b.csv
python -I scripts/draw_post_audit_frame.py --baseline /tmp/results-cf92e3b.csv
python -I scripts/summarize_post_audit.py
```

Run on the link set named above, the first command pair rewrites `joins_frame.csv`,
`joins_key.csv` and `frame_strata.csv` unchanged. The packets and verdicts are not reproducible
by script; they are recorded in `joins_results.csv`.
