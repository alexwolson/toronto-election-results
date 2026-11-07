# Provenance: how the release was made

This note records, stage by stage, what code did, what AI agents did and what the authors did in
building the release. It is drawn from the repository (commit metadata, the `reviewer` values in
the identity files, the model recorded in one review table, and the reports in `docs/research/`
and `docs/verification/`) and from Alex Olson's account of the tools of August and September and
of the authors' roles. Text in square brackets marks the one stage not yet done.

## Tools

| Period | Tool | What the repository records |
|---|---|---|
| 19 August 2026 | Claude Opus 4.8 (Anthropic), in Claude Code | Co-author lines on the first five commits, which built the pipeline and added the 2003 and 2006 council rosters. |
| 26 August to 30 September 2026 | OpenAI Codex: mainly GPT-5.6 Sol, with GPT-5.6 Luna and GPT-5.6 Terra for some broad research, which Sol verified | 42 commits with no co-author line. Four of their branches are named `codex/`, one review tag is `codex-primary-source-review-2026-09-30`, and the trustee career review records the model `gpt-5.6-sol` for its third reviewer, Sol. The reports of this period name two other researchers, Luna and Terra. |
| 26 September to 7 November 2026 | Claude Opus 5.5 (Anthropic), in Claude Code | Co-author lines on the two commits of 26 September and on every commit from 7 October except Dependabot's. One coordinating session, from 28 October, had launched 183 agents by 7 November, all Claude Opus 5.5, for the review, research and audit passes described below. |

The agents worked in the repository: they wrote the code, ran the build and the tests, and searched
the public web. From 28 October the coordinating agent read the Toronto Star and other newspapers
in ProQuest through the project owner's University of Toronto access, in a browser he had signed in
to. The agents it launched had no ProQuest access. Neither it nor they used LinkedIn or pages
behind another login. The Codex agents of August and September used only the public web.

Alex Olson did the authors' part of the work. He set the scope and the evidence standard, directed
the agents, and reviewed and merged the pull requests they opened. He decided individual links in
one stage, the primary review of August and September described below. Matt Elliott supported
the project and gave feedback on it throughout.

## Results

Election authorities' files are downloaded and parsed by code in `src/toronto_election_results/`;
no total from those files is typed by hand. Documents with no machine-readable form are
transcribed by scripts where possible: the City's archived 1994 and 1997 results (PDFs), its 2000
results pages and the Clerk's 2026 declaration of results. The Toronto Star's printed results,
which supply most 1994 and 1997 trustee Contests and eight 1994 council Contests, were transcribed
from ProQuest page images in the session of 29 October 2026 (Claude Opus 5.5).
`docs/research/school-boards-1994-1997-2026-10-29.md` reconciles them with the City's archive.

Tests, the release gates in the data dictionary and the comparison with external datasets
(`docs/verification/external-reconciliation-2026-11-07.md`) check the results. Alex Olson
reviewed all of the code in the agents' pull requests and read about a tenth of the Star
transcriptions.

## Rosters used for incumbency

- The 2003 and 2006 councils: two agents each compiled the sitting council from public sources,
  and their lists (`data/reference/roster_agent_a.txt`, `data/reference/roster_agent_b.txt`) were
  reconciled and checked against the City's list of councillors since 1998 (ADR 0002). They were
  added on 19 August 2026 with Claude Opus 4.8. Alex Olson reconciled the two lists.
- The 2010 to 2022 councils: the City's open data on Council attendance and votes, read by code.
- The 2000 council and the 1997 predecessor councils: compiled in November 2026 by the
  coordinating agent (Claude Opus 5.5) from the certified results, by-election results, the City's
  lists of councillors and Toronto Star reports. See the build notes and
  `docs/research/predecessor-rosters-1997-2026-11-07.md`.
- The House of Commons: the House's member exports and the Library of Parliament's ParlInfo, read
  by `scripts/build_house_of_commons_members.py`.
- The Legislative Assembly of Ontario: the member profiles on ola.org, which the site serves only
  to a browser. On 7 November 2026 the coordinating agent ran `scripts/ola_members.js` in the
  project owner's Chrome, with his permission, to save them, and
  `scripts/build_ontario_members.py` turned the file into
  `data/reference/ontario_legislature_members.csv`.
- Council appointments: `data/reference/council_appointments.csv`, compiled on 7 November 2026 by
  the coordinating agent from the City Clerk's list of Council vacancies since amalgamation,
  Council minutes and by-laws, and two news reports.
- External identifiers: `scripts/build_person_external_ids.py` matches House and Assembly members
  to Wikidata items, using the query results the coordinating agent saved from Wikidata's public
  query service on 7 November 2026.

## Person links

Code makes the links that need no judgement. Each Candidacy's own record founds its Person (4,941
links), and incumbency reported by the election authority (221) and exact names on a Council roster
(131) join runs. Code also proposes a link wherever a name matches an existing Person exactly, but
a name match alone never confirms one.

Every other link was decided in a review pass, by a curated identity assertion in
`src/toronto_election_results/identity_curations.py` or a disposition in
`data/reference/identity_review_dispositions.csv`. A disposition's `reviewer` value names its pass,
and the pass's report sets out its method. The passes took three forms.

- Discovery and verification (August 2026). The 2026 career reviews gave each mayoral and trustee
  candidate a discovery dossier by Luna and a separate verification by Terra, written without
  Luna's dossier. For trustees, Sol (`gpt-5.6-sol`) took 60 held decisions. A primary review
  settled disagreements (`docs/research/mayoral-career/2026/`, `docs/research/trustee-career/2026/`).
  Reports of 20 and 21 August 2026, such as
  `docs/research/consequential-12-council-identity-review-2026-08-20.md`, cover some of the other
  assertions and dispositions of this period. The 467 dispositions under
  `independent-adjudication-bucket-0` to `-2` have no report; their rationales follow templates
  built on the same-office structural rule. The agents of this period ran in OpenAI Codex. Most of
  the work was done with GPT-5.6 Sol, and Luna and Terra are GPT-5.6 Luna and GPT-5.6 Terra, used
  for some broad research that Sol then verified. Alex Olson carried out the primary review.
- Dual blind review (28 and 29 October 2026). For the 1993 to 2001 results, two agents took each
  batch of proposals without seeing each other's verdicts, against the evidence standard in the
  build notes. A link stood where both confirmed it. A primary reviewer settled the splits after
  reading the cited sources and could hold a confirmation both had made. The primary reviewer was
  the coordinating agent; no author settled a case.
- Research with a second check (30 October to 7 November 2026). Research agents searched public
  sources batch by batch and proposed dispositions with sources and quotations. In the federal and
  provincial holds (1 November), the municipal holds and the same-name and near-name reviews (3 to
  5 November), every proposed confirmation or join went to a second agent that had not done the
  research, and only the ones it accepted were applied. One join came later: on 7 November the
  coordinating agent joined Fatima Shaban's 2026 provincial by-election run to her federal runs
  from a source about her, and the census below audited it. The same day a script screened the
  Persons for changed surnames and found four pairs, none joined
  (`docs/verification/surname-change-screen-2026-11-07.md`). No author has yet reviewed any of
  these decisions.

The table counts the active links by what decided them, and the 413 Candidacies held without a
Person by the pass that held them. An assertion is dated by the commit that first added it; some
were extended later.

| Decided by | Period | Tool | Confirmed links | Held (unresolved or rejected) |
|---|---|---|---:|---:|
| Code: a Candidacy's own record | | | 4,941 | |
| Code: reported incumbency and roster names | | | 352 | |
| Curated assertions | August 2026 | OpenAI Codex (GPT-5.6); primary review by Alex Olson | 976 | |
| Dispositions | August and September 2026 | OpenAI Codex (GPT-5.6); primary review by Alex Olson | 129 | 294 |
| Curated assertions | 28 October to 7 November 2026 | Claude Opus 5.5 | 337 | |
| Dispositions | 28 October to 7 November 2026 | Claude Opus 5.5 | 951 | 119 |

Of the 2,745 links that join a Candidacy to a Person, 352 were made by code, 1,105 in August and
September 2026 and 1,288 between 28 October and 7 November 2026. Each link's `evidence_basis`
says whether it rests on an official record, a source about the person or the structural rules
alone.

## Audit

The audit of Person links (`docs/verification/link-audit-2026-11-03.md`) was carried out on 3
November 2026 by four agents, none of which had made or reviewed a link, working only from sources
they found themselves. A fifth agent checked each verdict that two Persons were one individual. All
five were Claude Opus 5.5. The census of the 136 joins made after that sample
(`docs/verification/link-audit-2026-11-07.md`) was carried out on 7 November 2026 by five more
agents under the same rules, and three others checked every verdict that a join was confirmed.
All eight were Claude Opus 5.5. The results files give each verdict's sources, quotations and notes.
`docs/verification/human-coding-2026-11-07.md` sets out a sample of joins for people to code
against the agents' verdicts, drawn by script on 7 November 2026. [The coding is not yet done.
Report it, and who did it, when it is.]

## Endorsements

The endorsement curations were researched in August 2026, in discovery reports and separate
verification reports (`docs/research/endorsement-*.md`); the coverage reports name their researchers
as Luna and Terra. Matt Elliott's tracker of 2022 endorsements, which he maintained during that
campaign, was used to find and check the Toronto Star editorial board's 2022 council choices; those
facts cite the Star's editorials (`docs/research/matt-elliott-2022-endorsement-matrix-audit.md`).
Progress Toronto's 2026 endorsements were added on 26 September 2026 with Claude Opus 5.5. The
data dictionary records the rule that chose the nine Endorsers and the project owner's approval
of the panel on 21 August 2026. The August work was done in OpenAI Codex, with GPT-5.6 Luna and
Terra as the researchers and GPT-5.6 Sol verifying their work.

## Reviewer values

`candidacy_person_links.reviewer` says which step decided each link:

- `identity_review.bootstrap/v1` and `municipal_rosters/v1`: code.
- `identity_curations/v1`: a curated identity assertion; the assertion's ID is in `evidence`.
- Any other value: a review pass, named for its report where it has one.

Alex Olson made the case-level decisions of the primary review in August and September. Every
other link was decided by code or by an agent, in the pass its `reviewer` value names.
