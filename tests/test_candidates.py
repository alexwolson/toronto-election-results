"""Name normalization and cross-election candidate identity."""

import pandas as pd

from toronto_election_results.candidates import assign_candidate_ids, normalize_name


class TestNormalizeName:
    def test_comma_format(self):
        assert normalize_name("Miller, David") == ("David Miller", "David", "Miller")

    def test_uppercase_surname_first(self):
        assert normalize_name("FORD ROB") == ("Rob Ford", "Rob", "Ford")

    def test_modern_surname_first(self):
        assert normalize_name("Crisanti Vincent") == ("Vincent Crisanti", "Vincent", "Crisanti")

    def test_comma_keeps_multiword_surname(self):
        assert normalize_name("Di Giorgio, Frank") == ("Frank Di Giorgio", "Frank", "Di Giorgio")

    def test_accents_preserved(self):
        assert normalize_name("Bailão Ana") == ("Ana Bailão", "Ana", "Bailão")

    def test_hyphenated_given_name(self):
        assert normalize_name("Brown Chloe-Marie") == ("Chloe-Marie Brown", "Chloe-Marie", "Brown")


class TestAssignCandidateIds:
    def _df(self, raw_names):
        names = [normalize_name(r)[0] for r in raw_names]
        return pd.DataFrame({"candidate_name": names})

    def test_same_person_across_name_orderings_gets_one_id(self):
        # comma form (2003) and uppercase form (2006) of the same person
        df = self._df(["Di Giorgio, Frank", "DI GIORGIO FRANK"])
        out = assign_candidate_ids(df)
        assert out["candidate_id"].nunique() == 1

    def test_accent_variants_merge(self):
        df = self._df(["Bailão Ana", "Bailao Ana"])
        out = assign_candidate_ids(df)
        assert out["candidate_id"].nunique() == 1

    def test_distinct_people_get_distinct_ids(self):
        df = self._df(["Miller, David", "Ford, Rob", "Tory, John"])
        out = assign_candidate_ids(df)
        assert out["candidate_id"].nunique() == 3

    def test_confidence_is_a_fraction(self):
        df = self._df(["Miller, David", "DI GIORGIO FRANK", "Di Giorgio, Frank"])
        out = assign_candidate_ids(df)
        assert out["candidate_id_confidence"].between(0.0, 1.0).all()

    def test_exact_key_match_is_full_confidence(self):
        df = self._df(["Di Giorgio, Frank", "DI GIORGIO FRANK"])
        out = assign_candidate_ids(df)
        # identical token-sorted key -> deterministic link, full confidence
        assert (out["candidate_id_confidence"] == 1.0).all()
