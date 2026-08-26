# CUPE Ontario council-applicability correction audit

**Audit date:** 2026-08-22  
**Scope:** read-only pre-implementation audit of enabling CUPE Ontario for
Toronto councillor contests and importing the verified 2025 Ward 25 endorsement.  
**Decision under audit:** `cupe_ontario.councillor_applicable` changes from
`false` to `true`; CUPE Ontario → Neethan Shan (2025 Ward 25) is imported as a
confirmed Endorsement.

## Conclusion

The panel change is internally consistent and should be implemented. The
verified 2025 target is the **2025** Ward 25 contest—not the similarly named
2018 Ward 25 contest:

| Field | Correct value |
|---|---|
| Endorser key | `cupe_ontario` |
| Endorser ID | `edr_7ba4ca8cc46e50b3b3184eae43467614` |
| Contest | `con_c8883aeeac29529eada91aebc451242b` |
| Candidacy | `can_2a0745629be0507080db6d72f4a6719b` |
| Event | `evt_ca435dada07f5ed9b041b7c3d24de732` |
| Election | 2025-09-29, councillor, Ward 25 |
| Announcement | 2025-09-15T19:51:32+00:00 (`second` precision if supported) |
| Endorsement kind | `endorsement` |
| Evidence | [CUPE Ontario: Shan for Scarborough](https://cupe.on.ca/shanforscarborough/) |

The first-party page explicitly says that CUPE Ontario is proud to endorse
Neethan Shan for Toronto City Council. Terra independently verified its
publication metadata before the poll. The dated Labour Council material is
corroboration only; it must not be used to infer an endorsement by Labour
Council or another CUPE affiliate. See [Terra's hold-recovery verification](endorsement-coverage-terra-verification-hold-recovery.md).

## Required implementation checklist

1. Set `councillor_applicable=true` for `cupe_ontario` in
   `data/reference/endorser_panel_curations.csv`.
2. Add one confirmed assertion for the exact 2025 IDs above. Do not reuse the
   2018 Ward 25 IDs (`con_eeda9883ca2d57148405d41f7f5a80a4` /
   `can_8fba857b4440581999ddfd32c59ec62f`), which already belong to the ATU
   Local 113 fact.
3. Add a comprehensive coverage curation for CUPE Ontario × 2025 Ward 25,
   scoped to `evt_ca435dada07f5ed9b041b7c3d24de732`, `councillor`, and
   `ward-25`. The evidence URL should be the CUPE page and the verification
   report should be `docs/research/endorsement-coverage-terra-verification-hold-recovery.md`.
4. Preserve the documented CUPE council searches below as
   `partially_searched` coverage curations. These are contest-batch searches,
   not negative endorsement facts.
5. Do not import CUPE Ontario → David Miller (2003 mayor). The exact entity
   remains unresolved even though the mayoral coverage cell is searched.
6. Do not transfer any Labour Council, CUPE local, CUPE district council, or
   other affiliate evidence to CUPE Ontario. The 2010 “Toronto Candidates”
   page is specifically a near-miss for this purpose.

## CUPE council coverage after the correction

The Luna report records an exact-entity search for every historical CUPE
council batch listed here. Terra's organizational verification confirms that
the searches are admissible as partial coverage, while the Shan page upgrades
one exact Contest to comprehensive coverage. “Partial” means a search was
logged but no complete slate or contest-wide source was recovered; it never
means that omitted candidates were not endorsed.

| Event date | Scope | Expected state | Machine selector |
|---|---|---|---|
| 2003-11-10 | Councillor, 44 wards | `partially_searched` | `evt_d89f777f34365c37b114ca39fb376591`, `councillor`, blank district |
| 2006-11-13 | Councillor, 44 wards | `partially_searched` | `evt_159f073fa6f15c23a840651723d3c3af`, `councillor`, blank district |
| 2010-10-25 | Councillor, 44 wards | `partially_searched` | `evt_5a786c1da7ec5e758036205f04351fc5`, `councillor`, blank district |
| 2014-10-27 | Councillor, 44 wards | `partially_searched` | `evt_54673fd104ab5ef08eb865e162ac040c`, `councillor`, blank district |
| 2016-07-25 | Councillor, Ward 2 | `partially_searched` | `evt_552c4874312956ae84afbbc5ee91b0f7`, `councillor`, `ward-2` |
| 2017-02-13 | Councillor, Ward 42 | `partially_searched` | `evt_b8284a5341635f79babdf7ddc512c2f6`, `councillor`, `ward-42` |
| 2018-10-22 | Councillor, 25 wards | `partially_searched` | `evt_e4fe1909276b5fbd91057022b350fff3`, `councillor`, blank district |
| 2021-01-15 | Councillor, Ward 22 | `partially_searched` | `evt_50c15fe55fa753fba75abfada8da3c38`, `councillor`, `ward-22` |
| 2022-10-24 | Councillor, 25 wards | `partially_searched` | `evt_a52ef78967f05336bdb5d591fd50f122`, `councillor`, blank district |
| 2023-11-30 | Councillor, Ward 20 | `partially_searched` | `evt_ee5715a80b5a532c8b778d94f6b7c9b8`, `councillor`, `ward-20` |
| 2024-11-04 | Councillor, Ward 15 | `partially_searched` | `evt_af73d490abf95ffdae38ca2c830e51f4`, `councillor`, `ward-15` |
| 2025-09-29 | Councillor, Ward 25 | `comprehensive_source_found` | `evt_ca435dada07f5ed9b041b7c3d24de732`, `councillor`, `ward-25` |
| 2026-10-26 | Councillor, all current target wards | `partially_searched` | live-event default: `evt_27c3a2e636a457f1b1f922774525b74a`, `councillor` |

There are **no CUPE council cells that should remain `not_searched`** if the
audited historical batch curations are imported. This is important because the
current default fallback was intentionally changed to `not_searched` for
unlogged historical work. Leaving the batch curations out would discard
documented search activity, not reveal a new evidentiary conclusion.

The historical partial batches contain no positive CUPE assertion. The only
new positive is the exact 2025 Ward 25 Shan cell. The 2026 councillor cells
remain `partially_searched` under the live-election rule, with the existing
assessment basis `current election searched through 2026-08-21`.

## Expected coverage counts

The current output has 2,385 Endorser × Contest cells:

| State | Current |
|---|---:|
| `partially_searched` | 1,021 |
| `not_applicable` | 900 |
| `comprehensive_source_found` | 181 |
| `not_searched` | 145 |
| `source_unavailable` | 138 |

CUPE currently contributes 265 cells: 257 `not_applicable`, 6 partial, and 2
comprehensive. Under the **recommended complete correction**—panel flag,
historical CUPE council batch curations, 2025 Ward 25 comprehensive curation,
and the new assertion—the CUPE slice becomes:

| CUPE state | Cells |
|---|---:|
| `partially_searched` | 262 (231 historical council + 25 live 2026 council + 6 existing mayor cells) |
| `comprehensive_source_found` | 3 (2010 mayor, 2023 mayor, 2025 Ward 25 council) |
| `not_searched` | 0 |
| `not_applicable` | 0 |

The expected whole-output distribution is therefore:

| State | Expected |
|---|---:|
| `partially_searched` | **1,277** |
| `not_applicable` | **643** |
| `comprehensive_source_found` | **182** |
| `not_searched` | **145** |
| `source_unavailable` | **138** |
| **Total** | **2,385** |

For comparison, flipping only the panel flag and importing the assertion while
omitting the historical CUPE coverage curations would yield 231 CUPE council
cells as `not_searched` and an overall distribution of 1,046 partial, 643 not
applicable, 182 comprehensive, 376 not searched, and 138 source unavailable.
That is not the audited result and should be treated as an implementation bug.

The assertion count should increase from **132** to **133** (132 confirmed,
one unresolved), and derived positive Endorsement facts from **131** to **132**.

## Source and policy checks

- The 2003 CUPE/Miller lead remains unresolved because “CUPE” is not enough to
  identify CUPE Ontario; keep the partial mayor coverage curation but do not
  create an assertion.
- CUPE Ontario's 2010 mayor and 2023 mayor cells are already comprehensive
  and remain unchanged.
- The 2010 council search found Labour Council and CUPE Toronto District
  Council material, not a CUPE Ontario council choice. It remains partial and
  creates no assertion.
- The 2025 Shan assertion uses CUPE Ontario's own first-party page. The Labour
  Council and Action Network references support timing/activity only and do
  not create affiliate or cross-entity facts.
- The 2025 CUPE Shan fact is distinct from the 2018 ATU Shan fact and from the
  2025 Progress Toronto Shan fact; no assertion or coverage conflict exists
  when the corrected IDs above are used.

## Inputs inspected

- [Panel curation](../../data/reference/endorser_panel_curations.csv)
- [Coverage curations](../../data/reference/endorsement_coverage_curations.csv)
- [Assertion curations](../../data/reference/endorsement_assertion_curations.csv)
- [Current coverage output](../../data/out/endorsement_coverage.csv)
- [Current assertion output](../../data/out/endorsement_assertions.csv)
- [Luna organization report](endorsement-coverage-luna-organizations-2003-2025.md)
- [Terra organization verification](endorsement-coverage-terra-verification-organizations.md)
- [Terra hold-recovery verification](endorsement-coverage-terra-verification-hold-recovery.md)

No code, reference CSV, or generated output was edited in this audit.
