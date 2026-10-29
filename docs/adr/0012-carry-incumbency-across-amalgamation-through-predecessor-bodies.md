# Carry incumbency across amalgamation through predecessor bodies

Status: accepted (2026-10-29). Amends ADR 0005.

## Context

ADR 0005 defines an Incumbent as a member of the last sitting roster for the same Office type and
Represented body. The bodies first elected on November 10, 1997 had no prior roster, so under that
rule no 1997 Candidacy is an Incumbent, even when a sitting Metro or North York councillor ran for
the new council. That hides the transition ADR 0010 brings into scope.

## Decision

- `incumbent` keeps its ADR 0005 meaning, so its definition does not change across the series.
- A new field, `predecessor_incumbent`, is `true` when the Person sat, on the day before polling,
  in a designated predecessor body for the same Office type. It is set only for the first election
  of each successor body and is null everywhere else. `predecessor_office_tenure_id` names the
  supporting Office tenure, as `incumbent_office_tenure_id` does for `incumbent`.
- Predecessor map, applied to the November 10, 1997 elections:

  | Successor body | Office type | Predecessor bodies |
  | --- | --- | --- |
  | Toronto City Council | Mayor | The six former councils (Toronto, North York, Scarborough, Etobicoke, York, East York): their mayors only |
  | Toronto City Council | City Councillor | Metropolitan Toronto Council and the six former councils |
  | Toronto District School Board | School Board Trustee | The Toronto, North York, Scarborough, Etobicoke, York and East York boards of education |
  | Toronto Catholic District School Board | School Board Trustee | Metropolitan Separate School Board (English-language trustees) |
  | Conseil scolaire Viamonde | School Board Trustee | Conseil des écoles françaises de la communauté urbaine de Toronto (CÉFCUT) |
  | Conseil scolaire catholique MonAvenir | School Board Trustee | French-language section of the Metropolitan Separate School Board |

- `true` needs a confirmed Person link and a supporting predecessor Office tenure. `false` needs a
  complete last sitting roster for every predecessor body of the Contest; until those rosters are
  acquired the field is null.

## Resolved questions

- The 1997 mayoralty counts only the six former mayors. Metro councillors and the indirectly
  chosen Metro Chair are not predecessors for Mayor, which keeps the same-office reading of
  ADR 0005.
- The school boards were checked against the Fewer School Boards Act, 1997 successions. The
  Metropolitan Toronto School Board is excluded: its members were appointed from the six boards
  of education, not elected to it. The French public and French Catholic successors are the
  boards now named Viamonde and MonAvenir (district school boards 58 and 64 in 1997).

## Consequences

- The predecessor Represented-body identifiers in `predecessor_incumbency.py` are provisional
  until the 1994 municipal adapter publishes those bodies and their rosters.
- Until predecessor rosters are acquired, `predecessor_incumbent` is null for every Candidacy.
- Models that want one incumbency signal across 1997 can combine the two fields; the release keeps
  them separate so neither definition shifts.
