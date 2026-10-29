# Name display fixes and identity follow-ups — 2026-10-29

Scope: three 2003 trustee names that were published in the wrong form, and five identity leads left open by the pre-2003 municipal and 2000 trustee reviews (Walter Melnyk, Tony Letra, Elizabeth Hill, Scott Harrison and Joseph Cohen). The evidence standard is the one used in those reviews. A confirmed link needs a person-specific source, or strong structural continuity for the same office type with an uncommon name. A link across office types needs a person-specific source, and exact name alone is never enough.

## Part A: name display

### Given-name-first declaration names

The trustee adapter (`trustees.py`) passed every trustee name to `candidates.normalize_name`, which reads a name without a comma as surname-first. That is the convention of the 2006 to 2022 poll-by-poll workbooks. The 2003 Conseil scolaire Viamonde Candidacies have no workbook, because all three wards were acclaimed. They are transcribed from the City Clerk's 2003 declaration of results, which prints every name given-name first: page 8 lists "FRANCOIS GUERIN", "DENYS BEGIN" and "ALAIN MASSON" as acclaimed in wards 2, 3 and 4. The normaliser reversed all three, so Denys Begin was a third affected row from the same source.

The 2022 Declaration of Acclamation is the same kind of source and had the same defect. Its French-board acclamations ("Benoit Fortin", "Geneviève Oger", "Nathalie Dufour Séguin") were published as "Fortin Benoit", "Oger Geneviève" and "Dufour Séguin Nathalie". I fixed those rows as well, because they come from the same transcription table and the same rule fixes them.

The fix is in the adapter, for this source. `_Acclamation` now records whether a declaration transcription is in given-name-first order, and the six declaration-only entries above are flagged. `_result_frame` displays a flagged row with the new `candidates.normalize_given_name_first`, which keeps the printed word order and only normalises spacing and capitalisation. `municipal_archive.py` already treats the given-name-first 1997 and 2000 archive pages the same way. The other declaration entries were either transcribed surname-first (2006 Claude Legere) or are rows a workbook also lists (for example 2003 Claude D'Aigle and 2006 Alain Masson), so they already displayed correctly and are not flagged.

### The stray space in LeBlanc-Miller

The 2003 TCDSB workbook prints "LeBlanc- Miller, Catherine". `normalize_name` collapsed runs of whitespace but kept the space after the hyphen. It now drops any space typed beside a hyphen, because a hyphen joins the parts of one name, and `known_multiword_surnames` applies the same rule so the name is not learned as a two-word surname. The row now displays as "Catherine Leblanc-Miller", the same form as her 2000, 2006 and 2010 rows.

A scan of all 345 published 2003 Clerk names (mayor, council and trustee) found no other name without a comma or with stray spacing. A scan of every published name found one more hyphen typo, the 2008 federal general-election row "El- Farouk Khaki" from Elections Canada's poll results. That row comes from a different source and does not pass through this normaliser. It is already linked to the same Person as his 2008 by-election row, so I left it unchanged.

### Rows changed

Raw names, the Candidacy ledger and all Candidacy IDs are unchanged. Only `candidate_name` changed, on these seven rows:

| Candidacy | Election | Board | Ward | Raw name | Before | After |
|---|---|---|---|---|---|---|
| `can_90f657c136335edeb00a8cc29149c879` | 2003 | Viamonde | 2 | FRANCOIS GUERIN | Guerin Francois | Francois Guerin |
| `can_733d7aab27a05f26ac3f9f859c22e362` | 2003 | Viamonde | 3 | DENYS BEGIN | Begin Denys | Denys Begin |
| `can_7343d07b0cfd59c4bf15318716932095` | 2003 | Viamonde | 4 | ALAIN MASSON | Masson Alain | Alain Masson |
| `can_dced59fe77ad5682a90e4bffd42645b6` | 2003 | TCDSB | 9 | LeBlanc- Miller, Catherine | Catherine Leblanc- Miller | Catherine Leblanc-Miller |
| `can_628f2c912c1c5b3481375b971c2d0965` | 2022 | Viamonde | 2 | Benoit Fortin | Fortin Benoit | Benoit Fortin |
| `can_b0d1c647178256309bb98544e892f006` | 2022 | Viamonde | 4 | Geneviève Oger | Oger Geneviève | Geneviève Oger |
| `can_11ede9c2b79853e9a17c4972d0f34f08` | 2022 | MonAvenir | 3 | Nathalie Dufour Séguin | Dufour Séguin Nathalie | Nathalie Dufour Séguin |

`data/reference/trustee_career_decisions.csv` records the published display name of each prior occurrence it reviews (`observed_ballot_name`), so the entries for the 2022 Oger and Fortin rows were updated to the new names.

### Identity effect

The change has no identity effect. All seven Candidacies already held confirmed links through curated assertions that locate them by Candidacy ID, and the registry adds rows only for Candidacies it has not seen. The rebuilt `people.csv` and `candidacy_person_links.csv` were byte-identical to the previous release, the bootstrap raised the same review flags, and no proposal was added or changed (the 59 active proposals are all 2026 pending Candidacies, as before). The difference would show only in a registry bootstrapped from nothing, where five rows would become exact-name proposals to an earlier record of the same person (for example 2003 Alain Masson to the 2000 Alain Masson record, and 2006 Denys Begin to the 2003 one). In the persisted registry those rows are already confirmed to that Person.

### Left open

- The 2010 and 2018 rows for Nathalie Dufour Séguin ("DUFOUR SÉGUIN NATHALIE" and "Dufour Séguin Nathalie" in the workbooks) display as "Séguin Nathalie Dufour". That is a different problem: the workbooks are surname-first, but the two-word surname has no hyphen, and no comma-form source in the trustee files teaches the split. The rows are linked to the right Person.
- The assertion locators in `identity_curations.py` still carry the old display names as labels ("Masson Alain", "Guerin Francois", "Begin Denys", "Oger Geneviève", "Fortin Benoit", "Dufour Séguin Nathalie"). They match by Candidacy ID, so I left that file untouched.

## Part B: identity leads

### 1. Walter Melnyk: no change

Records: the 1997 council Ward 19 run (`can_7579ade3e49d5dc581572fce2b8fba6b`), the 2000 TCDSB Ward 10 run (`can_16473b5096ec5f5497520951ba27b314`) and the 2014 council Ward 5 run (`can_bf11897bd8c752d0bfb0b070885e3de2`) stay unresolved against `per_6a5242868c1f526eab2db3f3b6f6da14`, which holds the 2006 council Ward 6 run.

Sources:

- https://en.wikipedia.org/wiki/1997_Toronto_municipal_election has a long candidate note on the Ward 19 candidate: "Walter Melnyk was a teacher in Peel, and later worked in sales", "He was a member of the Metro Toronto Separate School Board from 1980 to 1988", "He campaigned for a seat on the Toronto City Council in 1991, promising to introduce a taxpayers' bill of rights", and "He tried to return to the Separate School Board (now renamed as the Toronto Catholic District School Board) in 2000, but lost to Barbara Poplowski for a second time." It cites a 1988 Toronto Star article that gives his age as 39.
- https://en.wikipedia.org/wiki/2014_Toronto_municipal_election gives, without a citation, the 2014 Ward 5 candidate's issues: "supporting the property tax cap, introducing a Taxpayers Bill of Rights, and eliminating the land transfer tax."
- https://en.wikipedia.org/wiki/2006_Toronto_municipal_election has only his result row (309 votes) in Ward 6.
- I found nothing describing the 2006 or 2014 candidate in Global News's 2014 Ward 5 page, Sean Marshall's 2014 ward maps, the Ukrainian community press, or obituary searches.

The 1997 note joins the 1997 and 2000 runs, since the 2000 TCDSB Ward 10 contest is the one Barbara Poplawski won. No source places that man in Etobicoke-Lakeshore in 2006 or 2014. The 2014 platform repeats the taxpayers' bill of rights he campaigned on in 1991, and he would have been about 57 in 2006 and 65 in 2014. A shared policy idea is not identity evidence, though, and Ward 19 (High Park) does not overlap either Etobicoke-Lakeshore ward. Nothing shows the Etobicoke candidate to be a different man either. Per the project rule, the 1997 and 2000 runs stay unresolved against the existing Person, and no separate Person is created for them. The 2014 run also stays unresolved against the 2006 run (a neighbouring ward eight years later, with no source).

### 2. Tony Letra: 1997 confirmed, 2000 unchanged

Decision: `can_345785ba33dd545397a7a15ec83f710b` (1997 council Ward 21) confirmed to `per_0649ecb7cb135ca7aee48b5b74b79fb3`, which holds the 2010 council Ward 17 run. `can_f0f6068771fa57d89f002ae177e9de18` (2000 TCDSB Ward 10) stays unresolved.

Sources:

- https://movimentoperpetuo.ca/political-flyers-of-portuguese-canadian-candidates/ is the "Political Literature from Portuguese-Canadian Candidates in Toronto" page of Movimento Perpétuo: The Portuguese Diaspora in Canada, a digital companion to an exhibition, developed by Tempo Historical Consulting. It lists one António Letra under each election: "António Letra, Metro Separate School Board Trustee (lost)" (1982), "(won)" (1985 and 1994), "António Letra, Alderman, Ward 4, Trinity Bellwoods-Little Italy (3rd place, 1266)" (1988), "António Letra, Councillor, Ward 21, Davenport (5th place, 4788)" (1997) and "António Letra, Councillor, Ward 17, Davenport (3rd place, 2035 votes)" (2010). His 1988 flyers are filed as "Campaign-flyer-Tony-Letra".
- https://en.wikipedia.org/wiki/1988_Toronto_municipal_election lists "Tony Letra - 1,266" in Ward 4 (Trinity-Bellwoods and Little Italy).

The archive is a curated record of one person's campaigns, and it gives the official totals of both council Candidacies (4,788 votes and fifth place in 1997, 2,035 votes and third place in 2010). The 1988 vote total and the flyer filenames show that António and Tony Letra are the same candidate. That is a person-specific source placing him in both contests, so the 1997 run is confirmed. The archive lists no 2000 school board run, and its 2000 section names only Mário Silva. His Metro Separate School Board service (1985 to 1988 and 1994 to 1997) makes the 2000 TCDSB run plausible, but no source places him in that contest. A council-to-trustee link needs one, so that row stays as it was.

### 3. Elizabeth Hill: 2006 and 2015 confirmed

Decision: `can_8e6c404ce2545b19b3d5413a881d754b` (2006 TDSB Ward 6) and `can_72c3041be0cd59bba264c3eaf28436a3` (2015 Communist candidacy in Don Valley West) confirmed to `per_df78a26908df56398f6feaaa81ef11a4`, which holds the 2000 and 2003 TDSB Ward 6 wins.

Sources:

- https://communist-party.ca/?p=1804, the party's page for its Don Valley West candidate: "She was elected to the City of York Board of Education in 1988 and served as a Trustee for 18 years."
- https://en.wikipedia.org/wiki/Communist_Party_of_Canada_candidates_in_the_2015_Canadian_federal_election, Don Valley West row: "Elizabeth Hill | City of York Board of Education Trustee from 1988 to 2006 | F | 84 | 0.2 | 6/7". It cites the party page above.

The Wikipedia row gives the official 2015 result (84 votes, sixth of seven), so the party biography belongs to the 2015 Candidacy. It describes a trustee career from 1988 to 2006 that covers the target's 2000 and 2003 Ward 6 terms, which is the person-specific source a link from MP to trustee needs. The 2000 trustee review had already used this biography to confirm the 2000 run. For 2006, a career ending in 2006 means she was still the Ward 6 trustee, acclaimed there in 2003, when the 2006 Ward 6 Candidacy lost to Chris Tonks. The source and the same-ward continuity together place her in that contest.

### 4. Scott Harrison: 2012 by-election confirmed, 2000 and 2018 unchanged

Decision: `can_8eb0b96fd86159348a661a484ec38be0` (2012-02-27 TDSB Ward 20 by-election) confirmed to `per_cf67e953cc5d5813be347c92214ea37d`, which holds the TDSB Ward 19 runs of 2003 to 2014. The 2000 Ward 19 win (`can_adc17e058c1151e58a97e2f334a6c304`) and the 2018 Ward 17 run (`can_0c98702a96eb5c87bf47fb6ab98873f4`) stay unresolved.

Sources:

- https://www.theglobeandmail.com/news/toronto/former-trustee-to-run-in-tdsb-by-election/article4097986: "Scott Harrison, formerly a trustee for Ward 19, is now running in Ward 20, Scarborough-Agincourt on Feb. 27." and "Mr. Harrison lost his seat to union-backed trustee David Smith two years ago".
- https://www.theglobeandmail.com/news/toronto/voters-choose-at-least-12-new-school-trustees/article1215614/ (2010): "In Ward 19 (Scarborough Centre), trustee Scott Harrison, a firefighter and former police officer, was unseated by David Smith".
- https://torontoobserver.ca/2010/10/28/tdsb-incumbents-were-hit-and-miss-with-scarborough-voters/ describes David Smith beating incumbent Scott Harrison in Ward 19, without a start date.

The 2012 article names the by-election, its date and ward, and identifies the candidate as the Ward 19 trustee whom David Smith unseated in 2010, which is the target. That is person-specific news coverage, so the 2012 row is confirmed.

For 2000, no source I could read gives his first election. The existing curated assertion `scott-harrison-tdsb-2003-2010-continuity` cites TDSB board minutes (https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=101110.pdf&Type=M&Year=2010) as saying he served as a trustee for ten years. Ten years of service ending in November 2010 would begin with the term won in 2000. The fetch tool refused that URL and the TDSB site is not one this review may download from directly, so the wording was not checked and the 2000 row stays unresolved. If the minutes say ten years, the 2000 win can be confirmed on that basis.

For 2018, the TDSB Ward 17 (Scarborough Centre) contest was a rematch with David Smith, who had beaten him in 2010 and 2014. That is suggestive, but Scott Harrison is a common name and no source describes the 2018 candidate, so the row stays unresolved.

### 5. Joseph Cohen: no change

Records: the 2000 TDSB Ward 8 (`can_4385b18ccdb95d6fab3f75c18fd593fb`), 2006 TDSB Ward 11 (`can_715cf905cc095072bfc5b460cb9e0f34`), 2010 council Ward 10 (`can_fb59368b8b845261839d4fd98997b496`) and 2018 TDSB Ward 5 (`can_bca16b1c85215b4f8a6fc766fb6188c8`) runs stay unresolved against `per_c0e962facfbf55fc974ea57d9bc25d1e` (2003 TDSB Ward 8). The 1999 Green provincial candidate (`per_1c2d843566655effa0c53cb41b7bd745`) stays a separate Person.

Sources checked: the CJN's 2010 Ward 10 article (https://www.cjnews.com/news/ward-10-candidates-outline-priorities) says only "Cohen, a late addition to the race, did not respond to queries by The CJN's deadline". Wikipedia's 2010 page gives only his registration date (August 23). The 2010 LocalWiki candidate list (https://localwiki.org/toronto/2010ElectionWiki/Left) links a candidate page that the fetch tool would not open. The CJN's 2016 Ward 5 by-election article is about other candidates, and searches for the 2000, 2006 and 2018 trustee races found nothing about him.

The runs are all in north-central Toronto (Eglinton-Lawrence, St. Paul's and York Centre), which fits one man, but the name is common and no source describes any of these candidates, so none of the runs is linked.

## Counts

"Before" is the release after the 2010 TCDSB ward fix (`tcdsb-2010-ward-assignment-2026-10-29.md`).

| Measure | Before | After |
|---|---|---|
| `identity_review_dispositions.csv` rows | 1,399 | 1,399 |
| confirmed / unresolved / rejected | 464 / 934 / 1 | 468 / 930 / 1 |
| Candidacies with a published `person_id` | 6,608 | 6,612 |
| Candidacies with a null `person_id` | 950 | 946 |
| `candidacy_person_links.csv` rows | 10,689 | 10,693 |
| active proposed links | 59 | 59 |
| People (active / deprecated) | 4,963 (4,861 / 102) | 4,963 (4,861 / 102) |

The four new decisions replace their earlier rows in place under reviewer `identity-followups-2026-10-29`.

## Decisions

| Candidacy | Election | Contest | Name | Decision | Basis |
|---|---|---|---|---|---|
| `can_7579ade3e49d5dc581572fce2b8fba6b` | 1997 | Council Ward 19 | Walter Melnyk | unresolved (unchanged) | none |
| `can_16473b5096ec5f5497520951ba27b314` | 2000 | TCDSB Ward 10 | Walter Melnyk | unresolved (unchanged) | none |
| `can_bf11897bd8c752d0bfb0b070885e3de2` | 2014 | Council Ward 5 | Walter Melnyk | unresolved (unchanged) | none |
| `can_345785ba33dd545397a7a15ec83f710b` | 1997 | Council Ward 21 | Tony Letra | confirmed | person-specific |
| `can_f0f6068771fa57d89f002ae177e9de18` | 2000 | TCDSB Ward 10 | Tony Letra | unresolved (unchanged) | none |
| `can_8e6c404ce2545b19b3d5413a881d754b` | 2006 | TDSB Ward 6 | Elizabeth Hill | confirmed | person-specific |
| `can_72c3041be0cd59bba264c3eaf28436a3` | 2015 | Don Valley West (federal) | Elizabeth Hill | confirmed | person-specific |
| `can_adc17e058c1151e58a97e2f334a6c304` | 2000 | TDSB Ward 19 | Scott Harrison | unresolved (unchanged) | none |
| `can_8eb0b96fd86159348a661a484ec38be0` | 2012 | TDSB Ward 20 (by-election) | Scott Harrison | confirmed | person-specific |
| `can_0c98702a96eb5c87bf47fb6ab98873f4` | 2018 | TDSB Ward 17 | Scott Harrison | unresolved (unchanged) | none |
| `can_4385b18ccdb95d6fab3f75c18fd593fb` | 2000 | TDSB Ward 8 | Joseph Cohen | unresolved (unchanged) | none |
| `can_715cf905cc095072bfc5b460cb9e0f34` | 2006 | TDSB Ward 11 | Joseph Cohen | unresolved (unchanged) | none |
| `can_fb59368b8b845261839d4fd98997b496` | 2010 | Council Ward 10 | Joseph Cohen | unresolved (unchanged) | none |
| `can_bca16b1c85215b4f8a6fc766fb6188c8` | 2018 | TDSB Ward 5 | Joseph Cohen | unresolved (unchanged) | none |
