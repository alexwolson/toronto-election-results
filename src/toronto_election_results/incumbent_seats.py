"""Describe the seat behind each incumbency: how the member came to hold it, and where it was.

``incumbent`` says only that a candidate sat, on the eve of the election, in the same Office type
of the same Represented body. The Office tenure behind it also says how the member entered the
seat and which district it was. Three fields carry that onto the Candidacy:

- ``incumbent_appointed``: the member was appointed to the seat rather than elected to it.
- ``incumbent_held_district_id``: the district of the seat the member held.
- ``incumbent_changed_district``: the member is running somewhere other than that seat. Within
  one Boundary regime that means another district. Across a boundary change it means that less
  than half of the held district's area lies in the district now contested, which needs the
  geometry of both. A legislature seat outside the City, which has no district in the release,
  is always another district.

The three are null unless ``incumbent`` is true, and null where the tenure does not say: a 1995
Ontario incumbent flag gives neither the member's entry nor the seat.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

INCUMBENT_SEAT_COLUMNS = (
    "incumbent_appointed",
    "incumbent_held_district_id",
    "incumbent_changed_district",
)
# NAD83(CSRS) / MTM zone 10, the projection the City surveys in; areas are compared in it.
_AREA_CRS = "EPSG:2952"
_LEGISLATURES = frozenset({"canada_house_of_commons", "ontario_legislative_assembly"})


def _projected_geometries(districts: pd.DataFrame) -> dict[str, object]:
    available = districts.loc[
        districts["geometry_status"].eq("available") & districts["geometry"].notna(),
        ["district_id", "geometry"],
    ]
    if available.empty:
        return {}
    projected = gpd.GeoSeries(list(available["geometry"]), crs="EPSG:4326").to_crs(_AREA_CRS)
    return dict(zip(available["district_id"].astype(str), projected, strict=True))


def _changed_across_regimes(held: object, contested: object) -> object:
    held_area = held.area
    if held_area <= 0:
        raise ValueError("a held district's geometry has no area")
    return bool(held.intersection(contested).area / held_area < 0.5)


def add_incumbent_seat_fields(
    candidacies: pd.DataFrame, tenures: pd.DataFrame, districts: pd.DataFrame
) -> pd.DataFrame:
    """Return the Candidacies with the three incumbent seat fields filled from their tenures."""

    out = candidacies.copy()
    by_id = tenures.drop_duplicates("office_tenure_id").set_index("office_tenure_id")
    regime = dict(
        zip(districts["district_id"].astype(str), districts["boundary_regime"], strict=True)
    )
    shapes = _projected_geometries(districts)

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
        elif held in shapes and row.district_id in shapes:
            changed.append(_changed_across_regimes(shapes[held], shapes[row.district_id]))
        else:
            changed.append(pd.NA)

    out["incumbent_appointed"] = pd.array(appointed, dtype="boolean")
    out["incumbent_held_district_id"] = pd.array(held_ids, dtype="string")
    out["incumbent_changed_district"] = pd.array(changed, dtype="boolean")
    return out
