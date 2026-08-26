# Chloe Brown candidacy identity audit

Date: 2026-08-24  
Scope: four Toronto municipal candidacies currently divided between two Person records

## Disposition

**CONFIRM — high confidence.** The four candidacies below belong to one individual:

| Election | Ballot name | Candidacy ID | Pre-curation Person state |
|---|---|---|---|
| 2016-07-25 Ward 2 council by-election | Chloe-Marie Brown | `can_c9c2e18dba7955429a08971f4d728751` | `per_3d3501723d055766800769f77751b3bf` |
| 2022-10-24 mayoral election | Chloe-Marie Brown | `can_0a4ce7edba2e522ca838be9dddcdecee` | unresolved proposal to `per_3d3501723d055766800769f77751b3bf` |
| 2023-06-26 mayoral by-election | Chloe Brown | `can_f3c0829c97525d048039948585926327` | `per_abd4663f08cb5b11bbe72c502697a809` |
| 2026-10-26 Ward 1 council election | Chloe Brown | `can_e6be2215757451db85e79f587b054f77` | unresolved proposal to `per_abd4663f08cb5b11bbe72c502697a809` |

Implemented curation: link all four candidacies to
`per_3d3501723d055766800769f77751b3bf`, redirect
`per_abd4663f08cb5b11bbe72c502697a809` to that retained Person, and use
**Chloe Brown** as the preferred display name because that is the name used by her
current candidate-controlled campaign. Preserve `Chloe-Marie Brown` as the exact
2016 and 2022 ballot name.

## Evidence

### Direct 2022–2023–2026 bridge

The current candidate-controlled [Chloe Brown for Ward 1 biography](https://www.cb4ward1.ca/about)
identifies the 2026 candidate and explicitly states, “I ran for mayor in 2022 and
2023.” The page also says she grew up and later studied in Etobicoke North. The
City's official candidate feed identifies the Ward 1 candidate as Chloe Brown and
links to that same campaign website ([City of Toronto 2026 councillor-candidate feed](https://www.toronto.ca/data/elections/candidate_list/councilorCandidates_2026.json)).

The City Clerk's official declarations establish that the 2022 mayoral ballot used
**Chloe-Marie Brown** ([2022 declaration, p. 2](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf))
while the 2023 mayoral ballot used **Chloe Brown** ([2023 declaration, p. 2](https://www.toronto.ca/wp-content/uploads/2023/06/900e-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor.pdf)).
The [Samara Centre's election study](https://www.samaracentre.ca/articles/who-gets-a-platform-media-exposure-and-online-engagement)
independently resolves the variation, explicitly noting that 2023 candidate Chloe
Brown appeared as “Chloe-Marie Brown” on the 2022 ballot.

This is dispositive for the 2022, 2023, and 2026 occurrences: the current candidate
herself claims both prior mayoral runs, and the official records supply the exact
ballot names.

### 2016 bridge

The City Clerk's [2016 Ward 2 declaration](https://www.toronto.ca/wp-content/uploads/2017/08/8e3a-2017-byelection-ward2-declarationofresults.pdf)
records Chloe-Marie Brown as a councillor candidate in Etobicoke North. The exact,
uncommon full name matches the 2022 official mayoral record.

There is also distinctive biographical continuity:

- Contemporaneous [NOW reporting on the 2016 candidacy](https://nowtoronto.com/news/hey-look-another-ford/)
  identifies Chloe-Marie Brown as a George Brown College project-support officer
  and former Toronto Youth Cabinet policy-and-advocacy director.
- Her current candidate-controlled biography says she worked with George Brown
  College and on the Woodbine Casino Community Benefit Agreement.
- The Toronto Community Benefits Network's [2017 AGM account](https://www.communitybenefits.ca/agm_recap)
  identifies **Chloe-Marie Brown** as a Woodbine Casino community-benefits champion.
- An independent [2022 election-history account](https://www.stephentaylor.ca/data/political/canada/municipal/toronto/2022/)
  explicitly says that the 2022 mayoral candidate first ran in the 2016 Ward 2
  by-election.

No single located official or surviving candidate-controlled page states the whole
2016-to-2022 bridge in one sentence. That limitation does not make this a name-only
match: two official records use the exact uncommon name, the work history is
distinctive and continuous, and independent reporting explicitly connects the
elections. No contradictory occurrence or same-election collision was found.

## Implementation boundary

This audit supports an enumerated identity curation for exactly the four candidacy
IDs above. It does not authorize fuzzy matching of other `Chloe Brown` rows or
changes to ballot-name fields, vote totals, outcomes, or office classifications.
