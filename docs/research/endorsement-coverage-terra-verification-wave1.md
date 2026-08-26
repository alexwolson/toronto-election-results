# Verification audit: Terra mayor-endorsement coverage, wave 1

**Audit date:** 2026-08-22  
**Scope:** independent adjudication of the three proposed David Miller facts in
[`endorsement-coverage-terra-mayors-2003-2025.md`](endorsement-coverage-terra-mayors-2003-2025.md).
No curation input, generated output, or other data file was changed.

## Applied gate

The project admits a positive edge only for explicit electoral support, publicly
made before polls closed, by the exact approved Endorser for an in-scope Mayor
or Councillor Candidacy. A first-party statement is preferred, but a reputable
contemporaneous source that directly attributes the choice is sufficient.
Praise, policy agreement, an appearance, campaign employment, or a
post-election congratulations message is not enough. This audit treats a
post-poll article as qualifying only when it directly reports the already-made
campaign endorsement—not when it merely establishes a later alliance or
favourable comment.

The exact approved Endorser is **David Miller** (`edr_a7c5fbf78b725c8db8ec32c4c4fc177a`,
person `per_ad293f1387af572cad45897886519bb6`), eligible from 2003-12-01.
Each target below is a final City-Clerk-sourced City Council Candidacy in the
current `data/out/election_results.csv`; its Contest, date, office, ward, and
candidate name were checked from that row.

## Fact decisions

| Proposed fact | Target validation | Decision | Exact source evidence and timing |
| --- | --- | --- | --- |
| Miller → Gord Perks, 2006 Ward 14 | `can_8beb4a28087f5a58b667f68fdc297a43`; `con_b4c70c0c6f465c4091dce97cbbd286b3`; 2006-11-13, councillor, Ward 14, Gord Perks | **CONFIRM** | The *Philippine Reporter*’s [Nov. 1 pre-poll interview](https://philippinereporter.com/index.php/2006/11/01/rowena-santos-talks-to-the-philippine-reporter/) says: “Although the Mayor has endorsed her opponent Gord Perks …” (Mayor is David Miller in the immediately preceding text). This is explicit candidate-directed electoral support, published 12 days before the poll. Independently, York University’s preserved [Nov. 11 *National Post* account](https://www.yorku.ca/yfile/2006/11/14/york-university-charts-a-new-course/) reports that Perks “has earned the endorsement of Mayor David Miller,” two days before the poll. Neither is praise or an appearance. |
| Miller → Glenn De Baeremaeker, 2006 Ward 38 | `can_3f84dacf17b85bdbad830258c4a975a8`; `con_17c2e1a7404c5641823443ca7a6dcc10`; 2006-11-13, councillor, Ward 38, Glenn De Baeremaeker | **CONFIRM** | The *Philippine Reporter*’s [Nov. 16 contemporaneous election account](https://philippinereporter.com/?p=3703) identifies Ward 38’s winner as “Glenn De Baeremaeker … who was also endorsed by Mayor Miller.” The article is three days after the poll, but reports an endorsement made in the campaign—not a later congratulations, office appointment, or policy praise. “Also” connects it to the article’s just-described Miller-backed Ward 14 campaign; the claim is direct attribution to the exact individual. No earlier independently retrievable report was recovered in this audit, so retain this source-access limitation with the assertion. |
| Miller → Kevin Beaulieu, 2010 Ward 18 | `can_7c4e23514e3b546e8fc7ea161c40a4f1`; `con_d6f7b1cb92f959ab9408dbb936bcf2ff`; 2010-10-25, councillor, Ward 18, Kevin Beaulieu | **CONFIRM** | Nicole McIsaac’s [*Spacing* profile, Oct. 19](https://spacing.ca/toronto/2010/10/19/election-council-turnover-ward-18/), published six days before the poll, says: “Endorsed by Mayor David Miller, Gord Perks, Adam Giambrone and Adam Vaughan, Kevin Beaulieu …” It is a direct, unqualified electoral-support attribution, not an inference from Beaulieu’s former campaign job. The [Oct. 18 *Xtra* profile](https://xtramagazine.com/power/social-services-are-in-danger-kevin-beaulieu-8909) separately says he “has been endorsed by David Miller,” corroborating the timing and exact-person attribution. |

## Coverage disposition

`comprehensive_source_found` requires a complete slate source or an explicit
choice source at the specific contest cell; individual discoveries do not make
the rest of an event complete. `partially_searched` is appropriate where an
auditable limited source search has recovered relevant material without a
source-complete slate or a completed negative search.

| Event × office batch | Auditable search scope completed in this audit | If baseline were `not_searched` | Current data/out state | Decision |
| --- | --- | --- | --- | --- |
| David Miller, 2006-11-13 × City Council | Direct retrieval/search of the dated *Philippine Reporter* Ward 14 interview, its Nov. 16 election report, and York’s preserved Nov. 11 *National Post* election roundup; exact-name combinations for Miller/Perks and Miller/De Baeremaeker were also checked. These sources establish two named ward claims but present no Miller slate, exclusion list, or archive-wide search certificate. | Upgrade to **`partially_searched`** only. | Every eligible historical Miller contest cell, including Ward 14 (`con_b4c70c0c6f465c4091dce97cbbd286b3`) and Ward 38 (`con_17c2e1a7404c5641823443ca7a6dcc10`), is already `partially_searched` with basis “open-world historical search is not source-complete.” | **No data/out change required; not comprehensive.** |
| David Miller, 2010-10-25 × City Council | Direct retrieval of the dated *Spacing* Ward 18 candidate profile; separate *Xtra* profile; exact-name query for Miller/Beaulieu. These establish the Ward 18 fact only and do not enumerate the other 43 council races or supply a complete Miller slate. | Upgrade to **`partially_searched`** only. | Ward 18 (`con_d6f7b1cb92f959ab9408dbb936bcf2ff`) is already `partially_searched` with the same open-world basis. | **No data/out change required; not comprehensive.** |
| David Miller, 2010-10-25 × Mayor | This wave did not independently re-audit the existing Pantalone mayor assertion; it searched the proposed Ward 18 council claim. | No new recommendation from this wave. | The Mayor contest remains separately covered by existing project material. | **No coverage upgrade adjudicated here.** |

Therefore, the only coverage state that this evidence can support is
`partially_searched` for the two Council batches. It does **not** support
`comprehensive_source_found`, `searched_no_endorsement_found`, or any
candidate-level negative inference. Because the current output already has the
relevant cells at `partially_searched`, this audit recommends no coverage-file
mutation.

## Retrieval note

The two *Philippine Reporter* pages were discoverable with full dated text in
the source index, but their direct page fetches later returned a cache miss.
The quoted text and URLs above are retained exactly as independently retrieved;
the accessible York and Spacing pages provide durable corroboration for Perks
and Beaulieu respectively. This availability issue does not convert either
source into a negative finding.
