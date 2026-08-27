# Terra verification dossier: Dennis Hastings

## Review boundary

- Subject candidacy ID: `can_2f91a36290e058ea8f377bacce7ea2ff`
- Certified 2026 ballot name: Dennis Hastings
- Frozen Results release: `results-2026-08-27.1` (`ba5a660`)
- Verification date: 2026-08-27
- Scope: Toronto public elections from 2003 onward, across trustee, council, mayoral, provincial, and federal offices

## Independent identity anchors

- 2018 result has `per_28aee1cff92751488df840b788c6aebf`; later rows lack a link.
- The 2018 official trustee profile lists Dennis Hastings in TCDSB Ward 12: https://elections.ontarioschooltrustees.org/ResourceToolKit/2018Election/Query.aspx?board=Toronto+Catholic+District+School+Board&lang=en. TDSB official sources identify Trustee Dennis Hastings in Ward 1: https://www.tdsb.on.ca/About-Us/CEO/Learning-Centre-Model.
- A reliable education profile explicitly identifies the 2018 TCDSB candidate and 2022 elected TDSB trustee as the same Dennis Hastings: https://educationactiontoronto.com/articles/tdsbs-new-trustees-what-are-their-views-on-issues/.

## Independent Toronto election search

- Found Dennis Hastings in 2018 TCDSB Ward 12 and 2022 TDSB Ward 1. Also found four earlier **John Hastings** TDSB Ward 1 results; these are separate-person collisions.

## Exact result verification

- `can_29b93507076d5b0f91b874e85c6d47ab`: Dennis Hastings, 2018-10-22 TCDSB Ward 12, 521/9,093, 5.7297%, 5/5, not elected.
- `can_758d731c49c25e4a98554f4f9a0e69c9`: Dennis Hastings, 2022-10-24 TDSB Ward 1, 3,158/11,379, 27.7529%, 1/7, elected.
- City Clerk workbooks verify results; canonical data supplies share/rank. The 2026 candidate is pending.

## Identity verification

The education profile directly connects the 2018 unsuccessful TCDSB candidate to the elected 2022 TDSB trustee. Official TDSB records show ongoing Ward 1 service, providing a qualifying bridge to the certified 2026 candidacy.

## Collision and contradiction checks

- `can_1d5f22cb31545b39bbea76569bbdc3bb` (2006), `can_122cebab7cd954d4881ddef08d47b21a` (2010), `can_2fac6a1d01db57c1aaa9b689d02f2ede` (2014), and `can_2342d508261f551eb150d609cdcc356f` (2016) are **John Hastings**, not Dennis. They have a distinct person ID `per_13c35326e35f5616b2b579c7af89ed3c`; do not merge on surname/Ward 1.

## Negative searches and inaccessible sources

- Checked City/TDSB/TCDSB records, 2018/2022 archives, current board pages, Elections Ontario/Canada, and Dennis/John name forms.

## Luna comparison

- **Agreement — `can_29b93507076d5b0f91b874e85c6d47ab` and `can_758d731c49c25e4a98554f4f9a0e69c9`:** same facts and `confirm` dispositions.
- **Agreement — John Hastings rows:** both dossiers reject them as collisions, never Dennis history.
- **Disagreement:** none.

## Limitations

The 2026 contest is pending; identity relies on an explicit secondary bridge corroborated by official records.

## Verification conclusion

- `can_29b93507076d5b0f91b874e85c6d47ab`: **confirm**.
- `can_758d731c49c25e4a98554f4f9a0e69c9`: **confirm**.
- John Hastings 2006/2010/2014/2016 rows: **reject** as distinct-person collisions.
