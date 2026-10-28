# Carry incumbency across amalgamation through predecessor bodies

Status: proposed (2026-10-29). Amends ADR 0005. The predecessor map below is a draft for the
maintainer to confirm.

## Context

ADR 0005 defines an Incumbent as a member of the last sitting roster for the same Office type and
Represented body. The bodies first elected in 1997 had no prior roster, so under that rule no 1997
Candidacy is an Incumbent, even when a sitting Metro or North York councillor ran for the new
council. That hides the transition ADR 0010 brings into scope.

## Decision

- `incumbent` keeps its ADR 0005 meaning, so its definition does not change across the series. For
  the first election of a body created by amalgamation it is `false` for every Candidacy whose Person
  is confirmed.
- A new field, `predecessor_incumbent`, is `true` when the Person belonged to the last sitting
  roster of a designated predecessor body for the same Office type, before the first election of the
  successor body. It is null outside those first elections.
- Draft predecessor map, applied to the 1997 elections:

  | Successor body (first elected 1997) | Office type | Predecessor bodies |
  | --- | --- | --- |
  | Toronto City Council | Mayor | Councils of Toronto, North York, Scarborough, Etobicoke, York and East York (their mayors) |
  | Toronto City Council | City Councillor | Metropolitan Toronto Council and the six former municipal councils |
  | Toronto District School Board | School Board Trustee | Toronto, North York, Scarborough, Etobicoke, York and East York boards of education |
  | Toronto Catholic District School Board | School Board Trustee | Metropolitan Separate School Board |
  | French-language public board | School Board Trustee | Metropolitan Toronto French-Language School Council |
  | French-language Catholic board | School Board Trustee | French-language section of the Metropolitan Separate School Board |

- `true` and `false` follow ADR 0005's evidence rules: a confirmed Person link and a complete
  predecessor roster.

## Open questions for the maintainer

- Should Metro councillors count as predecessors for the 1997 mayoralty as well as for council?
- The 1997 school-board names and predecessors need checking against the Fewer School Boards Act,
  1997 regulations before this is accepted.
