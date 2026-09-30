# Candidate roster refresh — September 30, 2026

Force-refreshed all three official City candidate rosters using:

```sh
uv run python -m toronto_election_results.pipeline --skip-download --refresh-candidates
```

Sources: [Mayor](https://www.toronto.ca/data/elections/candidate_list/mayorCandidates_2026.json),
[Councillor](https://www.toronto.ca/data/elections/candidate_list/councilorCandidates_2026.json),
and [Trustee](https://www.toronto.ca/data/elections/candidate_list/trusteeCandidates_2026.json).
The build manifest records each source's retrieval time and SHA-256. Its candidate snapshot date
is September 30, derived from the oldest of the three retrieval dates in Toronto time.

The source comparison found 45 website differences from the previous cached rosters. Katie
Andrachuk's website was already present through the reviewed curation, leaving 44 stale canonical
websites to update. The [complete website diff](candidate-website-refresh-2026-09-30.csv) compares
the refreshed archive with commit `01e04107ad9023f7e8f2ee86bc878627deb92b07`.

| Office | Active candidates | Canonical websites updated |
| --- | ---: | ---: |
| Mayor | 53 | 4 |
| Councillor | 190 | 21 |
| Trustee | 118 | 19 |
| Total | 361 | 44 |

Candidate membership, names, and acclamation status match the previous rosters. The rebuilt archive
changes only `campaign_url` on those 44 existing result rows; all Candidacy IDs, Person links,
votes, outcomes, and historical rows are preserved. Every candidate's campaign URL reconciles with
the freshly acquired official roster, with Katie's reviewed curation retained.

The refresh exposed a scheme-less `www.maureenlarkinto.ca` entry that previously blocked parsing
the full trustee roster. The adapter now adds HTTPS to scheme-less `www.` links while retaining
the validation gate for unsupported and malformed URLs. Regression tests exercise the complete
roster parser, all-three-roster overwrite path, and snapshot dating.

Built a local Results preview bundle and descriptive Backend council/trustee feeds from the
refreshed canonical archive. Together with the mayoral candidate feed, they contain all 361
candidates and all 44 updated campaign URLs across 25 council wards and 29 trustee wards.
This preview is local validation; it is not a published release or production deployment.

Validation: pipeline QC passed, 463 Results tests passed, and Ruff lint passed. The September 3
Scarborough Southwest provincial result remains an explicit acquisition gap, recorded separately
in the build manifest. Its absence is not a stale candidate-roster issue.
