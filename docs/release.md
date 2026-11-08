# Freezing a release

The paper cites one frozen release. These are the steps to make it, in order. The release is
frozen once the human coding of Person links (`docs/verification/human-coding-2026-11-07.md`)
and the Toronto Star search of the remaining same-name and near-name pairs are done, so that no
link changes after the audit.

## Before the tag

1. Choose the release name, `results-YYYY-MM-DD.N`, from the day of the tag.
2. Set `RELEASE_ID` in `src/toronto_election_results/pipeline.py` to that date. Rows already in
   the identity registry and the Candidacy ledger keep the release they record; only rows made or
   closed from then on carry the new ID. (A test build on 7 November 2026 with the ID moved
   changed no table.)
3. Set `version` and `date-released` in `CITATION.cff`, and the release named in the README's
   Citing section.
4. Rebuild (`uv run python -m toronto_election_results.pipeline --skip-download`), rebuild again
   to check that every table is reproduced byte for byte, and run the tests.
5. If any Person link changed since the census in
   `docs/verification/link-audit-2026-11-07.md`, audit the changed joins under the same rules
   before going on, and record the new SHA-256 of `candidacy_person_links.csv` in that report.
6. Merge to `main`.

## The tag

7. Tag the merged commit `results-YYYY-MM-DD.N` and push the tag. While the Zenodo GitHub
   integration is on, a GitHub release named for the tag also archives this repository on Zenodo
   as software; it is turned off once the first data record exists.

## Publication

8. Publish the version from
   [toronto-election-records](https://github.com/alexwolson/toronto-election-records), following
   its `RELEASING.md`. It builds the user package and the provenance supplement from the tag,
   publishes them on Zenodo as the version's data record, registers the version for the R, Python
   and Stata loaders, and assembles the Dataverse deposit, which adds the City of Toronto's raw
   files from this repository's `data/raw/` (the Open Government Licence – Toronto lets anyone
   redistribute them). The other raw files stay cited by URL and checksum in the build manifest.
9. Add the version DOI to the README's Citing section and to `CITATION.cff` on `main`. The tagged
   copy cannot hold its own DOI.
