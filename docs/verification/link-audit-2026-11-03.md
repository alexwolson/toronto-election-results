# Audit of Person links, November 2026

This audit estimates two error rates in the release's Person links: how often a Person joins runs
by two different people (a false merge), and how often one individual's runs are split across two
Persons (a missed link). It was run on the release at commit `cf92e3b`, which had 8,099
Candidacies, 7,687 of them linked to 5,185 Persons.

No sampled join was found to tie two different people. With the strata weighted by size, the
one-sided 95% upper bound on the share of false merges is 3.9%. Weighted the same way, 73% of joins
were confirmed by agents working only from sources they found themselves, and the rest could be
neither confirmed nor refuted. Missed links are more common. Of 40 sampled pairs of Persons with
the same first and last name, 15 were one individual after a second check of the evidence, which
puts the share across all 196 such pairs at 37.5% (95% interval 23.8% to 52.9%). Those 15 have been
merged. The release now has 177 same-name pairs, and the 152 that were not sampled have not been
reviewed.

## Design

Two samples were drawn from the published tables by
[`scripts/draw_link_audit_sample.py`](../../scripts/draw_link_audit_sample.py) with seed 20261103.
Running it on the release at `cf92e3b` reproduces both samples, which are in
[`link-audit-2026-11-03/`](link-audit-2026-11-03/).

- Joins. Each pair of consecutive Candidacies (by election date) within one Person is a join; the
  release had 2,502. A join is stratified by the method of the later Candidacy's link: a curated
  identity assertion (1,025), a review disposition (908), incumbency reported by the election
  authority (222), the official record (216) or a Council roster (131). Forty joins were drawn from
  each of the first two strata, fifteen from each of the next two and ten from the last, 120 in
  all. The stratum records how the later Candidacy is linked, which is not always the link that
  made the join. In the official-record stratum the later Candidacy is the one its Person was
  built from, so the join was made by the earlier Candidacy's link, which for 12 of the 15
  sampled joins was a review disposition.
- Same-name pairs. Each pair of distinct Persons whose first and last names match, ignoring middle
  names and initials, may be a missed link; the release had 196. Forty were drawn.

Four agents checked the samples. None had made or reviewed any of the links, and they were told
not to read the release's identity research, curations or dispositions, so each verdict rests on
sources the agent found for itself. They searched the web (news, Wikipedia and its lists of party
candidates, campaign and party pages, candidate guides) and Elections Canada's candidate tables,
which give each federal candidate's occupation, with a limit of 35 searches each. They did not use
ProQuest, LinkedIn or pages behind a login, and name-matched databases did not count as evidence.

A join was rated confirmed when a source names both runs, gives a distinctive fact (occupation,
employer, office held, organization or a stated earlier campaign) for one run that another source
gives for the other, or shows the later candidate as the sitting holder of the seat the earlier
run won. It was rated contradicted when a source shows two different people, and not confirmed
when nothing found ties or separates the runs. A same-name pair was rated one person, different
people or undetermined on the same terms.

Each pair rated one person went to a fifth agent, which opened the cited pages, checked that the
quotes were there and matched the records, and judged the evidence against the standard the
release uses for every link (see the Identity section of [`docs/build-notes.md`](../build-notes.md)).
A shared party label is not a distinctive fact under that standard. A pair counts as one person
only if this second check accepted it.

Before sampling, the release was also checked as a whole: no Person has two Candidacies in the same
election.

Each stratum's rate has a Jeffreys posterior. The release-wide rate weights the strata by the
number of joins in each, and its interval comes from 200,000 Monte Carlo draws of the stratum
posteriors. Because no join was contradicted, the false-merge rate is reported as a one-sided upper
bound. [`scripts/summarize_link_audit.py`](../../scripts/summarize_link_audit.py) produces the
tables below from the results files, which hold each verdict with the agent's sources, quotes and
notes.

## Joins

| Stratum | Joins in release | Sampled | Confirmed | Contradicted | Not confirmed |
|---|---:|---:|---:|---:|---:|
| Curated assertion | 1,025 | 40 | 33 | 0 | 7 |
| Review disposition | 908 | 40 | 22 | 0 | 18 |
| Reported incumbency | 222 | 15 | 15 | 0 | 0 |
| Official record | 216 | 15 | 9 | 0 | 6 |
| Council roster | 131 | 10 | 10 | 0 | 0 |

The weighted share of joins that tie two different people is 0.0%, with a one-sided 95% upper
bound of 3.9%. The weighted share confirmed from the agents' own sources is 73.0% (95% interval
64.2% to 79.4%).

Every incumbency and roster join was confirmed. The 31 joins that were not confirmed are mostly
runs by minor candidates for whom the agents found nothing beyond result listings, and 21 of them
are for the same office, often in the same or a neighbouring ward. The review stratum has the
lowest confirmed share (22 of 40). Of its 18 joins that were not confirmed, eight rest on Toronto
Star articles read through ProQuest, which the agents could not use, four rest on candidate
guides from The Local that their searches did not find, and six rest on the release's structural
rules. A join that was not confirmed is not evidence of an error.

## Same-name pairs

| Verdict | Auditor | After second check |
|---|---:|---:|
| One person | 17 | 15 |
| Different people | 0 | 0 |
| Undetermined | 23 | 25 |

The share of same-name pairs that are one person is 37.5% (95% interval 23.8% to 52.9%), or about
74 of the 196 pairs.

The second check accepted 14 of the auditor's 17 pairs in full and one in part. It rejected two,
Julie Northrup and Diane Johnston, because the only tie between their runs is that both stood for
the Marxist-Leninist party, once under another party name. For John Steele it accepted the 2006
federal run and found that the evidence does not reach the 2003 provincial run already in his
Person (see Other findings).

Nine of the 15 join runs for different offices. The other six are for the same office, and in five
of them the printed name or the riding or ward changed between the runs.

## Fixes

Each accepted pair is now a person-record merge in
`src/toronto_election_results/identity_curations.py`, with the second check's rationale and
sources. Where a source covered a third Person or another held run, the merge or a disposition
includes it.

| Person | Runs joined | Sources |
|---|---|---|
| Stan Grzywna | 1999 Parkdale—High Park (Ontario) with his 2003 and 2006 runs there | Elections Ontario results; a 2007 copy of Wikipedia's list of Family Coalition Party candidates |
| Gloria Lindsay Luby | 1994 Etobicoke Ward 7 with her Toronto council runs from 1997 to 2010 | Wikipedia biography and 1994 election page |
| Sat K. Singh Khalsa | 1993 Davenport and 1997 Trinity—Spadina (federal) and 1999 Trinity—Spadina (Ontario), from three Persons | Wikipedia's list of 1999 Green Party of Ontario candidates; Elections Canada (1993) |
| Maria Saras-Voutsinas | 2014 TDSB Ward 15 and 2026 Ward 14 council | Eesti Elu (2014); Frequency News (2026); the City's 2026 candidate list |
| Unblind Tibbin | 2011 York West and 2021 Humber River—Black Creek (federal) | Angles Covered blog (2021); Elections Canada |
| John Nunziata | York South—Weston (federal, 1993 to 2000), 2003 mayor and 2014 Ward 12 | Wikipedia biography |
| Judith Snow | 1999 Don Valley West (Ontario) with her federal runs from 1993 to 2000 | Elections Canada occupations; Wikipedia; The Globe and Mail's obituary |
| John Sewell | 1999 Toronto Centre—Rosedale (Ontario) and 2006 Ward 21 | Wikipedia biography |
| Terry Parker | 2000 Parkdale—High Park (federal) with his runs there from 2004 to 2025 | Elections Canada occupations; Wikipedia's list of 2006 Marijuana Party candidates |
| Jim Conrad | 1993 St. Paul's (federal) and 1999 Willowdale (Ontario) | a 2007 copy of his Wikipedia biography; Elections Canada (1993) |
| Mehmet Ali Yagiz | 2003 and 2006 mayoral runs with his 2003 and 2006 Toronto—Danforth runs | Elections Ontario results; a 2007 copy of Wikipedia's list of 2003 independent candidates |
| John Steele | 2006 Eglinton—Lawrence (federal) with his 1994 and 2000 mayoral runs | Elections Canada occupation; The Militant (2000) |
| Pauline Browes | 1993 Scarborough Centre and 2006 Scarborough—Guildwood (federal) | Wikipedia biography; Eesti.ca (2006) |
| Ellery Hollingsworth | 1994 Scarborough Board of Education Ward 7 and 2000 Scarborough Southwest (federal) | Wikipedia's list of 2000 Progressive Conservative candidates |
| Magda Gondor Berkovits | 2006 and 2010 Ward 10 council | Wikipedia's 2010 election page |

Mehmet Ali Yagiz's 2006 mayoral run had been held against the Person with his provincial runs; a
disposition by `link-audit-2026-11-03` now confirms it. John Nunziata's 2014 run had been confirmed
to a Person that held only his 2003 mayoral run, and the merge replaces that disposition.

The fixes remove 16 Persons. The release now has 5,174 People (5,169 with a Candidacy), 7,688
Candidacies with a Person and 411 without. The samples keep the Person IDs of `cf92e3b`, so some
of them name Persons that these merges removed.

## Other findings

These came up during the audit and are not fixed here.

- John Steele's 2003 Parkdale—High Park run is in the Person with his 1994 and 2000 mayoral runs
  because an earlier review cited the Canadian Elections Database's description of the 2003
  candidate as a retired meat packer. The database groups candidates by name, and its entry is
  named for the 2006 federal candidate John Brian Steele, whom Elections Canada lists as a retired
  meat packer. The release's standard treats such databases as leads, and the audit found no other
  source on the 2003 candidate, so this link does not meet the standard.
- The release marks John Sewell as the incumbent in his 1999 Toronto Centre—Rosedale run and so
  gives him an MPP tenure in `office_tenures`. He never sat in the legislature. The flag comes
  from Elections Ontario's results file, and the release has no way to override it.
- The release labels the 2000 federal contest in Toronto—Danforth with the riding's earlier name,
  Broadview—Greenwood. Elections Canada reports the 2000 results under Toronto—Danforth.
- An Ellery Hollingsworth and a Jeremy Hollingsworth both ran for the TDSB in 2006, and a Jeremy
  Ellery Hollingsworth ran in 1997, so those trustee runs stay apart from the merged Person until a
  source places them.

## Limitations

The samples are small, and the intervals above are wide. The agents worked within a search budget
and without newspaper archives, so the confirmed share understates the support for the release's
links. The auditors and the second check were AI agents. Every verdict's sources, quotes and notes
are in the results files so that a reader can check them. Some evidence comes from archived copies
of Wikipedia pages, because the current pages no longer carry the text.

The same-name frame covers only Persons whose first and last names match after middle names and
initials are dropped. A missed link between a changed surname, a nickname or a different spelling
falls outside it, and the audit gives no estimate for those.

## Remaining same-name pairs

The release now has 177 same-name pairs. Twenty-five were in the sample and stay apart for lack of
evidence. If the sampled rate holds for the other 152, about 57 of them are one person (36 to 80 at
the ends of the 95% interval). They include Mary Hynes and Mary Trapani Hynes, Wiktor Borkowski
and Wiktor Pawel Borkowski, and Franz Cauchi and Franz L. Cauchi. Until they are reviewed with the
same method, this estimate stands as a known limitation of the release.
