# Toronto Election Results

A unified, analysis-ready dataset of election results from January 1, 2003 onward for contests
within the City of Toronto, plus evidence-backed endorsements in Toronto Mayor and City Councillor
contests. It is intended to feed an election model maintained elsewhere.

## Language

**Coverage window**:
Every completed in-scope election whose scheduled polling date is from January 1, 2003 through
August 20, 2026, inclusive, plus the October 26, 2026 Toronto municipal general Election event,
which enters as pending Candidacies and later receives its certified results. Other later elections
are out of scope unless the Coverage window is explicitly revised; a cancelled call that produces
no result is excluded.

**Endorsement collection window**:
Public Endorsements for in-scope Toronto Mayor and City Councillor Contests are collected through
the close of polls for the October 26, 2026 municipal election. Panel eligibility is frozen using
information available through August 20, 2026, but later qualifying Endorsements by those approved
Endorsers remain in scope.

**City of Toronto scope**:
Complete official contests whose electoral geography is contained within the municipal boundary of
the City of Toronto. A contest crossing the City boundary is not clipped into an artificial
Toronto-only result. The Greater Toronto Area is out of scope.
_Avoid_: Toronto-area, GTA.

**Toronto municipal election**:
An election administered by the City of Toronto for Mayor, City Councillor, or School Board
Trustee. General elections, by-elections, and acclamations are in scope; appointments are not
election results and are out of scope.

**General election**:
An election in which the ordinary slate of seats for a jurisdiction is contested, rather than a
vacancy being filled between general elections. Toronto's municipal general election is held every
four years; federal and provincial elections follow their own calendars.
_Avoid_: regular election.

**By-election**:
An off-cycle election to fill a vacant elected office between general elections. By-elections for
every in-scope office are included when they fall inside the Coverage window.
_Avoid_: special election, supplementary election.

**Election event**:
One officially called election administered by one Election authority. An Election event contains
one or more Contests and follows the authority's official event or writ identity; calendar year and
polling date alone are not identity. Separately called by-elections remain separate Election events
even when they share a polling date.

**Election authority**:
The organization that administers and certifies an Election event, such as the Toronto City Clerk,
Elections Ontario, or Elections Canada. It is distinct from the Represented body.

**Represented body**:
The institution whose membership an election fills: Toronto City Council, one of the four School
Boards, the House of Commons of Canada, or the Legislative Assembly of Ontario.

**Office type**:
The elected position being contested. In scope: **Mayor**, **City Councillor**, **School Board
Trustee**, **Member of Parliament**, and **Member of Provincial Parliament**.
_Avoid_: body, seat, position, race (see Contest).

**City Councillor**:
A member of Toronto City Council elected to represent a single ward.
_Avoid_: alderman, ward councillor.

**School Board Trustee**:
A member elected to represent a trustee ward on one of Toronto's four publicly funded school
boards.
_Avoid_: school trustee, board trustee.

**School Board**:
One of the four publicly funded boards whose trustees are elected in Toronto: Toronto District
School Board, Toronto Catholic District School Board, Conseil scolaire Viamonde, or Conseil
scolaire catholique MonAvenir.
_Avoid_: school district.

**Member of Parliament (MP)**:
A member elected to the House of Commons of Canada for a federal electoral district within the
City of Toronto scope.

**Member of Provincial Parliament (MPP)**:
A member elected to the Legislative Assembly of Ontario for a provincial electoral district within
the City of Toronto scope.

**Ward**:
A geographic electoral division that elects one City Councillor. Recorded **as each election
used it** — no cross-year reprojection — and tagged with its Ward system. Toronto used 44 wards
for 2003–2014 and 25 wards from 2018 onward; numbering and boundaries are **not** comparable
across that change.
_Avoid_: district, riding (riding is provincial/federal).

**Trustee ward**:
A geographic electoral division that elects a School Board Trustee for one School Board. It is not
the same namespace as a City Council ward, even when numbers or boundaries overlap.

**Electoral district**:
A legal geographic electoral division that elects one MP or MPP. Its identity does not depend on
whether a boundary polygon is available.
_Avoid_: ward; riding.

**Boundary regime**:
The set of electoral geographies used by one Represented body and geography family during a period.
Results retain the geography under which votes were cast; Boundary regimes from different bodies
or periods are not assumed comparable, even when district names match.

**Ward system**:
The ward regime an election ran under, distinguishing the two non-comparable eras: `44-ward`
(2003–2014, stable boundaries) and `25-ward` (2018 onward). It is a municipal-council-specific kind
of Boundary regime.

**Subdivision**:
The poll-level unit within an electoral geography. Subdivision data may appear in an authority's
source files, but votes are aggregated to the Contest and subdivision-level results are not part of
the dataset.
_Avoid_: poll, precinct.

**Contest**:
A single race for one Office type and Represented body, in one electoral geography, at one Election
event. The electoral geography may be the whole city, a Ward, a Trustee ward, or an Electoral
district. Every in-scope Contest is single-seat plurality: it elects at most one Person.
_Avoid_: race, seat.

**Candidacy**:
One person's official candidacy in one Contest, once included in the Election authority's certified
candidate list or ballot. A Person may have many Candidacies; each Candidacy refers to at most one
confirmed Person, and its source name is preserved independently from the Person's canonical name.
_Avoid_: treating candidate as a persistent person identity.

**Result status**:
Whether a Candidacy's election outcome is `pending` or `final`. A pending Candidacy has no certified
votes or outcome; the same persistent Candidacy becomes final when the Election authority certifies
the result.

**Person**:
An individual represented by a Candidacy, Office tenure, or an evidence-backed electoral source
needed by a dependent dataset. Existence as a Person does not imply inclusion in a certified field.

**Person alias**:
An evidence-backed source name that identifies exactly one Person. An alias supports exact
cross-dataset resolution but never creates or rewrites a Candidacy.
_Avoid_: Candidate alias, fuzzy name match.

**Person ID**:
An opaque, persistent identifier for one Person across every in-scope election and Office type. It
does not change when the Person contests a different geography, moves between Office types, or
changes how their name appears in a source. A link may be confirmed by authoritative evidence or
audited evidence-backed curation, but not by name similarity alone. Ambiguous Candidacies remain
unlinked until resolved.
_Avoid_: Candidate ID, name-derived identifier.

**Identity link**:
A versioned claim relating one Candidacy to one Person. `proposed` is an unreviewed suggestion,
`confirmed` publishes the Person ID, `unresolved` records a reviewed but insufficient claim, and
`rejected` records evidence that the proposed Person is not the candidate.
_Avoid_: treating a proposal or reviewed hold as a confirmed identity.

**Endorser**:
One exact individual or organization that may publicly support Candidacies. Parent bodies, locals,
affiliates, coalitions, editorial boards, owners, and individual members are distinct Endorsers and
never inherit one another's Endorsements.

**Panel endorser**:
An Endorser approved for systematic historical coverage under a frozen inclusion rule. Every Panel
endorser is applicable to both Toronto Mayor and City Councillor Contests. Applicability defines
the coverage universe; it neither asserts an Endorsement nor implies that a Contest-specific search
was completed. Endorsements from outside the panel may still be recorded, but they do not imply
comprehensive search coverage.

**Endorsement**:
An adjudicated fact that one Endorser publicly selected or urged the election of one Candidacy in
one Contest. An Endorser may endorse multiple Candidacies in the same Contest, and an Endorsement
creates no negative fact about any other Candidacy.
_Avoid_: support inferred from praise, policy agreement, affiliation, appearances, or silence.

**Endorsement assertion**:
A source-specific claim about an Endorsement, kept separately from the adjudicated fact. Its review
state is `proposed`, `confirmed`, `unresolved`, `rejected`, or `withdrawn`; candidate-controlled
claims remain proposed until independently corroborated, and a claim whose target cannot be mapped
to an in-scope Candidacy remains unresolved rather than creating a synthetic target.

**Endorsement coverage**:
The recorded search state for one Endorser and one Contest: `not_applicable`, `not_searched`,
`partially_searched`, `searched_no_endorsement_found`, `comprehensive_source_found`, or
`source_unavailable`. `not_applicable` reflects a scope or eligibility boundary, not an absent
Endorsement. Missing Endorsement evidence is never interpreted as a negative Endorsement.

**Party**:
A legal political organization reported by an election authority. Party identity is specific to
its jurisdiction: similarly named federal and provincial parties are distinct. A rename of the same
organization retains its identity; a merger or new legal successor does not. Party affiliation
describes a Candidacy, not the Person permanently.

**Party affiliation**:
The relationship between a Candidacy and a Party, when the election authority reports one. Its
status distinguishes `party`, `independent`, `non_partisan`, and `not_reported`; only `party`
identifies a Party.

**Vote share**:
A candidate's votes divided by the total valid votes cast in that contest. The primary modelling
target.
_Avoid_: percentage, vote fraction.

**Elected**:
The official outcome marking a Candidacy as elected, as certified by the Election authority. It is
not inferred solely from who has the most recorded votes because ties are resolved differently by
different authorities.
_Avoid_: winner, successful.

**Outcome method**:
The authoritative disposition of a Contest, such as vote, acclamation, lot, casting vote, required
by-election, or void result. A Contest remains part of the election record even when its Outcome
method produces no Candidacy vote rows or no elected Person.

**Coverage status**:
Whether the expected official data for a Contest has been obtained: `complete`, `partial`, or
`source_missing`. It is independent of Outcome method; a legal void is not a missing source. A
partially covered Contest contains only the facts that an official source establishes. A
source-missing Contest remains visible without Candidacy results, and its release must disclose the
gap rather than claim complete coverage.

**Event coverage**:
Whether the official record is sufficient to enumerate all Election events in a period. It may be
`complete` or `uncertain`; uncertainty does not justify inventing Events or Contest placeholders.

**Eligible electors**:
A count of people eligible to vote within a Contest's geography under the reported Electorate scope,
as defined by the responsible election authority. A labelled composite municipal-ballot count may
be used for Mayor and City Councillor; it is not substituted for a board-qualified trustee count.
Null when no applicable count is available.
_Avoid_: registered voters, electorate size.

**Electorate scope**:
The electoral geography and voter qualification to which Eligible electors, Ballots cast, and
Turnout apply. It distinguishes, for example, a composite municipal ballot from a board-qualified
trustee electorate.

**Ballots cast**:
A count of electors who cast a ballot at the same geography and Electorate scope as Eligible
electors. A labelled composite municipal-ballot count may be used for Mayor and City Councillor;
trustee Ballots cast are null unless an exact board-qualified measure exists.
_Avoid_: votes (that is per-candidate), total ballots.

**Turnout**:
`ballots_cast / eligible_electors` when both values describe the same geography and Electorate
scope. Distinct from `vote_share`'s denominator, which counts only valid votes cast for candidates
for one Office type.

**Incumbent**:
A Person who belongs to the last valid sitting roster for the same Office type and Represented body
before the Election event. For a dissolved legislature, this is the roster immediately before
dissolution. Changing electoral districts or crossing a Boundary regime does not end incumbency;
changing Office type or Represented body does. Other officeholding is a downstream career-history
feature derived through Person ID. Incumbency is unknown when the relevant roster cannot be
established reliably. True requires a confirmed Person link and matching Office tenure; false
requires a confirmed Person link and a complete roster that establishes absence. Otherwise the
status is unknown.
_Avoid_: sitting member (that's the source concept; incumbent is the per-row flag), returning
candidate.

**Office tenure**:
A dated period during which a Person holds an Office type in a Represented body. It records the
electoral district and whether the Person entered through election, acclamation, or appointment,
and provides the evidence for Incumbency. A tenure may begin before the Coverage window when it is
needed to classify an in-scope Candidacy; this does not bring the earlier election result into scope.

**Council composition**:
The reference record of who held the Mayor and each Councillor seat immediately before a given
election, including how they got there (elected / by-election / appointed). The source that makes
true incumbency derivable.

**Acclamation**:
A Candidacy declared Elected without a poll because the number of certified candidates does not
exceed the number of available seats. Votes and Vote share are null; explicitly scoped composite
municipal turnout may still describe participation in the other offices on the ballot.
_Avoid_: uncontested win, unopposed.
