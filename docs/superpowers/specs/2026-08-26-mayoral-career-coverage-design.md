# Canada-wide mayoral candidate career coverage

**Date:** 2026-08-26  
**Status:** Approved 2026-08-26

## Purpose

The certified 2026 Toronto mayoral field contains 53 candidates. Results currently
links some of those candidacies to existing People, but a Person ID may represent
only the 2026 occurrence and does not prove that the candidate's electoral career
has been researched. The public candidate page therefore shows history for only
three candidates even though 31 current candidacies have Person IDs.

Results will conduct a fresh, independent identity and career review for all 53
certified mayoral candidates. Confirmed history will cover the candidate's full
verified Canadian public-election career, without a geographic boundary or start
date. This is a mayoral-cohort coverage policy, not a general expansion of every
councillor's career coverage.

## Coverage policy

### Mayoral candidates

For every candidate on the certified 2026 Toronto mayoral ballot, Results will seek
all verifiable candidacies in Canadian public elections, regardless of year or
geography. Included offices are municipal council and mayor, school-board trustee,
provincial or territorial legislature, the House of Commons, and other directly
elected Canadian public offices supported by authoritative results.

Appointments, party nominations and leadership contests, endorsements, political
employment, and non-electoral public roles are excluded. Those facts may provide
identity evidence but are not electoral appearances.

All 53 candidates receive the new review. Existing links for Olivia Chow, Brad
Bradford, and Edward/Xiao Hua/Xiaohua Gong are starting hypotheses rather than
exemptions because their prior audits did not use the new Canada-wide, no-time-limit
coverage boundary.

"Full verified career" means every candidacy located by the documented search and
cleared by the evidence standard as of the review date. It does not claim that an
unfindable or unavailable historical record never existed. Known limitations are
recorded explicitly.

### Councillor candidates

Councillor identity work uses the same conservative evidentiary standard. Prior
work included broad proposal adjudication, independent review, collision audits,
and focused career audits for consequential cross-office cases. Ordinary
councillor history remains contest-centred within Results' Toronto coverage, with
targeted supplemental research where required. It is not a cohort-complete,
Canada-wide, no-time-limit career search.

The public methodology must describe this coverage difference without suggesting
that councillor identity adjudication used a lower evidence standard.

## Evidence standard

An official result establishes that a candidacy occurred; a same or similar name
does not by itself establish identity. A confirmed cross-event link requires a
defensible bridge from one or more of the following:

- an election authority or other official institutional biography connecting the
  person to both occurrences;
- a candidate-controlled or candidate-authored source explicitly describing the
  prior candidacy or office;
- an archived first-party source with equivalent specificity; or
- when primary sources are unavailable, multiple independent authoritative sources
  whose combined evidence is explicit, consistent, and free of collision signals.

Official or authoritative result evidence must support the exact contest, ballot
name, date, office, geography, votes, vote share, placement, and outcome that will
be published. Derived values must be reproducible from sourced totals.

Contradictory biographical facts, simultaneous same-name candidacies, incompatible
geographies, or unresolved name collisions block confirmation until resolved.

## Independent Luna/Terra workflow

The certified cohort is frozen from a specific Results release before research
begins. Each of the 53 candidates is processed through the same workflow:

1. **Luna discovery.** Luna searches candidate-controlled biographies, election
   authorities, official archives, and other admissible sources. Its dossier lists
   observed names, possible candidacies, exact result sources, identity bridges,
   collision candidates, negative searches, and known limitations.
2. **Terra verification.** Terra receives the same candidate and scope but not
   Luna's conclusions. It independently repeats the search, verifies exact result
   facts, evaluates identity evidence, and records collision and complement checks.
3. **Primary reconciliation.** The primary reviewer compares both dossiers and
   creates an occurrence-level decision matrix. A disagreement is held unless the
   cited evidence resolves it under the stated standard.
4. **Cohort collision audit.** The reconciled cohort is checked to ensure that one
   historical candidacy is not assigned to multiple current candidates and that
   possible same-name alternatives were considered.
5. **Canonical ingestion.** Only confirmed occurrences and links enter canonical
   Results. Holds, splits, rejections, and negative searches remain durable audit
   records and do not appear as candidate history.

Luna and Terra work in separate contexts to preserve independence. Research is
performed in small waves so evidence quality can be reviewed before scaling the
same protocol across the cohort.

## Durable research artifacts

Each candidate has two human-readable dossiers:

- `docs/research/mayoral-career/2026/<candidacy-id>-luna.md`
- `docs/research/mayoral-career/2026/<candidacy-id>-terra.md`

A structured registry at
`data/reference/mayoral_career_reviews.csv` contains one row per certified 2026
mayoral candidacy with:

- cohort and subject candidacy IDs;
- certified ballot and display names;
- resulting Person ID, when established;
- Luna and Terra report paths;
- review date and source-release boundary;
- review status and limitations;
- counts of confirmed, held, split, and rejected historical occurrences; and
- the primary adjudication rationale.

Candidate-level review statuses are:

- `reviewed`: at least one prior candidacy was confirmed and no known search
  limitation prevents the documented conclusion;
- `no_verified_prior_candidacy`: the complete documented search found no prior
  occurrence that met the evidence standard; and
- `reviewed_with_limitations`: the search was performed but unavailable records or
  unresolved evidence materially limit the completeness claim.

Occurrence-level decisions are `confirm`, `hold`, `split`, and `reject`.

## Canonical ingestion

Confirmed out-of-coverage results are stored in a sourced reference input at
`data/reference/mayoral_career_backfill.csv`. Each row carries the exact result
facts, source authority, source resource, source locator, subject 2026 candidacy,
decision reference, and observed ballot name.

The Results pipeline converts those rows into the existing canonical election
events, contests, electoral districts, candidacies, results, People, and link
history. It does not publish a parallel career-history result model. Existing
deterministic ID and provenance rules apply.

A cohort-occurrence mapping records which canonical historical candidacies were
reviewed or added under this policy and which 2026 subject candidacy they support.
This permits a full audit without adding cohort-specific fields to every canonical
result row.

## Release and frontend contract

The mayoral candidate feed continues to publish canonical `past_elections` rows.
It gains structured coverage metadata describing:

- the `full_verified_canadian_electoral_career` policy;
- the cohort and review date;
- the candidate-level review status; and
- any public-safe completeness limitation.

Candidate cards display confirmed results only. Holds, rejected links, agent
reports, and adjudication detail remain in Results. The frontend renders a concise
methodology note from the coverage metadata explaining that mayoral histories are
Canada-wide and have no time cutoff, while councillor histories use ordinary
Toronto-centred Results coverage.

The frontend performs no name matching, adjudication, result calculation, or
history construction.

## Validation and failure behaviour

The Results release fails validation unless:

- the cohort contains exactly the 53 certified candidates from the frozen source
  release;
- every candidate has both Luna and Terra dossiers;
- every candidate has one final candidate-level review status;
- every confirmed historical occurrence has authoritative result provenance and a
  final occurrence decision;
- every canonical historical candidacy is assigned to at most one cohort subject;
- all confirmed Person links satisfy the existing active-link and redirect rules;
- no pending contest is published as past history; and
- rebuilding from unchanged inputs produces identical canonical IDs and data.

A failed, missing, or inconclusive research case becomes a recorded hold or
`reviewed_with_limitations`; it is never silently promoted to a match. A missing
dossier or untouched candidate is a release-blocking error.

Tests cover cohort completeness, report presence, schema validation, deterministic
IDs, source provenance, duplicate and collision prevention, exact link history,
career-feed construction, and mayor-versus-councillor coverage metadata.

## Publication sequence

After research, adjudication, ingestion, and validation:

1. publish a new stable Results release;
2. publish a Polling release pinned to that exact Results release, even if polling
   observations are unchanged;
3. rebuild and publish Backend pinned to both exact upstream releases;
4. run the Frontend production resolver against the complete release chain; and
5. deploy only after the production build and candidate-page checks pass.

## Non-goals

- Building a general biography database for every person in Results.
- Applying Canada-wide lifetime coverage to the full councillor field.
- Inferring identity from a name match alone.
- Publishing appointments, nominations, employment, or endorsements as election
  appearances.
- Showing unresolved research or agent conclusions as public candidate history.
