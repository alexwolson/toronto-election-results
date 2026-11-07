"""Describe the seat behind each incumbency: how the member came to hold it, and where it was.

``incumbent`` says only that a candidate sat, on the eve of the election, in the same Office type
of the same Represented body. The Office tenure behind it also says how the member entered the
seat and which district it was. Three fields carry that onto the Candidacy:

- ``incumbent_appointed``: the member was appointed to the seat rather than elected to it.
- ``incumbent_held_district_id``: the district of the seat the member held.
- ``incumbent_changed_district``: the member is running somewhere other than that seat. Within
  one Boundary regime that means another district. Across a boundary change, the member keeps
  the seat when the district now contested holds more of the held district's people than any
  other district of the new regime does. For council wards the people are counted by the City's
  polls (voting subdivisions), each counting once. For ridings they are counted by census
  population (``census_points``): the points are dissemination areas, each weighted by its
  population, and a riding's people are the points inside its shape. Both follow where electors
  live more closely than area does. A tie, or no people found, leaves the field null, as does a
  boundary change without the points or the shapes it needs. A legislature seat outside the
  City, which has no district in the release, is always another district.

The three are null unless ``incumbent`` is true, and null where the tenure does not say: a 1995
Ontario incumbent flag gives neither the member's entry nor the seat.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from .census_points import PopulationPoints

INCUMBENT_SEAT_COLUMNS = (
    "incumbent_appointed",
    "incumbent_held_district_id",
    "incumbent_changed_district",
)
_LEGISLATURES = frozenset({"canada_house_of_commons", "ontario_legislative_assembly"})


def _main_successor(
    points: Sequence[object], regime: pd.DataFrame, weights: Sequence[float] | None = None
) -> object:
    """Return the district of ``regime`` holding the most weight, or NA without a clear one.

    Each point weighs one unless ``weights`` gives its weight.
    """

    weights = [1.0] * len(points) if weights is None else weights
    counts = {
        district_id: sum(
            weight for point, weight in zip(points, weights, strict=True) if geometry.covers(point)
        )
        for district_id, geometry in zip(regime["district_id"], regime["geometry"], strict=True)
    }
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] == 0 or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        return pd.NA
    return ranked[0][0]


def _held_population(
    held_shape: object, census: PopulationPoints
) -> tuple[list[object], list[float]]:
    """The census points inside a held district's shape, with their populations."""

    inside = [
        (point, weight)
        for point, weight in zip(census.points, census.weights, strict=True)
        if held_shape.covers(point)
    ]
    return [point for point, _ in inside], [weight for _, weight in inside]


def add_incumbent_seat_fields(
    candidacies: pd.DataFrame,
    tenures: pd.DataFrame,
    districts: pd.DataFrame,
    poll_points: Mapping[str, Sequence[object]] | None = None,
    population_points: Mapping[str, PopulationPoints] | None = None,
) -> pd.DataFrame:
    """Return the Candidacies with the three incumbent seat fields filled from their tenures.

    ``poll_points`` gives one point inside each poll of a held council ward, keyed by
    district_id. ``population_points`` gives the census points to compare ridings with, keyed by
    the Boundary regime of the Contest.
    """

    out = candidacies.copy()
    if "incumbent" not in out or not out["incumbent"].eq(True).fillna(False).any():
        out["incumbent_appointed"] = pd.array([pd.NA] * len(out), dtype="boolean")
        out["incumbent_held_district_id"] = pd.array([pd.NA] * len(out), dtype="string")
        out["incumbent_changed_district"] = pd.array([pd.NA] * len(out), dtype="boolean")
        return out
    district_columns = [
        "district_id",
        "boundary_regime",
        "official_district_id",
        "geometry_status",
        "geometry",
    ]
    if not set(district_columns).issubset(districts.columns):
        districts = pd.DataFrame(columns=district_columns)
    by_id = tenures.drop_duplicates("office_tenure_id").set_index("office_tenure_id")
    regime = dict(
        zip(districts["district_id"].astype(str), districts["boundary_regime"], strict=True)
    )
    polls = {} if poll_points is None else poll_points
    population = {} if population_points is None else population_points
    mapped = districts.loc[
        districts["geometry_status"].eq("available")
        & districts["geometry"].notna()
        & ~districts["official_district_id"].eq("city"),
        ["district_id", "boundary_regime", "geometry"],
    ]
    mapped_ids = set(mapped["district_id"])
    shapes = dict(zip(mapped["district_id"], mapped["geometry"], strict=True))
    successors: dict[tuple[str, object], object] = {}

    appointed: list[object] = []
    held_ids: list[object] = []
    changed: list[object] = []
    for row in out.itertuples(index=False):
        if not (pd.notna(row.incumbent) and bool(row.incumbent)):
            appointed.append(pd.NA)
            held_ids.append(pd.NA)
            changed.append(pd.NA)
            continue
        tenure = by_id.loc[row.incumbent_office_tenure_id]
        if tenure["started_on_precision"] == "unknown":
            appointed.append(pd.NA)
            held_ids.append(pd.NA)
            changed.append(pd.NA)
            continue
        entry = tenure["entry_method"]
        if entry not in {"election", "appointment"}:
            raise ValueError(f"Office tenure {row.incumbent_office_tenure_id} has entry {entry!r}")
        appointed.append(entry == "appointment")
        held = tenure["district_id"]
        if pd.isna(held):
            if row.represented_body not in _LEGISLATURES:
                raise ValueError(
                    f"Office tenure {row.incumbent_office_tenure_id} has no district outside a "
                    "legislature"
                )
            held_ids.append(pd.NA)
            changed.append(True)
            continue
        held = str(held)
        held_ids.append(held)
        if row.office_type == "mayor" or held == row.district_id:
            changed.append(False)
        elif regime.get(held) == row.boundary_regime:
            changed.append(True)
        elif held in polls and row.district_id in mapped_ids:
            key = (held, row.boundary_regime)
            if key not in successors:
                contested = mapped.loc[mapped["boundary_regime"].eq(row.boundary_regime)]
                successors[key] = _main_successor(polls[held], contested)
            successor = successors[key]
            changed.append(pd.NA if pd.isna(successor) else successor != row.district_id)
        elif (
            row.represented_body in _LEGISLATURES
            and row.boundary_regime in population
            and held in mapped_ids
            and row.district_id in mapped_ids
        ):
            key = (held, row.boundary_regime)
            if key not in successors:
                contested = mapped.loc[mapped["boundary_regime"].eq(row.boundary_regime)]
                points, weights = _held_population(shapes[held], population[row.boundary_regime])
                successors[key] = _main_successor(points, contested, weights)
            successor = successors[key]
            changed.append(pd.NA if pd.isna(successor) else successor != row.district_id)
        else:
            changed.append(pd.NA)

    out["incumbent_appointed"] = pd.array(appointed, dtype="boolean")
    out["incumbent_held_district_id"] = pd.array(held_ids, dtype="string")
    out["incumbent_changed_district"] = pd.array(changed, dtype="boolean")
    return out
