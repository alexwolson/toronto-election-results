"""Incumbency: council-composition extraction and the incumbent flag."""

from pathlib import Path

import pandas as pd

from toronto_election_results.candidates import assign_candidate_ids, match_key, normalize_name
from toronto_election_results.incumbency import (
    council_members_before,
    enrich_composition,
    flag_incumbents,
    parse_roster_text,
    reconcile_rosters,
    roster_to_composition,
)


def _mk(name):
    return match_key(normalize_name(name)[0])


COUNCIL_FIXTURES = Path(__file__).parent / "fixtures" / "council"
_EMPTY_COMPOSITION = pd.DataFrame(
    columns=[
        "election_year",
        "member_name",
        "match_key",
        "alt_key",
        "incumbent_source",
        "confidence",
    ]
)


class TestCouncilMembersBefore:
    def _members(self):
        return council_members_before(2018, raw=COUNCIL_FIXTURES)

    def test_keeps_sitting_member_from_attendance(self):
        m = self._members()
        row = m[m["member_name"].str.contains("Bailao")]
        assert len(row) == 1
        assert row["incumbent_source"].iloc[0] == "city_attendance"

    def test_keeps_late_appointee_from_voting_only(self):
        """Tsao appears only in voting but is active through the final year -> kept."""
        m = self._members()
        row = m[m["member_name"].str.contains("Tsao")]
        assert len(row) == 1
        assert row["incumbent_source"].iloc[0] == "city_voting"

    def test_drops_member_who_departed_before_the_final_year(self):
        """McConnell's latest activity predates the term's final year -> not a sitting member."""
        m = self._members()
        assert not m["member_name"].str.contains("McConnell").any()


class TestFlagIncumbents:
    def _results(self, names_years):
        rows = [
            {
                "election_year": y,
                "candidate_name_raw": n,
                "elected": False,
                "election_type": "general",
                "office": "councillor",
            }
            for n, y in names_years
        ]
        df = pd.DataFrame(rows)
        normalized = df["candidate_name_raw"].map(normalize_name)
        df["candidate_name"] = [n[0] for n in normalized]
        return assign_candidate_ids(df)

    def test_appointee_matched_via_roster(self):
        """A candidate not in the prior winners is flagged from the composition roster."""
        composition = council_members_before(2018, raw=COUNCIL_FIXTURES)
        results = self._results([("Bailao Ana", 2018), ("Newcomer Jane", 2018)])
        out = flag_incumbents(results, composition, roster_confidence={2018: 0.95})

        bailao = out[out["candidate_name"].str.contains("Bailao")].iloc[0]
        newcomer = out[out["candidate_name"].str.contains("Newcomer")].iloc[0]
        assert bailao["incumbent"] and bailao["incumbent_source"] == "city_attendance"
        assert not newcomer["incumbent"]
        assert pd.isna(newcomer["incumbent_source"])

    def test_prior_winner_flagged_even_when_name_form_drifts(self):
        """Won the prior election as 'Norman Kelly', runs as 'Norm Kelly' -> still incumbent."""
        df = pd.DataFrame(
            {
                "election_year": [2010, 2014],
                "candidate_name_raw": ["Norman Kelly", "Norm Kelly"],
                "elected": [True, False],
                "election_type": "general",
                "office": "councillor",
            }
        )
        df["candidate_name"] = [normalize_name(n)[0] for n in df["candidate_name_raw"]]
        df = assign_candidate_ids(df)  # clusters Norm/Norman Kelly to one id
        out = flag_incumbents(df, composition=_EMPTY_COMPOSITION, roster_confidence={2014: 0.95})
        kelly_2014 = out[(out["election_year"] == 2014)].iloc[0]
        assert kelly_2014["incumbent"]
        assert kelly_2014["incumbent_source"] == "prior_winner"

    def test_council_by_election_is_never_incumbent(self):
        """A council by-election fills a vacant ward -> incumbent False even if won a prior election."""
        df = pd.DataFrame(
            {
                "election_year": [2022, 2023],
                "candidate_name_raw": ["Sitter Sam", "Sitter Sam"],
                "elected": [True, False],
                "election_type": ["general", "by_election"],
                "office": "councillor",
            }
        )
        df["candidate_name"] = [normalize_name(n)[0] for n in df["candidate_name_raw"]]
        df = assign_candidate_ids(df)
        out = flag_incumbents(df, composition=_EMPTY_COMPOSITION, roster_confidence={})
        by_row = out[out["election_year"] == 2023].iloc[0]
        assert not by_row["incumbent"]
        assert pd.isna(by_row["incumbent_source"])

    def test_incumbent_confidence_always_populated(self):
        composition = council_members_before(2018, raw=COUNCIL_FIXTURES)
        results = self._results([("Bailao Ana", 2018), ("Newcomer Jane", 2018)])
        out = flag_incumbents(results, composition, roster_confidence={2018: 0.95})
        assert out["incumbent_confidence"].between(0.0, 1.0).all()
        assert out["incumbent_confidence"].notna().all()


def test_council_surnames_extracts_multiword_lastnames():
    from toronto_election_results.incumbency import RAW, council_surnames

    if not (RAW / "attendance").exists():
        import pytest

        pytest.skip("council data not downloaded")
    surnames = council_surnames()
    assert "carmichael greb" in surnames  # double-barrelled surname, authoritative from LastName
    assert "di giorgio" in surnames


class TestRosterReconciliation:
    ROSTER_A = "2000-2003 | 1 | Suzan Hall | elected\n2000-2003 | 30 | Laura Jones | appointed\n"
    ROSTER_B = "2000-2003 | 1 | Suzan Hall | elected\n2000-2003 | 30 | L. Jones | appointed\n"

    def test_parse_roster_text(self):
        df = parse_roster_text(self.ROSTER_A)
        assert list(df.columns) == ["term", "ward", "member_name", "arrival"]
        assert df.iloc[1]["member_name"] == "Laura Jones"

    def test_agreement_is_high_confidence_no_disagreement(self):
        reconciled, disagreements = reconcile_rosters(self.ROSTER_A, self.ROSTER_A)
        assert disagreements == []
        assert (reconciled["confidence"] == 0.85).all()

    def test_disagreement_is_flagged_and_lower_confidence(self):
        reconciled, disagreements = reconcile_rosters(self.ROSTER_A, self.ROSTER_B)
        # ward 30: "Laura Jones" vs "L. Jones" -> different identity key
        assert any("ward 30" in d for d in disagreements)
        assert reconciled[reconciled["ward"] == "30"]["confidence"].iloc[0] == 0.70

    def test_roster_maps_term_to_election_year(self):
        reconciled, _ = reconcile_rosters(self.ROSTER_A, self.ROSTER_A)
        comp = roster_to_composition(reconciled)
        assert (comp["election_year"] == 2003).all()
        assert match_key("Suzan Hall") in set(comp["match_key"])

    def test_name_variant_disagreement_keeps_alias(self):
        """Same surname -> a name-form variant: keep A's name, carry B's form as an alias key."""
        a = "2000-2003 | 7 | George Mammoliti | elected\n"
        b = "2000-2003 | 7 | Giorgio Mammoliti | elected\n"
        reconciled, _ = reconcile_rosters(a, b)
        row = reconciled.iloc[0]
        assert row["member_name"] == "George Mammoliti"
        assert row["alt_name"] == "Giorgio Mammoliti"
        comp = roster_to_composition(reconciled)
        assert comp.iloc[0]["alt_key"] == match_key("Giorgio Mammoliti")

    def test_person_swap_disagreement_has_no_alias(self):
        """Different people (a mid-term replacement) -> keep A (end-of-term), no alias for B."""
        a = "2000-2003 | 17 | Fred Dominelli | appointed\n"
        b = "2000-2003 | 17 | Betty Disero | elected\n"
        reconciled, _ = reconcile_rosters(a, b)
        row = reconciled.iloc[0]
        assert row["member_name"] == "Fred Dominelli"
        assert pd.isna(row["alt_name"])


class TestEnrichComposition:
    def _results(self, rows):
        return pd.DataFrame(
            rows, columns=["candidate_name", "candidate_id", "election_year", "office", "elected"]
        )

    def _composition(self, rows):
        return pd.DataFrame(
            [
                {
                    "election_year": y,
                    "member_name": n,
                    "match_key": _mk(n),
                    "alt_key": None,
                    "office": roster_office,
                    "incumbent_source": "wikipedia",
                    "confidence": 0.85,
                }
                for y, n, roster_office in rows
            ]
        )

    def test_matched_member_gets_id_and_office_from_prior_win(self):
        results = self._results([("Jane Ward", "cJANE", 2010, "councillor", True)])
        out = enrich_composition(self._composition([(2014, "Jane Ward", "councillor")]), results)
        row = out.iloc[0]
        assert row["candidate_id"] == "cJANE"
        assert row["office"] == "councillor"
        assert row["candidate_id_resolution"] == "matched"

    def test_office_tracks_councillor_to_mayor_move(self):
        results = self._results(
            [("Bob Ex", "cBOB", 2006, "councillor", True), ("Bob Ex", "cBOB", 2010, "mayor", True)]
        )
        # roster mislabels Bob as councillor; his most-recent prior win (2010) was mayor
        out = enrich_composition(self._composition([(2014, "Bob Ex", "councillor")]), results)
        assert out.iloc[0]["office"] == "mayor"

    def test_null_id_member_falls_back_to_roster_office(self):
        results = self._results([("Someone Else", "cX", 2010, "councillor", True)])
        # a member who never appears in results (e.g. an incumbent mayor whose win predates the data)
        out = enrich_composition(self._composition([(2003, "Retired Mayor", "mayor")]), results)
        row = out.iloc[0]
        assert pd.isna(row["candidate_id"])
        assert row["office"] == "mayor"
        assert row["candidate_id_resolution"] == "no_results_match"
