# Toronto endorsement census, 2003–2026

**Status:** Approved design  
**Date:** 2026-08-28  
**Repository:** `toronto-election-results`

## Purpose

Build one audited endorsement census covering historical Toronto mayoral and
City Council elections from 2003 onward and the current 2026 election. The work
closes known historical gaps, particularly paywalled Toronto Star and Toronto
Sun editorials, while applying the same evidence and coverage rules to newly
published 2026 endorsements.

This phase ends with canonical, release-ready Results data. It does not change
the model, Backend feeds, or public frontend. Those uses will be designed only
after the completed evidence and coverage are reviewed.

## Frozen endorser panel

The census is limited to the nine already approved Endorsers:

1. Progress Toronto;
2. Toronto Star Editorial Board;
3. Toronto Sun Editorial Board;
4. CUPE Ontario;
5. Elementary Teachers of Toronto (ETT);
6. Amalgamated Transit Union Local 113;
7. David Miller;
8. John Tory; and
9. Olivia Chow.

Archive discoveries do not expand this panel during the pass. Credible facts
involving an out-of-panel Endorser may be noted as out-of-scope leads, but they
do not enter the census or silently change its completeness denominator.

The existing eligibility dates and office-applicability decisions remain
authoritative. The census covers Toronto mayor and City Councillor contests,
including general elections and by-elections. Trustees and other offices are
out of scope. Individual former or current mayors are searched only from their
existing eligibility dates; no pre-eligibility endorsements are imported.

## Governing semantics

ADR 0008 remains controlling. An Endorsement is a positive edge from one exact
Endorser to one exact Candidacy in one Contest. The dataset is open-world:
absence of a verified fact never means opposition, neutrality, or an
endorsement of another candidate.

Assertions remain distinct from adjudicated facts. Coverage remains distinct
from both. Parent bodies, locals, affiliates, editorial boards, publishers,
owners, coalitions, officeholders, and individual members are not
interchangeable.

The evidence must establish an affirmative selection by the exact approved
Endorser and must have been published before polls closed. Existing approved
wording exceptions, including Progress Toronto's champion selections, retain
their source wording and canonical treatment.

## Research unit: election source packages

The primary research unit is an Endorser's source package for an election
event, not an individual candidate query. A package may be:

- one editorial selecting a mayoral candidate;
- one council-endorsement article;
- a multi-part editorial series covering groups of wards;
- a union or organization slate;
- a set of first-party announcements that together forms a demonstrably
  complete package; or
- an individual officeholder's published list of endorsed candidates.

The expected census is generated from canonical Contests and the frozen panel.
Related Contest cells are grouped under a likely source package without losing
their individual Contest identities. One validated package may therefore
support multiple positive facts and multiple coverage cells.

Candidate-name searches are a recovery and verification technique, not the
default unit of work. Discovery begins with the Endorser, election date window,
office, and likely package language. This is especially important for
newspaper editorials, where a single package or short series may resolve an
entire election.

## Research-control census

The implementation will provide a deterministic census or queue derived from:

- canonical election events and Contests;
- the frozen Endorser panel;
- eligibility and office-applicability rules;
- existing assertions and confirmed facts; and
- existing coverage selectors and assessed-through dates.

The census is a research-control artifact, not a second canonical endorsement
dataset. It identifies expected source packages, current disposition, related
Contest cells, existing evidence, and outstanding research. Human research
decisions continue to enter the existing assertion and coverage curations, and
the existing assembly remains the only path into canonical output tables.

Every expected package has one operational disposition:

- `validated_package_found`;
- `partial_evidence_only`;
- `searched_no_recoverable_package`;
- `source_unavailable`; or
- `not_yet_searched`.

These operational labels guide research. They do not manufacture endorsement
facts or candidate-level negatives and need not become a new public release
table.

## Coverage rules

Coverage is recorded at the broadest level directly supported by the evidence:

- A complete newspaper package covering every ward may establish
  comprehensive council coverage for that paper and election.
- A mayoral editorial establishes coverage only for that mayoral Contest.
- A complete slate establishes coverage only for the Contests demonstrably
  included in the slate's declared scope.
- An isolated candidate announcement establishes one positive assertion but
  does not prove that no other candidates were selected.
- A bounded search records what was searched and through when, but does not
  turn an unrecovered package into a non-endorsement conclusion.
- Inaccessible, missing, or incomplete archives are recorded as limitations,
  not negative facts.

Existing coverage-state vocabulary and fail-closed selector expansion remain
authoritative for canonical output. If implementation requires more detailed
operational states, they remain in the research-control layer unless a separate
schema change is justified and approved.

For 2026, every result is an explicit as-of snapshot. Searches record an
`assessed_through` date. Before polls close, 2026 coverage cannot be declared
complete for the election merely because no further package has yet appeared.
Later passes move the date forward and add new evidence without rewriting the
meaning of earlier searches. The pipeline rejects a backwards movement in the
assessment date.

## Paywalled and authenticated evidence

U of T Libraries access may be used to retrieve otherwise unavailable Star,
Sun, or other approved-panel evidence. Authenticated evidence is sufficient by
itself when it directly satisfies the endorsement gate; a second public source
is not required.

Each authenticated source record must retain enough durable metadata for an
independent audit:

- publication;
- editorial board or exact attributed Endorser;
- article or package title;
- publication date and, when available, time;
- page, issue, document identifier, or database record identifier;
- U of T database or provider used for retrieval;
- retrieval date;
- stable publisher, catalogue, DOI, permalink, or bibliographic URL when
  available;
- the exact candidate and election context supported; and
- a concise evidence summary.

A short supporting excerpt may be retained when useful and permitted. The
repository must not contain institutional credentials, cookies, authenticated
session URLs, full downloaded articles, page-image collections, or licensed
database exports. Authentication and multifactor prompts are completed by the
user. The research workflow operates only after access is established.

If licence terms prevent retention of an excerpt or document, bibliographic
metadata plus a sufficiently specific paraphrased evidence summary is the
durable record. Paywall status is a provenance characteristic, not a lower
evidence grade.

## Discovery and independent validation

The established Luna/Terra protocol applies to every source package.

### Luna discovery

Luna:

1. searches for the expected source package;
2. records queries, archives, databases, date windows, and retrieval paths;
3. identifies every plausible positive selection in the package;
4. proposes exact Endorser, candidate, election, timing, evidence type, and
   coverage disposition;
5. records exclusions and ambiguity rather than resolving them by inference;
   and
6. produces a human-readable discovery report with source locators.

For Star and Sun, Luna searches public publisher archives first, then uses U of
T sources for missing material. For the other seven Endorsers, Luna begins with
first-party sites, document archives, preserved social posts, web archives, and
reputable contemporaneous direct attribution.

### Terra verification

Terra independently checks:

- exact Endorser identity;
- exact candidate and canonical Candidacy/Contest resolution;
- publication timing before poll close;
- whether the source language is an affirmative selection;
- whether the evidence is primary or a qualifying direct attribution;
- whether a package is complete enough for the proposed coverage state;
- whether any package member, exception, withdrawal, death, or superseded
  candidacy needs special handling; and
- whether all bibliographic and authenticated-access metadata are adequate.

Terra assigns confirm, hold, reject, or coverage-only dispositions. Luna's
proposal never writes directly to canonical curations. Only Terra-validated
decisions are applied.

## Execution order

Research proceeds by Endorser in this order:

1. Toronto Star Editorial Board;
2. Toronto Sun Editorial Board;
3. Progress Toronto;
4. ATU Local 113;
5. CUPE Ontario;
6. Elementary Teachers of Toronto;
7. David Miller;
8. John Tory; and
9. Olivia Chow.

The newspaper archive deficit is addressed first, but all nine use the same
census, evidence gate, and canonical assembly. Within an Endorser, election
events are processed chronologically unless archive structure makes a grouped
search materially more reliable.

## Data flow and repository boundaries

All implementation and canonical data changes belong in Results:

1. canonical Contests and panel rules generate the expected census;
2. Luna discovery reports propose package and fact decisions;
3. Terra reports validate or reject those proposals;
4. accepted decisions update endorsement assertion and coverage curations;
5. existing assembly resolves IDs and produces `endorsers`,
   `endorsement_assertions`, `endorsements`, and `endorsement_coverage`;
6. validation compares the generated delta with the reviewed decisions; and
7. the Results release bundle packages the canonical tables and provenance.

Polling does not own endorsement facts. Backend does not infer, score, or
transform them during this phase. The frontend does not display them during
this phase.

## Failure handling

The workflow fails closed when:

- a candidate does not resolve to exactly one Candidacy in the expected
  Contest;
- an assertion was published after polls closed;
- a source names a different entity from the approved Endorser;
- an authenticated citation lacks enough metadata for later audit;
- a package-level coverage selector expands beyond the demonstrated scope;
- duplicate package or curation keys are introduced;
- two packages create conflicting facts or coverage decisions;
- eligibility or office-applicability rules are violated; or
- a 2026 assessment date moves backwards.

Ambiguity produces a hold, not a best-guess fact. Unavailable sources preserve
the gap explicitly. The existing unresolved John Tory/Cynthia Lai assertion
remains unresolved unless this pass supplies both admissible evidence and a
valid canonical treatment; it is not silently dropped or confirmed.

## Verification

Automated verification will cover:

- deterministic expected-census inventory;
- correct eligibility and office scope;
- unique package, assertion, and coverage keys;
- exact Candidacy and Contest resolution;
- pre-poll publication timing;
- coverage-selector expansion limited to intended Contests;
- authenticated-source metadata requirements;
- non-regressing `assessed_through` dates;
- existing open-world and exact-entity invariants;
- CSV/Parquet parity for all four canonical endorsement tables;
- deterministic full-pipeline rebuilds; and
- release-manifest hashes, row counts, and source provenance.

The final Terra audit compares the complete generated delta with the research
decisions. It enumerates confirmed facts, holds, rejects, exclusions, coverage
changes, and every newly comprehensive cell. It also confirms that no
out-of-panel Endorser entered the canonical census.

## Completion and review gate

The research pass is complete when:

- every expected Endorser/election source package has a recorded disposition;
- every proposed fact has independent Terra validation;
- every coverage claim has documented scope and evidence;
- the 2026 snapshot records its exact assessed-through date;
- all Results tests and release validators pass;
- a clean rebuild reproduces the same canonical artifacts; and
- a human-readable final report describes confirmed facts, archive gaps,
  inaccessible sources, holds, rejects, and remaining limitations.

The completed branch will contain the census mechanism or artifact, Luna
discovery reports, Terra verification reports, updated curations, rebuilt
canonical output, and a release-ready bundle. No GitHub release is published
until the project owner reviews the evidence and coverage report and gives
explicit approval. Modelling and public presentation remain separate future
design decisions.
