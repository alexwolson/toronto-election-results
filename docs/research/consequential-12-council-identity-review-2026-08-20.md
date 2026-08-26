# Consequential council identity review — 12 cases (2026-08-20)

## Scope and decision rule

This is an independent second-pass audit of the 12 council candidacies in the
upstream handoff. The audit checked the canonical release
(`data/out/election_results.csv`) and the active review ledger
(`data/reference/identity_review_dispositions.csv`) before reviewing the
proposed identity links.

The review began from release hash
`1fb95d9e0e5c8ef9c19721a1c6e639cf032c7789348097244111ddf214e350f4`,
matching the handoff. At that baseline all 12 candidacies had
`person_id = NULL` and an `unresolved` disposition. The official result rows establish that the
named candidacies occurred, and establish the recorded outcome; they do not by
themselves establish that a same-name occurrence is the retained Person.

I used the following threshold:

* **CONFIRM** requires an explicit candidate-authored, campaign-controlled,
  party/board, or other first-party bridge identifying the council candidate
  and the retained Person's prior office, supplemented by official result or
  institutional records where useful. An explicit bridge in reputable
  institutional journalism also qualifies when separate official records
  corroborate both occurrences; this exception is recorded rather than treated
  as first-party evidence.
* **HOLD** means the occurrence is real and the proposed target is plausible,
  but no admissible bridge was located. The release should remain null-linked.
* **SPLIT** requires positive contrary evidence (for example, a same-event
  collision or evidence of two distinct people). No split evidence was found
  in this batch.

Exact-name matching and an official result row alone are not identity evidence.

## Adjudication

| Decision | Candidacy | Council occurrence | Proposed retained Person | Bridge / rationale |
|---|---|---|---|---|
| **CONFIRM** | `can_8702c409b44c56869788d0fcb7ee8999` | 2018-10-22, Toronto council Ward 19 | `per_b05bca5a3f225453b8484ce46c8b2bb8` — Matthew Kellway | The Ward 19 candidate questionnaire identifies Kellway's council campaign and his service as MP for Beaches–East York; the House of Commons historical record corroborates that MP identity. [DECA Ward 19 questionnaire](https://deca.to/ward-19-candidate-qa-matthew-kellway/) · [House of Commons member record](https://www.ourcommons.ca/Members/en/matthew-kellway%2871585%29) · [City 2018 declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) |
| **CONFIRM** | `can_246c0347d317593aa183f92681afb95e` | 2018-10-22, Toronto council Ward 8 | `per_c264c8a222ea5baea6a15b1bfeac3ae0` — Jennifer Arp | The archived first-party campaign site identifies Arp as the 2018 council candidate and states that she was elected a public-school trustee in 2014. [Archived campaign home](https://web.archive.org/web/20181214222254/https://www.jenniferarp.ca/) · [Archived campaign biography](https://web.archive.org/web/20181026215109/https://www.jenniferarp.ca/about) · [City 2018 declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) |
| **CONFIRM** | `can_b07911ac186c5fedbb0acd5ccd8a2bd8` | 2018-10-22, Toronto council Ward 17 | `per_fd89e2daa64b5513ba56eb9e1c8b51f7` — Ken Lister | Lister's archived first-party council campaign states that he served four years as a TDSB trustee; the TDSB institutional biography identifies the same trustee. His current first-party biography independently preserves the trustee identity. [Archived campaign site](https://web.archive.org/web/20181026215226/https://www.kenlister.ca/) · [TDSB biography](https://www.tdsb.on.ca/ward17/Ward17/KenListerBio.aspx) · [Ken Lister biography](https://www.kenlister.ca/aboutken) · [City 2018 declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) |
| **CONFIRM** | `can_690689c4111c50918c06f6b446c95d0d` | 2018-10-22, Toronto council Ward 3 | `per_b94977f840da534caf789477d036ee8c` — Pamela Gough | The archived first-party council campaign biography describes Gough's elected TDSB trustee tenure in Etobicoke–Lakeshore. [Archived campaign home](https://web.archive.org/web/20181106153055/https://www.votegough.ca/) · [Archived campaign biography](https://web.archive.org/web/20181106152912/https://www.votegough.ca/about-pamela/) · [TDSB 2014–2018 trustee record](https://schoolweb.tdsb.on.ca/Portals/0/AdultLearners/docs/WEBsummerL4Lfinal.pdf) · [City 2018 declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) |
| **CONFIRM** | `can_34fbfb27258159f1b05bf2d0cb8302ff` | 2018-10-22, Toronto council Ward 7 | `per_d56a01f9891c5106ba8bf6281c6f713c` — Tiffany Ford | The archived first-party Ward 7 council campaign identifies Ford and states that she had served the preceding three years as the local public-school trustee. [Archived Tiffany Ford campaign](https://web.archive.org/web/20181214230713/https://tiffanyford2018.ca/) · [TDSB 2014–2018 trustee record](https://schoolweb.tdsb.on.ca/Portals/0/AdultLearners/docs/WEBsummerL4Lfinal.pdf) · [City 2018 declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) |
| **CONFIRM** | `can_f9f7d971b99c52cf9a48edf7b1dd38ba` | 2021-01-15, Toronto council Ward 22 by-election | `per_cbad12eb2bc15f4fb7ba5a96bd68dec9` — Manna Wong | Wong's candidate questionnaire names the campaign as “Manna Wong for City Council Ward 22” and says she had been the elected Scarborough–Agincourt school trustee since 2014. The City's compliance record identifies Manna Wong as the Ward 22 council candidate. [Candidate questionnaire (PDF)](https://static1.squarespace.com/static/5aae198d96e76f27dc9377ce/t/5fd90dea89ea717cb5d4a69a/1608060394760/Manna%2BWong%2B-%2BScarbrough-Agincourt%2BBy-election%2BProgressive%2BChampion%2BSurvey%2B.pdf) · [City compliance record](https://secure.toronto.ca/council/agenda-item.do?item=2021.EA8.5) · [Official 2014 trustee result archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip) |
| **CONFIRM** | `can_cc7dfd8b06db51e592901dc4b159ca78` | 2022-10-24, Toronto council Ward 11 | `per_9f569a842c9e527b88cda3fc73dbfacb` — Norm Di Pasquale | A contemporaneous first-party campaign newsletter calls Di Pasquale both the outgoing Catholic trustee and the University–Rosedale council candidate. An official City communication identifies him as the Ward 9 TCDSB trustee. [Kristyn Wong-Tam campaign newsletter](https://www.kristynwongtam.ca/newsletter_october_7_2022) · [Official City communication](https://www.toronto.ca/legdocs/mmis/2022/cc/comm/communicationfile-152340.pdf) · [City 2022 declaration](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf) |
| **CONFIRM** | `can_94c9f534cc225dbbb74ad1b9aa11a1d7` | 2023-11-30, Toronto council Ward 20 by-election | `per_74212bbadc535bca8fa201bda63cee06` — Malika Ghous | The candidate's first-person questionnaire response identifies Ghous as the sitting TDSB trustee for Scarborough Southwest and states that she was running in the council by-election. The City's financial-filing record identifies Malika Ghous as a Ward 20 councillor candidate. [Candidate questionnaire responses](https://beachmetro.com/2023/11/15/scarborough-southwest-byelection-2023-candidate-malika-ghous-answers-our-questions/) · [City campaign-filing record](https://secure.toronto.ca/EFD/jsf/candidate2018/candidate_campaign_status.xhtml?campaign=20) · [Official 2022 trustee result archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip) |
| **CONFIRM** | `can_77360db1d61055b1862abdad17f5e03c` | 2025-09-29, Toronto council Ward 25 by-election | `per_3c246b205ffd55298633b81a804f8b82` — Anu Sriskandarajah | Sriskandarajah's first-party campaign identifies her as the Ward 25 council candidate and says she had served as the Scarborough–Rouge Park school-board trustee for seven years. The City's certified candidate list links the campaign identity to the Ward 25 candidacy. [Anu Sriskandarajah campaign](https://www.dranu.ca/) · [City certified candidate list](https://www.toronto.ca/city-government/elections/ward-25-scarborough-rouge-park-by-election-list-of-candidates-third-party-advertisers/) · [Official 2022 trustee result archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip) |
| **CONFIRM** | `can_3b00773d04365f64a37bf88fce264eaf` | 2018-10-22, Toronto council Ward 16 | `per_656bf9ee8956529195719d111d5fe53d` — David Caplan | CityNews explicitly identifies the former MPP as the person who ran in Ward 16 in 2018. The Legislative Assembly record and City declaration independently corroborate the two occurrences. This is an explicit institutional-journalism bridge, not a first-party bridge. [CityNews identity bridge](https://toronto.citynews.ca/2019/07/25/former-mpp-david-caplan-dead-at-54/) · [Ontario Legislative Assembly biography](https://www.ola.org/en/members/all/david-caplan) · [City 2018 declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) |
| **CONFIRM** | `can_d0b1cdfb35165fb0acbf31c7cd5ae8c2` | 2022-10-24, Toronto council Ward 1 | `per_194efd592b915c2ca63859d3ebbef5e0` — Avtar Minhas | The archived candidate-authored 2022 campaign says that Minhas had been elected TDSB Ward 1 trustee and was now running for councillor in Ward 1. Official City and TDSB records corroborate both occurrences. [Archived 2022 campaign](https://web.archive.org/web/20220823012849id_/http://voteminhas.ca/) · [Archived campaign text bundle](https://web.archive.org/web/20220823012913id_/http://voteminhas.ca/static/js/main.42ee0824.js) · [TDSB 2016 annual report](https://www.tdsb.on.ca/Portals/0/AboutUs/Director/AnnualReport2016FINAL.pdf) · [City 2022 declaration](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf) |
| **CONFIRM** | `can_910c3031a66e5d91978ea8cb4b25fd15` | 2022-10-24, Toronto council Ward 7 | `per_2d23abe818995711b696fd8b8f2af4ed` — Christopher Mammoliti | A contemporaneous Ward 7 candidate interview identifies Mammoliti as the 2022 council candidate, states that he had served four years as TDSB trustee, and records his first-person campaign answers. Official City and TDSB records corroborate the occurrences. [Emery Village Voice candidate interview](https://emeryvillagevoice.ca/Meet-Your-Ward-7-Humber-River---Black-Creek-2022-election-candidates) · [TDSB biography/news release](https://www.tdsb.on.ca/News/Article-Details/ArtMID/474/ArticleID/1557/Alexander-Brown-Acclaimed-Chair-of-the-Toronto-District-School-Board) · [City 2022 declaration](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf) |

## Outcome and release impact

The initial pass produced nine confirmations and three holds. A targeted
follow-up located new explicit bridges for all three holds, so the final
disposition is **12 `CONFIRM`, 0 `HOLD`, and 0 `SPLIT`**. Minhas and Mammoliti
have candidate-authored or direct candidate-interview bridges. Caplan has an
explicit reputable-journalism bridge with independent official corroboration.

No vote totals, vote shares, ranks, elected flags, or outcome fields should be
changed. Only the 12 `person_id` values and their review dispositions change.
