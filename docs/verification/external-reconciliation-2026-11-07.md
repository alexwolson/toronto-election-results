# Reconciliation with external datasets, November 2026

This check compares the release's results with two datasets compiled independently of it: Semra
Sevi's files of federal and Ontario candidates, and the Canadian Municipal Elections Database
(CMED). It was run on the release at commit `84b52d2`. Of the 749 Contests compared, 681 agree on
every candidate's name and vote total and on the winners. Each difference in the other 68 was
checked against the election authority's own results, and none is an error in the release. They
are errors in the external files, names spelled or ordered differently, two by-elections that
Sevi's Ontario file lacks, and three choices the release documents: the final recount of one 1994
race, null vote totals for Acclamations, and no Candidacy for a candidate whose votes were not
counted.

## Sources

| Dataset | Version | File | Compared |
|---|---|---|---|
| Semra Sevi, *Who Runs? Canadian Federal and Ontario Provincial Candidates since 1867*, Harvard Dataverse, [doi:10.7910/DVN/ABFNSQ](https://doi.org/10.7910/DVN/ABFNSQ) | 9 (11 April 2024) | `federal-candidates-2023-12-11rev.csv` | Toronto ridings at the 18 federal general elections and by-elections from 25 October 1993 to 20 September 2021 |
| | | `ontario candidates.csv` | Toronto ridings at the 18 Ontario general elections and by-elections from 8 June 1995 to 7 June 2018 |
| Reed Merrill, Jack Lucas and others, *Canadian Municipal Elections Database*, Borealis, [doi:10.5683/SP2/4MZJPQ](https://doi.org/10.5683/SP2/4MZJPQ) | 6 (10 April 2023) | `elec.dta` | Mayor and council races at Toronto's nine general elections from 1994 to 2022; for 1994, the former City of Toronto's mayor and council and the eight Metro Council wards within it |

Both datasets are released under CC0. The release also covers elections these files do not: the
federal elections from 2024, the Ontario elections from 2022, the 2026 municipal election,
municipal by-elections, school trustees, and the 1994 races in the other five former municipalities
and the other 20 Metro wards. Those are not checked here.

## Method

[`scripts/reconcile_external_sources.py`](../../scripts/reconcile_external_sources.py) matches each
external Contest to the release's Contest at the same election and the same riding or ward. Within
a Contest it pairs Candidacies that share a surname and a vote total, then pairs what is left by
vote total alone, which records a name difference, or by surname alone, which records a vote
difference. A Candidacy left unpaired is missing from one side. The winners are compared as well.
Names are compared after case, accents and punctuation are removed.

Three adjustments make the files comparable. The release keeps one name for a District within its
Boundary regime, so its 2000 Contest in federal district 35008 is labelled Broadview—Greenwood,
while Elections Canada and Sevi use the riding's new name, Toronto—Danforth. CMED numbers the 1994
Metro wards, and each number is mapped to the ward its winner represented. Sevi's Ontario file
marks no winners, so the top total in each riding is taken as the winner.

The script writes [`contests.csv`](external-reconciliation-2026-11-07/contests.csv), one row per
Contest compared with its status, and
[`differences.csv`](external-reconciliation-2026-11-07/differences.csv), one row per difference
with the finding that explains it.

## Results

| Source | Contests | Agree | Differ | Not in external file | Release Candidacies | External rows |
|---|---:|---:|---:|---:|---:|---:|
| Sevi, federal | 241 | 237 | 4 | 0 | 1,510 | 1,510 |
| Sevi, Ontario | 177 | 173 | 2 | 2 | 1,163 | 1,144 |
| CMED | 331 | 271 | 60 | 0 | 2,235 | 2,236 |

In 38 of the 60 CMED Contests that differ, and in two of the four federal ones, the only
difference is how a name is spelled, spaced or ordered.

## Differences in vote totals

### CMED totals that the City's results contradict

For 13 Candidacies CMED's total differs from the release's, and the City's own results give the
release's figure. Most of CMED's figures differ from the City's by one digit.

| Election | Contest | Candidate | Release | CMED | City record checked |
|---|---|---|---:|---:|---|
| 1994 | Former City Ward 10 | James Brookman | 259 | 359 | Archived 1994 results |
| 1997 | Ward 5 | Nicolo Fortunato | 1,925 | 1,952 | Archived 1997 results |
| 1997 | Ward 8 | Frank Di Giorgio | 11,487 | 22,487 | Archived 1997 results |
| 2000 | Ward 41 | Mike Thomas | 4,714 | 9,714 | Archived 2000 Ward 41 page |
| 2003 | Ward 23 | John Filion | 13,836 | 13,838 | Clerk's declaration of results |
| 2006 | Ward 24 | David Shiner | 6,930 | 6,960 | Clerk's declaration of results |
| 2006 | Ward 39 | Mike Del Grande | 7,964 | 7,064 | Clerk's declaration of results |
| 2014 | Ward 22 | Bob Murphy | 1,586 | 1,587 | Clerk's declaration of results |
| 2014 | Ward 23 | David Mousavi | 7,951 | 7,051 | Clerk's declaration of results |
| 2018 | Ward 2 | John Campbell | 13,441 | 3,441 | Clerk's declaration of results |
| 2018 | Ward 18 | Lily Cheng | 5,149 | 5,139 | Clerk's declaration of results |
| 2018 | Mayor | Logan Choy | 3,518 | 4,518 | Clerk's declaration of results |
| 2022 | Ward 13 | Nicki Ward | 3,940 | 3,840 | Clerk's declaration of results |

The archived 1994 and 1997 results are the City's PDFs in
[`data/reference/municipal_archive/`](../../data/reference/municipal_archive/), and the 2000 page
is in [`data/reference/vote2000_html/`](../../data/reference/vote2000_html/). The declarations are
the Clerk's official declarations of results for
[2003](https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf),
[2006](https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf),
[2014](https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf),
[2018](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf)
and
[2022](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf).
The release's totals from 2003 on are sums of the City's poll-by-poll files, and for these
Candidacies they equal the declarations.

### CMED's 1997 Wards 26 and 27

The City's 1997 results list Ward 27's candidates directly below Ward 26's. For five candidates
from Steve Ellis to Randy Leach, CMED's total is the one the City prints two names further down
the list: Ellis has Paul Jewett's 268, Tom Jakobek has Stan Kumorek's 1,535, Jewett has Leach's
4,837, Kumorek has Michael McDonald's 5,245 and Leach has Frances Nunziata's 14,354. CMED also
gives Sandra Bussin 12,323, where the City prints 13,323. The release has the City's figures for
all six.

### Federal by-elections

Sevi's totals differ from the release's by one to ten votes for seven candidates at two
by-elections: Scarborough—Agincourt on 11 December 2017 and Toronto Centre on 26 October 2020.
The release sums Elections Canada's poll-by-poll results, and its totals equal those in Elections
Canada's Official Voting Results for
[2017](https://elections.ca/res/rep/off/ovr_2017d/46/table12E.html) and
[2020](https://elections.ca/res/rep/off/ovr_2020/52/table12E.html). Sevi's totals agree with the
release's at the other 16 federal elections in the comparison.

### Ontario by-elections

Sevi's totals differ from the release's for nine candidates at two Ontario by-elections:
Scarborough—Rouge River on 24 November 2005 and Parkdale—High Park on 14 September 2006. The
release follows Elections Ontario's official results. There, the candidate totals sum to the
valid ballots Elections Ontario counted in each riding (16,504 and 28,516); Sevi's do not. For
example, Elections Ontario gives Bas Balkissoon 9,327 votes in 2005, where Sevi gives 9,380.

Sevi's Ontario file has no rows for the Beaches—East York by-election of 20 September 2001 or the
Scarborough—Rouge River by-election of 1 September 2016, which account for the 19 Candidacies the
file lacks.

### Choices the release documents

- Acclamations. Five acclaimed candidates have null votes in the release, which follows its rule
  that an Acclamation has no vote total; CMED records 0. They are Dennis Fotinos, Anne Johnston and
  Joe Pantalone (Metro Council, 1994) and Kyle Rae and David Soknacki (council, 2000).
- The 1994 race in the former City's Ward 3. The release carries the final judicial recount
  reported by The Globe and Mail on 16 December 1995 (Mario Silva 2,979, Tony O'Donohue 2,969).
  CMED has the election-night count printed in the City's archived results (2,976 and 2,961).
- Cynthia Lai, 2022. Lai, the councillor for Ward 23 Scarborough North and a candidate for
  re-election, died on 21 October 2022, three days before polling. The City had already printed
  the ballots, and it announced that votes cast for her would not be counted
  ([news release, 21 October 2022](https://www.toronto.ca/news/impact-of-the-passing-of-councillor-cynthia-lai-on-the-scarborough-north-ward-23-election/)).
  The Clerk's declaration lists only the other three candidates, so the release has no Candidacy
  for her in that Contest. CMED has a row for her with 0 votes.

## Differences in names

The other 52 differences concern names, and none changes a total or a winner. In 40 of them the
external file spells a name differently from the authority. For example, CMED has Frances
Ninziata for Frances Nunziata in 2000 and 2006, Mitch Goldhar for Mitch Gold in 2006 (Ryan
Goldhar was a separate candidate that year) and Matthew Wong-Tam for Matthew Wong in 2014. Sevi has
Mark Vitala for Mark Viitala in 2004. In each of the 40 the release's `candidate_name` has the
words of `candidate_name_raw`, the authority's printed name, given name first. Three more differ
only in spacing (Anna Dicarlo, Chris Mac Donald, Nick Di Nizio), and Sevi has one in the other
order (Brian Chang, 2020). In two, the external file copies the printed name and the release puts
the given name first: Worrick Russell, whom the 1997 archive printed as "Russell Worrick" (see
`data/reference/candidate_name_curations.csv`), and Zeynel Ari, whom the City's 2022
poll-by-poll file prints surname first. The other six are the same winners with names CMED spells
differently.

## Reproducing

Download the three files in their original formats from the repositories' access API and run:

```sh
python -I scripts/reconcile_external_sources.py \
  federal-candidates-2023-12-11rev.csv "ontario candidates.csv" elec.dta \
  docs/verification/external-reconciliation-2026-11-07
```

| File | Datafile | MD5 |
|---|---|---|
| [`federal-candidates-2023-12-11rev.csv`](https://dataverse.harvard.edu/api/access/datafile/10100743?format=original) | 10100743 | `44d2f813e7ce01cd7fb0bb4ac5d4f19f` |
| [`ontario candidates.csv`](https://dataverse.harvard.edu/api/access/datafile/4311750?format=original) | 4311750 | `28c1b4704be939f7b92cec2321023f22` |
| [`elec.dta`](https://borealisdata.ca/api/access/datafile/463496?format=original) | 463496 | `2251542a94056981ea3a03e8bf2045a9` |

The script reads `data/out/election_results.csv`, so a later release can be checked the same way.
