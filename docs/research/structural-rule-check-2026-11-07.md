# Structural rule check (2026-11-07)

This pass recorded what each confirmed curated link rests on, as the new `evidence_basis` field of
`candidacy_person_links`, and then tested every link recorded as structural against the rules in
the Identity section of [`docs/build-notes.md`](../build-notes.md). Dispositions changed here are
under reviewer `structural-rule-check-2026-11-07`.

## Recording the basis

Each confirmed link made by an identity assertion or a review disposition is recorded in
`data/reference/identity_link_basis.csv` as resting on a source about the person
(`person_specific_source`), on the structural rules alone (`structural`) or, for three 1994 North
York trustee runs that the City's archive also printed under council wards, on the same official
record (`official_record`). Where a pass's report tabulates a basis for each Candidacy, the label
comes from that table, and `label_source` names the report. Elsewhere it comes from the link's own
rationale, which says what ties the runs. A rationale that says the link is structural, or rests
on same-office continuity or on the rule for runs at both levels in one riding, is structural. So
is one whose only cited evidence is the official results and which names no source about the
person. An occupation that the candidate records give for each run counts as a source about the
person, as it does in the link audit. Links made automatically need no record: a Candidacy's own
Person is `own_record`, and authority-reported incumbency and Council rosters are
`official_record`.

## Testing the structural links

Each structural link was tested for a run of the same Person that it continues: the same office
type with at most one general election between and the same Party where Parties apply, or a House
of Commons run and an Ontario legislature run in a riding of the same name within two years. Each
Person whose runs span two office types was also tested for a source that ties the offices. Party
labels that changed form between years (Natural Law Party of Canada and Natural Law Party, for
example) count as one Party, and so does Reform's 2000 successor, the Canadian Alliance. Name
commonness and ward overlap are judged by the reviewers and were not retested.

Twelve Persons joined runs for different offices on results alone, which the rules do not allow.
Each is a public figure, and each assertion now cites a page that names the runs: the Wikipedia
biographies of Ana Bailão, Brad Duguid, Gary Crawford, Giorgio Mammoliti (for his 2023 mayoral
run), Gord Perks, Irene Jones, Joe Cressy, Lorenzo Berardinetti, Mark Saunders and Mike Del Grande,
and Wikipedia's page on the 2023 mayoral by-election for Sarah Climenhaga and Erwin Sniedzins. Two
others whose rationales were short summaries, Cory Deville's mayoral career review and Mitch
Gold's 1994 trustee and mayoral runs, already cite such a source.

Twelve same-office joins failed the gap or party test. Most came from the earliest adjudication
passes, before the rules were written down. Sources were found for three:

- Bernard Trottier, 2025 House of Commons run in Etobicoke—Lakeshore: his Wikipedia biography gives
  his 2011 win, his 2015 defeat and his 2025 candidacy there.
- Priti Lamba, 2021 House run in Etobicoke North: the Toronto Star's riding result of 21 September
  2021 says she also ran against Kirsty Duncan in 2011.
- John Papadakis, 2014 council run in Ward 29: the Toronto Observer's report of 27 October 2014,
  already cited by his other assertion, describes the 2014 candidate as the former East York
  councillor.

The other nine are held, so each keeps its candidate Person for audit and has no `person_id`:

| Run | Why it fails |
|---|---|
| Bob Smith, 2014 council, Ward 31 | Two general elections after his 2003 run there, and a common name |
| George Szebik, 2015 House, Etobicoke North | Two general elections after his 2006 run there |
| Robert Spencer, 2018 TDSB Ward 18 | Two general elections after his 2006 run, and the 2018 Ward 18 is a different area |
| Vilma Santos-Bidinost, 2018 TDSB Ward 1 | Two general elections after her 2006 run there |
| Erwin Sniedzins, 2014 mayor | Two general elections before his 2023 mayoral run; no source ties it to his provincial runs |
| Charles Roddy Sutherland, 2022 Ontario, Willowdale | Three general elections after his 2007 run there |
| Stella Kargiannakis, 2022 Ontario, Don Valley East | Three general elections after her 2007 run; The Local's 2022 guide lists her other runs but not this one |
| Sharolyn Vettese, 2025 Ontario, Willowdale | Five general elections after her 2003 run there |
| Lilya Eklishaeva, 2025 Ontario, Willowdale | Independent in 2025 after a 2022 run for the Freedom of Choice, Peace & Justice Party |

No Person was emptied, so the release keeps 5,079 People. Confirmed links fall from 7,695 to 7,686.
`tests/test_link_basis.py` now runs the same test on every structural link in each build.
