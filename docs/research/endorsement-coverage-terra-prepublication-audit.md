# Pre-publication audit: endorsement research wave

**Audit date:** 2026-08-22  
**Auditor:** Terra  
**Scope:** the 34 positive assertions newly verified in the current Luna/Terra
research wave; all rows in `data/reference/endorsement_coverage_curations.csv`.
This was a read-only audit. It did not rebuild or change `data/out`.

## Release decision

**No blocker found.** The exact 34 expected new facts are present, and no extra
facts from the same research wave slipped in. Every one resolves against the
current output dimensions with the intended election date, office, ward,
candidate, Contest, and Candidacy. The focused endorsement assembly also
passes.

| Wave | Expected / found | Dimension fields matched | Evidence report |
|---|---:|---:|---|
| David Miller | 3 / 3 | 3 / 3 | [wave-1 verification](endorsement-coverage-terra-verification-wave1.md) |
| Toronto Sun, 2018 council | 13 / 13 | 13 / 13 | [editorial verification](endorsement-coverage-terra-verification-editorial.md) |
| Progress Toronto | 2 / 2 | 2 / 2 | [organizational verification](endorsement-coverage-terra-verification-organizations.md) |
| ATU Local 113, 2018 council | 16 / 16 | 16 / 16 | [organizational verification](endorsement-coverage-terra-verification-organizations.md) |
| **Total** | **34 / 34** | **34 / 34** | |

For every row, the audit joined the curated `expected_candidacy_id` to
`data/out/election_results.csv` and compared the expected Contest ID, election
date, office type, official district ID, and stored candidate name. All six
checks passed for all 34 rows; there were no missing IDs, duplicate matches, or
metadata mismatches. The relevant Contest/Candidacy ID pairs are also all
present in the corresponding Terra verification report (3/3 Miller, 13/13 Sun,
and 18/18 organizational pairs).

Focused assembly of the current dimensions and reference inputs passed with 9
Endorsers, 132 assertions (131 confirmed and 1 unresolved), 131 derived
positive facts, and 2,385 Endorser-by-Contest coverage cells.

## Exact fact set audited

The table is the complete scoped delta. Names are the current dataset
`candidate_name` values; minor source-name variants are retained separately in
`asserted_candidate_name`.

| Curated fact | Date / ward | Candidate | Contest ID | Candidacy ID |
|---|---|---|---|---|
| `miller_2006_w14_perks` | 2006-11-13 / 14 | Gord Perks | `con_b4c70c0c6f465c4091dce97cbbd286b3` | `can_8beb4a28087f5a58b667f68fdc297a43` |
| `miller_2006_w38_debaeremaeker` | 2006-11-13 / 38 | Glenn De Baeremaeker | `con_17c2e1a7404c5641823443ca7a6dcc10` | `can_3f84dacf17b85bdbad830258c4a975a8` |
| `miller_2010_w18_beaulieu` | 2010-10-25 / 18 | Kevin Beaulieu | `con_d6f7b1cb92f959ab9408dbb936bcf2ff` | `can_7c4e23514e3b546e8fc7ea161c40a4f1` |
| `sun_2018_w01_ford` | 2018-10-22 / 1 | Michael Ford | `con_922d425132ad5243b459c0ca40a6dcd9` | `can_b52f6554caab5bc08b7deca203ffd5d5` |
| `sun_2018_w02_holyday` | 2018-10-22 / 2 | Stephen Holyday | `con_3fc9df4b254c5eb6a2a7fb629a124bfb` | `can_02d0984005935af0b592f3ad185eff48` |
| `sun_2018_w03_grimes` | 2018-10-22 / 3 | Mark Grimes | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_881b56db387e50b19b0aa61d56b09724` |
| `sun_2018_w04_tummillo` | 2018-10-22 / 4 | Evan Tummillo | `con_f961284da53f5a38ba3a20e7e998ef4f` | `can_b6b790f30421564ca2e9c8263737a42e` |
| `sun_2018_w05_nunziata` | 2018-10-22 / 5 | Frances Nunziata | `con_ac347f98e5715159b3adecf8debcbde8` | `can_8c722fdcbad151f7a215974077dcdcbb` |
| `sun_2018_w06_pasternak` | 2018-10-22 / 6 | James Pasternak | `con_849867f583195ad38c77941612883bd9` | `can_56769676131c5f708884abdfea79deef` |
| `sun_2018_w08_greb` | 2018-10-22 / 8 | Greb Christin Carmichael | `con_caa23fae586656b2bab11ee711073a2c` | `can_6f92d616fbc254aa87d1296422abbdae` |
| `sun_2018_w17_liu` | 2018-10-22 / 17 | Christina Liu | `con_7a4043e26d4256e78ee3861fb81e718a` | `can_a6628f45e8ae5f50a48d6645d8d8646f` |
| `sun_2018_w18_moini` | 2018-10-22 / 18 | Sam Moini | `con_4def6d4e85f85950babb9030e4eae0cb` | `can_fafe793aa442549aa62e15c5f44bc07f` |
| `sun_2018_w21_thompson` | 2018-10-22 / 21 | Michael Thompson | `con_16fad19349255393a28639cd62e83ae3` | `can_44edb32c95a155788c97ba51aab252a9` |
| `sun_2018_w23_lai` | 2018-10-22 / 23 | Cynthia Lai | `con_c85783d7c9a4550bae21b8e14f2ff992` | `can_736c4515a83c5c4d99d7bbb1acdd5f7a` |
| `sun_2018_w24_ainslie` | 2018-10-22 / 24 | Paul Ainslie | `con_7e6cf2fd75ba560a900bb024e72fe99c` | `can_a138036d836c5c8da46d76df542f931f` |
| `sun_2018_w25_mckelvie` | 2018-10-22 / 25 | Jennifer Mckelvie | `con_eeda9883ca2d57148405d41f7f5a80a4` | `can_76a5898fec8b5e3983638f5c9354afe3` |
| `progress_2018_w03_morley` | 2018-10-22 / 3 | Amber Morley | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_a4e55da62ed2509cb497ad0bfd65c11f` |
| `progress_2021_w22_wong` | 2021-01-15 / 22 | Manna Wong | `con_53468b4ee3c7510aba4d708f584951a9` | `can_f9f7d971b99c52cf9a48edf7b1dd38ba` |
| `atu_2018_w03_morley` | 2018-10-22 / 3 | Amber Morley | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_a4e55da62ed2509cb497ad0bfd65c11f` |
| `atu_2018_w04_perks` | 2018-10-22 / 4 | Gord Perks | `con_f961284da53f5a38ba3a20e7e998ef4f` | `can_f016d26c42dc5073b6e91d974223d0a7` |
| `atu_2018_w05_olawoye` | 2018-10-22 / 5 | Lekan Olawoye | `con_ac347f98e5715159b3adecf8debcbde8` | `can_467ce1971c8b595a88cebb67edda463a` |
| `atu_2018_w06_augimeri` | 2018-10-22 / 6 | Maria Augimeri | `con_849867f583195ad38c77941612883bd9` | `can_4eec1f4fc03c5c2192fa031a86b3420d` |
| `atu_2018_w07_perruzza` | 2018-10-22 / 7 | Anthony Perruzza | `con_990816d2030b592787bdf4a19382627f` | `can_6dfeac63c0665cf483c6ac6a4934541e` |
| `atu_2018_w09_bailao` | 2018-10-22 / 9 | Ana Bailão | `con_55f5230db0d85c499ce7cea0ce379f5f` | `can_a9d93ea575e9511aad1985615dbd47f9` |
| `atu_2018_w10_cressy` | 2018-10-22 / 10 | Joe Cressy | `con_2865d31031005dd897904c3f07e4d039` | `can_c17e828fbf045e0087095cfa28321105` |
| `atu_2018_w11_layton` | 2018-10-22 / 11 | Mike Layton | `con_810611751acb5e86ab30b3277e7e6dad` | `can_aa928563d472570d901401bff637b922` |
| `atu_2018_w12_mihevc` | 2018-10-22 / 12 | Joe Mihevc | `con_8b4a03ef5a3c55c4ab20662c886b31a7` | `can_daba066aa91d57bb8ac1116dacf2f2bc` |
| `atu_2018_w13_wong_tam` | 2018-10-22 / 13 | Kristyn Wong-Tam | `con_3a43982e2a0450b2a3f4c5241f6965d8` | `can_c370bbf8fd765d9694fd4f089ba3d462` |
| `atu_2018_w14_fletcher` | 2018-10-22 / 14 | Paula Fletcher | `con_1b8d99f619f758efb737805a20bcf6fb` | `can_d7591ea7a10b549e97f6a6ec33e194d6` |
| `atu_2018_w17_carroll` | 2018-10-22 / 17 | Shelley Carroll | `con_7a4043e26d4256e78ee3861fb81e718a` | `can_577ddf8125b85bf18e731f150dca4600` |
| `atu_2018_w18_tabasi_nejad` | 2018-10-22 / 18 | Nejad Saman Tabasi | `con_4def6d4e85f85950babb9030e4eae0cb` | `can_bd1df746d51c51459c672d68456dc7e6` |
| `atu_2018_w19_kellway` | 2018-10-22 / 19 | Matthew Kellway | `con_45eb3e143f1b5492b4652498c957ed6b` | `can_8702c409b44c56869788d0fcb7ee8999` |
| `atu_2018_w23_samuel` | 2018-10-22 / 23 | Felicia Samuel | `con_c85783d7c9a4550bae21b8e14f2ff992` | `can_cd24b1b0a226537e8e6a4cc6ad03981a` |
| `atu_2018_w25_shan` | 2018-10-22 / 25 | Neethan Shan | `con_eeda9883ca2d57148405d41f7f5a80a4` | `can_8fba857b4440581999ddfd32c59ec62f` |

All 34 are `confirmed`. The Sun entries use the single publisher editorial
dated 2018-10-21; the Progress entries use dated first-party campaign pages
(2018-10-04 and 2020-12-15); the ATU entries use the first-party October 2018
slate at month precision. The Miller facts retain the verified attribution
types and their source-specific timing, including the explicitly labelled
post-poll campaign attribution for De Baeremaeker.

## Exclusions and Ward 25 identity check

The intentional exclusions are intact:

- The 13 names rejected from Luna's secondary 2018 Sun transcription have
  **zero** Toronto-Sun 2018-council assertion rows. This check is scoped to the
  Sun: for example, Ana Bailão and Joe Mihevc appropriately appear as distinct
  **ATU** facts, not as Sun facts.
- The two Toronto Star holds (Giambrone 2003 Ward 18 and Miller 2006 mayor)
  have **zero** Star assertions on their held Candidacy IDs.
- CUPE Ontario has **zero** assertions for Miller 2003 or the corrected Shan
  2025 Candidacy. The latter remains evidence-confirmed but panel-inapplicable
  because CUPE's approved `councillor_applicable` value is `false`.

Ward 25 is correctly separated by event. The new ATU fact is the **2018** Shan
row, `con_eeda9883ca2d57148405d41f7f5a80a4` /
`can_8fba857b4440581999ddfd32c59ec62f`. The existing Progress Toronto fact is
the distinct **2025** Shan row, `con_c8883aeeac29529eada91aebc451242b` /
`can_2a0745629be0507080db6d72f4a6719b`; no CUPE fact uses either locator. The
2018 Sun Ward 25 fact is separately and correctly Jennifer McKelvie, with its
own Candidacy ID in the same 2018 Contest.

## Coverage-curation audit

`endorsement_coverage_curations.csv` has 114 unique selectors: 95
`partially_searched` and 19 `comprehensive_source_found` (93 councillor, 21
mayor). Against the current Toronto target dimensions, they expand to **855
unique Endorser-by-Contest cells**: 812 partial and 43 comprehensive.

| Endorser | Expanded cells |
|---|---:|
| ATU Local 113 | 212 |
| CUPE Ontario | 5 |
| David Miller | 88 |
| Elementary Teachers of Toronto | 235 |
| Progress Toronto | 28 |
| Toronto Star Editorial Board | 52 |
| Toronto Sun Editorial Board | 235 |
| **Total** | **855** |

Every selector matches at least one current target Contest (range: 1–44), and
there are no duplicate resolved `(endorser, contest)` cells. There is also no
broad event/office selector combined with a district-specific selector for the
same Endorser/event/office, so broad expansion cannot shadow a narrower
curation. The implemented resolver fails closed if such an overlap is later
introduced.

Panel precedence is intact: all 114 selectors are after the Endorser's
eligibility start and target an applicable office. In particular, no CUPE
councillor selector overrides the approved `not_applicable` policy. No
curation collides with a built-in complete-slate/explicit-choice or Star
`source_unavailable` default; curated coverage is therefore a documented
addition, not an accidental override.

The research reports support the selected states:

- **2** Miller selectors cite the wave-1 verification and its mayoral search
  certificate.
- **24** editorial selectors cite the Terra editorial verification and Luna
  editorial search certificate.
- **88** organizational selectors cite the Terra organizational verification
  and Luna organizational search certificate.

All 114 evidence URLs are HTTPS and all 228 referenced local report paths
exist. The 19 comprehensive selectors have an actual complete slate or an
explicit choice for that Contest; they do not generate candidate-level
non-endorsement facts. The 95 partial selectors record bounded source work
only. None uses `searched_no_endorsement_found`, and no coverage basis asserts
opposition, neutrality, or a candidate-level negative. This preserves the
dataset's open-world semantics.

## Pre-publication notes

1. Seven Star `partially_searched` selectors use the generic
   `https://www.thestar.com/` as their evidence URL rather than a specific
   article. Their checked-in verification/search reports do describe the exact
   searches, so the state is auditable and this does not affect any positive
   fact. Replacing the generic URL with a stable specific retrieval target,
   when one exists, would improve provenance granularity.
2. **Resolved before publication:** `not_searched` historical cells now carry
   a null `assessed_through`; dated rows correspond to a curation, an audited
   default, or the live 2026 search. The post-publication audit below verifies
   this across the full output.

The remaining generic-URL improvement does not block the research wave or the
release: it concerns provenance presentation, not fact identity, source
admissibility, selector expansion, or open-world inference.

## Post-publication audit

**Audit date:** 2026-08-22  
**Scope:** rebuilt `data/out` and `build_manifest.json` after the 34-fact wave
and the coverage-date metadata correction. This check was read-only.

### Published-release decision

**No data correctness, integrity, or deterministic-replay blocker found.** The
published artifacts exactly match the current checked-in curation inputs and
pass the full release validator. The pre-publication conclusions above are
therefore confirmed against the actual release, not only against in-memory
inputs.

The initial report-hash caveat is closed by the provenance delta audit below.

### Manifest and serialization integrity

- All **113/113** manifest source records matched the current file's byte
  count and SHA-256.
- All **24/24** manifest artifacts matched their current byte count, SHA-256,
  and recorded row count.
- CSV and Parquet have identical normalized contents for all four endorsement
  tables: `endorsers` (9), `endorsement_assertions` (132), `endorsements`
  (131), and `endorsement_coverage` (2,385).
- The full release validation suite passed after the serialized district WKB
  geometries were restored for geometric validation. A fresh, in-memory
  assembly from the current output dimensions and curation inputs also exactly
  matched each of the four published endorsement tables.

This independently confirms the current output's stability. It complements
the release owner's two rebuilds with identical artifact hashes.

### Facts and exclusions

Published counts are exactly **9** Endorsers, **132** assertions (**131**
confirmed and **1** unresolved), and **131** positive Endorsement facts. The
fact set is the complete 34-row wave described above plus **97** pre-existing
confirmed facts; a fresh assembly produced exactly the same 131 facts.

All intentional exclusions remain absent from the published assertions and
facts:

- the 13 rejected Toronto Sun 2018 secondary-transcription names;
- Toronto Star's held Giambrone 2003 and Miller 2006 claims;
- CUPE Ontario → Miller 2003; and
- CUPE Ontario → Shan 2025, which remains outside CUPE's approved council
  applicability despite its separate evidence status.

The Ward 25 distinction survives publication exactly as intended:

| Event | Endorser | Candidate | Contest / Candidacy |
|---|---|---|---|
| 2018-10-22 | ATU Local 113 | Neethan Shan | `con_eeda9883ca2d57148405d41f7f5a80a4` / `can_8fba857b4440581999ddfd32c59ec62f` |
| 2025-09-29 | Progress Toronto | Neethan Shan | `con_c8883aeeac29529eada91aebc451242b` / `can_2a0745629be0507080db6d72f4a6719b` |

No CUPE assertion uses either Shan Candidacy. The separate 2018 Sun Ward 25
fact correctly targets Jennifer McKelvie in the 2018 Contest.

### Published coverage semantics

The published coverage distribution is:

| State | Cells |
|---|---:|
| `partially_searched` | 1,021 |
| `not_applicable` | 900 |
| `comprehensive_source_found` | 181 |
| `not_searched` | 145 |
| `source_unavailable` | 138 |
| `searched_no_endorsement_found` | 0 |

The obsolete blanket basis `open-world historical search is not source-complete`
appears **zero** times. All **145** `not_searched` cells have a null
`assessed_through`; all **1,340** audited/current cells in
`partially_searched`, `comprehensive_source_found`, or `source_unavailable`
have a date. The 900 `not_applicable` cells are also dated as release metadata.

Panel precedence holds in the published table: all **257** CUPE Ontario
councillor cells are `not_applicable`; no council assertion or coverage
curation bypasses that rule. One coverage row exists for every approved
Endorser × Mayor/City-Councillor Contest (9 × 265 = 2,385), no cell key is
duplicated, and no coverage state is transformed into a candidate-level
negative fact.

The checked-in coverage curation file has **114** unique selectors (95 partial,
19 comprehensive) that resolve to **855** unique cells (812 partial, 43
comprehensive). Each selector resolves to at least one current target Contest;
there are no overlap, broad-versus-specific, eligibility, or office-
applicability conflicts.

### Report-hash hardening delta: closed

The initial audit found that the 114 coverage selectors named six checked-in
verification/search reports without manifest hashes. That gap is now fixed:
the source-file collector reads both report-path columns in
`endorsement_coverage_curations.csv`, and the rebuilt manifest records all six
Markdown reports as sources.

The narrow post-fix audit found **119/119** manifest sources valid by current
path, byte count, and SHA-256. This includes **6/6** referenced research
reports, each of which matches the manifest's exact byte count and SHA-256.
All **24/24** artifacts also remain valid by bytes, hash, and row count.

The provenance package is therefore now manifest-tamper-evident at the same
level as the formal curation inputs. No data or semantic regression accompanied
the hardening: the rebuilt output remains 9 Endorsers, 132 assertions (131
confirmed and 1 unresolved), 131 positive facts, and 2,385 coverage cells with
the validated distribution and open-world invariants above. A fresh
post-hardening endorsement reassembly also exactly matches all four published
endorsement tables.
