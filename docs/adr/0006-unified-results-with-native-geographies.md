# Use one results table with native electoral geographies

Status: accepted

The expanded dataset uses one primary table whose grain is one Candidacy in one official Contest
across municipal, school-board, federal, and provincial elections. Common modelling fields belong
in that table, including foreign keys plus commonly used labels and metrics so routine modelling
does not require many joins. Normalized metadata tables remain authoritative; electoral-boundary
geometry and genuinely authority-specific details are companion data. Poll/subdivision
records may be parsed to produce official Contest totals but are not published as a result grain.
Every Contest identifies its election authority, electoral geography, and Boundary regime exactly
as used when votes were cast. Results are not reprojected onto a common map or joined across
authorities merely because district names match. A Boundary regime belongs to one Represented body
and geography family, and an Electoral district is identified within that regime by its official
key. This is an intentional breaking schema change: the broader model will replace ward-only
assumptions rather than preserve compatibility with the existing municipal-only schema. Every
in-scope Contest is single-seat plurality. Eligible electors, Ballots cast, and Turnout belong to
the Contest with an explicit Electorate scope and are repeated in the primary table for modelling;
there is no separate Electorate table. Explicitly labelled composite municipal-ballot statistics may
attach to Mayor and City Councillor Contests at the matching geography, but never substitute for
board-qualified trustee statistics. Published geometry is likewise limited to Contest-level
electoral geographies, replacing the current subdivision-boundary output; missing historical
geometry does not exclude a Contest or its results and is reported separately. Legal Outcome method
and data Coverage status are independent: `complete`, `partial`, and `source_missing` describe only
whether the expected official data was obtained. A source-missing Contest may ship as an explicit
placeholder without fabricated Candidacy rows, but the release cannot claim complete coverage. Each
authoritative table carries simple source authority/resource/detail fields, while one build manifest
records retrieval metadata and checksums; there is no generic provenance entity or cell-level
lineage model. The manifest also records election calls deliberately excluded because they were
cancelled before producing a result and periods where the official event archive is not provably
complete. In particular, Toronto trustee by-election Event coverage for 2003–2011 is `uncertain`.

## Published artifacts

- `election_results` — modelling-ready Candidacy rows
- `election_events`
- `contests`
- `people`
- `candidacy_person_links`
- `parties`
- `office_tenures`
- `electoral_districts` — Contest-level geometry
- one source/build manifest

Represented body, Boundary regime, and Electorate scope remain fields in their owning tables rather
than separate lookup artifacts. The dataset does not publish separate Electorate, generic
provenance, or poll-results tables.

Every public primary and foreign key is persistent across releases. Corrections deprecate or
redirect identities with visible history; published identifiers are never silently recycled.
When an authority supplies no candidate identifier, the build resolves the ballot occurrence
through the checked-in Candidacy identity ledger before assigning the public ID. The ledger's
project occurrence key is initially based on source position rather than a candidate name. Once a
Contest is registered, name or inventory changes fail closed until an explicit, release-versioned
ledger correction is recorded. The ledger is a checksummed build input, not another result grain.
Once a release manifest tracks the ledger, the next build verifies the ledger bytes against that
manifest and will not interpret a missing path as a first build. Any intentional ledger advance or
interrupted ledger-first publication that leaves the manifest behind requires explicit recovery;
silently accepting it could discard locator-correction history.

## Null semantics

- Numeric zero always means an observed zero; missing or inapplicable values are null.
- An acclaimed Candidacy is elected, with null votes and vote-derived fields. Explicitly scoped
  composite municipal turnout may remain populated.
- A void or no-winner Contest retains only facts certified by its Election authority and never has
  an inferred elected Candidacy.
- A partially covered Contest publishes known official Candidacies with unavailable fields null.
- A source-missing Contest publishes only its Contest placeholder.
