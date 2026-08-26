"""Conservative, district-independent federal prior-holder evidence."""

import pandas as pd

from toronto_election_results.federal_rosters import build_federal_roster_evidence
from toronto_election_results.identity import derive_incumbency


def _federal_row(
    candidacy_id: str,
    event_id: str,
    election_date: str,
    election_type: str,
    person_id: str,
    candidate_name: str,
    *,
    elected: bool,
    incumbent_reported: bool | None,
    district_id: str,
) -> dict[str, object]:
    return {
        "candidacy_id": candidacy_id,
        "event_id": event_id,
        "election_date": election_date,
        "election_type": election_type,
        "election_authority": "elections_canada",
        "represented_body": "canada_house_of_commons",
        "office_type": "mp",
        "person_id": person_id,
        "candidate_name": candidate_name,
        "district_id": district_id,
        "elected": elected,
        "incumbent_reported": incumbent_reported,
        "source_detail": f"https://www.elections.ca/result/{candidacy_id}",
    }


def test_prior_elected_continuity_proves_true_across_boundaries_and_bad_false_flags():
    rows = [
        _federal_row(
            "can_cycle_marker",
            "ec-ge-41",
            "2011-05-02",
            "general",
            "per_other",
            "Other Winner",
            elected=True,
            incumbent_reported=False,
            district_id="ed-old-other",
        ),
        _federal_row(
            "can_adam_prior",
            "ec-be-2014-06-30",
            "2014-06-30",
            "by_election",
            "per_adam",
            "Adam Vaughan",
            elected=True,
            incumbent_reported=False,
            district_id="ed-trinity-spadina",
        ),
        _federal_row(
            "can_craig_prior",
            "ec-be-2012-03-19",
            "2012-03-19",
            "by_election",
            "per_craig",
            "Craig Scott",
            elected=True,
            incumbent_reported=False,
            district_id="ed-toronto-danforth-old",
        ),
        _federal_row(
            "can_peggy_prior",
            "ec-ge-41",
            "2011-05-02",
            "general",
            "per_peggy",
            "Peggy Nash",
            elected=True,
            incumbent_reported=False,
            district_id="ed-parkdale-old",
        ),
        _federal_row(
            "can_kirsty_prior",
            "ec-ge-41",
            "2011-05-02",
            "general",
            "per_kirsty",
            "Kirsty Duncan",
            elected=True,
            incumbent_reported=False,
            district_id="ed-etobicoke-old",
        ),
    ]
    for slug, name in [
        ("adam", "Adam Vaughan"),
        ("craig", "Craig Scott"),
        ("peggy", "Peggy Nash"),
        ("kirsty", "Kirsty Duncan"),
    ]:
        rows.append(
            _federal_row(
                f"can_{slug}_current",
                "ec-ge-42",
                "2015-10-19",
                "general",
                f"per_{slug}",
                name,
                elected=slug in {"adam", "kirsty"},
                # EC's field is known not to be complete proof of this project's
                # cross-boundary, same-office definition.
                incumbent_reported=False,
                district_id=f"ed-{slug}-new-boundary",
            )
        )
    candidacies = pd.DataFrame(rows)

    evidence = build_federal_roster_evidence(candidacies)
    current = candidacies.query("event_id == 'ec-ge-42'")
    derived = derive_incumbency(current, evidence.rosters).set_index("candidate_name")

    for name in ["Adam Vaughan", "Craig Scott", "Peggy Nash", "Kirsty Duncan"]:
        assert derived.loc[name, "incumbent"] == True
    assert evidence.rosters["roster_complete"].eq(False).all()
    assert set(evidence.rosters.query("event_id == 'ec-ge-42'")["person_id"].dropna()) == {
        "per_adam",
        "per_craig",
        "per_peggy",
        "per_kirsty",
    }
    ge42_roster = evidence.rosters.query("event_id == 'ec-ge-42'")
    assert ge42_roster["reference_date"].eq("2015-08-01").all()
    assert ge42_roster["reference_date_rule"].eq("day_before_official_parliament_dissolution").all()
    ge42_tenures = evidence.office_tenures[
        evidence.office_tenures["office_tenure_id"].isin(ge42_roster["office_tenure_id"].dropna())
    ]
    assert ge42_tenures["entry_method"].eq("election").all()
    assert ge42_tenures["started_on_precision"].eq("election_date").all()


def test_false_flag_or_stale_pre_cycle_win_never_proves_false_or_true():
    candidacies = pd.DataFrame(
        [
            _federal_row(
                "can_stale_win",
                "ec-ge-40",
                "2008-10-14",
                "general",
                "per_stale",
                "Stale Winner",
                elected=True,
                incumbent_reported=False,
                district_id="ed-old",
            ),
            _federal_row(
                "can_cycle_marker",
                "ec-ge-41",
                "2011-05-02",
                "general",
                "per_other",
                "Other Winner",
                elected=True,
                incumbent_reported=False,
                district_id="ed-other",
            ),
            _federal_row(
                "can_stale_current",
                "ec-ge-42",
                "2015-10-19",
                "general",
                "per_stale",
                "Stale Winner",
                elected=False,
                incumbent_reported=False,
                district_id="ed-new",
            ),
            _federal_row(
                "can_new_current",
                "ec-ge-42",
                "2015-10-19",
                "general",
                "per_new",
                "New Candidate",
                elected=False,
                incumbent_reported=False,
                district_id="ed-new-2",
            ),
        ]
    )

    evidence = build_federal_roster_evidence(candidacies)
    derived = derive_incumbency(
        candidacies.query("event_id == 'ec-ge-42'"), evidence.rosters
    ).set_index("candidate_name")

    assert pd.isna(derived.loc["Stale Winner", "incumbent"])
    assert pd.isna(derived.loc["New Candidate", "incumbent"])


def test_authority_reported_true_does_not_override_a_later_election_loss():
    candidacies = pd.DataFrame(
        [
            _federal_row(
                "can_170e509cc71258e88e1efb5a0eb3e7e7",
                "ec-ge-41",
                "2011-05-02",
                "general",
                "per_ted",
                "Ted Opitz",
                elected=True,
                incumbent_reported=False,
                district_id="dst_f9f2054a899f5b29903afdeb23e753a7",
            ),
            _federal_row(
                "can_1c4dea510aae5edab6401e934ec98d6c",
                "ec-ge-42",
                "2015-10-19",
                "general",
                "per_ted",
                "Ted Opitz",
                elected=False,
                incumbent_reported=True,
                district_id="dst_1bc62eabeaad547eba65542f394ef772",
            ),
            _federal_row(
                "can_f34d3f0075eb57fbacdf120260fd827e",
                "ec-ge-45",
                "2025-04-28",
                "general",
                "per_ted",
                "Ted Opitz",
                elected=False,
                # EC reports this as true even though his last House candidacy
                # was a loss and he did not sit in the dissolved Parliament.
                incumbent_reported=True,
                district_id="dst_780b90119e715fcabbfbfa777d651cd5",
            ),
        ]
    )

    evidence = build_federal_roster_evidence(candidacies)
    current = candidacies.query("event_id == 'ec-ge-45'")
    derived = derive_incumbency(current, evidence.rosters)

    assert pd.isna(derived["incumbent"].item())


def test_elected_replacement_ends_olivia_chows_prior_win_continuity():
    candidacies = pd.DataFrame(
        [
            _federal_row(
                "can_38801a15d10c5a99b98d9879fedfa2c7",
                "ec-ge-41",
                "2011-05-02",
                "general",
                "per_olivia",
                "Olivia Chow",
                elected=True,
                incumbent_reported=True,
                district_id="dst_ec7099a5f12a56dba3805f2ecfcf3f25",
            ),
            _federal_row(
                "can_c551fcf020b756d3848173f97c9c4d03",
                "ec-be-2014-06-30",
                "2014-06-30",
                "by_election",
                "per_adam",
                "Adam Vaughan",
                elected=True,
                incumbent_reported=False,
                district_id="dst_ec7099a5f12a56dba3805f2ecfcf3f25",
            ),
            _federal_row(
                "can_7754a84422c45a848e61be0d0d30d054",
                "ec-ge-42",
                "2015-10-19",
                "general",
                "per_olivia",
                "Olivia Chow",
                elected=False,
                incumbent_reported=True,
                district_id="dst_de8904d51a775a2a9c7bfa8ffecb0ebf",
            ),
        ]
    )

    evidence = build_federal_roster_evidence(candidacies)
    current = candidacies.query("event_id == 'ec-ge-42'")
    derived = derive_incumbency(current, evidence.rosters)

    assert pd.isna(derived["incumbent"].item())
