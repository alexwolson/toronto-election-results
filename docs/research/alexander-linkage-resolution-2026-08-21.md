# Chris Alexander linkage resolution — 2026-08-21

## Scope and result

The requested “Alexander” is **Chris Alexander**, the former Conservative MP
and cabinet minister now running for Toronto mayor in the 2026 municipal
election. This is not Alexander Brown, Michael Alexander, or another historical
Toronto candidate whose name contains “Alexander”.

There is currently **no in-scope candidacy row** for Chris Alexander:

* `data/out/election_results.csv` has no `candidate_name` or
  `candidate_name_raw` containing “Chris Alexander”, “Christopher Alexander”,
  or “Alexander Chris”.
* `data/reference/candidacy_identity_ledger.csv` likewise has no such
  occurrence.
* Consequently there is no current `candidacy_id`, raw ballot name, `person_id`,
  or `candidacy_person_links.csv` status to update for this candidate.

This is expected under the current release boundary: the project includes
completed events through 2026-04-13, while Toronto's 2026 municipal general
election is scheduled for October 26, 2026, after the 2026-08-20 cutoff. The
City's [candidate-information page](https://www.toronto.ca/city-government/elections/candidates-third-party-advertisers/candidate-information/become-a-candidate/)
sets the 2026 nomination period and election date. The City's [candidate-list
page](https://www.toronto.ca/city-government/elections/candidate-list/) is the
authoritative place to capture the eventual certified ballot/display name, but
its candidate table is client-rendered and is not included in the current
dataset.

The candidacy itself is not merely a name-search hypothesis: contemporaneous
reporting says Alexander announced the campaign and registered at City Hall on
July 29, 2026. The project still has no event/candidacy row because the 2026
municipal contest has not been ingested. The City's election notice says the
final certified candidate list is available after nominations close, so the
project should not manufacture a raw ballot spelling from the campaign site or
from news copy.

## Identity bridge

The campaign's first-party site identifies the mayoral campaign as “Chris for
Mayor” and names the candidate Chris Alexander. Its biography says he was the
MP for Ajax—Pickering from 2011 to 2015 and Minister of Citizenship and
Immigration from 2013 to 2015. [Chris Alexander campaign site](https://chrisalexander.ca/)

The House of Commons' official member record independently identifies the same
Chris Alexander as the Conservative MP for Ajax—Pickering, elected May 2, 2011
and defeated in the 2015 Ajax election, and records his ministerial role.
[House of Commons member record](https://www.ourcommons.ca/members/en/chris-alexander%2871576%29)
· [House of Commons roles and election history](https://www.ourcommons.ca/members/en/chris-alexander%2871576%29/roles)

Reputable contemporaneous reporting confirms that this same former MP entered
the 2026 Toronto mayoral race. The Canadian Press report carried by Global
News identifies Chris Alexander, describes the campaign spokesman's
registration announcement, and connects the candidate to the Ajax—Pickering
MP record. [Global News / Canadian Press report](https://globalnews.ca/news/11998168/chris-alexander-toronto-mayoral-candidacy/)

Taken together, the first-party campaign and official parliamentary record are
strong identity evidence for a future 2026 Toronto mayoral candidacy. No
historical Toronto-contained election occurrence is present to link in the
current release; Ajax—Pickering/Ajax federal contests are outside this dataset's
Toronto-contained federal geography.

## Exact in-scope row status

| Item | Current value |
|---|---|
| Intended contest | 2026 Toronto City Council, mayor (future event; not in release) |
| Expected candidate display name | `Chris Alexander` (campaign-controlled wording; not yet a certified ballot spelling in this release) |
| Expected raw ballot name | Unknown until the City Clerk publishes the certified candidate/ballot record |
| Current `candidacy_id` | None |
| Current `person_id` | None; no Chris Alexander Person exists in `data/out/people.csv` |
| Current link/disposition | None; no row in `data/out/candidacy_person_links.csv` or `data/reference/identity_review_dispositions.csv` |
| Historical out-of-scope identity anchor | Official House of Commons Chris Alexander, MP Ajax—Pickering (2011–2015) |

### Observed name forms

| Form | Status and use |
|---|---|
| `Chris Alexander` | Campaign site, House of Commons member record, and reporting; best current display-name candidate |
| `Hon. Chris Alexander` | Official parliamentary honorific; identity evidence only, not a ballot alias |
| `Christopher Alexander` / `ALEXANDER CHRIS` | Not observed in the current project or the cited first-party campaign/parliamentary records; do not infer as raw ballot text |
| `ALEXANDER MICHAEL` | Existing 2006/2010 raw result name for a different person; collision guard, not an alias |

The existing mayoral rows with “Alexander” are unrelated and must not be
reused: `can_4d23def20f175393892913ecf6e676bc` and
`can_69bf16173cdc53cd83ab74190b0ad830` are Michael Alexander in 2006 and 2010,
respectively, linked to `per_75acdc8e18f1542e9b84c1738d3909a9`.

## Recommendation for the linkage pass

Do not create or repurpose a current historical candidacy link. When the 2026
mayoral candidate record is added, preserve the City's certified raw/display
name, create a new Person for Chris Alexander if the registry has no suitable
anchor, and attach the first-party campaign and House of Commons evidence to
that new candidacy. The campaign name should be recorded as `Chris Alexander`
unless the certified City Clerk record supplies a different ballot form.

Do not merge the future mayoral occurrence into Michael Alexander or Alexander
Brown merely because the surname appears in a name search.

## Sources

* [City of Toronto — candidate nominations and final certified list notice](https://www.toronto.ca/news/candidate-nominations-and-third-party-advertiser-registrations-open-tomorrow-for-2026-municipal-election/)
* [TorontoToday — registration at Toronto City Hall (July 29, 2026)](https://www.torontotoday.ca/local/politics-government/chris-alexander-run-mayor-toronto-former-harper-cabinet-minister-12605221)
