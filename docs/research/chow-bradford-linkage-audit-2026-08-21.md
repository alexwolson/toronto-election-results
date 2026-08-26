# Olivia Chow and Brad Bradford linkage audit — 2026-08-21

## Scope and method

This is a research-only audit of the release covering **2003-01-01 through
2026-08-20**. I checked the CSV and Parquet result, link, and People artifacts,
the candidacy identity ledger, the active identity-disposition ledger, and the
curated identity assertion in `src/toronto_election_results/identity_curations.py`.
The release contains 11 in-scope candidacies for the two requested Persons:
eight for Olivia Chow and three for Brad Bradford.

The decision standard is conservative: an official result establishes that an
occurrence exists; it does not, by itself, establish that every same-name
occurrence is the same Person. A link is confirmed here when first-party or
official institutional records bridge the career, with the City Clerk or
Elections Canada result used to verify the exact candidacy. A split requires
positive contrary evidence or a same-event collision.

## Executive finding

All 11 current links are correct and should remain confirmed:

* Olivia Chow: `per_a4291ca7539b53e2acc1c4f108bc73e6` (active).
* Brad Bradford: `per_d8dfddfb642358e299f4b428292666bf` (active).

There are no null links, active proposed links, or wrong-person links among
these 11 candidacies. There are no same-event collisions. The release also
contains a deprecated Olivia Chow Person, `per_eab5d793562056d8bf6ef814d5ec6674`,
redirecting to the active ID; its historical link rows have `valid_to_release`
set to `2026-08-20` and must not be treated as competing current links.

The surname search has several deliberate non-matches: M. H. Fatique Chowdhury
Kabir, Andre Chow-Leong, James Chow, and Lawrence Lychowyd are separate
Persons. None is linked to Olivia Chow. No other `Bradford` occurrence exists
in the release.

## Exact candidacy decisions

| Candidacy | Occurrence | Current candidate spelling | Current release link | Decision and evidence |
|---|---|---|---|---|
| `can_a3451138425b591f847f2b9754a341e7` | 2003-11-10, Toronto City Council councillor, Ward 20 | `Chow, Olivia` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The City’s official councillor history lists Olivia Chow in the 2001–2003 and 2004–2006 Council terms; the official City biography says she served 14 years on Council before becoming an MP. The 2003 Clerk result is the exact release occurrence. |
| `can_fe37dded901d5906af86784a5a9abb38` | 2004-06-28, House of Commons MP, Trinity—Spadina | `Olivia Chow` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The official House of Commons roles page lists Olivia Chow as a Trinity–Spadina candidate in 2004 and defeated; the City biography bridges her Council service to her 2006 federal election, and the official Elections Canada result establishes this 2004 candidate row. |
| `can_e1c8ce61046054db9abaaac00fec448f` | 2006-01-23, House of Commons MP, Trinity—Spadina | `Olivia Chow` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The House roles page records her 2006 election and MP tenure; the City biography explicitly says she was elected MP for Trinity–Spadina in 2006 after her Toronto Council career. |
| `can_6a2df1bf407e5c7e97fa146a927e4a5a` | 2008-10-14, House of Commons MP, Trinity—Spadina | `Olivia Chow` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The House roles page records the 2008 Trinity–Spadina re-election and the official Elections Canada result establishes the occurrence. |
| `can_38801a15d10c5a99b98d9879fedfa2c7` | 2011-05-02, House of Commons MP, Trinity—Spadina | `Olivia Chow` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The House roles page records the 2011 re-election and MP tenure; this is the same official House member record as the 2006 and 2008 rows. |
| `can_f8596729724057669c4cc01eef5fc959` | 2014-10-27, Toronto City Council mayor | `CHOW OLIVIA` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The City’s official biography bridges Olivia’s Council career to her federal service and identifies her return to Toronto public life after federal politics; the 2014 City Clerk mayoral result establishes the exact candidacy. The ballot’s uppercase/reversed name is a formatting variant, not a new Person. |
| `can_7754a84422c45a848e61be0d0d30d054` | 2015-10-19, House of Commons MP, Spadina—Fort York | `Olivia Chow` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The House roles page lists the 2015 Spadina–Fort York candidacy as defeated and the Elections Canada result establishes the exact row. This is the same named House member whose roles page also records the 2004–2011 Trinity–Spadina candidacies. |
| `can_ffd12261189f582d95b5d8495efc720d` | 2023-06-26, Toronto City Council mayoral by-election | `Chow Olivia` | `per_a4291ca7539b53e2acc1c4f108bc73e6` | **CONFIRM.** The City’s official mayoral biography says Olivia Chow ran for and won Mayor in 2023; the Clerk’s official declaration lists `Olivia Chow` as elected. The reversed ballot-name order is a formatting variant. |
| `can_aeb469c9e30b5f37a4f25f6a757d2ca4` | 2018-10-22, Toronto City Council councillor, Ward 19 — Beaches-East York | `Bradford Brad` | `per_d8dfddfb642358e299f4b428292666bf` | **CONFIRM.** The City’s official councillor-history page lists Brad Bradford in the 2018–2022 Council term, and the City’s official Ward 19 profile identifies the same Brad Bradford as Councillor. The City Clerk result establishes the exact 2018 occurrence; `Bradford Brad` is the source’s surname-first ballot form. |
| `can_8a8622ea6deb5fc893af017dd09e6cb6` | 2022-10-24, Toronto City Council councillor, Ward 19 — Beaches-East York | `Bradford Brad` | `per_d8dfddfb642358e299f4b428292666bf` | **CONFIRM.** The City’s official 2022 declaration lists Brad Bradford elected in Ward 19, and the City councillor-history page lists him in both the 2018–2022 and 2022–2026 terms. Same body, office, ward, and distinctive full name; no collision. |
| `can_e2537c90636857a282bf0de3b3401f7e` | 2023-06-26, Toronto City Council mayoral by-election | `Bradford Brad` | `per_d8dfddfb642358e299f4b428292666bf` | **CONFIRM.** The City Clerk’s official mayoral declaration lists Brad Bradford as a candidate. The official Ward 19 profile and the City’s 2018/2022 councillor-history entries establish the same Brad Bradford immediately before the mayoral run; the full name is distinctive and no same-event collision exists. |

## Incumbency review

The canonical `incumbent` field is an office-specific continuity field, not a
general statement that a candidate has ever held elected office. The observed
values are consistent with that rule:

| Person / candidacy | `incumbent` | `incumbent_reported` | Assessment |
|---|---:|---:|---|
| Chow, 2003 Ward 20 councillor | `True` | null | Correct: she was the sitting councillor in the same City Council office. |
| Chow, 2004 MP | null | `False` | Correct: she was not an incumbent MP in that contest. |
| Chow, 2006 MP | null | `False` | Correct: first federal win in the release. |
| Chow, 2008 MP | null | `True` | Correct source-reported federal incumbent; canonical `incumbent` is not derived for federal rows. |
| Chow, 2011 MP | null | `True` | Correct source-reported federal incumbent; canonical `incumbent` is not derived for federal rows. |
| Chow, 2014 mayor | `False` | null | Correct: she was a mayoral challenger, not the sitting mayor. |
| Chow, 2015 MP | null | `True` | This is an Elections Canada source flag, retained in `incumbent_reported`; it does not make her the canonical same-office incumbent. The House’s official roles page records the candidacy as defeated. Treat as a source-reporting nuance, not an identity error. |
| Chow, 2023 mayor | `False` | null | Correct: the mayoral office was vacant after the prior mayor’s resignation. |
| Bradford, 2018 Ward 19 councillor | `False` | null | Correct: first election to the newly configured Ward 19 seat. |
| Bradford, 2022 Ward 19 councillor | `True` | null | Correct: same Person, same Council office and same Ward 19 seat. |
| Bradford, 2023 mayor | `False` | null | Correct: mayoral by-election for a vacant city-wide office; Ward 19 incumbency does not carry across office type. |

No incumbency correction is recommended.

## Artifact-level checks

* `data/out/election_results.csv` and `.parquet` contain exactly the 11 rows
  above with non-null intended Person IDs.
* `data/out/candidacy_person_links.csv` and `.parquet` contain exactly one
  active (`valid_to_release` null) confirmed link per row. The extra historical
  rows point to deprecated Olivia Chow and are closed at the release cutoff.
* `data/out/people.csv` and `.parquet` contain active records for Olivia Chow
  and Brad Bradford, plus the redirected/deprecated Olivia Chow record noted
  above.
* `data/reference/candidacy_identity_ledger.csv` contains all 11 candidacy
  anchors, with no missing source occurrence.
* `data/reference/identity_review_dispositions.csv` has no active unresolved or
  proposed disposition for any of these 11 rows; the current resolution is the
  curated official cross-event assertion for Chow and official/municipal roster
  links for Bradford.
* Grouping these rows by `(event_id, candidate_name)` yields no duplicate;
  therefore there is no positive split signal or same-event collision.

## Sources

Official records used to establish the occurrences and bridges:

* [City of Toronto — About Mayor Olivia Chow](https://www.toronto.ca/city-government/council/office-of-the-mayor/about-mayor/) — explicitly connects her Toronto Council career, 2006–2014 House service, and 2023 mayoral victory.
* [City of Toronto — Councillors Since 1998](https://www.toronto.ca/explore-enjoy/history-art-culture/mayors-councillors-reeves-chairmen/city-of-toronto-councillors/) — lists Olivia Chow in the 1998–2000, 2001–2003, and 2004–2006 terms, and Brad Bradford in 2018–2022 and 2022–2026.
* [House of Commons — Olivia Chow roles and election candidates](https://www.ourcommons.ca/members/en/olivia-chow%2820816%29/roles) — official MP tenures and the 2004, 2006, 2008, 2011, and 2015 federal candidacies.
* [City of Toronto — 2003 Clerk declaration](https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf), [2018 Clerk declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf), and [2022 municipal declaration](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf) — official municipal candidacy and outcome records.
* [City of Toronto — Councillor Brad Bradford](https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-19/) — official Ward 19 identity and first-party biography supplied to the City.
* [City of Toronto — 2023 mayoral by-election declaration](https://www.toronto.ca/wp-content/uploads/2023/06/900e-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor.pdf) — official declaration listing both Olivia Chow (elected) and Brad Bradford (candidate).
* [Elections Canada official results, 2004](https://www.elections.ca/scripts/OVR2004/23/data/ON.zip), [2006](https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip), [2008](https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip), [2011](https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip), and [2015](https://www.elections.ca/res/rep/off/ovr2015app/41/data_donnees/pollresults_resultatsbureau35.zip) — official federal result rows corresponding to Chow’s candidacies.

