# Five-candidate pilot reconciliation

**Review date:** 2026-08-26  
**Frozen source:** `results-2026-08-26.1` at
`cfc5e8c946486e83745c27d92600d6227997a687`

## Protocol findings

The independent reports agreed on the substantive career findings for Alex Cruze,
Alton Frederick, Amy Rosen, and Brad Bradford. They disagreed on Bahira Abdulsalam's
2025 Ontario candidacy: Luna found it and Terra did not.

Primary review confirmed the Ontario occurrence. Elections Ontario's official Don
Valley West tabulation records **BAHIRA ABDULSALAM**, 247 votes, sixth of six, on
2025-02-27. The VoteMate profile for that contest links to `bahira.ca` and labels its
biography and reason for running as submitted by the candidate or campaign team; it
identifies the same professional engineer, PhD holder, Toronto community advocate,
and former mayoral candidate. Together these provide authoritative result evidence
and an identity bridge beyond the name match.

The pilot also found and corrected two discovery-report errors:

- VoteMate's “fifth time running in Don Valley West” statement belongs to Sheena
  Sharp, not Bahira Abdulsalam.
- The 2018 Ward 19 candidate was Morley Rosenberg, not “Morley Rosen.”

The underlying sources resolved both errors; neither changes a confirmed career.

## Status calibration

The approved `reviewed_with_limitations` status is reserved for a concrete,
material candidate-level gap. The ordinary fact that historical municipal and
school-board archives are fragmented is part of the public review boundary and
does not, by itself, force every candidate into that status.

- `reviewed`: one or more prior candidacies are confirmed, with no concrete known
  gap that materially limits the documented conclusion.
- `no_verified_prior_candidacy`: the documented Canada-wide search found no prior
  occurrence meeting the standard and no concrete unresolved lead remains.
- `reviewed_with_limitations`: the review is complete as a task, but a specific
  missing identity anchor, inaccessible likely record, or unresolved occurrence
  materially limits the result.

This calibration preserves the design's rule that “full verified career” means all
occurrences found and verified as of the review date, not proof that an unknown
record cannot exist.

## Candidate reconciliation

| Candidate | Reconciled status | Confirmed occurrences | Material limitation |
| --- | --- | ---: | --- |
| Alex Cruze | `reviewed_with_limitations` | 0 | No independent biographical anchor beyond the certified ballot. |
| Alton Frederick | `reviewed_with_limitations` | 0 | No independent biographical anchor beyond the certified ballot. |
| Amy Rosen | `no_verified_prior_candidacy` | 0 | None; strong current identity anchors and no unresolved electoral lead. |
| Bahira Abdulsalam | `reviewed` | 3 | None after primary resolution of the missed Ontario occurrence. |
| Brad Bradford | `reviewed` | 3 | None; all three Toronto occurrences have institutional continuity evidence. |

All six confirmed occurrences already exist in canonical Results, so their
ingestion action is `reuse_existing`; the pilot adds identity linkage and mapping,
not duplicate result rows.

## Pilot gate

The protocol is suitable to scale after these adjustments:

1. Agents must search recent provincial contests explicitly even when a federal
   contest for the same candidate is found.
2. Candidate-submitted profiles may supply identity continuity, but never replace
   official result facts.
3. A reviewer must verify that snippets or adjacent candidate text are attributed
   to the correct person.
4. Collision leads must retain the exact official ballot name.
5. Generic archive fragmentation belongs in the methodology boundary; only a
   candidate-specific material gap changes the candidate status.
