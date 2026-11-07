# Screen for changed surnames, November 2026

The same-name and near-name reviews ([`same-name-review-2026-11-03.md`](same-name-review-2026-11-03.md),
[`near-name-review-2026-11-04.md`](near-name-review-2026-11-04.md)) compare Persons whose printed
names match or nearly match. A candidate who ran again under a new surname would fall outside both.
[`scripts/screen_surname_changes.py`](../../scripts/screen_surname_changes.py) looks for such
pairs among the released Persons: two Persons with the same first name who ran for the same office
in the same district, at most one general election apart and never in the same election, under
different surnames. The first name must belong to no more than six Persons in the release, and
mayoral races are left out because every mayoral candidate shares one district.

The screen finds four pairs, listed in
[`surname-change-screen-2026-11-07/pairs.csv`](surname-change-screen-2026-11-07/pairs.csv). None is
joined, and all four stay separate Persons.

| District | Earlier run | Later run | Finding |
|---|---|---|---|
| Scarborough Centre (federal) | Dorothy Sauras, 2004, Communist | Dorothy Laxton, 2006, New Democratic Party | Different parties. Elections Canada lists Sauras as a retired medical social worker; no source was found on Laxton's occupation or on either name used by the other. |
| Ward 26 (council) | Muhammad Bajwa, 2000 | Muhammad Alam, 2003 and 2006 | No source ties the two names. |
| Ward 42 (council) | Venthan Ramanathavavuniyan, 2010 | Venthan Ramana, 2014 | The later surname is the start of the earlier one, so these are probably one person, but the Toronto Observer's 2010 ward guide and Toronto LocalWiki's 2014 candidate list name each run without anything that links them. A shortened surname is not among the name changes the structural rules accept. |
| Ward 20 (council) | Dean Jepson, 2003 | Dean Maher, 2010 | No source ties the two names. |

The screen cannot find a change that also moved the candidate to another office or district, or a
first name that changed as well. The ProQuest search of the Toronto Star that the earlier reviews
used for the hardest same-name groups was not repeated here.
