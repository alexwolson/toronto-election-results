# Record suspended campaigns as candidate facts with evidence

Status: accepted

## Context

The City Clerk's certified candidate list marks each candidate only Active or Withdrawn. A
withdrawal is the legal act, and it was available until the August 21, 2026 deadline; a withdrawn
candidate leaves the list and has no Candidacy. On October 6, 2026, Chris Alexander publicly ended
his mayoral campaign. Because that came after the deadline, his Candidacy stays on the certified
list and the ballot, can still receive votes, and the roster still marks him Active. The roster
therefore cannot say that his campaign ended, or when.

The downstream forecast needs that date. Results publishes candidate fields, so the date should
have one owner here rather than being typed into each consumer.

## Decision

- **Record a Suspended Campaign as an evidence-backed curation.** Each row of
  `data/reference/campaign_suspension_curations.csv` dates one Candidacy:
  `candidacy_id, candidate_name, campaign_suspended_on, evidence_url, verified_on, rationale`. The
  file is shaped like the campaign-URL curation. Its evidence is a first-party statement or major
  news coverage of the candidate publicly ending the campaign.
- **Treat it as an open-world fact, as ADR 0008 does for Endorsements.** A row is a positive fact.
  A null date means no Suspended Campaign is recorded; it is not a reviewed claim that the campaign
  is still running.
- **Leave the certified field alone.** The curation never removes, renames, or changes the
  Result status of a Candidacy, and it adds no column to the canonical tables. The City's roster
  stays the only source of the certified field.
- **Fail closed.** The loader rejects any of these:
  - an unknown or repeated Candidacy, or a name that differs from the Candidacy's;
  - a Candidacy outside the 2026 Toronto mayoral field;
  - a date that is not `YYYY-MM-DD`, or one after its verification or after election day;
  - evidence that is not an `http(s)` URL, or a blank field.

  The release also refuses to build when the file is missing, so a lost file cannot publish every
  date as null.
- **Scope.** Only the mayoral candidates feed publishes the date, so only 2026 mayoral Candidacies
  can be curated. Extending it to other offices is a new decision.

## Consequences

- `mayoral_candidates.json` moves from schema 5 to 6. Every candidate has a required
  `campaign_suspended_on`, either an ISO date or null, and the release manifest's
  `feed_versions.mayoral_candidates` is 6. The field changes what a consumer must show for a
  candidate who is still on the ballot. The version is bumped rather than added quietly: the
  frontend accepts only 6, and the Backend refuses a Results release older than 6. A mismatched
  pair fails the build instead of publishing a stale status.
- The Backend reads the date from its pinned Results release to start its handling of the exit.
- The frontend's /candidates page shows "Campaign suspended Oct. 6", formatted from the date.
- Polling does not read this feed version and is unaffected.
- The build manifest lists the curation among its checksummed sources.
