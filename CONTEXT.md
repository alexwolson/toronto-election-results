# Toronto Election Results

A unified dataset of City of Toronto municipal election results (2003–present) for the
Mayor and City Councillor offices, intended to feed an election model maintained elsewhere.

## Language

**Toronto municipal election**:
An election run by the City of Toronto for local office. In scope: general elections and
mayoral/council by-elections from 2003 onward. (2000 was dropped: it has no electorate data and
weaker results provenance than later years.) School-trustee races are out of scope.

**General election**:
The city-wide election held every four years for all offices at once (2003, 2006, 2010, 2014,
2018, 2022).
_Avoid_: regular election.

**By-election**:
An off-cycle election to fill a single vacant seat between general elections. A **council**
by-election fills one vacant ward, so no candidate is a sitting holder of it (`incumbent = false`);
a **mayoral** by-election (e.g. June 26, 2023) is a city-wide contest that sitting councillors
enter, so person-based incumbency still applies. Available from City Open Data from 2016 onward —
earlier mid-term vacancies were filled by appointment, not by-election.
_Avoid_: special election, supplementary election.

**Office**:
The position being contested. Only two are in scope: **Mayor** (one city-wide seat) and
**City Councillor** (one seat per ward).
_Avoid_: seat, position, race (see Contest).

**City Councillor**:
A member of Toronto City Council elected to represent a single ward.
_Avoid_: alderman, ward councillor.

**Ward**:
A geographic electoral division that elects one City Councillor. Recorded **as each election
used it** — no cross-year reprojection — and tagged with its Ward system. Toronto used 44 wards
for 2003–2014 and 25 wards from 2018 onward; numbering and boundaries are **not** comparable
across that change.
_Avoid_: district, riding (riding is provincial/federal).

**Ward system**:
The ward regime an election ran under, distinguishing the two non-comparable eras: `44-ward`
(2003–2014, stable boundaries) and `25-ward` (2018 onward). Carried as a column so downstream
models can decide how, or whether, to bridge the two.

**Subdivision**:
The poll-level unit within a ward (a "voting subdivision"). Vote totals are summed *out* of the
results table to ward level, but subdivision **boundary polygons** (2006 onward only) are shipped
as a companion spatial dataset for downstream models that want geography.
_Avoid_: poll, precinct.

**Contest**:
A single race a candidate runs in: one office, in one ward (for councillor) or city-wide (for
mayor), in one election. The unit that vote totals sum to at ward-level grain.
_Avoid_: race, seat.

**Candidate**:
A person who appears on the ballot for one contest. The grain of a dataset row is one candidate
in one contest.

**Vote share**:
A candidate's votes divided by the total valid votes cast in that contest. The primary modelling
target.
_Avoid_: percentage, vote fraction.

**Elected**:
The boolean marking the candidate who won a contest — the top vote-getter (the sole candidate if
acclaimed), cross-checked against the council composition (every winner takes office or is a
documented mid-term departure).
_Avoid_: winner, successful.

**Candidate ID**:
A persistent identifier linking the same person across elections, assigned by **fuzzy name
matching** and carrying a **match-confidence score** — a derived, uncertain link, not ground
truth. Underpins incumbency.
_Avoid_: person key, politician id.

**Eligible electors**:
The City's `Total Eligible Electors` for a geography — electors on the Voters' List plus
election-day additions (minus deletions, 2018+). The turnout denominator. Office-independent (one
composite ballot), so a ward's figure attaches to both its councillor and its mayor slice.
_Avoid_: registered voters, electorate size.

**Ballots cast**:
The City's `Number Voted` — electors who cast a ballot in a contest's geography (ward for
councillor, city-wide for mayor). The turnout numerator.
_Avoid_: votes (that is per-candidate), total ballots.

**Turnout**:
`ballots_cast / eligible_electors` for a contest. Distinct from `vote_share`'s denominator, which
counts only valid votes cast *for candidates* in one office.

**Incumbent**:
A candidate who was a **sitting holder of the office at the time of the election** — whether they
reached the seat by winning the prior election, winning a by-election, or being **appointed** to
fill a mid-term vacancy. Requires a Council-composition reference, not just prior election winners.
_Avoid_: sitting member (that's the source concept; incumbent is the per-row flag), returning
candidate.

**Council composition**:
The reference record of who held the Mayor and each Councillor seat immediately before a given
election, including how they got there (elected / by-election / appointed). The source that makes
true incumbency derivable.

**Acclamation**:
A contest won uncontested, with no ballots cast. The winner is `elected` with `acclaimed = true`
and null votes / vote share.
_Avoid_: uncontested win, unopposed.
