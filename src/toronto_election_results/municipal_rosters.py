"""Evidence-backed City Council rosters for v2 Person incumbency.

The legacy composition extractor remains the source of who sat on Council, but its
fuzzy ``candidate_id`` layer is deliberately not used here.  A roster occurrence can
confirm a Candidacy-to-Person link only through an exact normalized display name and
the roster's event context.  Incumbency itself remains a same-body, same-office
comparison in :func:`toronto_election_results.identity.derive_incumbency`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .candidates import known_multiword_surnames, normalize_name
from .identity import validate_identity_tables
from .incumbency import RAW, REFERENCE, TERM_BEFORE_ELECTION, build_composition, council_surnames
from .schema import stable_id

_BODY = "toronto_city_council"
_REVIEWER = "municipal_rosters/v1"
_WHITESPACE = re.compile(r"\s+")

# Total offices in the last-holder snapshot: councillors plus one mayor.
_EXPECTED_GENERAL_ROSTER_SIZE = {
    2003: 45,
    2006: 45,
    2010: 45,
    2014: 45,
    2018: 45,
    2022: 26,
}

# The attendance/voting union deliberately catches late appointees, but a few
# departed members also survive its activity window.  City remuneration reports
# identify the replacement and the office that was filled for the rest of the term.
# Keeping this small correction table visible is safer than pretending activity is a
# seat identifier.
_LAST_HOLDER_REPLACEMENTS = {
    2014: [
        (
            "Doug Holyday",
            "Peter Leon",
            "https://www.toronto.ca/legdocs/mmis/2014/ex/bgrd/backgroundfile-68167.pdf",
            "appointed",
        ),
        (
            "Adam Vaughan",
            "Ceta Ramkhalawansingh",
            "https://www.toronto.ca/legdocs/mmis/2015/ex/bgrd/backgroundfile-78750.pdf",
            "appointed",
        ),
        (
            "Peter Milczyn",
            "James Maloney",
            "https://www.toronto.ca/legdocs/mmis/2015/ex/bgrd/backgroundfile-78750.pdf",
            "appointed",
        ),
    ],
    2018: [
        (
            "Pam McConnell",
            "Lucy Troisi",
            "https://www.toronto.ca/legdocs/mmis/2019/ex/bgrd/backgroundfile-131208.pdf",
            "appointed",
        ),
        (
            "Ron Moeser",
            "Jim Hart",
            "https://www.toronto.ca/legdocs/mmis/2019/ex/bgrd/backgroundfile-131208.pdf",
            "appointed",
        ),
        (
            "Shelley Carroll",
            "Jonathan Tsao",
            "https://www.toronto.ca/legdocs/mmis/2019/ex/bgrd/backgroundfile-131208.pdf",
            "appointed",
        ),
        (
            "Chin Lee",
            "Miganoush Megardichian",
            "https://www.toronto.ca/legdocs/mmis/2019/ex/bgrd/backgroundfile-131208.pdf",
            "appointed",
        ),
    ],
    2022: [
        (
            "Joe Cressy",
            "Joe Mihevc",
            "https://www.toronto.ca/legdocs/mmis/2023/ex/bgrd/backgroundfile-235964.pdf",
            "appointed",
        ),
        (
            "Kristyn Wong-Tam",
            "Robin Buxton Potts",
            "https://www.toronto.ca/legdocs/mmis/2023/ex/bgrd/backgroundfile-235964.pdf",
            "appointed",
        ),
        (
            "Michael Ford",
            "Rose Milczyn",
            "https://www.toronto.ca/legdocs/mmis/2023/ex/bgrd/backgroundfile-235964.pdf",
            "appointed",
        ),
    ],
}

_PEOPLE_COLUMNS = [
    "person_id",
    "preferred_name",
    "identity_status",
    "redirect_to_person_id",
    "created_release",
]
_LINK_COLUMNS = [
    "candidacy_id",
    "person_id",
    "link_status",
    "method",
    "evidence",
    "reviewer",
    "valid_from_release",
    "valid_to_release",
]
_TENURE_COLUMNS = [
    "office_tenure_id",
    "person_id",
    "represented_body",
    "office_type",
    "district_id",
    "started_on",
    "started_on_precision",
    "ended_on",
    "ended_on_precision",
    "entry_method",
    "source_authority",
    "source_detail",
]
_ROSTER_COLUMNS = [
    "event_id",
    "person_id",
    "represented_body",
    "office_type",
    "office_tenure_id",
    "roster_complete",
    "reference_date",
    "reference_date_rule",
    "source_detail",
]
_FLAG_COLUMNS = [
    "review_flag_id",
    "candidacy_id",
    "flag_type",
    "severity",
    "related_candidacy_ids",
    "detail",
    "release_id",
]


@dataclass(frozen=True)
class MunicipalRosterEvidence:
    """Updated identity registry plus municipal tenure and roster evidence."""

    people: pd.DataFrame
    candidacy_person_links: pd.DataFrame
    office_tenures: pd.DataFrame
    rosters: pd.DataFrame
    review_flags: pd.DataFrame


def _required(frame: pd.DataFrame, columns: set[str], table: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{table} is missing required columns: {', '.join(missing)}")


def _clean_text(value: object) -> str | None:
    if value is None or value is pd.NA or pd.isna(value):
        return None
    cleaned = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    return cleaned or None


def _exact_key(value: object) -> str:
    cleaned = _clean_text(value)
    if cleaned is None:
        raise ValueError("a roster or candidate name cannot be null or blank")
    # Diacritics and punctuation remain significant.  This is exact normalization,
    # not the legacy token-sorted or rapidfuzz identity key.
    return cleaned.casefold()


def _evidence(rule: str, **details: object) -> str:
    return json.dumps(
        {"rule": rule, **details}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _source_record(row: pd.Series) -> dict[str, object]:
    record: dict[str, object] = {"candidacy_id": str(row["candidacy_id"])}
    for column in ["source_authority", "source_resource", "source_detail"]:
        value = _clean_text(row.get(column))
        if value is not None:
            record[column] = value
    return record


def _candidate_display(raw_name: object, known_surnames: set[str]) -> str:
    raw = _clean_text(raw_name)
    if raw is None:
        raise ValueError("candidate_name_raw cannot be null or blank")
    # Toronto ballot files are documented as surname-first.  normalize_name only
    # parses that source grammar; identity is still an exact comparison afterward.
    return normalize_name(raw, known_surnames=known_surnames)[0]


def _composition_source(row: pd.Series, *, election_year: int) -> str:
    source = _clean_text(row.get("incumbent_source")) or "curated_composition"
    detail: dict[str, object] = {
        "rule": "last_valid_council_composition_before_general_election",
        "member_name": str(row["member_name"]),
        "source": source,
    }
    confidence = row.get("confidence")
    if confidence is not None and confidence is not pd.NA and not pd.isna(confidence):
        detail["source_confidence"] = float(confidence)
    arrival = _clean_text(row.get("arrival"))
    if arrival is not None:
        detail["entry_method"] = _entry_method(arrival)
    if source in {"city_attendance", "city_voting"}:
        term = TERM_BEFORE_ELECTION.get(election_year)
        collection = "attendance" if source == "city_attendance" else "voting"
        filename = (
            f"councillors-meeting-attendance-{term}.csv"
            if collection == "attendance"
            else f"member-voting-record-{term}.csv"
        )
        detail["source_file"] = f"data/raw/council/{collection}/{filename}"
    elif source == "wikipedia":
        detail["source_files"] = [
            "data/reference/roster_agent_a.txt",
            "data/reference/roster_agent_b.txt",
        ]
    reconciliation = _clean_text(row.get("reconciliation_source"))
    if reconciliation is not None:
        detail["last_holder_reconciliation"] = json.loads(reconciliation)
    return json.dumps(detail, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def reconcile_composition_last_holders(composition: pd.DataFrame) -> pd.DataFrame:
    """Remove superseded members from the legacy attendance/voting union.

    The legacy extractor has no seat column.  For a small number of end-of-term
    appointments it contains both the departed member and the final appointee.  City
    remuneration reports state the replacement chain, allowing an exact-name,
    source-backed correction without fuzzy matching.
    """

    if composition.empty:
        return composition.copy()
    _required(composition, {"election_year", "member_name"}, "composition")
    out = composition.copy()
    if "arrival" not in out:
        out["arrival"] = pd.NA
    if "reconciliation_source" not in out:
        out["reconciliation_source"] = pd.NA
    drop_indexes: set[object] = set()
    for year, replacements in _LAST_HOLDER_REPLACEMENTS.items():
        year_rows = pd.to_numeric(out["election_year"], errors="coerce").eq(year)
        for former, replacement, source, arrival in replacements:
            former_rows = year_rows & out["member_name"].map(_exact_key).eq(_exact_key(former))
            replacement_rows = year_rows & out["member_name"].map(_exact_key).eq(
                _exact_key(replacement)
            )
            if not replacement_rows.any():
                continue
            record = json.dumps(
                {
                    "former_member": former,
                    "last_holder": replacement,
                    "source": source,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            out.loc[replacement_rows, "reconciliation_source"] = record
            out.loc[replacement_rows, "arrival"] = arrival
            drop_indexes.update(out.index[former_rows])
    return out.drop(index=sorted(drop_indexes)).reset_index(drop=True)


def _entry_method(arrival: object) -> str:
    """Map the roster's arrival vocabulary to the public tenure vocabulary."""

    value = _clean_text(arrival)
    if value is None:
        return "unknown"
    normalized = value.casefold().replace("_", "-")
    if normalized in {"appointed", "appointment"}:
        return "appointment"
    if normalized in {"elected", "election", "by-election", "byelection"}:
        return "election"
    if normalized in {"acclaimed", "acclamation"}:
        return "acclamation"
    raise ValueError(f"unknown composition arrival method: {value!r}")


def _canonical_people(people: pd.DataFrame) -> dict[str, str]:
    redirects = dict(
        people.loc[
            people["redirect_to_person_id"].notna(),
            ["person_id", "redirect_to_person_id"],
        ].itertuples(index=False, name=None)
    )
    canonical: dict[str, str] = {}
    for person_id in people["person_id"].astype(str):
        current = person_id
        visited: set[str] = set()
        while current in redirects:
            if current in visited:
                raise ValueError(f"cyclic Person redirect involving {current!r}")
            visited.add(current)
            current = str(redirects[current])
        canonical[person_id] = current
    return canonical


def _prepare_registry(
    people: pd.DataFrame, links: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    people_out = people.copy()
    links_out = links.copy()
    for column in _PEOPLE_COLUMNS:
        if column not in people_out:
            people_out[column] = pd.NA
    for column in _LINK_COLUMNS:
        if column not in links_out:
            links_out[column] = pd.NA
    people_out = people_out[_PEOPLE_COLUMNS]
    links_out = links_out[_LINK_COLUMNS]
    validate_identity_tables(people_out, links_out)
    return people_out, links_out


def _prepare_candidacies(candidacies: pd.DataFrame, *, raw: Path) -> pd.DataFrame:
    _required(
        candidacies,
        {
            "candidacy_id",
            "event_id",
            "election_date",
            "election_type",
            "represented_body",
            "office_type",
            "candidate_name_raw",
            "elected",
        },
        "candidacies",
    )
    work = candidacies.loc[candidacies["represented_body"].eq(_BODY)].copy()
    if work.empty:
        return work
    if work["candidacy_id"].duplicated().any():
        duplicate = work.loc[work["candidacy_id"].duplicated(keep=False), "candidacy_id"].iloc[0]
        raise ValueError(f"duplicate municipal candidacy_id: {duplicate!r}")
    work["_date"] = pd.to_datetime(work["election_date"], errors="coerce")
    if work["_date"].isna().any():
        bad = work.loc[work["_date"].isna(), "election_date"].iloc[0]
        raise ValueError(f"invalid election_date: {bad!r}")
    try:
        work["elected"] = work["elected"].astype("boolean")
    except (TypeError, ValueError) as exc:
        raise ValueError("elected must contain booleans or nulls") from exc

    surnames = known_multiword_surnames(work["candidate_name_raw"])
    if raw.exists():
        try:
            surnames.update(council_surnames(raw=raw))
        except FileNotFoundError, KeyError:
            # A fixture may intentionally contain only the files needed by
            # build_composition; comma-form ballot names still provide safe parsing.
            pass
    work["_display_name"] = work["candidate_name_raw"].map(
        lambda value: _candidate_display(value, surnames)
    )
    work["_name_key"] = work["_display_name"].map(_exact_key)
    return work.sort_values(["_date", "candidacy_id"], kind="stable").reset_index(drop=True)


def build_municipal_roster_evidence(
    candidacies: pd.DataFrame,
    people: pd.DataFrame,
    candidacy_person_links: pd.DataFrame,
    *,
    release_id: str,
    composition: pd.DataFrame | None = None,
    reference: Path = REFERENCE,
    raw: Path = RAW,
) -> MunicipalRosterEvidence:
    """Build auditable Council roster snapshots and confirm roster-backed identities.

    General-election snapshots use ``build_composition`` and are complete.  A
    councillor by-election snapshot contains certified winners since the latest
    general election, but remains incomplete because appointments and departures
    are not comprehensively established.  A mayoral by-election uses the last
    certified mayoral holder and is complete for that single office.

    Exact normalized name by itself never changes a link.  Confirmation occurs only
    while processing a named member of an event-scoped roster, and the evidence JSON
    retains both the roster record and official Candidacy source.
    """

    release = _clean_text(release_id)
    if release is None:
        raise ValueError("release_id cannot be null or blank")
    people_out, links_out = _prepare_registry(people, candidacy_person_links)
    work = _prepare_candidacies(candidacies, raw=raw)
    if work.empty:
        return MunicipalRosterEvidence(
            people_out.reset_index(drop=True),
            links_out.reset_index(drop=True),
            pd.DataFrame(columns=_TENURE_COLUMNS),
            pd.DataFrame(columns=_ROSTER_COLUMNS),
            pd.DataFrame(columns=_FLAG_COLUMNS),
        )

    composition_supplied = composition is not None
    if composition is None:
        composition_work = build_composition(reference=reference, raw=raw)
    else:
        composition_work = composition.copy()
    if not composition_work.empty:
        _required(
            composition_work,
            {"election_year", "member_name", "office", "incumbent_source", "confidence"},
            "composition",
        )
        composition_work = reconcile_composition_last_holders(composition_work)

    tenure_rows: list[dict[str, object]] = []
    roster_rows: list[dict[str, object]] = []
    flag_rows: list[dict[str, object]] = []
    roster_people_by_name: dict[str, set[str]] = {}

    def flag(
        *,
        event_id: object,
        candidacy_id: object = pd.NA,
        flag_type: str,
        severity: str,
        related: list[str] | None = None,
        detail: str,
    ) -> None:
        related_ids = sorted(related or [])
        candidate_component = "none" if pd.isna(candidacy_id) else str(candidacy_id)
        flag_rows.append(
            {
                "review_flag_id": stable_id(
                    "irf",
                    "municipal_roster",
                    release,
                    str(event_id),
                    candidate_component,
                    flag_type,
                    json.dumps(related_ids, separators=(",", ":")),
                ),
                "candidacy_id": candidacy_id,
                "flag_type": flag_type,
                "severity": severity,
                "related_candidacy_ids": json.dumps(related_ids, separators=(",", ":")),
                "detail": detail,
                "release_id": release,
            }
        )

    def canonical_map() -> dict[str, str]:
        return _canonical_people(people_out)

    def active_links(candidacy_id: str, *, status: str | None = None) -> pd.DataFrame:
        selected = links_out.loc[
            links_out["candidacy_id"].eq(candidacy_id) & links_out["valid_to_release"].isna()
        ]
        return selected if status is None else selected.loc[selected["link_status"].eq(status)]

    def linked_person(candidacy_id: str, *, include_proposed: bool) -> str | None:
        statuses = ["confirmed", "proposed"] if include_proposed else ["confirmed"]
        selected = active_links(candidacy_id)
        selected = selected.loc[
            selected["link_status"].isin(statuses) & selected["person_id"].notna()
        ]
        if selected.empty:
            return None
        canonical = canonical_map()
        if include_proposed:
            municipal_candidacy_ids = set(work["candidacy_id"].astype(str))
            municipal_confirmed = links_out.loc[
                links_out["valid_to_release"].isna()
                & links_out["link_status"].eq("confirmed")
                & links_out["candidacy_id"].isin(municipal_candidacy_ids)
                & links_out["person_id"].notna(),
                "person_id",
            ]
            municipal_people = {
                canonical.get(str(person_id), str(person_id)) for person_id in municipal_confirmed
            }
            proposed_without_city_evidence = selected["link_status"].eq("proposed") & ~selected[
                "person_id"
            ].map(lambda value: canonical.get(str(value), str(value))).isin(municipal_people)
            selected = selected.loc[~proposed_without_city_evidence]
            if selected.empty:
                return None
        person_ids = {
            canonical.get(str(person_id), str(person_id)) for person_id in selected["person_id"]
        }
        return next(iter(person_ids)) if len(person_ids) == 1 else None

    def create_person(*, anchor: str, preferred_name: str) -> str:
        nonlocal people_out
        person_id = stable_id("per", "municipal_roster", anchor)
        if not people_out["person_id"].eq(person_id).any():
            people_out = pd.concat(
                [
                    people_out,
                    pd.DataFrame(
                        [
                            {
                                "person_id": person_id,
                                "preferred_name": preferred_name,
                                "identity_status": "active",
                                "redirect_to_person_id": pd.NA,
                                "created_release": release,
                            }
                        ],
                        columns=_PEOPLE_COLUMNS,
                    ),
                ],
                ignore_index=True,
            )
        return person_id

    def redirect_person(
        *,
        losing_person_id: str,
        canonical_person_id: str,
        event_id: str,
        candidacy_id: str,
        roster_source: str,
    ) -> str:
        """Merge a bootstrap singleton under stronger roster continuity evidence."""

        canonical = canonical_map()
        losing = canonical.get(losing_person_id, losing_person_id)
        winner = canonical.get(canonical_person_id, canonical_person_id)
        if losing == winner:
            return winner
        losing_rows = people_out["person_id"].eq(losing)
        winning_rows = people_out["person_id"].eq(winner)
        if int(losing_rows.sum()) != 1 or int(winning_rows.sum()) != 1:
            raise ValueError("a municipal Person redirect must have unique registry endpoints")
        if people_out.loc[winning_rows, "identity_status"].item() != "active":
            raise ValueError("a municipal Person redirect target must be active")
        people_out.loc[losing_rows, "identity_status"] = "deprecated"
        people_out.loc[losing_rows, "redirect_to_person_id"] = winner
        flag(
            event_id=event_id,
            candidacy_id=candidacy_id,
            flag_type="municipal_roster_person_redirect",
            severity="info",
            related=[candidacy_id],
            detail=_evidence(
                "roster_exact_name_resolves_bootstrap_singleton_conflict",
                losing_person_id=losing,
                canonical_person_id=winner,
                roster=json.loads(roster_source),
            ),
        )
        return winner

    def confirm_link(
        candidacy: pd.Series,
        person_id: str,
        *,
        event_id: str,
        roster_source: str,
    ) -> bool:
        nonlocal links_out
        candidacy_id = str(candidacy["candidacy_id"])
        confirmed = active_links(candidacy_id, status="confirmed")
        canonical = canonical_map()
        confirmed_people = {
            canonical.get(str(value), str(value)) for value in confirmed["person_id"].dropna()
        }
        canonical_person = canonical.get(person_id, person_id)
        if confirmed_people and confirmed_people != {canonical_person}:
            # Bootstrap source-occurrence anchors are intentionally conservative:
            # formatting drift can create two singleton People.  Exact identity in
            # an authoritative event roster is stronger continuity evidence, so the
            # later singleton redirects to the roster/prior-election Person.
            for losing_person in sorted(confirmed_people - {canonical_person}):
                canonical_person = redirect_person(
                    losing_person_id=losing_person,
                    canonical_person_id=canonical_person,
                    event_id=event_id,
                    candidacy_id=candidacy_id,
                    roster_source=roster_source,
                )
            confirmed_people = {canonical_person}

        # Preserve the alias-valued link as closed history and publish a new active
        # link to the canonical Person.  This makes the correction explicit to
        # consumers that validate link pairs without following Person redirects.
        active_for_candidate = (
            links_out["candidacy_id"].eq(candidacy_id) & links_out["valid_to_release"].isna()
        )
        alias_confirmed = (
            active_for_candidate
            & links_out["link_status"].eq("confirmed")
            & ~links_out["person_id"].eq(canonical_person)
        )
        had_alias_correction = bool(alias_confirmed.any())
        close = active_for_candidate & (~links_out["link_status"].eq("confirmed") | alias_confirmed)
        links_out.loc[close, "valid_to_release"] = release
        canonical_confirmed = (
            active_for_candidate
            & links_out["valid_to_release"].isna()
            & links_out["link_status"].eq("confirmed")
            & links_out["person_id"].eq(canonical_person)
        )
        if canonical_confirmed.any():
            return True

        links_out = pd.concat(
            [
                links_out,
                pd.DataFrame(
                    [
                        {
                            "candidacy_id": candidacy_id,
                            "person_id": canonical_person,
                            "link_status": "confirmed",
                            "method": (
                                "municipal_authoritative_roster_person_correction"
                                if had_alias_correction
                                else "municipal_authoritative_roster_exact_name"
                            ),
                            "evidence": _evidence(
                                "exact_normalized_name_in_authoritative_event_roster",
                                roster=json.loads(roster_source),
                                candidacy=_source_record(candidacy),
                                represented_body=_BODY,
                            ),
                            "reviewer": _REVIEWER,
                            "valid_from_release": release,
                            "valid_to_release": pd.NA,
                        }
                    ],
                    columns=_LINK_COLUMNS,
                ),
            ],
            ignore_index=True,
        )
        return True

    def person_for_candidacy(
        candidacy: pd.Series, *, event_id: str, roster_source: str, member_name: str
    ) -> str:
        candidacy_id = str(candidacy["candidacy_id"])
        person_id = linked_person(candidacy_id, include_proposed=True)
        if person_id is None:
            person_id = create_person(
                anchor=f"candidacy:{candidacy_id}", preferred_name=member_name
            )
        confirm_link(
            candidacy,
            person_id,
            event_id=event_id,
            roster_source=roster_source,
        )
        return person_id

    def exact_current_matches(event_group: pd.DataFrame, name_key: str) -> pd.DataFrame:
        # Identity may cross offices; office is deliberately applied only by
        # derive_incumbency after the Person link is established.
        return event_group.loc[event_group["_name_key"].eq(name_key)]

    def confirm_current_match(
        event_group: pd.DataFrame,
        *,
        name_key: str,
        person_id: str,
        roster_source: str,
    ) -> None:
        matches = exact_current_matches(event_group, name_key)
        event_id = str(event_group["event_id"].iloc[0])
        if len(matches) == 1:
            confirm_link(
                matches.iloc[0],
                person_id,
                event_id=event_id,
                roster_source=roster_source,
            )
        elif len(matches) > 1:
            ids = sorted(matches["candidacy_id"].astype(str))
            flag(
                event_id=event_id,
                flag_type="ambiguous_event_roster_name",
                severity="error",
                related=ids,
                detail=(
                    "More than one Candidacy in the event has the roster member's exact "
                    "normalized name; none was linked from the roster."
                ),
            )

    def latest_prior_elected(name_key: str, before: pd.Timestamp) -> pd.DataFrame:
        candidates = work.loc[
            work["_date"].lt(before) & work["_name_key"].eq(name_key) & work["elected"].eq(True)
        ]
        if candidates.empty:
            return candidates
        return candidates.loc[candidates["_date"].eq(candidates["_date"].max())]

    def append_member(
        *,
        event_id: str,
        reference_date: object,
        person_id: str,
        office_type: str,
        district_id: object,
        started_on: object,
        started_on_precision: str,
        ended_on_precision: str,
        entry_method: str,
        reference_date_rule: str,
        roster_complete: bool,
        source_detail: str,
    ) -> None:
        tenure_id = stable_id("ten", "municipal_roster", event_id, _BODY, office_type, person_id)
        tenure_rows.append(
            {
                "office_tenure_id": tenure_id,
                "person_id": person_id,
                "represented_body": _BODY,
                "office_type": office_type,
                "district_id": district_id,
                "started_on": started_on,
                "started_on_precision": started_on_precision,
                "ended_on": reference_date,
                "ended_on_precision": ended_on_precision,
                "entry_method": entry_method,
                "source_authority": "City of Toronto",
                "source_detail": source_detail,
            }
        )
        roster_rows.append(
            {
                "event_id": event_id,
                "person_id": person_id,
                "represented_body": _BODY,
                "office_type": office_type,
                "office_tenure_id": tenure_id,
                "roster_complete": roster_complete,
                "reference_date": reference_date,
                "reference_date_rule": reference_date_rule,
                "source_detail": source_detail,
            }
        )

    def append_empty_scope(
        *,
        event_id: str,
        reference_date: object,
        office_type: str,
        roster_complete: bool,
        reference_date_rule: str,
        source_detail: str,
    ) -> None:
        roster_rows.append(
            {
                "event_id": event_id,
                "person_id": pd.NA,
                "represented_body": _BODY,
                "office_type": office_type,
                "office_tenure_id": pd.NA,
                "roster_complete": roster_complete,
                "reference_date": reference_date,
                "reference_date_rule": reference_date_rule,
                "source_detail": source_detail,
            }
        )

    def resolve_roster_person(
        *,
        member_name: str,
        name_key: str,
        prior: pd.DataFrame,
        event_group: pd.DataFrame,
        roster_source: str,
    ) -> tuple[str, pd.Series | None]:
        event_id = str(event_group["event_id"].iloc[0])
        if len(prior) == 1:
            anchor = prior.iloc[0]
            return (
                person_for_candidacy(
                    anchor,
                    event_id=event_id,
                    roster_source=roster_source,
                    member_name=member_name,
                ),
                anchor,
            )
        if len(prior) > 1:
            flag(
                event_id=event_id,
                flag_type="ambiguous_latest_elected_roster_identity",
                severity="error",
                related=sorted(prior["candidacy_id"].astype(str)),
                detail=(
                    f"Roster member {member_name!r} has multiple officially elected exact-name "
                    "Candidacies on the most recent prior date."
                ),
            )

        matches = exact_current_matches(event_group, name_key)
        if len(matches) == 1:
            anchor = matches.iloc[0]
            return (
                person_for_candidacy(
                    anchor,
                    event_id=event_id,
                    roster_source=roster_source,
                    member_name=member_name,
                ),
                None,
            )

        prior_roster_people = roster_people_by_name.get(name_key, set())
        if len(prior_roster_people) == 1:
            return next(iter(prior_roster_people)), None
        person_id = create_person(
            anchor=f"roster:{event_id}:{name_key}", preferred_name=member_name
        )
        return person_id, None

    for event_id, event_group in work.groupby("event_id", sort=False):
        event_dates = event_group["_date"].drop_duplicates()
        event_types = event_group["election_type"].drop_duplicates()
        if len(event_dates) != 1 or len(event_types) != 1:
            raise ValueError(f"date/type is inconsistent in municipal event {event_id!r}")
        event_date = event_dates.iloc[0]
        event_type = str(event_types.iloc[0])
        event_year = int(event_date.year)
        offices = set(event_group["office_type"].astype(str))

        if event_type == "general":
            if composition_work.empty:
                continue
            year_composition = composition_work.loc[
                pd.to_numeric(composition_work["election_year"], errors="coerce").eq(event_year)
            ]
            if year_composition.empty:
                flag(
                    event_id=event_id,
                    flag_type="missing_general_election_composition",
                    severity="error",
                    detail=f"No council composition was available for the {event_year} general election.",
                )
                continue

            members_before = len(roster_rows)
            ambiguous_member = False
            for _, member in year_composition.iterrows():
                member_name = _clean_text(member["member_name"])
                if member_name is None:
                    flag(
                        event_id=event_id,
                        flag_type="blank_composition_member_name",
                        severity="error",
                        detail="A general-election composition row has no member name.",
                    )
                    continue
                name_key = _exact_key(member_name)
                prior = latest_prior_elected(name_key, event_date)
                ambiguous_member = ambiguous_member or len(prior) > 1
                source_office = _clean_text(member["office"])
                if source_office not in {"mayor", "councillor"}:
                    raise ValueError(f"unknown composition office: {source_office!r}")
                office_type = (
                    str(prior.iloc[0]["office_type"]) if len(prior) == 1 else source_office
                )
                roster_source = _composition_source(member, election_year=event_year)
                person_id, anchor = resolve_roster_person(
                    member_name=member_name,
                    name_key=name_key,
                    prior=prior,
                    event_group=event_group,
                    roster_source=roster_source,
                )
                confirm_current_match(
                    event_group,
                    name_key=name_key,
                    person_id=person_id,
                    roster_source=roster_source,
                )
                roster_people_by_name.setdefault(name_key, set()).add(person_id)
                append_member(
                    event_id=str(event_id),
                    reference_date=event_date.date(),
                    person_id=person_id,
                    office_type=office_type,
                    district_id=anchor.get("district_id", pd.NA) if anchor is not None else pd.NA,
                    started_on=(anchor["_date"].date() if anchor is not None else pd.NA),
                    started_on_precision=("election_date" if anchor is not None else "unknown"),
                    ended_on_precision="at_or_after_reference",
                    entry_method=(
                        "election" if anchor is not None else _entry_method(member.get("arrival"))
                    ),
                    reference_date_rule="last_valid_roster_before_event",
                    roster_complete=False,
                    source_detail=roster_source,
                )

            new_members = roster_rows[members_before:]
            office_counts = {
                office_type: sum(row["office_type"] == office_type for row in new_members)
                for office_type in ("mayor", "councillor")
            }
            duplicate_people = len(
                {
                    (row["office_type"], row["person_id"])
                    for row in new_members
                    if not pd.isna(row["person_id"])
                }
            ) != len(new_members)
            if composition_supplied:
                declared_complete = False
                if "roster_complete" in year_composition:
                    try:
                        declared_complete = bool(
                            year_composition["roster_complete"]
                            .astype("boolean")
                            .fillna(False)
                            .all()
                        )
                    except (TypeError, ValueError) as exc:
                        raise ValueError("composition.roster_complete must be boolean") from exc
                expected_shape = all(
                    office_counts[office_type] > 0
                    for office_type in offices & {"mayor", "councillor"}
                )
            else:
                expected = _EXPECTED_GENERAL_ROSTER_SIZE.get(event_year)
                declared_complete = expected is not None
                expected_shape = (
                    expected is not None
                    and len(new_members) == expected
                    and office_counts["mayor"] == 1
                    and office_counts["councillor"] == expected - 1
                )
            general_complete = bool(
                declared_complete
                and expected_shape
                and not ambiguous_member
                and not duplicate_people
            )
            for row in new_members:
                row["roster_complete"] = general_complete

            if not general_complete:
                flag(
                    event_id=event_id,
                    flag_type="incomplete_general_election_roster",
                    severity="error",
                    detail=_evidence(
                        "general_roster_cannot_prove_absence",
                        election_year=event_year,
                        source_declared_complete=declared_complete,
                        roster_members=len(new_members),
                        mayor_members=office_counts["mayor"],
                        councillor_members=office_counts["councillor"],
                        ambiguous_member=ambiguous_member,
                        duplicate_people=duplicate_people,
                    ),
                )

            for office_type in sorted(offices & {"mayor", "councillor"}):
                if not any(row["office_type"] == office_type for row in new_members):
                    detail = _evidence(
                        "composition_contains_no_member_for_office",
                        election_year=event_year,
                        office_type=office_type,
                    )
                    append_empty_scope(
                        event_id=str(event_id),
                        reference_date=event_date.date(),
                        office_type=office_type,
                        roster_complete=False,
                        reference_date_rule="last_valid_roster_before_event",
                        source_detail=detail,
                    )
            continue

        if event_type != "by_election":
            continue

        # The latest certified councillor winners are useful identity context even
        # for a mayor-only by-election: a sitting councillor who runs for mayor must
        # resolve to the same Person before same-office incumbency can prove False.
        # This context is not promoted to a complete councillor roster.
        prior_generals = work.loc[
            work["_date"].lt(event_date)
            & work["election_type"].eq("general")
            & work["office_type"].eq("councillor")
        ]
        latest_general_date = prior_generals["_date"].max() if not prior_generals.empty else pd.NaT
        known_winners = work.loc[
            work["_date"].lt(event_date)
            & work["office_type"].eq("councillor")
            & work["elected"].eq(True)
        ]
        if not pd.isna(latest_general_date):
            known_winners = known_winners.loc[known_winners["_date"].ge(latest_general_date)]
        if "district_id" in known_winners:
            known_winners = known_winners.loc[known_winners["district_id"].notna()]
            latest_by_district = known_winners.groupby("district_id", sort=False)[
                "_date"
            ].transform("max")
            known_winners = known_winners.loc[known_winners["_date"].eq(latest_by_district)]

        resolved_councillor_holders: list[tuple[pd.Series, str, str]] = []
        for _, holder in known_winners.iterrows():
            source = _evidence(
                "certified_winner_since_latest_general_in_incomplete_by_election_roster",
                prior_candidacy=_source_record(holder),
                event_id=str(event_id),
            )
            person_id = person_for_candidacy(
                holder,
                event_id=str(event_id),
                roster_source=source,
                member_name=str(holder["_display_name"]),
            )
            confirm_current_match(
                event_group,
                name_key=str(holder["_name_key"]),
                person_id=person_id,
                roster_source=source,
            )
            resolved_councillor_holders.append((holder, person_id, source))

        if "mayor" in offices:
            prior_mayors = work.loc[
                work["_date"].lt(event_date)
                & work["office_type"].eq("mayor")
                & work["elected"].eq(True)
            ]
            if not prior_mayors.empty:
                prior_mayors = prior_mayors.loc[
                    prior_mayors["_date"].eq(prior_mayors["_date"].max())
                ]
            if len(prior_mayors) == 1:
                holder = prior_mayors.iloc[0]
                source = _evidence(
                    "last_certified_mayoral_holder_before_by_election",
                    prior_candidacy=_source_record(holder),
                    event_id=str(event_id),
                )
                person_id = person_for_candidacy(
                    holder,
                    event_id=str(event_id),
                    roster_source=source,
                    member_name=str(holder["_display_name"]),
                )
                confirm_current_match(
                    event_group,
                    name_key=str(holder["_name_key"]),
                    person_id=person_id,
                    roster_source=source,
                )
                append_member(
                    event_id=str(event_id),
                    reference_date=event_date.date(),
                    person_id=person_id,
                    office_type="mayor",
                    district_id=holder.get("district_id", pd.NA),
                    started_on=holder["_date"].date(),
                    started_on_precision="election_date",
                    ended_on_precision="before_or_at_reference",
                    entry_method="election",
                    reference_date_rule="last_person_in_role_before_event",
                    roster_complete=True,
                    source_detail=source,
                )
            else:
                related = sorted(prior_mayors["candidacy_id"].astype(str))
                flag(
                    event_id=event_id,
                    flag_type="missing_or_ambiguous_last_mayoral_holder",
                    severity="error",
                    related=related,
                    detail="A unique last certified mayoral holder could not be established.",
                )
                append_empty_scope(
                    event_id=str(event_id),
                    reference_date=event_date.date(),
                    office_type="mayor",
                    roster_complete=False,
                    reference_date_rule="last_person_in_role_before_event",
                    source_detail=_evidence(
                        "last_mayoral_holder_unresolved", event_id=str(event_id)
                    ),
                )

        if "councillor" in offices:
            added = 0
            for holder, person_id, source in resolved_councillor_holders:
                append_member(
                    event_id=str(event_id),
                    reference_date=event_date.date(),
                    person_id=person_id,
                    office_type="councillor",
                    district_id=holder.get("district_id", pd.NA),
                    started_on=holder["_date"].date(),
                    started_on_precision="election_date",
                    ended_on_precision="at_or_after_reference",
                    entry_method="election",
                    reference_date_rule="known_elected_holders_before_by_election",
                    roster_complete=False,
                    source_detail=source,
                )
                added += 1
            if not added:
                append_empty_scope(
                    event_id=str(event_id),
                    reference_date=event_date.date(),
                    office_type="councillor",
                    roster_complete=False,
                    reference_date_rule="known_elected_holders_before_by_election",
                    source_detail=_evidence(
                        "no_known_elected_councillor_holders", event_id=str(event_id)
                    ),
                )

    tenures = pd.DataFrame(tenure_rows, columns=_TENURE_COLUMNS)
    rosters = pd.DataFrame(roster_rows, columns=_ROSTER_COLUMNS)
    flags = pd.DataFrame(flag_rows, columns=_FLAG_COLUMNS)
    final_canonical = _canonical_people(people_out)
    if not tenures.empty:
        tenures["person_id"] = tenures["person_id"].map(
            lambda value: final_canonical.get(str(value), value) if not pd.isna(value) else value
        )
    if not rosters.empty:
        rosters["person_id"] = rosters["person_id"].map(
            lambda value: final_canonical.get(str(value), value) if not pd.isna(value) else value
        )
        scope_columns = ["event_id", "represented_body", "office_type"]
        duplicate_canonical = rosters["person_id"].notna() & rosters.duplicated(
            [*scope_columns, "person_id"], keep=False
        )
        for scope, duplicates in rosters.loc[duplicate_canonical].groupby(
            scope_columns, sort=False, dropna=False
        ):
            event_id, _, office_type = scope
            rosters.loc[
                rosters[scope_columns].eq(pd.Series(scope, index=scope_columns)).all(axis=1),
                "roster_complete",
            ] = False
            flag(
                event_id=event_id,
                flag_type="duplicate_canonical_person_in_roster",
                severity="error",
                detail=(
                    f"Person redirects collapsed {len(duplicates)} {office_type} roster rows; "
                    "the scope cannot prove absence."
                ),
            )
        flags = pd.DataFrame(flag_rows, columns=_FLAG_COLUMNS)
    if not tenures.empty:
        tenures = tenures.drop_duplicates("office_tenure_id", keep="first")
    if not rosters.empty:
        member_rows = rosters["person_id"].notna()
        rosters = pd.concat(
            [
                rosters.loc[member_rows].drop_duplicates(
                    ["event_id", "represented_body", "office_type", "person_id"], keep="first"
                ),
                rosters.loc[~member_rows],
            ],
            ignore_index=True,
        )
        # A populated scope does not also need an empty marker row.
        populated = set(
            rosters.loc[rosters["person_id"].notna(), ["event_id", "office_type"]].itertuples(
                index=False, name=None
            )
        )
        keep = rosters["person_id"].notna() | ~rosters[["event_id", "office_type"]].apply(
            tuple, axis=1
        ).isin(populated)
        rosters = rosters.loc[keep].copy()
        rosters["roster_complete"] = rosters["roster_complete"].astype("boolean")
        rosters = rosters.sort_values(
            ["reference_date", "event_id", "office_type", "person_id"],
            kind="stable",
            na_position="last",
        ).reset_index(drop=True)
    if not flags.empty:
        flags = flags.drop_duplicates("review_flag_id").sort_values(
            ["severity", "flag_type", "candidacy_id"], kind="stable", na_position="last"
        )

    people_out["person_id"] = people_out["person_id"].astype("string")
    people_out["redirect_to_person_id"] = people_out["redirect_to_person_id"].astype("string")
    links_out["person_id"] = links_out["person_id"].astype("string")
    links_out["valid_to_release"] = links_out["valid_to_release"].astype("string")
    validate_identity_tables(people_out, links_out)
    return MunicipalRosterEvidence(
        people_out.reset_index(drop=True),
        links_out.reset_index(drop=True),
        tenures.reset_index(drop=True),
        rosters.reset_index(drop=True),
        flags.reset_index(drop=True),
    )
