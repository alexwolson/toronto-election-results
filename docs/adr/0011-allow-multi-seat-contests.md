# Allow multi-seat Contests

Status: accepted (2026-10-29). Amends ADR 0006 and the Contest definition in CONTEXT.md.

## Context

Every in-scope Contest has been single-seat plurality. The pre-2003 coverage in ADR 0010 breaks that
rule: the first council of the amalgamated city was elected from two-member wards in 1997, and some
1994 councils and school boards also elected more than one member per ward. Splitting those wards
into artificial single-seat Contests would misstate the ballot; dropping them would remove the
elections ADR 0010 exists to cover.

## Decision

- A Contest elects `seats_available` members, taken from the authority's source or, where the source
  does not state it, from the governing statute or council composition record. It is never inferred
  from the number of winners in the data.
- Validation requires exactly `seats_available` elected Candidacies in a resolved Contest, in place of
  exactly one. An Acclamation occurs when certified candidates do not exceed `seats_available`.
- `vote_share` keeps its definition: votes divided by `total_contest_votes`. In a multi-seat Contest a
  voter may cast several votes, so shares describe shares of votes, not of voters, and are not
  comparable with single-seat shares. `seats_available` sits in the primary table so modellers can
  filter or adjust.
- Where an archived source lists votes but does not mark who was elected, `elected` is derived from
  the top `seats_available` vote totals and the Contest records that derivation in its source fields.
  A tie at the last seat leaves `elected` null for the tied Candidacies until an official outcome is
  found.

## Consequences

- Every Contest from 2003 onward keeps `seats_available = 1`; existing outputs do not change.
- Consumers who assume one winner per Contest must filter on `seats_available` for the early years.
- Incumbency and Office tenures work unchanged: each elected member gets a tenure for the ward.
