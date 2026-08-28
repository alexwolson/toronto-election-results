# Luna authenticated sourcing and canonical-ID resolution: Toronto Sun, 2018

**Research date:** 2026-08-28  \
**Researcher:** Luna  \
**Endorser:** Toronto Sun Editorial Board (`toronto_sun_editorial_board`)

**Evidence packet:** [Toronto Sun endorsements recovered through U of T Libraries](endorsement-census-sun-utoronto-proquest-evidence-2026-08-28.md)  \
**Canonical tables:** `data/out/election_events.csv`, `data/out/contests.csv`, and `data/out/election_results.csv`

**Scope:** The authenticated 2018 Toronto Sun city-council endorsement package. This report proposes imports only; it does not edit curation CSVs or release outputs.

## Resolution result

All **27** positive rows in the packet resolve to exactly one canonical 2018 Toronto City Council contest and candidacy using `(event_id, office_type, official_district_id, normalized candidate name)`. No candidate was missing and no row was ambiguous at the identity level. The Results table's canonical display name is retained, even where the packet uses a source typo or a different name order.

There are **23 straightforward proposed imports** and **four candidate rows held for Terra's interpretation of two multi-candidate sections**: both candidates in Ward 15 and both candidates in Ward 20. The identity resolutions for those four rows are nevertheless exact and are recorded below so Terra can validate the source meaning without repeating the canonical lookup.

| Package | Positive rows | Identity resolution | Proposed disposition | Evidence |
|---|---:|---|---|---|
| 2018 City Council, Wards 1–25 | 27 | 27 unique canonical candidacies; 23 straightforward, 4 interpretation holds | Import 23 after Terra review; hold Wards 15 and 20 pending Terra | [ProQuest 2125467176](https://www.proquest.com/docview/2125467176), [publisher article](https://torontosun.com/news/local-news/toronto-sun-endorsements-for-city-council) |

## Row-by-row canonical resolution and import proposal

The proposed curation key is deterministic and is included for the downstream curation pass. `confirmed` means the candidate identity and single-candidate positive choice are ready for Terra's normal validation. `terra_hold` means the identity is resolved but the package's two-candidate wording must be adjudicated before creating an edge.

| Ward | Packet name | Canonical Results name | Canonical district | `contest_id` | `candidacy_id` | `person_id` | Proposed state | Proposed curation key |
|---:|---|---|---|---|---|---|---|---|
| 1 | Michael Ford | Michael Ford | `Ward 1 — Etobicoke North` | `con_922d425132ad5243b459c0ca40a6dcd9` | `can_b52f6554caab5bc08b7deca203ffd5d5` | `per_b8c7ac1e1bdd57698d5f7955f63c2c25` | `confirmed` | `sun_2018_w01_michaelford` |
| 2 | Stephen Holyday | Stephen Holyday | `Ward 2 — Etobicoke Centre` | `con_3fc9df4b254c5eb6a2a7fb629a124bfb` | `can_02d0984005935af0b592f3ad185eff48` | `per_cb9a349d2c375d6ca82d06405b9986e0` | `confirmed` | `sun_2018_w02_stephenholyday` |
| 3 | Mark Grimes | Mark Grimes | `Ward 3 — Etobicoke-Lakeshore` | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_881b56db387e50b19b0aa61d56b09724` | `per_3e52aa435eb8566fb37510ab305dff54` | `confirmed` | `sun_2018_w03_markgrimes` |
| 4 | Evan Tummillo | Evan Tummillo | `Ward 4 — Parkdale-High Park` | `con_f961284da53f5a38ba3a20e7e998ef4f` | `can_b6b790f30421564ca2e9c8263737a42e` | `missing` | `confirmed` | `sun_2018_w04_evantummillo` |
| 5 | Frances Nunziata | Frances Nunziata | `Ward 5 — York South-Weston` | `con_ac347f98e5715159b3adecf8debcbde8` | `can_8c722fdcbad151f7a215974077dcdcbb` | `per_d476ff1e2e605a88914636edbdfcb79a` | `confirmed` | `sun_2018_w05_francesnunziata` |
| 6 | James Pasternak | James Pasternak | `Ward 6 — York Centre` | `con_849867f583195ad38c77941612883bd9` | `can_56769676131c5f708884abdfea79deef` | `per_3f72f66a6a385b0eae3279e7de8d12a0` | `confirmed` | `sun_2018_w06_jamespasternak` |
| 7 | Giorgio Mammoliti | Giorgio Mammoliti | `Ward 7 — Humber River-Black Creek` | `con_990816d2030b592787bdf4a19382627f` | `can_0b38c9e9981f56af8bccc1f2eb6c2c82` | `per_3ec4e3ff861d57519f52e15b4a9449a7` | `confirmed` | `sun_2018_w07_giorgiomammoliti` |
| 8 | Christin Carmichael Greb | Greb Christin Carmichael | `Ward 8 — Eglinton-Lawrence` | `con_caa23fae586656b2bab11ee711073a2c` | `can_6f92d616fbc254aa87d1296422abbdae` | `per_e256786d3b3e5f829cdc6defa004044a` | `confirmed` | `sun_2018_w08_christincarmichaelgreb` |
| 9 | Ana Bailão | Ana Bailão | `Ward 9 — Davenport` | `con_55f5230db0d85c499ce7cea0ce379f5f` | `can_a9d93ea575e9511aad1985615dbd47f9` | `per_e42110d6d55c5145b6ff91e7169bffae` | `confirmed` | `sun_2018_w09_anabailao` |
| 10 | Kevin Vuong | Kevin Vuong | `Ward 10 — Spadina-Fort York` | `con_2865d31031005dd897904c3f07e4d039` | `can_28eb19db01df5e0489bf5730e980a2b0` | `per_0bf581c7815c51f6964d53ddb7b07052` | `confirmed` | `sun_2018_w10_kevinvuong` |
| 11 | Joyce Rowlands | Joyce Rowlands | `Ward 11 — University-Rosedale` | `con_810611751acb5e86ab30b3277e7e6dad` | `can_2be6eb5c966a5c3e922215053eac8307` | `missing` | `confirmed` | `sun_2018_w11_joycerowlands` |
| 12 | Joe Mihevc | Joe Mihevc | `Ward 12 — Toronto-St. Paul's` | `con_8b4a03ef5a3c55c4ab20662c886b31a7` | `can_daba066aa91d57bb8ac1116dacf2f2bc` | `per_247212de46b050cda328eb649ffaf5d3` | `confirmed` | `sun_2018_w12_joemihevc` |
| 13 | Lucy Troisi | Lucy Troisi | `Ward 13 — Toronto Centre` | `con_3a43982e2a0450b2a3f4c5241f6965d8` | `can_b3ceb20f257e54d18ba8274029a709b6` | `per_2cca1e22c6125cc6ad6b3c491b53cf3e` | `confirmed` | `sun_2018_w13_lucytroisi` |
| 14 | Mary Fragedakis | Mary Fragedakis | `Ward 14 — Toronto-Danforth` | `con_1b8d99f619f758efb737805a20bcf6fb` | `can_a0c2320659e855448b8aa28f1740d5bd` | `per_bae4184cf53b5159b67beb668a0d26f4` | `confirmed` | `sun_2018_w14_maryfragedakis` |
| 15 | Jon Burnside | Jon Burnside | `Ward 15 — Don Valley West` | `con_6a1f4d7470675d869b3b11aede0812f2` | `can_72220a1f527a5ffb9ca19e3502f58894` | `per_9387d636b99c5fdd8edee8549f902b74` | `terra_hold` | `sun_2018_w15_jonburnside` |
| 15 | Jaye Robinson | Jaye Robinson | `Ward 15 — Don Valley West` | `con_6a1f4d7470675d869b3b11aede0812f2` | `can_365f117d8c1a5b0097b2c1b3414d99dd` | `per_a0a0b8b1222d525daa9c375c565026f0` | `terra_hold` | `sun_2018_w15_jayerobinson` |
| 16 | Denzil Minnan-Wong | Denzil Minnan-Wong | `Ward 16 — Don Valley East` | `con_147dca9e3758595d8766dc52d11a65f4` | `can_f9ea8f5f2f22545b961d7d1aebffe984` | `per_cacdaf09421e5b0e98d0138141449f29` | `confirmed` | `sun_2018_w16_denzilminnanwong` |
| 17 | Christina Liu | Christina Liu | `Ward 17 — Don Valley North` | `con_7a4043e26d4256e78ee3861fb81e718a` | `can_a6628f45e8ae5f50a48d6645d8d8646f` | `per_d46587cbda0d51099533785d087f2a52` | `confirmed` | `sun_2018_w17_christinaliu` |
| 18 | Sam Moini | Sam Moini | `Ward 18 — Willowdale` | `con_4def6d4e85f85950babb9030e4eae0cb` | `can_fafe793aa442549aa62e15c5f44bc07f` | `per_9132d528b429522ab6e1d0e2e49fde60` | `confirmed` | `sun_2018_w18_sammoini` |
| 19 | Brad Bradford | Brad Bradford | `Ward 19 — Beaches-East York` | `con_45eb3e143f1b5492b4652498c957ed6b` | `can_aeb469c9e30b5f37a4f25f6a757d2ca4` | `per_d8dfddfb642358e299f4b428292666bf` | `confirmed` | `sun_2018_w19_bradbradford` |
| 20 | Michelle Holland-Berardinetti | Michelle Holland-Berardinetti | `Ward 20 — Scarborough Southwest` | `con_6fd864aec40c5bbc9f3eb32d2e9e4379` | `can_156a9ea4f7dc57baa65c20af16ff5205` | `per_0483d7ff289356e1880e355bd328a312` | `terra_hold` | `sun_2018_w20_michellehollandberardinetti` |
| 20 | Gary Crawford | Gary Crawford | `Ward 20 — Scarborough Southwest` | `con_6fd864aec40c5bbc9f3eb32d2e9e4379` | `can_709e43151ddd5089b8c98b7291f7a5ca` | `per_6889ce57bbda567f950b56abf65ade53` | `terra_hold` | `sun_2018_w20_garycrawford` |
| 21 | Michael Thompson | Michael Thompson | `Ward 21 — Scarborough Centre` | `con_16fad19349255393a28639cd62e83ae3` | `can_44edb32c95a155788c97ba51aab252a9` | `per_d6e9f3947fda53a490136416df97c3cf` | `confirmed` | `sun_2018_w21_michaelthompson` |
| 22 | Norm Kelly | Norm Kelly | `Ward 22 — Scarborough-Agincourt` | `con_c555f2e9b45051a8b960bdbb0ac6080a` | `can_4185e2b2d994537280b8eae979cfdaec` | `per_1595883add5a5e7abb1bcdde1e768611` | `confirmed` | `sun_2018_w22_normkelly` |
| 23 | Cynthia Lai | Cynthia Lai | `Ward 23 — Scarborough North` | `con_c85783d7c9a4550bae21b8e14f2ff992` | `can_736c4515a83c5c4d99d7bbb1acdd5f7a` | `per_862b8cbfcf92520896d872844b4455b7` | `confirmed` | `sun_2018_w23_cynthialai` |
| 24 | Paul Ainslie | Paul Ainslie | `Ward 24 — Scarborough-Guildwood` | `con_7e6cf2fd75ba560a900bb024e72fe99c` | `can_a138036d836c5c8da46d76df542f931f` | `per_c0e1c9bb6045570b873969e4c462da62` | `confirmed` | `sun_2018_w24_paulainslie` |
| 25 | Jennifer McKelvie | Jennifer Mckelvie | `Ward 25 — Scarborough-Rouge Park` | `con_eeda9883ca2d57148405d41f7f5a80a4` | `can_76a5898fec8b5e3983638f5c9354afe3` | `per_11598fb6d485564eb5053b8787400814` | `confirmed` | `sun_2018_w25_jennifermckelvie` |

## Identity and spelling audit

- **Ward 8:** The packet gives “Christin Carmichael Greb”; the canonical Results row is `Greb Christin Carmichael`. The ward, contest, candidacy, and person record all match; this is a name-order difference, not a missing person.
- **Ward 13:** The packet's source observation records “Lucy Trosi.” The evidence packet identifies the incumbent as Lucy Troisi; the canonical Results row is `Lucy Troisi`. This is a source spelling error resolved to the unique canonical candidacy.
- **Ward 25:** The canonical display name is `Jennifer Mckelvie` (capitalization retained from Results), while the packet uses `Jennifer McKelvie`.
- **Wards 4 and 11:** Canonical candidacies exist but `person_id` is currently blank for Evan Tummillo and Joyce Rowlands. This does not prevent a contest/candidacy-level endorsement proposal; it is a Results identity-data gap, not an endorsement matching ambiguity.
- **Ward 20:** The packet's `Michelle Holland-Berardinetti` form matches the canonical row exactly; Gary Crawford also has a distinct unique canonical candidacy in the same contest.

## Terra questions: multi-candidate sections

### Ward 15 — Jon Burnside and Jaye Robinson

The article section heading says “Jon Burnside or Jaye Robinson.” Its explanation says both incumbents are quality candidates, that the board struggled to choose one, and that voters would be well served by either. Luna has resolved both names to the same Ward 15 contest. Terra should determine whether the package's language meets the project's rule for two positive endorsement edges. Until then, both rows remain `terra_hold`.

### Ward 20 — Michelle Holland-Berardinetti and Gary Crawford

The section heading names Michelle Holland-Berardinetti. The explanation says voters cannot lose with either Holland-Berardinetti or Gary Crawford and that the board would keep both. Luna has resolved both names to the same Ward 20 contest. Terra should determine whether this is a two-edge endorsement or whether the named heading should control. The evidence for Gary Crawford is stronger than a passing mention, but this report does not make the final interpretation. Until then, both rows remain `terra_hold`.

## Other source observations that are not endorsement edges

- **Ward 10:** Karlene Nation receives favourable supplementary praise, but the named and reasoned endorsement is Kevin Vuong. No Nation edge is proposed.
- **Mayoral cross-reference:** The package repeats the Sun's endorsement of John Tory. That mayoral endorsement is already curated; this article is corroborating evidence, not a duplicate proposed edge.

## Proposed import record

For each row Terra approves, the proposed curation record is:

```text
endorser_id=toronto_sun_editorial_board
election_event_id=evt_e4fe1909276b5fbd91057022b350fff3
contest_id=<row above>
candidacy_id=<row above>
endorsement_kind=editorial_choice
date=2018-10-20
date_precision=day
source_type=publisher_editorial_authenticated_archive
source_url=https://www.proquest.com/docview/2125467176
review_state=confirmed
```

Use the publisher date recorded in the packet (2018-10-20) for the package-level source date. The duplicate ProQuest records dated 2018-10-21 do not create a separate endorsement event.

## Terra handoff

1. Validate the 23 single-candidate choices against the authenticated full text and the canonical IDs above.
2. Decide whether Ward 15 supports both Jon Burnside and Jaye Robinson as positive edges.
3. Decide whether Ward 20 supports both Michelle Holland-Berardinetti and Gary Crawford, or only the named heading choice.
4. Preserve the Ward 10 Karlene Nation praise and the mayoral cross-reference as package metadata, not endorsement edges.
5. Resolve the two person-ID gaps in the Results identity layer separately if the project requires person-level joins; they are not blockers for candidacy-level source attribution.
