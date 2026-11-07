# Freezing a release

The paper cites one frozen release. These are the steps to make it, in order. The release is
frozen once the human coding of Person links (`docs/verification/human-coding-2026-11-07.md`)
and the Toronto Star search of the remaining same-name and near-name pairs are done, so that no
link changes after the audit.

## Before the tag

1. Choose the release name, `results-YYYY-MM-DD.N`, from the day of the tag.
2. Set `RELEASE_ID` in `src/toronto_election_results/pipeline.py` to that date. Links, Persons
   and Candidacy ledger rows made or closed from then on carry it.
3. Set `version` and `date-released` in `CITATION.cff`, and the release named in the README's
   Citing section.
4. Rebuild (`uv run python -m toronto_election_results.pipeline --skip-download`), rebuild again
   to check that every table is reproduced byte for byte, and run the tests.
5. If any Person link changed since the census in
   `docs/verification/link-audit-2026-11-07.md`, audit the changed joins under the same rules
   before going on. If only the file changed, for example because closed rows now carry the new
   release ID, record its SHA-256 in that report and say that the joins are the same.
6. Merge to `main`.

## The tag

7. Publish a GitHub release named for the tag from `main`. Zenodo archives the tagged
   repository and mints a version DOI.
8. Add the version DOI to the README's Citing section on `main`. The tagged copy cannot hold its
   own DOI.

## The Dataverse mirror

9. On the tagged commit, with the City's raw files in `data/raw/`, run
   `python -I scripts/build_deposit.py TAG ZENODO_VERSION_DOI OUT_DIR`. It copies the release
   tables, the documentation and the City of Toronto's raw files, which the Open Government
   Licence – Toronto lets anyone redistribute, and writes the values for the deposit form to
   `DATAVERSE.md`. The other raw files stay cited by URL and checksum in the build manifest.
10. Deposit `OUT_DIR` in the CJPS Dataverse with those values, cross-referencing the Zenodo DOI,
    and add the Dataverse DOI to the README.
