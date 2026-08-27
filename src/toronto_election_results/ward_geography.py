"""Sourced historical City and trustee ward geographic labels."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

CITY_WARD_COLUMNS = (
    "boundary_regime",
    "official_district_id",
    "geographic_name",
    "source_authority",
    "source_url",
    "source_date",
)

TRUSTEE_CROSSWALK_COLUMNS = (
    "board_id",
    "office_code",
    "represented_body",
    "display_name",
    "short_name",
    "boundary_regime",
    "ward_id",
    "official_geographic_name",
    "city_boundary_regime",
    "city_wards",
    "source_authority",
    "source_url",
    "source_date",
)

CITY_WARD_REGIMES = {
    "toronto_council_44_wards": frozenset(range(1, 45)),
    "toronto_council_25_wards": frozenset(range(1, 26)),
}

BOARD_CONTRACTS = {
    "tdsb": {
        "office_code": "3",
        "represented_body": "toronto_district_school_board",
        "display_name": "Toronto District School Board",
        "short_name": "TDSB",
    },
    "tcdsb": {
        "office_code": "4",
        "represented_body": "toronto_catholic_district_school_board",
        "display_name": "Toronto Catholic District School Board",
        "short_name": "TCDSB",
    },
    "viamonde": {
        "office_code": "5",
        "represented_body": "conseil_scolaire_viamonde",
        "display_name": "Conseil scolaire Viamonde",
        "short_name": "Viamonde",
    },
    "monavenir": {
        "office_code": "6",
        "represented_body": "conseil_scolaire_catholique_monavenir",
        "display_name": "Conseil scolaire catholique MonAvenir",
        "short_name": "MonAvenir",
    },
}


def _read_required_csv(path: str | Path, columns: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype="string", keep_default_na=False)
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"ward geography file is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, columns].copy()
    for column in columns:
        frame[column] = frame[column].str.strip()
    return frame


def _validate_source_rows(frame: pd.DataFrame, *, label: str) -> None:
    for row in frame.itertuples(index=False):
        if not row.source_authority or not row.source_date:
            raise ValueError(f"{label} requires source authority and date")
        parsed = urlparse(row.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{label} has invalid source URL: {row.source_url!r}")


def _integer(value: str, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"ward geography has invalid {field}: {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"ward geography has invalid {field}: {value!r}")
    return parsed


def load_city_ward_geographic_names(path: str | Path) -> pd.DataFrame:
    """Load sourced City ward names keyed by native boundary regime and number."""

    frame = _read_required_csv(path, CITY_WARD_COLUMNS)
    if frame.empty:
        raise ValueError("City ward geography cannot be empty")
    if (frame["geographic_name"] == "").any():
        raise ValueError("City ward geography requires a geographic name")
    unknown_regimes = sorted(set(frame["boundary_regime"]) - set(CITY_WARD_REGIMES))
    if unknown_regimes:
        raise ValueError(f"City ward geography has unknown regime: {unknown_regimes[0]}")
    frame["official_district_id"] = frame["official_district_id"].map(
        lambda value: _integer(value, field="City ward")
    )
    for row in frame.itertuples(index=False):
        if row.official_district_id not in CITY_WARD_REGIMES[row.boundary_regime]:
            raise ValueError(
                f"City ward {row.official_district_id} is invalid for {row.boundary_regime}"
            )
    if frame.duplicated(["boundary_regime", "official_district_id"]).any():
        raise ValueError("City ward geography repeats a boundary-regime/ward key")
    _validate_source_rows(frame, label="City ward geography")
    return frame.sort_values(
        ["boundary_regime", "official_district_id"], kind="stable"
    ).reset_index(drop=True)


def _city_ward_tuple(value: str) -> tuple[int, ...]:
    if not value:
        raise ValueError("trustee crosswalk requires component City wards")
    wards = tuple(_integer(part.strip(), field="component City ward") for part in value.split(";"))
    if len(wards) != len(set(wards)):
        raise ValueError("trustee crosswalk repeats a component City ward")
    return wards


def load_trustee_ward_crosswalks(path: str | Path, city_wards: pd.DataFrame) -> pd.DataFrame:
    """Load sourced trustee-to-City-ward crosswalks for every boundary regime."""

    frame = _read_required_csv(path, TRUSTEE_CROSSWALK_COLUMNS)
    if frame.empty:
        raise ValueError("trustee crosswalk cannot be empty")
    frame["ward_id"] = frame["ward_id"].map(lambda value: _integer(value, field="trustee ward"))
    frame["city_wards"] = frame["city_wards"].map(_city_ward_tuple)
    if frame.duplicated(["represented_body", "boundary_regime", "ward_id"]).any():
        raise ValueError("trustee crosswalk repeats a board/regime/ward key")

    city_keys = {
        (row.boundary_regime, row.official_district_id)
        for row in city_wards.itertuples(index=False)
    }
    for row in frame.itertuples(index=False):
        try:
            contract = BOARD_CONTRACTS[row.board_id]
        except KeyError as exc:
            raise ValueError(f"trustee crosswalk has unknown board: {row.board_id}") from exc
        for field in ("office_code", "represented_body", "display_name", "short_name"):
            if getattr(row, field) != contract[field]:
                raise ValueError(f"trustee crosswalk {row.board_id} has invalid {field}")
        expected_prefix = f"{row.board_id}-trustee-wards-"
        if not row.boundary_regime.startswith(expected_prefix):
            raise ValueError(f"trustee crosswalk {row.board_id} has invalid boundary regime")
        if row.city_boundary_regime not in CITY_WARD_REGIMES:
            raise ValueError(
                f"trustee crosswalk has unknown City regime: {row.city_boundary_regime}"
            )
        for ward in row.city_wards:
            if (row.city_boundary_regime, ward) not in city_keys:
                raise ValueError(
                    f"trustee crosswalk {row.board_id} Ward {row.ward_id} references "
                    f"unknown City ward {ward} in {row.city_boundary_regime}"
                )
    _validate_source_rows(frame, label="trustee crosswalk")
    return frame.sort_values(["board_id", "boundary_regime", "ward_id"], kind="stable").reset_index(
        drop=True
    )


def derive_trustee_ward_geography(
    crosswalk: pd.DataFrame, city_wards: pd.DataFrame
) -> pd.DataFrame:
    """Add official-or-derived geographic and number-plus-name trustee labels."""

    city_names = {
        (row.boundary_regime, row.official_district_id): row.geographic_name
        for row in city_wards.itertuples(index=False)
    }
    rows: list[dict[str, object]] = []
    for row in crosswalk.itertuples(index=False):
        official_name = row.official_geographic_name or None
        if official_name is None:
            ordered_names: list[str] = []
            for ward in row.city_wards:
                name = city_names[(row.city_boundary_regime, ward)]
                if name not in ordered_names:
                    ordered_names.append(name)
            geographic_name = "; ".join(ordered_names)
            provenance = "derived_from_city_wards"
        else:
            geographic_name = official_name
            provenance = "official"
        values = row._asdict()
        values.update(
            {
                "geographic_name": geographic_name,
                "district_display_name": f"Ward {row.ward_id} — {geographic_name}",
                "name_provenance": provenance,
            }
        )
        rows.append(values)
    return pd.DataFrame(rows)


def build_ward_geography_catalogue(
    city_wards: pd.DataFrame, trustee_crosswalk: pd.DataFrame
) -> pd.DataFrame:
    """Return the canonical 2003-present City and trustee district-name dimension."""

    city = city_wards.assign(
        represented_body="toronto_city_council",
        geographic_name=city_wards["geographic_name"],
        district_display_name=(
            "Ward "
            + city_wards["official_district_id"].astype(str)
            + " — "
            + city_wards["geographic_name"]
        ),
        name_provenance="official",
    )[
        [
            "represented_body",
            "boundary_regime",
            "official_district_id",
            "geographic_name",
            "district_display_name",
            "name_provenance",
        ]
    ]
    trustees = derive_trustee_ward_geography(trustee_crosswalk, city_wards).rename(
        columns={"ward_id": "official_district_id"}
    )[
        [
            "represented_body",
            "boundary_regime",
            "official_district_id",
            "geographic_name",
            "district_display_name",
            "name_provenance",
        ]
    ]
    catalogue = pd.concat([city, trustees], ignore_index=True)
    catalogue["official_district_id"] = catalogue["official_district_id"].astype(str)
    if (
        len(catalogue) != 332
        or catalogue.duplicated(
            ["represented_body", "boundary_regime", "official_district_id"]
        ).any()
    ):
        raise ValueError("ward geography catalogue must contain 332 unique district keys")
    return catalogue.sort_values(
        ["represented_body", "boundary_regime", "official_district_id"], kind="stable"
    ).reset_index(drop=True)


def enrich_electoral_districts(
    districts: pd.DataFrame, city_wards: pd.DataFrame, trustee_crosswalk: pd.DataFrame
) -> pd.DataFrame:
    """Attach canonical ward labels without changing source ``district_name`` values."""

    catalogue = build_ward_geography_catalogue(city_wards, trustee_crosswalk)
    out = districts.copy()
    out["_ward_key"] = out["official_district_id"].astype("string")
    council = out["represented_body"].eq("toronto_city_council")
    out.loc[council, "_ward_key"] = out.loc[council, "_ward_key"].str.removeprefix("ward-")
    enriched = out.merge(
        catalogue.rename(columns={"official_district_id": "_ward_key"}),
        on=["represented_body", "boundary_regime", "_ward_key"],
        how="left",
        validate="many_to_one",
    )

    observed = enriched.loc[enriched["district_display_name"].notna()]
    observed_keys = set(
        zip(
            observed["represented_body"],
            observed["boundary_regime"],
            observed["_ward_key"].astype(str),
            strict=True,
        )
    )
    catalogue_keys = set(
        zip(
            catalogue["represented_body"],
            catalogue["boundary_regime"],
            catalogue["official_district_id"],
            strict=True,
        )
    )
    missing = sorted(catalogue_keys - observed_keys)
    if missing:
        raise ValueError(f"canonical results are missing ward geography key: {missing[0]}")
    return enriched.drop(columns="_ward_key")
