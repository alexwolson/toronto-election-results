# Complete cohort audit

Audit date: 2026-08-26  
Frozen cohort: `results-2026-08-26.1` at `cfc5e8c946486e83745c27d92600d6227997a687`

## Completeness

- Certified mayoral candidates: 53
- Final review records: 53
- Independent dossiers: 106 (one Luna discovery and one Terra verification per candidate)
- Adjudicated occurrence leads: 114
- Confirmed existing canonical occurrences: 58
- Confirmed result backfills: 9

## Collision and complement checks

- Each canonical historical candidacy maps to at most one current mayoral subject; the mapping registry enforces uniqueness.
- Every confirmed `reuse_existing` occurrence has exactly one canonical mapping.
- Every confirmed `add_backfill` occurrence has exactly one sourced backfill row.
- Every hold, split, and reject has `ingestion_action=none` and is excluded from canonical history.
- Candidate-level confirm, hold, split, and reject totals equal the occurrence-level decision registry.
- Repeated-surname and near-name pairs in the cohort were explicitly checked, including Braeden Chow / Olivia Chow / Logan Choy and Henoke Yohannes / Leila Yohannes.
- Distinctive alternative-name identities were reconciled where primary evidence permitted it, including Edward Gong / Xiao Hua Gong / Xiaohua Gong.
- Plausible repeated-candidate histories without a bridge to the current filer remain held, including Sandeep Srivastava and Thomas Hall.
- Disproved search leads remain explicit rejects rather than silently disappearing, including the false federal claims reviewed for Laura Ellis, Sandeep Srivastava, and Weizhen Tang.

The executable complete-registry contract validates all structural invariants against the frozen 53-candidate cohort.
