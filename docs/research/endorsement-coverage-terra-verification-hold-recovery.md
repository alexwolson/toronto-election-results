# Terra verification: historical endorsement hold-recovery leads

**Research date:** 2026-08-22  
**Scope:** independent verification of the four leads in
`endorsement-coverage-luna-hold-recovery.md`. No datasets, curations, or
generated outputs were changed.

## Decision rule

An importable fact requires an affirmative choice by the exact approved
endorser for the exact candidate/contest, published before the poll. A source
must itself make the attribution (first-party/publisher-owned), or be a
reputable contemporaneous source that directly attributes it. A bibliographic
title, a search result, or an uncited secondary summary is a recovery lead,
not the fact.

## Dispositions

| Proposed fact | Target | Decision | Why |
| --- | --- | --- | --- |
| Toronto Star Editorial Board → Adam Giambrone, 2003 Ward 18 | `con_4b3374ab9039564fa8ed1cedf493a0e3`; `can_82808b3e4f6e57b893db83438007ba68` | **HOLD** | No publisher-owned editorial text or qualifying contemporaneous direct attribution was recovered. |
| Toronto Star Editorial Board → David Miller, 2006 mayor | `con_5d8609e7e7f4584ea28ad032690bdae8`; `can_60df17cf5ac95996aad15c760e40ee19` | **HOLD** | The secondary bibliographic record identifies an editorial title and date but is not the editorial or a qualifying direct attribution. |
| CUPE Ontario → David Miller, 2003 mayor | `con_945161409a0450f29e351ff3f263f815`; `can_63e1ea224f9a5132ae24d181a6bd7ca2` | **HOLD** | The available material attributes support only to generic “CUPE”/Canadian Union of Public Employees, not the distinct entity CUPE Ontario. |
| CUPE Ontario → Neethan Shan, 2025 Ward 25 | `con_c8883aeeac29529eada91aebc451242b`; `can_2a0745629be0507080db6d72f4a6719b` | **CONFIRM** | CUPE Ontario’s own page explicitly endorses Shan and its first-party metadata gives a 2025-09-15 publication time, before the 2025-09-29 poll. The subsequently clarified panel rule applies every approved Endorser to both municipal offices. |

## 1. Star → Giambrone, 2003 Ward 18 — HOLD

The target is correctly identified in the City’s official 2003 election
results. The positive statement found is an uncited claim in Adam Giambrone’s
[Wikipedia biography](https://en.wikipedia.org/wiki/Adam_Giambrone). It names
the *Toronto Star*, but does not reproduce, link to, or cite an editorial. A
bibliographic reference to a November 6 Ward 18 item is a useful retrieval
target, not direct evidence of the board’s affirmative choice.

**Finding:** no direct attribution meeting the decision rule was recovered.
Keep the lead, but do not load an assertion.

## 2. Star → Miller, 2006 mayor — HOLD

The only recovered item is a secondary bibliographic record identifying a
*Toronto Star* editorial, “Qualified support for David Miller,” dated
2006-11-10, p. A26 ([record](https://en-academic.com/dic.nsf/enwiki/5061563/)).
It establishes a precise archive-retrieval target and is temporally before the
2006-11-13 vote. It does not reproduce the editorial, establish its precise
meaning, or qualify as publisher-owned evidence/direct contemporaneous
attribution.

**Finding:** hold. The Star archive scan or a reputable contemporaneous source
directly quoting/attributing the board’s selection remains necessary.

## 3. CUPE Ontario → Miller, 2003 mayor — HOLD

The recovered campaign-history material says Miller had support from “the
Canadian Union of Public Employees”/“CUPE” and identifies a March 5, 2003
*National Post* item, “Union backs Miller for mayoralty run” ([bibliographic
trail](https://en-academic.com/dic.nsf/enwiki/5061563/)). Neither establishes
that the choice came from **CUPE Ontario**, rather than CUPE National, a CUPE
local, or another CUPE body. CUPE Ontario’s own 2006 material discusses the
mayoral race but does not make a positive choice for Miller ([CUPE Ontario,
2006](https://cupe.on.ca/d307/gloves-off-jane-mayoral)).

**Finding:** hold for exact-entity failure. Do not transfer generic CUPE or
labour support to CUPE Ontario. A contemporaneous CUPE Ontario release naming
Miller, or the full March 2003 report specifically identifying CUPE Ontario,
would be needed.

## 4. CUPE Ontario → Shan, 2025 Ward 25 — CONFIRM, with two important distinctions

### Fact confidence and timing

CUPE Ontario’s own [“Shan for
Scarborough”](https://cupe.on.ca/shanforscarborough/) page expressly says:
“CUPE Ontario is proud to endorse Neethan Shan for Toronto City Council in the
Ward 25 Scarborough by-election.” This is an exact-entity, first-party,
candidate-specific positive choice.

The page’s source metadata independently supplies the timing the discovery
memo could not see:

- `datePublished`: **2025-09-15T19:51:32+00:00**
- `dateModified`: 2025-09-15T20:04:42+00:00

That is precise-to-the-second first-party page metadata and precedes the
2025-09-29 poll by fourteen days. The page’s visible “Monday, September 30”
instruction is evidently stale/wrong (the poll was September 29), but does not
undercut the machine-readable publication timestamp. A separate, dated
[Toronto & York Region Labour Council post](https://www.labourcouncil.ca/elect-neethan-shan-in-scarborough-rouge-park/)
published September 22 also announces a September 23 canvass “with CUPE ON”;
it corroborates contemporaneous CUPE Ontario campaign activity, but is not
needed to prove the exact CUPE Ontario fact.

**Evidence disposition:** **CONFIRM.** The proper 2025 key is
`con_c8883aeeac29529eada91aebc451242b` /
`can_2a0745629be0507080db6d72f4a6719b`, with date precision `second` and
source date `2025-09-15T19:51:32+00:00` (or `2025-09-15` if the assertion
schema accepts dates only).

### Ledger-key correction

The Luna memo labels the 2025 Ward 25 fact with
`con_eeda9883ca2d57148405d41f7f5a80a4` /
`can_8fba857b4440581999ddfd32c59ec62f`. The canonical ledger shows that
pair belongs to the **2018-10-22** Ward 25 general election. It must not be
used for the 2025 endorsement. The 2025 contest/candidacy are the IDs listed
above.

### Panel-policy implementation update

The panel rule was subsequently clarified: every approved panel Endorser is
applicable to both Toronto Mayor and City Councillor Contests. That shared
scope does not lower the evidence bar, but this independently verified fact
now meets both the evidence and scope rules and is loadable under the corrected
2025 keys.

## Result

This pass confirms one new importable fact (CUPE Ontario → Neethan Shan, 2025
Ward 25). The other three leads remain holds. The two Star leads need archival
editorial text/direct attribution; the 2003 CUPE lead needs exact-entity
evidence.
