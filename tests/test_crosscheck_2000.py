"""Wikipedia cross-check parser for the 2000 results."""

import pandas as pd

from toronto_election_results.crosscheck_2000 import crosscheck_2000, parse_wikipedia_wards

# Two header forms: plain, and with the ward number wrapped inside a wikilink.
WIKITEXT = """
'''Ward 34 - [[Don Valley East (federal electoral district)|Don Valley East]]:'''
*(incumbent) [[Denzil Minnan-Wong]] 8,730
*Kim Scott 5,078

'''[[Ward 20 Scarborough Southwest|Ward 36 - Scarborough Southwest]]:'''
*(incumbent) [[Brian Ashton (politician)|Brian Ashton]] 9,374
*Robert Scott 3,682

'''Ward 27 - [[Toronto Centre]]:'''
*(incumbent) [[Kyle Rae]] acclaimed
"""


def test_linked_ward_header_is_parsed_to_correct_ward():
    """Ward 36's number is inside a link; its candidates must not bleed into ward 34."""
    wards = parse_wikipedia_wards(WIKITEXT)
    assert 34 in wards and 36 in wards
    assert any("minnan-wong" in k for k in wards[34])
    assert any("ashton" in k for k in wards[36])
    # ward 34 must NOT contain ward 36's Ashton
    assert not any("ashton" in k for k in wards[34])


def test_acclamation_parsed_as_none():
    wards = parse_wikipedia_wards(WIKITEXT)
    (votes,) = set(wards[27].values())
    assert votes is None


def test_crosscheck_reports_matches_and_gaps():
    city = pd.DataFrame(
        [
            {
                "office": "councillor",
                "ward_number": 34,
                "candidate_name_raw": "DENZIL MINNAN-WONG",
                "votes": 8730,
            },
            {
                "office": "councillor",
                "ward_number": 34,
                "candidate_name_raw": "KIM SCOTT",
                "votes": 5078,
            },
        ]
    )
    report = crosscheck_2000(city, WIKITEXT)
    assert report["mismatches"] == []
    assert 34 in report["wards_checked"]
