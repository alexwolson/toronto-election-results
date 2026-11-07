"""Census population points: compiling them from Statistics Canada's files, and reading them."""

from __future__ import annotations

import importlib.util
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from toronto_election_results.census_points import (
    CENSUS_FOR_REGIME,
    read_population_points,
)

REPO_ROOT = Path(__file__).parents[1]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zip(path: Path, member: str, payload: bytes) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member, payload)
    return path


def _gaf_2021(path: Path) -> Path:
    header = '"CSDUID_SDRIDU","DAUID_ADIDU","DARPLAT_ADLAT","DARPLONG_ADLONG","DBUID_IDIDU","DBPOP2021_IDPOP2021"'
    rows = [
        "3520005,35200001,43.70000,-79.40000,3520000101,120",
        "3520005,35200001,43.70000,-79.40000,3520000102,30",
        "3520005,35200002,43.71000,-79.39000,3520000201,0",
        "3521005,35210001,43.60000,-79.60000,3521000101,999",
    ]
    text = header + "\n" + "\n".join(rows) + "\n"
    return _zip(path, "2021_92-151_X.csv", text.encode("latin-1"))


def _gaf_2011(path: Path) -> Path:
    """A workbook in the 2011 layout: no header, fields by position, CSDuid at index 24."""

    def row(dbuid, population, dauid, lat, long, csd):
        cells = [""] * 30
        cells[0], cells[1], cells[6], cells[9], cells[10], cells[24] = (
            dbuid,
            population,
            dauid,
            lat,
            long,
            csd,
        )
        return cells

    book = Workbook()
    sheet = book.active
    sheet.append(row("3520000101", "200", "35200001", "43.701", "-79.401", "3520005"))
    sheet.append(row("3520000102", "50", "35200001", "43.701", "-79.401", "3520005"))
    sheet.append(row("3521000101", "999", "35210001", "43.6", "-79.6", "3521005"))
    buffer = io.BytesIO()
    book.save(buffer)
    return _zip(path, "2011_92-151_XBB_XLSX.xlsx", buffer.getvalue())


def test_compile_sums_block_population_by_dissemination_area_within_toronto(tmp_path):
    script = _load_script("build_census_population_points")
    frame = script.compile_points(_gaf_2011(tmp_path / "a.zip"), _gaf_2021(tmp_path / "b.zip"))
    assert frame.columns.tolist() == ["census_year", "dauid", "latitude", "longitude", "population"]
    assert frame.to_dict("records") == [
        {
            "census_year": 2011,
            "dauid": "35200001",
            "latitude": 43.701,
            "longitude": -79.401,
            "population": 250,
        },
        {
            "census_year": 2021,
            "dauid": "35200001",
            "latitude": 43.7,
            "longitude": -79.4,
            "population": 150,
        },
        {
            "census_year": 2021,
            "dauid": "35200002",
            "latitude": 43.71,
            "longitude": -79.39,
            "population": 0,
        },
    ]


def test_read_population_points_keys_each_census_by_the_regimes_drawn_from_it(tmp_path):
    path = tmp_path / "points.csv"
    pd.DataFrame(
        {
            "census_year": [2011, 2021, 2021],
            "dauid": ["35200001", "35200001", "35200002"],
            "latitude": [43.701, 43.7, 43.71],
            "longitude": [-79.401, -79.4, -79.39],
            "population": [250, 150, 0],
        }
    ).to_csv(path, index=False)
    points = read_population_points(path)
    assert set(points) == set(CENSUS_FOR_REGIME)
    assert CENSUS_FOR_REGIME == {
        "federal-2013-representation-order": 2011,
        "ontario-2018-124": 2011,
        "federal-2023-representation-order": 2021,
    }
    in_2021 = points["federal-2023-representation-order"]
    # An area with no population carries no weight and is left out.
    assert in_2021.weights == (150.0,)
    assert in_2021.points[0].x == pytest.approx(-79.4, abs=1e-5)
    assert in_2021.points[0].y == pytest.approx(43.7, abs=1e-5)
    assert points["ontario-2018-124"] == points["federal-2013-representation-order"]


def test_read_population_points_without_the_file_gives_none(tmp_path):
    assert read_population_points(tmp_path / "missing.csv") == {}
