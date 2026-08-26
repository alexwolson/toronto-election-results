# Canada-wide mayoral career coverage implementation plan

**Date:** 2026-08-26  
**Design:** `docs/superpowers/specs/2026-08-26-mayoral-career-coverage-design.md`  
**Primary repository:** `toronto-election-results`

## Objective

Research and adjudicate the full verified Canadian electoral career of every one
of the 53 candidates on Toronto's certified 2026 mayoral ballot. Publish only
evidence-backed canonical results and identity links, record the coverage boundary
and limitations explicitly, and carry the resulting feeds through the existing
Results → Polling → Backend → Frontend release chain.

## Operating rules

- Freeze the cohort from the current certified Results release before research.
- Review all 53 candidates, including Chow, Bradford, and Gong.
- Luna discovery and Terra verification remain independent. Do not include one
  agent's findings or conclusions in the other agent's prompt.
- A name match is a lead, never proof.
- Do not ingest an occurrence without authoritative result facts and a qualifying
  identity bridge.
- Research agents produce evidence dossiers; the primary agent owns adjudication,
  canonical edits, tests, commits, releases, and external mutations.
- Process candidates in waves and reconcile each wave before starting ingestion.
- Preserve holds and negative searches as audit records. Never convert an
  incomplete search into a claim that no career history exists.

## Task 1: Freeze and validate the cohort

### Files

- Add `data/reference/mayoral_career_cohort_2026.csv`.
- Add cohort loading and validation in a focused Results module.
- Add cohort tests under `tests/`.

### Work

1. Export the 53 certified candidates from `mayoral_candidates.json` or its
   canonical source table, retaining candidacy ID, ballot name, current Person ID,
   event ID, contest ID, and frozen Results source commit/release.
2. Sort by candidacy ID for deterministic output.
3. Validate that the cohort exactly equals the certified mayoral contest and has
   no duplicate candidacy or Person assumptions.
4. Treat current Person IDs as hypotheses. Do not mark any candidate reviewed from
   existing link state alone.

### Tests

- Exactly 53 unique certified mayoral candidacies.
- No non-mayoral or non-2026 candidacy enters the cohort.
- The frozen cohort rebuilds byte-identically.
- A ballot change, addition, or removal fails the cohort contract visibly.

### Commit

`Define the certified mayoral career-review cohort`

## Task 2: Add review, decision, and backfill contracts

### Files

- Add `data/reference/mayoral_career_reviews.csv`.
- Add `data/reference/mayoral_career_decisions.csv`.
- Add `data/reference/mayoral_career_backfill.csv`.
- Add a cohort-occurrence mapping table.
- Add schema readers and validators in a focused Results module.
- Add dossier directories under `docs/research/mayoral-career/2026/`.

### Work

1. Define candidate-level statuses: `reviewed`,
   `no_verified_prior_candidacy`, and `reviewed_with_limitations`.
2. Define occurrence decisions: `confirm`, `hold`, `split`, and `reject`.
3. Require Luna and Terra report paths, source release, review date, limitations,
   decision counts, and primary rationale for every cohort row.
4. Require exact result and provenance fields for every confirmed backfill row.
5. Require every decision to identify its subject 2026 candidacy and proposed
   historical occurrence.
6. Add dossier templates specifying search scope, observed names, candidate claims,
   possible occurrences, exact-result evidence, identity bridges, collisions,
   negative searches, limitations, and conclusion.

### Tests

- Invalid statuses, missing reports, missing sources, and duplicate decisions fail.
- A confirmed row without an identity bridge or exact result provenance fails.
- A held or rejected row cannot enter the publishable backfill.
- Paths must resolve inside the repository and point to the correct candidate.

### Commit

`Add mayoral career review contracts`

## Task 3: Pilot the independent research protocol

### Scope

Run a five-candidate alphabetical pilot containing:

- at least one candidate with known history;
- at least one current-only Person;
- at least one null-Person candidate;
- at least one common-name collision risk; and
- at least one expected no-history case.

### Work

1. Dispatch one Luna discovery task using `gpt-5.6-luna`.
2. Independently dispatch one Terra verification task using `gpt-5.6-terra`.
3. Give both agents the approved evidence standard, cohort rows, and dossier
   template, but no conclusions from the other agent.
4. Require direct source URLs and distinguish result evidence from identity evidence.
5. Reconcile the reports occurrence by occurrence.
6. Audit false-positive risks, missing source fields, and how negative searches are
   documented.
7. Adjust only the protocol or schema—not the evidence threshold—before scaling.

### Gate

Do not begin the remaining 48 candidates until the pilot produces valid dossiers,
independent conclusions, and an unambiguous reconciliation record.

### Commit

`Pilot independent mayoral career reviews`

## Task 4: Complete all 53 Luna/Terra reviews

### Wave structure

1. Divide the certified cohort into deterministic alphabetical waves of five or
   six candidates.
2. Run Luna discovery and Terra verification concurrently for each wave in separate
   contexts.
3. Write reports only to candidate-specific files to prevent concurrent edit
   conflicts.
4. Reconcile and validate a wave before advancing it to final adjudication.
5. Track cohort progress from the structured review registry, not from chat state.

### Required dossier content

- Certified 2026 candidacy and observed name forms.
- Candidate-controlled biographical claims.
- Canada-wide, no-time-limit election-authority searches.
- Every plausible prior candidacy, including rejected alternatives.
- Exact contest and outcome source for each proposed occurrence.
- Explicit identity bridge or reason the bridge is inadequate.
- Same-name, same-event, geographic, age, career, and biographical collision checks.
- Negative searches and inaccessible source sets.
- A completeness limitation when the available record cannot support a clean claim.

### Primary reconciliation

- `confirm` only when both result facts and identity meet the approved standard.
- `hold` when identity or result evidence remains insufficient.
- `split` when evidence establishes different people.
- `reject` when a proposed target is contradicted or collides.
- Where Luna and Terra disagree, preserve the disagreement and hold unless the
  primary evidence resolves it directly.

### Commits

Commit completed, reconciled research waves in small groups using messages of the
form `Review mayoral career cohort wave N`.

## Task 5: Run the cohort-wide collision and complement audit

### Work

1. Build an index of every proposed and confirmed historical occurrence.
2. Fail on any occurrence assigned to two current candidates.
3. Check repeated surnames, name variants, aliases, simultaneous candidacies, and
   deprecated Person redirects across the complete cohort.
4. Check that every candidate's likely career claims were either confirmed or
   represented by an explicit hold/reject decision.
5. Revisit dossier conclusions when the cohort-level view reveals a collision or
   missing complement.
6. Finalize all 53 candidate-level statuses and limitations.

### Tests

- One historical candidacy maps to at most one cohort subject.
- Every confirmed occurrence is represented in exactly one decision.
- Every cohort member has two reports and a final status.
- Candidate-level decision counts equal occurrence-level records.

### Commit

`Adjudicate the complete mayoral career cohort`

## Task 6: Ingest confirmed career backfill into canonical Results

### Work

1. Implement a dedicated adapter for sourced mayoral-career backfill rows.
2. Reuse existing event, contest, district, candidacy, Person, and link-history
   constructors and deterministic IDs.
3. Preserve exact source ballot names while selecting preferred display names
   through existing identity curation rules.
4. Create or extend canonical events and contests outside Toronto and before 2003
   only for confirmed cohort occurrences.
5. Record the cohort-occurrence mapping without adding cohort-specific columns to
   every canonical result.
6. Ensure pending 2026 candidacies remain pending and never appear as past results.
7. Build twice from unchanged inputs and compare canonical IDs and artifacts.

### Tests

- Exact votes, totals, shares, rank, outcome, office, district, and date survive the
  adapter.
- Backfilled IDs are deterministic.
- Existing canonical occurrences are reused rather than duplicated.
- New links have valid active Person targets and link history.
- Holds, splits, and rejections never populate modelling `person_id` or history.
- Existing Results row counts and values change only through reviewed additions or
  identity corrections.

### Commit

`Ingest verified mayoral candidate careers`

## Task 7: Publish coverage metadata in Results feeds

### Work

1. Advance the mayoral-candidate feed schema.
2. Add top-level coverage policy, cohort, source release, and review date.
3. Add candidate-level review status and public-safe limitation text.
4. Populate `past_elections` only from confirmed canonical candidacies before the
   2026 election.
5. Keep research paths, rejected alternatives, and internal adjudication rationale
   out of the public feed.
6. Include the coverage registry and mapping tables in the Results release bundle
   when appropriate for machine audit, while keeping human dossiers in the repo.

### Tests

- All 53 feed candidates carry a review status.
- Confirmed full-career history appears most recent first.
- A reviewed candidate with no confirmed history has an empty history and the
  correct explicit status.
- Mayor coverage is `full_verified_canadian_electoral_career`.
- Existing council coverage remains Toronto-centred and is not relabelled.

### Commit

`Publish verified mayoral career coverage`

## Task 8: Update Backend and Frontend consumers

### Backend

- Accept the advanced Results feed schema without reconstructing history.
- Preserve Results coverage metadata in the Backend release or direct feed handoff.
- Add no name matching or career research logic.

### Frontend

- Update feed types for the advanced schema.
- Render a concise methodology note from feed metadata:
  mayoral careers are Canada-wide with no year cutoff; councillor histories use
  ordinary Toronto-centred Results coverage.
- Continue displaying confirmed history only.
- Do not expose holds, rejected identities, or agent names as candidate-card facts.

### Tests

- Feed parsing and schema validation.
- Methodology note content and accessibility.
- Candidate cards for prior history, no verified history, and limited review.
- Regression coverage for Chow, Bradford, Gong, and at least one newly linked
  candidate.

### Commits

- Backend: `Consume mayoral career coverage metadata`
- Frontend: `Explain verified mayoral career coverage`

## Task 9: Full validation and publication

### Results

1. Run the complete Results test suite and lint/format checks.
2. Build twice and verify deterministic artifacts.
3. Confirm all 53 cohort rows, 106 dossiers, final decision counts, and zero
   collision violations.
4. Build and publish the next stable Results release.

### Polling

1. Build a new Polling release pinned to the exact new Results release.
2. Run the complete Polling tests and release lint.
3. Publish the stable Polling release even if observations are unchanged.

### Backend

1. Hydrate the exact new Results and Polling releases.
2. Run the complete Backend suite.
3. Build forecast and all 25 council cards without modifying tracked inputs.
4. Publish a stable Backend release with exact upstream pins and checksums.

### Frontend

1. Run tests and source lint.
2. Run the real `vercel-build` resolver against the published release chain.
3. Inspect the generated candidate page for history, empty-history, and limitation
   cases.
4. Deploy with `vercel --prod` only after explicit deployment authorization.
5. Verify the production candidates page returns HTTP 200 and displays the expected
   coverage note and representative histories.

## Completion criteria

- Every certified 2026 mayoral candidate has independent Luna and Terra dossiers.
- Every candidate has a final, validated review status.
- Every published historical occurrence has exact result provenance and a confirmed
  identity bridge.
- The canonical dataset contains the full verified Canadian electoral career found
  for the cohort, without a year cutoff.
- No held, split, rejected, pending, or ambiguous occurrence appears publicly.
- Results, Polling, and Backend stable releases form one verified dependency chain.
- The Frontend explains the mayor-versus-councillor coverage distinction and builds
  successfully from that chain.
