from datetime import date

import pandas as pd

from toronto_election_results.predecessor_incumbency import derive_predecessor_incumbency


def _candidacy(body, office, election_date, person_id):
    return {
        "candidacy_id": f"can_{body}_{office}_{person_id}",
        "represented_body": body,
        "office_type": office,
        "election_date": election_date,
        "person_id": person_id,
    }


def _tenure(tenure_id, person_id, body, office, started, ended):
    return {
        "office_tenure_id": tenure_id,
        "person_id": person_id,
        "represented_body": body,
        "office_type": office,
        "started_on": started,
        "ended_on": ended,
    }


TENURES = pd.DataFrame(
    [
        _tenure("ten_ny", "per_a", "north_york_city_council", "councillor", "1994-12-01", None),
        _tenure("ten_metro", "per_b", "metro_toronto_council", "councillor", "1994-12-01", None),
        _tenure(
            "ten_left", "per_c", "metro_toronto_council", "councillor", "1994-12-01", "1996-06-30"
        ),
        _tenure("ten_mayor", "per_d", "scarborough_city_council", "mayor", "1994-12-01", None),
    ]
)
FIRST = date(1997, 11, 10)


def test_sitting_predecessor_members_are_predecessor_incumbents():
    candidacies = pd.DataFrame(
        [
            _candidacy("toronto_city_council", "councillor", FIRST, "per_a"),
            _candidacy("toronto_city_council", "councillor", FIRST, "per_b"),
            _candidacy("toronto_city_council", "mayor", FIRST, "per_d"),
        ]
    )

    out = derive_predecessor_incumbency(candidacies, TENURES)

    assert out["predecessor_incumbent"].tolist() == [True, True, True]
    assert out["predecessor_office_tenure_id"].tolist() == ["ten_ny", "ten_metro", "ten_mayor"]


def test_absence_is_false_only_when_every_predecessor_roster_is_complete():
    candidacies = pd.DataFrame([_candidacy("toronto_city_council", "councillor", FIRST, "per_c")])
    complete = frozenset(
        [("metro_toronto_council", "councillor")]
        + [
            (body, "councillor")
            for body in (
                "former_toronto_city_council",
                "north_york_city_council",
                "scarborough_city_council",
                "etobicoke_city_council",
                "york_city_council",
                "east_york_borough_council",
            )
        ]
    )

    unknown = derive_predecessor_incumbency(candidacies, TENURES)
    known = derive_predecessor_incumbency(candidacies, TENURES, complete_rosters=complete)

    assert unknown["predecessor_incumbent"].isna().all()
    assert known["predecessor_incumbent"].tolist() == [False]


def test_other_offices_elections_and_unlinked_people_stay_null():
    candidacies = pd.DataFrame(
        [
            _candidacy("toronto_city_council", "mayor", FIRST, "per_a"),
            _candidacy("toronto_city_council", "councillor", date(2000, 11, 13), "per_a"),
            _candidacy("toronto_city_council", "councillor", FIRST, pd.NA),
        ]
    )

    out = derive_predecessor_incumbency(candidacies, TENURES)

    assert out["predecessor_incumbent"].isna().all()
    assert out["predecessor_office_tenure_id"].isna().all()
