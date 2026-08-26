"""Public-contract tests for the Elections Canada federal-results adapter.

The fixtures are tiny extracts in Elections Canada's official raw-data formats. Expected totals
are literal worked examples from those rows, independent of the adapter's implementation.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from toronto_election_results.federal import (
    NORMALIZED_COLUMNS,
    download_federal_event,
    federal_contest_manifest,
    federal_event_manifest,
    load_federal_results,
    parse_federal_results,
)
from toronto_election_results.schema import normalize_adapter_frame

FIXTURES = Path(__file__).parent / "fixtures" / "federal"
LONG_RESULTS = FIXTURES / "pollresults_resultatsbureau35007.csv"
WIDE_RESULTS = FIXTURES / "pollbypoll35080.csv"
WIDE_2004_RESULTS = FIXTURES / "2004-pollbypoll35080.csv"
SUMMARY_2004_RESULTS = FIXTURES / "table12-2004.csv"
HISTORICAL_2014_RESULTS = FIXTURES / "historical-results-35080-2014.html"


def test_manifest_covers_completed_toronto_federal_events_through_cutoff():
    events = federal_event_manifest()
    contests = federal_contest_manifest()

    assert len(events) == 16
    assert (events["election_type"] == "general").sum() == 8
    assert (events["election_type"] == "by_election").sum() == 8
    assert events["election_date"].max().isoformat() == "2026-04-13"

    general = contests[contests["election_type"] == "general"]
    by_election = contests[contests["election_type"] == "by_election"]
    assert len(general) == 187
    assert len(by_election) == 12

    assert list(
        by_election[["election_date", "official_district_id", "district_name"]].itertuples(
            index=False, name=None
        )
    ) == [
        (pd.Timestamp("2008-03-17").date(), "35093", "Toronto Centre"),
        (pd.Timestamp("2008-03-17").date(), "35100", "Willowdale"),
        (pd.Timestamp("2012-03-19").date(), "35094", "Toronto—Danforth"),
        (pd.Timestamp("2013-11-25").date(), "35093", "Toronto Centre"),
        (pd.Timestamp("2014-06-30").date(), "35080", "Scarborough—Agincourt"),
        (pd.Timestamp("2014-06-30").date(), "35095", "Trinity—Spadina"),
        (pd.Timestamp("2017-12-11").date(), "35093", "Scarborough—Agincourt"),
        (pd.Timestamp("2020-10-26").date(), "35108", "Toronto Centre"),
        (pd.Timestamp("2020-10-26").date(), "35118", "York Centre"),
        (pd.Timestamp("2024-06-24").date(), "35090", "Toronto—St. Paul's"),
        (pd.Timestamp("2026-04-13").date(), "35096", "Scarborough Southwest"),
        (pd.Timestamp("2026-04-13").date(), "35112", "University—Rosedale"),
    ]

    # The 2008 Don Valley West call was cancelled when the general-election writ superseded it.
    assert not (
        (contests["election_date"] == pd.Timestamp("2008-09-22").date())
        & (contests["district_name"] == "Don Valley West")
    ).any()
    assert all(
        url.startswith("https://www.elections.ca/")
        for urls in events["source_urls"]
        for url in urls
    )
    wide = events[events["source_layout"] == "wide_poll"]
    assert set(wide["event_id"]) == {
        "ec-ge-38",
        "ec-be-2008-03-17",
        "ec-be-2012-03-19",
        "ec-be-2013-11-25",
        "ec-be-2014-06-30",
    }
    enriched_2004 = wide[wide["event_id"] == "ec-ge-38"].iloc[0]
    assert enriched_2004["summary_source_urls"] == (
        "https://www.elections.ca/scripts/OVR2004/23/data/table12.csv",
    )
    assert enriched_2004["unavailable_source_fields"] == ()
    assert enriched_2004["winner_derivation"] == "official_summary_indicator"

    historical_enriched = wide[wide["event_id"] != "ec-ge-38"]
    assert (
        historical_enriched["unavailable_source_fields"]
        .map(lambda fields: fields == ("incumbent_reported", "elected"))
        .all()
    )
    assert historical_enriched["summary_source_urls"].map(bool).all()
    assert (historical_enriched["winner_derivation"] == "unique_certified_vote_maximum").all()


def test_long_poll_rows_become_one_normalized_row_per_candidacy():
    result = parse_federal_results(LONG_RESULTS, event_id="ec-ge-44")

    assert list(result.columns) == NORMALIZED_COLUMNS
    assert len(result) == 2

    elected = result.loc[result["candidate_name_raw"] == "Nathaniel Erskine-Smith"].iloc[0]
    assert elected["official_district_id"] == "35007"
    assert elected["district_name"] == "Beaches—East York"
    assert elected["office_type"] == "mp"
    assert elected["party_name_raw"] == "Liberal"
    assert elected["affiliation_status"] == "party"
    assert elected["votes"] == 283
    assert bool(elected["elected"])
    assert bool(elected["incumbent_reported"])
    assert elected["eligible_electors"] == 936
    assert elected["ballots_cast"] == 294
    assert elected["turnout_scope"] == "federal_electoral_district"
    assert elected["source_authority"] == "Elections Canada"
    assert elected["source_resource"] == "Official Voting Results — Raw Data"

    independent = result.loc[result["candidate_name_raw"] == "Diane Joseph"].iloc[0]
    assert independent["party_name_raw"] == "Independent"
    assert independent["affiliation_status"] == "independent"
    assert independent["votes"] == 8
    assert not bool(independent["elected"])
    assert not bool(independent["incumbent_reported"])


def test_long_poll_rows_reject_malformed_candidate_votes(tmp_path):
    source = LONG_RESULTS.read_text(encoding="utf-8-sig").replace(
        ",Y,Y,183\n", ",Y,Y,not-a-number\n", 1
    )
    path = tmp_path / LONG_RESULTS.name
    path.write_text(source, encoding="utf-8-sig")

    with pytest.raises(ValueError, match="candidate votes"):
        parse_federal_results(path, event_id="ec-ge-44")


def test_normalized_rows_cross_the_shared_adapter_seam():
    adapter_rows = parse_federal_results(LONG_RESULTS, event_id="ec-ge-44")

    normalized = normalize_adapter_frame(adapter_rows)

    assert normalized["office_type"].unique().tolist() == ["mp"]
    assert normalized["official_district_id"].unique().tolist() == ["35007"]
    assert normalized["district_id"].str.startswith("dst_").all()
    assert normalized["candidacy_id"].str.startswith("can_").all()


def test_2008_malformed_district_quote_is_removed_from_normalized_name(tmp_path):
    source = LONG_RESULTS.read_text(encoding="utf-8-sig").replace(
        '35007,"Beaches--East York"',
        '35007,Beaches--East York"',
    )
    path = tmp_path / LONG_RESULTS.name
    path.write_text(source, encoding="utf-8-sig")

    result = parse_federal_results(path, event_id="ec-ge-44")

    assert result["district_name"].unique().tolist() == ["Beaches—East York"]


def test_general_election_zip_is_filtered_to_manifested_toronto_districts(tmp_path):
    archive = tmp_path / "ontario.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        zipped.write(LONG_RESULTS, arcname=LONG_RESULTS.name)
        zipped.writestr(
            "pollresults_resultatsbureau99999.csv",
            LONG_RESULTS.read_text(encoding="utf-8-sig").replace("35007", "99999"),
        )

    result = parse_federal_results(archive, event_id="ec-ge-44")

    assert set(result["official_district_id"]) == {"35007"}
    assert result["candidate_name_raw"].tolist() == ["Diane Joseph", "Nathaniel Erskine-Smith"]


def test_zip_with_no_manifested_district_returns_an_empty_normalized_frame(tmp_path):
    archive = tmp_path / "outside-toronto.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        zipped.writestr(
            "pollresults_resultatsbureau99999.csv",
            LONG_RESULTS.read_text(encoding="utf-8-sig").replace("35007", "99999"),
        )

    result = parse_federal_results(archive, event_id="ec-ge-44")

    assert result.empty
    assert list(result.columns) == NORMALIZED_COLUMNS


def test_2004_zip_uses_member_name_when_wide_csv_omits_district_number(tmp_path):
    lines = WIDE_RESULTS.read_text(encoding="utf-8-sig").splitlines()
    header = (
        lines[0]
        .split(",", 1)[1]
        .replace(
            "Electoral District Name/Nom de circonscription",
            "Electoral District/Circonscription",
            1,
        )
    )
    without_district_number = "\n".join([header, *(line.split(",", 1)[1] for line in lines[1:])])
    archive = tmp_path / "ON.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        zipped.writestr("pollbypoll35080.csv", without_district_number)

    result = parse_federal_results(archive, event_id="ec-ge-38")

    assert result["official_district_id"].unique().tolist() == ["35080"]
    assert result["district_name"].unique().tolist() == ["Scarborough—Agincourt"]


def test_wide_rows_with_blank_poll_numbers_remain_distinct_groups(tmp_path):
    source = WIDE_RESULTS.read_text(encoding="utf-8-sig") + (
        '35080,"Scarborough--Agincourt/Scarborough--Agincourt",,"Group 1",'
        "1,2,3,4,5,1,16,20\n"
        '35080,"Scarborough--Agincourt/Scarborough--Agincourt",,"Group 2",'
        "2,3,4,5,6,1,21,30\n"
    )
    path = tmp_path / WIDE_RESULTS.name
    path.write_text(source, encoding="utf-8-sig")

    result = parse_federal_results(path, event_id="ec-be-2014-06-30")

    assert result["eligible_electors"].unique().tolist() == [870]
    assert result["ballots_cast"].unique().tolist() == [200]


@pytest.mark.parametrize(
    ("source_fragment", "malformed_fragment", "field"),
    [
        (",54,7,14,", ",54,not-a-number,14,", "candidate votes"),
        (",0,76,432\n", ",0,not-a-number,432\n", "total votes"),
        (",0,76,432\n", ",0,76,not-a-number\n", "electors"),
    ],
)
def test_wide_poll_rows_reject_malformed_numeric_values(
    tmp_path, source_fragment, malformed_fragment, field
):
    source = WIDE_RESULTS.read_text(encoding="utf-8-sig").replace(
        source_fragment, malformed_fragment, 1
    )
    path = tmp_path / WIDE_RESULTS.name
    path.write_text(source, encoding="utf-8-sig")

    with pytest.raises(ValueError, match=field):
        parse_federal_results(path, event_id="ec-be-2014-06-30")


@pytest.mark.parametrize("non_vote_cell", ["", "Void/Supprimé"])
def test_wide_poll_non_vote_candidate_cell_contributes_zero_votes(tmp_path, non_vote_cell):
    source = WIDE_RESULTS.read_text(encoding="utf-8-sig").replace(
        ",1,0,0,76,432\n", f",1,{non_vote_cell},0,76,432\n", 1
    )
    path = tmp_path / WIDE_RESULTS.name
    path.write_text(source, encoding="utf-8-sig")

    result = parse_federal_results(path, event_id="ec-be-2014-06-30")

    assert result.set_index("candidate_name_raw").loc["Shahbaz Mir", "votes"] == 1


def test_wide_poll_blank_contest_metrics_remain_unknown_not_zero(tmp_path):
    source = WIDE_RESULTS.read_text(encoding="utf-8-sig")
    source = source.replace(",0,76,432\n", ",0,,\n", 1)
    source = source.replace(",1,87,388\n", ",1,,\n", 1)
    path = tmp_path / WIDE_RESULTS.name
    path.write_text(source, encoding="utf-8-sig")

    result = parse_federal_results(path, event_id="ec-be-2014-06-30")

    assert result["eligible_electors"].isna().all()
    assert result["ballots_cast"].isna().all()


def test_long_rows_use_poll_name_to_distinguish_blank_poll_numbers(tmp_path):
    source = LONG_RESULTS.read_text(encoding="utf-8-sig") + (
        '35007,"Beaches--East York","Beaches--East York",,"Group 1",N,N,"",1,100,'
        '"Erskine-Smith","","Nathaniel","Liberal","Libéral",Y,Y,30\n'
        '35007,"Beaches--East York","Beaches--East York",,"Group 1",N,N,"",1,100,'
        '"Joseph","","Diane","Independent","Indépendant(e)",N,N,2\n'
        '35007,"Beaches--East York","Beaches--East York",,"Group 2",N,N,"",2,200,'
        '"Erskine-Smith","","Nathaniel","Liberal","Libéral",Y,Y,50\n'
        '35007,"Beaches--East York","Beaches--East York",,"Group 2",N,N,"",2,200,'
        '"Joseph","","Diane","Independent","Indépendant(e)",N,N,3\n'
    )
    path = tmp_path / LONG_RESULTS.name
    path.write_text(source, encoding="utf-8-sig")

    result = parse_federal_results(path, event_id="ec-ge-44")

    assert result["eligible_electors"].unique().tolist() == [1236]
    assert result["ballots_cast"].unique().tolist() == [382]


def test_wide_poll_rows_preserve_unknown_party_and_mark_unique_top_vote_getter():
    result = parse_federal_results(WIDE_RESULTS, event_id="ec-be-2014-06-30")

    assert result["candidate_name_raw"].tolist() == [
        "Arnold Chan",
        "Elizabeth Ying Long",
        "Kevin Clarke",
        "Shahbaz Mir",
        "Trevor Ellis",
    ]
    assert result.set_index("candidate_name_raw")["votes"].to_dict() == {
        "Arnold Chan": 108,
        "Elizabeth Ying Long": 10,
        "Kevin Clarke": 8,
        "Shahbaz Mir": 1,
        "Trevor Ellis": 35,
    }
    assert (result["affiliation_status"] == "not_reported").all()
    assert result["party_name_raw"].isna().all()
    assert result.set_index("candidate_name_raw")["elected"].to_dict() == {
        "Arnold Chan": True,
        "Elizabeth Ying Long": False,
        "Kevin Clarke": False,
        "Shahbaz Mir": False,
        "Trevor Ellis": False,
    }
    assert result["incumbent_reported"].isna().all()
    assert (result["eligible_electors"] == 820).all()
    assert (result["ballots_cast"] == 163).all()


def test_2004_table12_enriches_wide_rows_with_official_affiliation_and_flags():
    result = parse_federal_results(
        WIDE_2004_RESULTS,
        event_id="ec-ge-38",
        summary_paths=SUMMARY_2004_RESULTS,
    )

    assert result.set_index("candidate_name_raw")["party_name_raw"].to_dict() == {
        "Andrew Faust": "Conservative",
        "D'Arcy Palmer": "N.D.P.",
        "Jim Karygiannis": "Liberal",
        "Tony J. Karadimas": "PC Party",
        "Wayne Yeechong": "Green Party",
    }
    assert (result["affiliation_status"] == "party").all()
    assert result.set_index("candidate_name_raw")["incumbent_reported"].to_dict() == {
        "Andrew Faust": False,
        "D'Arcy Palmer": False,
        "Jim Karygiannis": True,
        "Tony J. Karadimas": False,
        "Wayne Yeechong": False,
    }
    assert result.set_index("candidate_name_raw")["elected"].to_dict() == {
        "Andrew Faust": False,
        "D'Arcy Palmer": False,
        "Jim Karygiannis": True,
        "Tony J. Karadimas": False,
        "Wayne Yeechong": False,
    }
    assert result["source_detail"].str.contains("table12.csv", regex=False).all()


def test_2004_table12_enrichment_rejects_incomplete_or_mismatched_summary(tmp_path):
    incomplete = tmp_path / SUMMARY_2004_RESULTS.name
    incomplete.write_text(
        "\n".join(SUMMARY_2004_RESULTS.read_text(encoding="utf-8").splitlines()[:-1]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="summary coverage does not match"):
        parse_federal_results(
            WIDE_2004_RESULTS,
            event_id="ec-ge-38",
            summary_paths=incomplete,
        )

    vote_mismatch = tmp_path / "vote-mismatch.csv"
    vote_mismatch.write_text(
        SUMMARY_2004_RESULTS.read_text(encoding="utf-8").replace(
            'Jim Karygiannis ** Liberal/Libéral,"Scarborough, Ont/Ont.",'
            "Parliamentarian/Parlementaire,26400,",
            'Jim Karygiannis ** Liberal/Libéral,"Scarborough, Ont/Ont.",'
            "Parliamentarian/Parlementaire,26401,",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="vote totals disagree"):
        parse_federal_results(
            WIDE_2004_RESULTS,
            event_id="ec-ge-38",
            summary_paths=vote_mismatch,
        )


def test_early_by_election_historical_table_enriches_party_without_inference():
    result = parse_federal_results(
        WIDE_RESULTS,
        event_id="ec-be-2014-06-30",
        summary_paths=HISTORICAL_2014_RESULTS,
    )

    assert result.set_index("candidate_name_raw")["party_name_raw"].to_dict() == {
        "Arnold Chan": "Liberal Party of Canada",
        "Elizabeth Ying Long": "New Democratic Party",
        "Kevin Clarke": "Independent",
        "Shahbaz Mir": "Green Party of Canada",
        "Trevor Ellis": "Conservative Party of Canada",
    }
    assert result.set_index("candidate_name_raw")["affiliation_status"].to_dict() == {
        "Arnold Chan": "party",
        "Elizabeth Ying Long": "party",
        "Kevin Clarke": "independent",
        "Shahbaz Mir": "party",
        "Trevor Ellis": "party",
    }
    assert result["incumbent_reported"].isna().all()
    assert bool(result.loc[result["candidate_name_raw"] == "Arnold Chan", "elected"].iloc[0])


def test_wide_tied_maximum_stays_unknown_while_lower_candidates_are_not_elected(tmp_path):
    tied_source = (
        WIDE_RESULTS.read_text(encoding="utf-8-sig")
        .replace(",54,7,14,1,0,0,76,432", ",54,7,54,1,0,0,116,432")
        .replace(",54,1,21,9,1,1,87,388", ",54,1,54,9,1,1,120,388")
    )
    path = tmp_path / WIDE_RESULTS.name
    path.write_text(tied_source, encoding="utf-8-sig")

    result = parse_federal_results(path, event_id="ec-be-2014-06-30")

    tied = result[result["candidate_name_raw"].isin({"Arnold Chan", "Trevor Ellis"})]
    lower = result[~result.index.isin(tied.index)]
    assert tied["elected"].isna().all()
    assert lower["elected"].tolist() == [False] * len(lower)


class _Response:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size: int):
        assert chunk_size > 0
        yield self.content


class _Session:
    def __init__(self, content: bytes):
        self.content = content
        self.urls: list[str] = []

    def get(self, url: str, **kwargs):
        self.urls.append(url)
        assert kwargs["stream"] is True
        return _Response(self.content)


class _BrokenResponse(_Response):
    def iter_content(self, chunk_size: int):
        yield b"partial"
        raise RuntimeError("connection lost")


class _BrokenSession(_Session):
    def get(self, url: str, **kwargs):
        self.urls.append(url)
        return _BrokenResponse(self.content)


def test_download_is_event_scoped_atomic_and_idempotent(tmp_path):
    session = _Session(b"official csv bytes")

    first = download_federal_event("ec-be-2012-03-19", tmp_path, session=session)
    second = download_federal_event("ec-be-2012-03-19", tmp_path, session=session)

    assert first == second
    assert [path.name for path in first] == [
        "pollbypoll_bureauparbureau35094.csv",
        "35094_e.html",
    ]
    assert first[0].parent == tmp_path / "ec-be-2012-03-19"
    assert first[0].read_bytes() == b"official csv bytes"
    assert not list(first[0].parent.glob("*.part"))
    assert len(session.urls) == 2


def test_2004_download_includes_poll_archive_and_official_summary(tmp_path):
    session = _Session(b"official source bytes")

    paths = download_federal_event("ec-ge-38", tmp_path, session=session)

    assert [path.name for path in paths] == ["ON.zip", "table12.csv"]
    assert session.urls == [
        "https://www.elections.ca/scripts/OVR2004/23/data/ON.zip",
        "https://www.elections.ca/scripts/OVR2004/23/data/table12.csv",
    ]


def test_failed_download_leaves_neither_final_nor_partial_file(tmp_path):
    with pytest.raises(RuntimeError, match="connection lost"):
        download_federal_event(
            "ec-be-2012-03-19",
            tmp_path,
            session=_BrokenSession(b"unused"),
        )

    event_dir = tmp_path / "ec-be-2012-03-19"
    assert not list(event_dir.iterdir())


def test_load_reads_a_deterministic_event_scoped_cache(tmp_path):
    event_dir = tmp_path / "ec-ge-44"
    event_dir.mkdir()
    archive = event_dir / "pollresults_resultatsbureau35.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        zipped.write(LONG_RESULTS, arcname=LONG_RESULTS.name)

    with pytest.raises(ValueError, match="contest coverage does not match"):
        load_federal_results(tmp_path, event_ids=("ec-ge-44",))

    result = load_federal_results(tmp_path, event_ids=("ec-ge-44",), validate=False)

    assert list(result.columns) == NORMALIZED_COLUMNS
    assert result["event_id"].unique().tolist() == ["ec-ge-44"]
    assert result["candidate_name_raw"].tolist() == [
        "Diane Joseph",
        "Nathaniel Erskine-Smith",
    ]


def test_load_2004_cache_applies_the_manifested_summary_enrichment(tmp_path):
    event_dir = tmp_path / "ec-ge-38"
    event_dir.mkdir()
    archive = event_dir / "ON.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        zipped.write(WIDE_2004_RESULTS, arcname="pollbypoll35080.csv")
    (event_dir / "table12.csv").write_bytes(SUMMARY_2004_RESULTS.read_bytes())

    result = load_federal_results(tmp_path, event_ids=("ec-ge-38",), validate=False)

    winner = result.loc[result["candidate_name_raw"] == "Jim Karygiannis"].iloc[0]
    assert winner["party_name_raw"] == "Liberal"
    assert bool(winner["incumbent_reported"])
    assert bool(winner["elected"])
