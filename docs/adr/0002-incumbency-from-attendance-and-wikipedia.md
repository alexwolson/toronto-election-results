# Derive incumbency from council-attendance data + Wikipedia, not a single roster

Status: accepted

## Context

`incumbent` is defined as a **sitting holder of the office at election time**, including
councillors who reached their seat by mid-term **appointment** (Toronto fills many council
vacancies by appointment, not by-election). No City results file carries incumbency, and —
verified against the City's open-data portal, Clerk pages, Archives, and TMMIS — **there is
no single authoritative source giving full council composition (elected + appointed, with
dates) before each election 2000–2023.** It must be assembled.

## Decision

Build a **Council-composition reference** (sitting Mayor + Councillors immediately before each
in-scope election) from a tiered source strategy:

- **2010, 2014, 2018, 2022** — City open data **`members-of-toronto-city-council-meeting-attendance`
  ∪ `...-voting-record`**: the distinct `City Council` members in the final pre-election
  sessions. Authoritative, dated, and **includes appointees**. Both datasets are cross-checked
  because an appointee can appear in one but not the other.
- **2000** — Wikipedia's `(incumbent)` markers in the 2000 article (parsed mechanically; the
  markers are clean bullets).
- **2003, 2006** — **two independent agent-compiled rosters, reconciled**, cross-checked against
  the City's authoritative "Councillors Since 1998" roster. Both name forms are kept where the
  agents disagree. Low-confidence tier.
- **Mayor** — the mayor sits on Council, so a re-running incumbent mayor is captured by the same
  mechanism. The **2023 by-election has no incumbent mayor** (office vacant after Tory's
  resignation), but sitting 2022-elected councillors who ran are person-based incumbents.

## How the flag is set (implementation)

Two paths, in priority order:
1. **Prior-winner** — the candidate's `candidate_id` was `elected` in the immediately-prior
   in-scope election. This is the robust bulk of incumbency: because it rides on the fuzzy
   candidate identity, name-form drift (`Norm`/`Norman`, `A.A.`/`Adrian`) never breaks it.
2. **Roster** — the candidate's identity key matches a sitting member in the composition. This
   supplies 2000 and the mid-term **appointees**/by-election winners who did not win the prior
   election.

## Consequences

- Incumbency is **person-based**, so the attendance/voting datasets' lack of a ward column is
  irrelevant — we only need the set of sitting people.
- Confidence is **tiered**: prior-winner 0.95, City rosters 0.90–0.95, Wikipedia 0.85.
- Derived winners are separately validated against the composition (`crosscheck_winners`): every
  councillor winner is in the next council or a documented departure.
