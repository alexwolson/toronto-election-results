# Model endorsements as open-world, evidence-backed facts

Status: accepted

The endorsement dataset records a positive edge from one exact Endorser to one Candidacy in one
Contest; it never manufactures negative edges for the other candidates. Source-level Endorsement
assertions are kept separately from adjudicated facts, and a separate Endorser-by-Contest coverage
record distinguishes an unsearched or unavailable source from a completed search that found no
endorsement. Parent organizations, locals, affiliates, editorial boards, owners, coalitions, and
members are separate Endorsers, while a joint statement may create separate facts for each exact
organization that explicitly assented.

Systematic historical coverage is limited to the frozen approved panel: Progress Toronto, the
Toronto Star Editorial Board, the Toronto Sun Editorial Board, CUPE Ontario, Elementary Teachers of
Toronto, ATU Local 113, David Miller, John Tory, and Olivia Chow. Verified facts outside that panel
may be retained without a completeness claim. The institutional gate requires a qualifying 2023
mayoral endorsement plus the approved structural evidence; the individual cohort consists of
people living on August 20, 2026 who had served as Mayor of amalgamated Toronto, with eligibility
beginning when each first assumed that office.

Every approved panel Endorser is in scope for both Toronto Mayor and City Councillor Contests.
That shared applicability defines which Endorser-by-Contest coverage cells exist; it does not
permit inference of an Endorsement, a neutral stance, or a completed search. Each positive fact
still requires its own exact-entity, timely evidence.

Because 2026 endorsements target the current municipal field, certified 2026 Candidacies enter the
dataset before voting with `result_status=pending` and null result values. Their persistent
Candidacy IDs are retained when the City Clerk later certifies the outcomes, rather than creating a
separate campaign identity or a replacement result row.
