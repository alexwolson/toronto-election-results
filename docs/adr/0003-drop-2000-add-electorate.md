# Drop the 2000 election; add electorate & turnout

Status: accepted

## Context

The dataset originally floored at 2000. But 2000 is an outlier on data quality: it is absent from
Open Data (results came from the City's archived website, with no poll-level detail and no
certified Clerk's declaration), and — decisively — **no eligible-elector / turnout data exists for
2000 anywhere** (Open Data voter-statistics start in 2003; the archived site and Wikipedia give no
absolute electorate counts). Meanwhile we are adding electorate and turnout, which every other year
has. Carrying 2000 would mean a year that is weaker on results and simply null on the new columns.

## Decision

- **Drop 2000 entirely.** The dataset floors at **2003**. The 2000-specific parser, cross-check,
  and archived reference pages are removed (recoverable from git history).
- **Add contest-level electorate columns** from the City's "Elections – Voter Statistics" datasets
  (2003–2022) + the 2023 mayoral By-Election Voter Statistics:
  - `eligible_electors` = **Total Eligible Electors** (list electors + election-day additions). This
    is the City's own turnout denominator. (The pre-election `Total Electors` was available too but
    not carried.)
  - `ballots_cast` = **Number Voted**, used consistently for all years. Rejected/declined ballots
    are published only 2018+, so they are deliberately *excluded* to keep `ballots_cast` — and thus
    `turnout` — comparable across the whole series.
  - `turnout` = `ballots_cast / eligible_electors`.
- Electorate is **office-independent** (one composite ballot), so a ward's figure attaches to its
  councillor contest and, summed city-wide, to the mayor contest.

## Consequences

- Incumbency for 2003 no longer has an in-scope prior election, so it is supplied entirely by the
  2000–2003 council roster (unchanged behaviour, just no `prior_winner` contribution for 2003).
- `turnout` is a true turnout (distinct from `vote_share`, whose denominator is only valid votes for
  one office). But `eligible_electors` is **not** a clean cross-year population series — the Voters'
  List is rebuilt each cycle and inflated by day-of registration.
- Anyone needing 2000 must recover it from git history; the electorate gap makes it a second-class
  year regardless.
