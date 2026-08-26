"""Audited corrections for identities that cross election data silos.

This module deliberately does not perform record linkage.  Every merge is an
enumerated assertion about exact candidacy occurrences and carries official-source
evidence.  A repeated name that is not enumerated is never touched.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, replace

import pandas as pd

from .identity import validate_identity_tables
from .schema import stable_id


@dataclass(frozen=True)
class CandidacyLocator:
    """An exact occurrence covered by a curated identity assertion."""

    event_id: str
    represented_body: str
    office_type: str
    candidate_name: str
    district_id: str | None = None
    candidacy_id: str | None = None


@dataclass(frozen=True)
class CuratedIdentityAssertion:
    """Officially evidenced claim that enumerated candidacies are one Person."""

    assertion_id: str
    preferred_name: str
    occurrences: tuple[CandidacyLocator, ...]
    evidence_urls: tuple[str, ...]
    rationale: str
    registry_person_ids: tuple[str, ...] = ()
    canonical_person_id: str | None = None


@dataclass(frozen=True)
class IdentityCuration:
    """Corrected registry plus a compact, publishable assertion audit."""

    people: pd.DataFrame
    candidacy_person_links: pd.DataFrame
    assertions: pd.DataFrame


@dataclass(frozen=True)
class CanonicalPersonEvidence:
    """Tenure and roster tables rewritten through active Person redirects."""

    office_tenures: pd.DataFrame
    rosters: pd.DataFrame


def _name_key(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).casefold()


def _active(links: pd.DataFrame) -> pd.Series:
    return links["valid_to_release"].isna()


def _canonical_map(people: pd.DataFrame) -> dict[str, str]:
    redirects = dict(
        people.loc[
            people["redirect_to_person_id"].notna(),
            ["person_id", "redirect_to_person_id"],
        ].itertuples(index=False, name=None)
    )
    resolved: dict[str, str] = {}
    for person_id in people["person_id"]:
        current = person_id
        visited: set[str] = set()
        while current in redirects:
            if current in visited:
                raise ValueError(f"cyclic Person redirect involving {current!r}")
            visited.add(current)
            current = redirects[current]
        resolved[person_id] = current
    return resolved


def _locate(candidacies: pd.DataFrame, locator: CandidacyLocator) -> pd.Series:
    mask = (
        candidacies["event_id"].eq(locator.event_id)
        & candidacies["represented_body"].eq(locator.represented_body)
        & candidacies["office_type"].eq(locator.office_type)
    )
    if locator.candidacy_id is None:
        mask &= candidacies["candidate_name"].map(_name_key).eq(_name_key(locator.candidate_name))
    else:
        mask &= candidacies["candidacy_id"].eq(locator.candidacy_id)
    if locator.district_id is not None:
        mask &= candidacies["district_id"].eq(locator.district_id)
    matches = candidacies.loc[mask]
    if len(matches) != 1:
        raise ValueError(
            f"curated locator {locator!r} matched {len(matches)} candidacies; expected 1"
        )
    return matches.iloc[0]


def _assert_valid(assertion: CuratedIdentityAssertion) -> None:
    if not assertion.assertion_id.strip():
        raise ValueError("curated assertion_id cannot be blank")
    if not assertion.occurrences:
        raise ValueError("a curated identity assertion must enumerate a candidacy occurrence")
    if len(assertion.occurrences) + len(assertion.registry_person_ids) < 2:
        raise ValueError(
            "a curated identity assertion must enumerate at least two registry entities"
        )
    if len(assertion.registry_person_ids) != len(set(assertion.registry_person_ids)):
        raise ValueError("an assertion cannot enumerate a registry Person more than once")
    if (
        assertion.canonical_person_id is not None
        and assertion.canonical_person_id not in assertion.registry_person_ids
    ):
        raise ValueError(
            "an explicitly canonical Person must also be enumerated in registry_person_ids"
        )
    if not assertion.rationale.strip():
        raise ValueError(f"assertion {assertion.assertion_id!r} has no rationale")
    if not assertion.evidence_urls or any(
        not url.startswith("https://") for url in assertion.evidence_urls
    ):
        raise ValueError(
            f"assertion {assertion.assertion_id!r} requires HTTPS official evidence URLs"
        )


def _new_person_row(
    people: pd.DataFrame,
    person_id: str,
    preferred_name: str,
    release_id: str,
) -> dict[str, object]:
    row = {column: pd.NA for column in people.columns}
    row.update(
        {
            "person_id": person_id,
            "preferred_name": preferred_name,
            "identity_status": "active",
            "redirect_to_person_id": pd.NA,
        }
    )
    if "created_release" in people.columns:
        row["created_release"] = release_id
    return row


def _curation_evidence(
    assertion: CuratedIdentityAssertion,
    source_rows: list[dict[str, object]],
) -> str:
    payload = {
        "assertion_id": assertion.assertion_id,
        "official_evidence_urls": list(assertion.evidence_urls),
        "rationale": assertion.rationale,
        "registry_person_ids": list(assertion.registry_person_ids),
        "canonical_person_id": assertion.canonical_person_id,
        "source_candidacies": source_rows,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def apply_curated_identity_assertions(
    candidacies: pd.DataFrame,
    people: pd.DataFrame,
    candidacy_person_links: pd.DataFrame,
    release_id: str,
    *,
    assertions: tuple[CuratedIdentityAssertion, ...] | None = None,
) -> IdentityCuration:
    """Apply explicit Person corrections while retaining append-only link history.

    An assertion may explicitly preserve one enumerated registry Person as canonical;
    otherwise the first enumerated occurrence with an active confirmed link supplies
    the canonical Person ID.  If none is linked, the assertion receives a
    deterministic ID.  Every losing Person remains visible as a deprecated redirect,
    and every superseded link is closed at ``release_id`` before a confirmed curated
    link is appended.  Non-enumerated same-name candidacies are untouched.
    """

    required_candidacy = {
        "candidacy_id",
        "event_id",
        "represented_body",
        "office_type",
        "candidate_name",
        "source_detail",
    }
    missing = sorted(required_candidacy - set(candidacies.columns))
    if missing:
        raise ValueError(f"candidacies is missing curation columns: {', '.join(missing)}")
    if not str(release_id).strip():
        raise ValueError("release_id cannot be blank")

    selected = DEFAULT_IDENTITY_ASSERTIONS if assertions is None else assertions
    assertion_ids = [assertion.assertion_id for assertion in selected]
    if len(assertion_ids) != len(set(assertion_ids)):
        raise ValueError("curated assertion_id values must be unique")

    people_out = people.copy()
    links_out = candidacy_person_links.copy()
    validate_identity_tables(people_out, links_out)
    audit_rows: list[dict[str, object]] = []

    for assertion in selected:
        _assert_valid(assertion)
        located = [_locate(candidacies, locator) for locator in assertion.occurrences]
        candidacy_ids = [str(row["candidacy_id"]) for row in located]
        if len(candidacy_ids) != len(set(candidacy_ids)):
            raise ValueError(
                f"assertion {assertion.assertion_id!r} enumerates a candidacy more than once"
            )

        canonical = _canonical_map(people_out)
        active_confirmed = links_out.loc[
            _active(links_out)
            & links_out["link_status"].eq("confirmed")
            & links_out["candidacy_id"].isin(candidacy_ids)
            & links_out["person_id"].notna()
        ]
        ordered_people: list[str] = []
        for candidacy_id in candidacy_ids:
            for person_id in active_confirmed.loc[
                active_confirmed["candidacy_id"].eq(candidacy_id), "person_id"
            ]:
                resolved = canonical[str(person_id)]
                if resolved not in ordered_people:
                    ordered_people.append(resolved)
        for person_id in assertion.registry_person_ids:
            matches = people_out["person_id"].eq(person_id)
            if int(matches.sum()) != 1:
                raise ValueError(
                    f"assertion {assertion.assertion_id!r} registry Person "
                    f"{person_id!r} matched {int(matches.sum())} rows; expected 1"
                )
            resolved = canonical[person_id]
            if resolved not in ordered_people:
                ordered_people.append(resolved)

        if assertion.canonical_person_id is not None:
            canonical_person_id = assertion.canonical_person_id
        elif ordered_people:
            canonical_person_id = ordered_people[0]
        else:
            canonical_person_id = stable_id(
                "per", "curated_identity_assertion", assertion.assertion_id
            )
            people_out = pd.concat(
                [
                    people_out,
                    pd.DataFrame(
                        [
                            _new_person_row(
                                people_out,
                                canonical_person_id,
                                assertion.preferred_name,
                                release_id,
                            )
                        ]
                    ),
                ],
                ignore_index=True,
            )

        canonical = _canonical_map(people_out)
        losing_roots = {
            canonical[person_id]
            for person_id in ordered_people
            if canonical[person_id] != canonical_person_id
        }
        if assertion.canonical_person_id is not None:
            pinned_root = canonical[assertion.canonical_person_id]
            if pinned_root != canonical_person_id:
                losing_roots.add(pinned_root)
        losing_ids = {person_id for person_id, root in canonical.items() if root in losing_roots}
        losing_ids |= losing_roots
        losing_ids.discard(canonical_person_id)

        target_active_before = links_out.loc[
            _active(links_out) & links_out["candidacy_id"].isin(candidacy_ids)
        ]
        already_applied = bool(
            not losing_roots
            and len(target_active_before) == len(candidacy_ids)
            and target_active_before["candidacy_id"].nunique() == len(candidacy_ids)
            and target_active_before["link_status"].eq("confirmed").all()
            and target_active_before["person_id"].eq(canonical_person_id).all()
        )

        if losing_roots:
            root_mask = people_out["person_id"].isin(losing_roots)
            people_out.loc[root_mask, "identity_status"] = "deprecated"
            people_out.loc[root_mask, "redirect_to_person_id"] = canonical_person_id

        canonical_mask = people_out["person_id"].eq(canonical_person_id)
        people_out.loc[canonical_mask, "preferred_name"] = assertion.preferred_name
        people_out.loc[canonical_mask, "identity_status"] = "active"
        people_out.loc[canonical_mask, "redirect_to_person_id"] = pd.NA

        if already_applied:
            audit_rows.append(
                {
                    "assertion_id": assertion.assertion_id,
                    "preferred_name": assertion.preferred_name,
                    "canonical_person_id": canonical_person_id,
                    "candidacy_ids": json.dumps(candidacy_ids),
                    "redirected_person_ids": json.dumps([]),
                    "evidence_urls": json.dumps(list(assertion.evidence_urls)),
                    "release_id": release_id,
                }
            )
            continue

        source_rows = [
            {
                "candidacy_id": row["candidacy_id"],
                "event_id": row["event_id"],
                "represented_body": row["represented_body"],
                "office_type": row["office_type"],
                "candidate_name": row["candidate_name"],
                "source_detail": row["source_detail"],
            }
            for row in located
        ]
        evidence = _curation_evidence(assertion, source_rows)

        # Re-home active links to redirected identities, including candidacies not
        # explicitly listed here.  This prevents consumers from depending on a
        # deprecated Person while retaining the closed historical assertion.
        if losing_ids:
            losing_active_mask = _active(links_out) & links_out["person_id"].isin(losing_ids)
            losing_active = links_out.loc[losing_active_mask].copy()
            links_out.loc[losing_active_mask, "valid_to_release"] = release_id
            rehomed_rows: list[dict[str, object]] = []
            for old in losing_active.to_dict("records"):
                if old["candidacy_id"] in candidacy_ids:
                    continue
                old.update(
                    {
                        "person_id": canonical_person_id,
                        "valid_from_release": release_id,
                        "valid_to_release": pd.NA,
                    }
                )
                if old["link_status"] == "confirmed":
                    old.update(
                        {
                            "method": "curated_person_redirect",
                            "evidence": evidence,
                            "reviewer": "identity_curations/v1",
                        }
                    )
                rehomed_rows.append(old)
            if rehomed_rows:
                links_out = pd.concat(
                    [links_out, pd.DataFrame(rehomed_rows, columns=links_out.columns)],
                    ignore_index=True,
                )

        target_active = _active(links_out) & links_out["candidacy_id"].isin(candidacy_ids)
        links_out.loc[target_active, "valid_to_release"] = release_id
        curated_rows = [
            {
                "candidacy_id": candidacy_id,
                "person_id": canonical_person_id,
                "link_status": "confirmed",
                "method": "curated_official_cross_event_identity",
                "evidence": evidence,
                "reviewer": "identity_curations/v1",
                "valid_from_release": release_id,
                "valid_to_release": pd.NA,
            }
            for candidacy_id in candidacy_ids
        ]
        links_out = pd.concat(
            [links_out, pd.DataFrame(curated_rows, columns=links_out.columns)],
            ignore_index=True,
        )
        audit_rows.append(
            {
                "assertion_id": assertion.assertion_id,
                "preferred_name": assertion.preferred_name,
                "canonical_person_id": canonical_person_id,
                "candidacy_ids": json.dumps(candidacy_ids),
                "redirected_person_ids": json.dumps(sorted(losing_roots)),
                "evidence_urls": json.dumps(list(assertion.evidence_urls)),
                "release_id": release_id,
            }
        )

    # Nullable string dtypes keep comparisons with a newly created Person's null
    # redirect well-defined inside the shared registry validator.
    people_out["person_id"] = people_out["person_id"].astype("string")
    people_out["redirect_to_person_id"] = people_out["redirect_to_person_id"].astype("string")
    validate_identity_tables(people_out, links_out)
    return IdentityCuration(
        people=people_out,
        candidacy_person_links=links_out,
        assertions=pd.DataFrame(
            audit_rows,
            columns=[
                "assertion_id",
                "preferred_name",
                "canonical_person_id",
                "candidacy_ids",
                "redirected_person_ids",
                "evidence_urls",
                "release_id",
            ],
        ),
    )


def canonicalize_person_evidence(
    people: pd.DataFrame,
    office_tenures: pd.DataFrame,
    rosters: pd.DataFrame,
) -> CanonicalPersonEvidence:
    """Rewrite already-built evidence tables to canonical active Person IDs.

    Municipal roster construction can create a Person before later curation proves
    that the holder is an already-linked candidate.  Curation preserves that losing
    Person as a redirect; this function carries the same correction into the tenure
    and event-roster evidence so ``derive_incumbency`` compares canonical IDs on both
    sides.  Duplicate members caused by canonicalization fail closed.
    """

    required_people = {
        "person_id",
        "identity_status",
        "redirect_to_person_id",
    }
    missing_people = sorted(required_people - set(people.columns))
    if missing_people:
        raise ValueError(
            f"people is missing evidence-canonicalization columns: {', '.join(missing_people)}"
        )
    for frame, label, required in (
        (office_tenures, "office_tenures", {"office_tenure_id", "person_id"}),
        (
            rosters,
            "rosters",
            {
                "event_id",
                "represented_body",
                "office_type",
                "office_tenure_id",
                "person_id",
            },
        ),
    ):
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{label} is missing columns: {', '.join(missing)}")

    canonical = _canonical_map(people)
    active_people = set(people.loc[people["identity_status"].eq("active"), "person_id"].astype(str))

    def rewrite(frame: pd.DataFrame, label: str) -> pd.DataFrame:
        out = frame.copy()
        unknown = out["person_id"].notna() & ~out["person_id"].isin(canonical)
        if unknown.any():
            raise ValueError(
                f"{label} references unknown Person {out.loc[unknown, 'person_id'].iloc[0]!r}"
            )
        out["person_id"] = out["person_id"].map(
            lambda value: pd.NA if pd.isna(value) else canonical[str(value)]
        )
        deprecated = out["person_id"].notna() & ~out["person_id"].isin(active_people)
        if deprecated.any():
            raise ValueError(f"{label} did not resolve to an active canonical Person")
        out["person_id"] = out["person_id"].astype("string")
        return out

    tenures_out = rewrite(office_tenures, "office_tenures")
    rosters_out = rewrite(rosters, "rosters")
    if tenures_out["office_tenure_id"].duplicated().any():
        raise ValueError("office_tenure_id must remain unique after Person canonicalization")
    known_tenures = set(tenures_out["office_tenure_id"].dropna())
    missing_tenures = rosters_out["office_tenure_id"].notna() & ~rosters_out[
        "office_tenure_id"
    ].isin(known_tenures)
    if missing_tenures.any():
        raise ValueError("a canonicalized roster references an unknown office_tenure_id")
    members = rosters_out.loc[rosters_out["person_id"].notna()]
    duplicate_members = members.duplicated(
        ["event_id", "represented_body", "office_type", "person_id"], keep=False
    )
    if duplicate_members.any():
        duplicate = members.loc[duplicate_members].iloc[0]
        raise ValueError(
            "Person redirect creates a duplicate roster member in "
            f"event {duplicate['event_id']!r}, body {duplicate['represented_body']!r}, "
            f"office {duplicate['office_type']!r}"
        )
    return CanonicalPersonEvidence(tenures_out, rosters_out)


def _pinned_occurrence(
    candidacy_id: str,
    event_id: str,
    represented_body: str,
    office_type: str,
    candidate_name: str,
) -> CandidacyLocator:
    """Keep a curation stable when a presentation-normalized name changes."""

    return CandidacyLocator(
        event_id,
        represented_body,
        office_type,
        candidate_name,
        candidacy_id=candidacy_id,
    )


def _anchored_continuity_assertion(
    assertion_id: str,
    preferred_name: str,
    registry_person_id: str,
    occurrences: tuple[tuple[str, str, str, str, str], ...],
    evidence_urls: tuple[str, ...] | str,
    rationale: str,
) -> CuratedIdentityAssertion:
    """Build a compact, occurrence-pinned assertion around an existing Person."""

    if isinstance(evidence_urls, str):
        evidence_urls = (evidence_urls,)

    return CuratedIdentityAssertion(
        assertion_id=assertion_id,
        preferred_name=preferred_name,
        occurrences=tuple(_pinned_occurrence(*occurrence) for occurrence in occurrences),
        evidence_urls=evidence_urls,
        rationale=rationale,
        registry_person_ids=(registry_person_id,),
    )


def _anchored_same_office_continuity_assertion(
    assertion_id: str,
    preferred_name: str,
    registry_person_id: str,
    represented_body: str,
    office_type: str,
    occurrences: tuple[tuple[str, str, str], ...],
    evidence_urls: tuple[str, ...] | str,
    rationale: str,
) -> CuratedIdentityAssertion:
    """Build an anchored assertion for pins that all seek the same office."""

    return _anchored_continuity_assertion(
        assertion_id,
        preferred_name,
        registry_person_id,
        tuple(
            (candidacy_id, event_id, represented_body, office_type, candidate_name)
            for candidacy_id, event_id, candidate_name in occurrences
        ),
        evidence_urls,
        rationale,
    )


DEFAULT_IDENTITY_ASSERTIONS: tuple[CuratedIdentityAssertion, ...] = (
    CuratedIdentityAssertion(
        assertion_id="doug-ford-toronto-council-and-ontario-legislature",
        preferred_name="Doug Ford",
        occurrences=(
            CandidacyLocator(
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_city_council",
                "councillor",
                "Doug Ford",
            ),
            CandidacyLocator(
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_city_council",
                "mayor",
                "Doug Ford",
            ),
            CandidacyLocator("on-2018-general", "ontario_legislative_assembly", "mpp", "Doug Ford"),
            CandidacyLocator("on-2022-general", "ontario_legislative_assembly", "mpp", "Doug Ford"),
            CandidacyLocator("on-2025-general", "ontario_legislative_assembly", "mpp", "Doug Ford"),
        ),
        evidence_urls=(
            "https://www.ola.org/sites/default/files/node-files/hansard/document/pdf/2018/2018-11/02-AUG-2018_L014_0.pdf",
        ),
        rationale=(
            "Ontario Hansard identifies Premier Doug Ford as a former Toronto city "
            "councillor; the enumerated official election rows provide each occurrence."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="olivia-chow-toronto-council-house-and-mayoral-candidacies",
        preferred_name="Olivia Chow",
        occurrences=(
            CandidacyLocator(
                "evt_d89f777f34365c37b114ca39fb376591",
                "toronto_city_council",
                "councillor",
                "Olivia Chow",
            ),
            *(
                CandidacyLocator(event, "canada_house_of_commons", "mp", "Olivia Chow")
                for event in ("ec-ge-38", "ec-ge-39", "ec-ge-40", "ec-ge-41")
            ),
            CandidacyLocator(
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_city_council",
                "mayor",
                "Olivia Chow",
            ),
            CandidacyLocator("ec-ge-42", "canada_house_of_commons", "mp", "Olivia Chow"),
            CandidacyLocator(
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Olivia Chow",
            ),
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/olivia-chow%2820816%29/roles",
            "https://www.ourcommons.ca/Content/House/411/Debates/037/HAN037-E.PDF",
        ),
        rationale=(
            "The House roles record enumerates her federal candidacies and official "
            "House debate records her prior city-councillor service."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="yvan-baker-ontario-legislature-and-house",
        preferred_name="Yvan Baker",
        occurrences=(
            CandidacyLocator(
                "on-2014-general", "ontario_legislative_assembly", "mpp", "Yvan Baker"
            ),
            CandidacyLocator(
                "on-2018-general", "ontario_legislative_assembly", "mpp", "Yvan Baker"
            ),
            *(
                CandidacyLocator(event, "canada_house_of_commons", "mp", "Yvan Baker")
                for event in ("ec-ge-43", "ec-ge-44", "ec-ge-45")
            ),
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/yvan-baker%28105121%29/roles",
            "https://www.ourcommons.ca/Content/Committee/441/FINA/Evidence/EV11814804/FINAEV51-E.PDF",
        ),
        rationale=(
            "The House roles record enumerates his federal candidacies and official "
            "committee evidence records that he was previously an Ontario MPP."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="adam-vaughan-toronto-council-and-house",
        preferred_name="Adam Vaughan",
        occurrences=(
            *(
                CandidacyLocator(event, "toronto_city_council", "councillor", "Adam Vaughan")
                for event in (
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                )
            ),
            *(
                CandidacyLocator(event, "canada_house_of_commons", "mp", "Adam Vaughan")
                for event in ("ec-be-2014-06-30", "ec-ge-42", "ec-ge-43")
            ),
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/adam-vaughan%2854434%29/roles",
            "https://www.ourcommons.ca/documentviewer/en/42-1/ETHI/meeting-137/evidence",
        ),
        rationale=(
            "The House roles record enumerates his federal candidacies and official "
            "committee evidence identifies him as both a former city councillor and MP."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="craig-scott-house-candidacies",
        preferred_name="Craig Scott",
        occurrences=tuple(
            CandidacyLocator(event, "canada_house_of_commons", "mp", "Craig Scott")
            for event in ("ec-be-2012-03-19", "ec-ge-42")
        ),
        evidence_urls=("https://www.ourcommons.ca/members/en/craig-scott%2875006%29/roles",),
        rationale="The official House roles record enumerates both candidacies.",
    ),
    CuratedIdentityAssertion(
        assertion_id="peggy-nash-house-candidacies",
        preferred_name="Peggy Nash",
        occurrences=tuple(
            CandidacyLocator(event, "canada_house_of_commons", "mp", "Peggy Nash")
            for event in ("ec-ge-38", "ec-ge-39", "ec-ge-40", "ec-ge-41", "ec-ge-42")
        ),
        evidence_urls=("https://www.ourcommons.ca/members/en/peggy-nash%283242%29/roles",),
        rationale="The official House roles record enumerates these candidacies.",
    ),
    CuratedIdentityAssertion(
        assertion_id="kirsty-duncan-house-candidacies",
        preferred_name="Kirsty Duncan",
        occurrences=tuple(
            CandidacyLocator(event, "canada_house_of_commons", "mp", "Kirsty Duncan")
            for event in ("ec-ge-40", "ec-ge-41", "ec-ge-42", "ec-ge-43", "ec-ge-44")
        ),
        evidence_urls=("https://www.ourcommons.ca/members/en/kirsty-duncan%2858877%29/roles",),
        rationale="The official House roles record enumerates these candidacies.",
    ),
    CuratedIdentityAssertion(
        assertion_id="brad-duguid-city-council-and-ontario-legislature",
        preferred_name="Brad Duguid",
        occurrences=tuple(
            _pinned_occurrence(
                candidate_id, event, "ontario_legislative_assembly", "mpp", "Brad Duguid"
            )
            for candidate_id, event in (
                ("can_d85f9037881253bcbf687ecfc44511b5", "on-2003-general"),
                ("can_95a4bf1a2b7d5f83a497d5f64ffc7e36", "on-2007-general"),
                ("can_957cee0d0375593690349bb4d1a8e805", "on-2011-general"),
                ("can_864171b9868d51449e6a69c8e32d9189", "on-2014-general"),
            )
        ),
        registry_person_ids=("per_e58710f18fe45bc89242f5432144686b",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/1999/agendas/council/cc/cc991123/pof10rpt/cl006.pdf",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "Official City minutes identify Councillor Brad Duguid and Elections "
            "Ontario records enumerate his subsequent provincial candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="catherine-leblanc-miller-consecutive-tcdsb-candidacies",
        preferred_name="Catherine LeBlanc-Miller",
        occurrences=(
            _pinned_occurrence(
                "can_dced59fe77ad5682a90e4bffd42645b6",
                "evt_d89f777f34365c37b114ca39fb376591",
                "toronto_catholic_district_school_board",
                "trustee",
                "Catherine LeBlanc-Miller",
            ),
            _pinned_occurrence(
                "can_d1005a8210675119a0356ed070ee51a7",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Catherine LeBlanc-Miller",
            ),
        ),
        evidence_urls=("https://open.toronto.ca/dataset/election-results/",),
        rationale=(
            "The Clerk's official results show the same named Ward 9 trustee elected "
            "in consecutive 2003 and 2006 elections. The two same-name 2010 rows in "
            "different wards are deliberately not asserted."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="el-farouk-khaki-2008-federal-candidacies",
        preferred_name="El-Farouk Khaki",
        occurrences=(
            _pinned_occurrence(
                "can_139226bcc6e250059e10dbfe8f1dbc42",
                "ec-be-2008-03-17",
                "canada_house_of_commons",
                "mp",
                "El-Farouk Khaki",
            ),
            _pinned_occurrence(
                "can_5594e86af0ba5045a3e92173454df1de",
                "ec-ge-40",
                "canada_house_of_commons",
                "mp",
                "El-Farouk Khaki",
            ),
        ),
        evidence_urls=(
            "https://www.elections.ca/res/rep/off/ovr_2008/ovr_2008.pdf",
            "https://www.elections.ca/content.aspx?dir=rep/off/sta_2008&document=app3&lang=e&section=res",
        ),
        rationale=(
            "Elections Canada records the same Toronto lawyer and NDP candidate in "
            "Toronto Centre's March by-election and October 2008 general election."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="fred-dominelli-appointed-councillor-and-2006-candidacy",
        preferred_name="Fred Dominelli",
        occurrences=(
            _pinned_occurrence(
                "can_49d21e3e05c052698e3b0850fddb5778",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_city_council",
                "councillor",
                "Fred Dominelli",
            ),
        ),
        registry_person_ids=("per_41b5394fedeb573da516d637125cd66f",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/2003/agendas/council/cc030521/cofa.pdf",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Council minutes record Fred Dominelli's 2003 Ward 17 "
            "appointment; the Clerk records his 2006 Ward 17 candidacy."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="irene-jones-city-council-and-2003-ontario-candidacy",
        preferred_name="Irene Jones",
        occurrences=(
            _pinned_occurrence(
                "can_74e88596d0595d93ac34d63c4a6d203e",
                "on-2003-general",
                "ontario_legislative_assembly",
                "mpp",
                "Irene Jones",
            ),
        ),
        registry_person_ids=("per_bf5a65098e415b36ae204453a00c714a",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/2003/minutes/council/cc030722.pdf",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "Official 2003 Council minutes identify Councillor Irene Jones and the "
            "official provincial result records her Etobicoke-Lakeshore candidacy."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="james-maloney-appointed-councillor-and-house-candidacies",
        preferred_name="James Maloney",
        occurrences=tuple(
            _pinned_occurrence(
                candidate_id, event, "canada_house_of_commons", "mp", "James Maloney"
            )
            for candidate_id, event in (
                ("can_507b41ffc03553a2bac3f1ddd670d66a", "ec-ge-42"),
                ("can_7d2c03c32b635413a4dadacdae03eeac", "ec-ge-43"),
                ("can_b63d80e3b18e506eb4ab175aaba6d7cc", "ec-ge-44"),
                ("can_b346aab66a0b5993a2beaef37907feb3", "ec-ge-45"),
            )
        ),
        registry_person_ids=("per_b8324f45adf156c09aba26338117cad3",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/mmis/2015/ex/bgrd/backgroundfile-78750.pdf",
            "https://www.ourcommons.ca/members/en/james-maloney%2888748%29/roles",
        ),
        rationale=(
            "The City records James Maloney's 2014 Ward 5 appointment and the House "
            "roles record enumerates his four federal terms."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="john-turmel-cross-jurisdiction-candidacies",
        preferred_name='John "The Engineer" Turmel',
        occurrences=(
            _pinned_occurrence(
                "can_4808cd73525b568fba9f45c9ece08d9b",
                "on-2006-09-14-by-064",
                "ontario_legislative_assembly",
                "mpp",
                "John C. Turmel",
            ),
            _pinned_occurrence(
                "can_ced34b2367b957978646a74100cd9700",
                "on-2009-09-17-by-077",
                "ontario_legislative_assembly",
                "mpp",
                "John Turmel",
            ),
            _pinned_occurrence(
                "can_9064e64eef795e9588ce68d046b0a023",
                "on-2010-02-04-by-094",
                "ontario_legislative_assembly",
                "mpp",
                "John Turmel",
            ),
            _pinned_occurrence(
                "can_1b9594951cbc54bfab5faa115511f257",
                "ec-be-2012-03-19",
                "canada_house_of_commons",
                "mp",
                "John C. Turmel",
            ),
            _pinned_occurrence(
                "can_7f3aac44e68f5d9ea74902ab3d73ac91",
                "ec-be-2013-11-25",
                "canada_house_of_commons",
                "mp",
                'John "The Engineer" Turmel',
            ),
            _pinned_occurrence(
                "can_1ffed0fd1e3b5968887937c9ce4bec01",
                "ec-be-2014-06-30",
                "canada_house_of_commons",
                "mp",
                'John "The Engineer" Turmel',
            ),
            _pinned_occurrence(
                "can_9c6c74b5b95c5a7ba227543f3408afa8",
                "on-2016-09-01-by-083",
                "ontario_legislative_assembly",
                "mpp",
                "John Turmel",
            ),
            _pinned_occurrence(
                "can_65e20b3844db52118029142566e13d01",
                "ec-be-2017-12-11",
                "canada_house_of_commons",
                "mp",
                "John 'The Engineer' Turmel",
            ),
            _pinned_occurrence(
                "can_0aeae71e7f85504f986949276978e2ad",
                "ec-be-2020-10-26",
                "canada_house_of_commons",
                "mp",
                "John The Engineer Turmel",
            ),
            _pinned_occurrence(
                "can_f0bc58dffc8850be93e893a2bc5d5d49",
                "on-2023-07-27-by-095",
                "ontario_legislative_assembly",
                "mpp",
                "John Turmel",
            ),
        ),
        evidence_urls=(
            "https://www.elections.ca/content.aspx?dir=rep/off/sta_2019&document=app2&lang=e&section=res",
            "https://www.elections.ca/content.aspx?dir=rep/off/ovr_2009&document=synopsis&lang=e&section=res",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "Official federal and provincial results consistently identify the "
            "Brantford engineer under the enumerated John Turmel ballot variants."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="jonathan-tsao-appointed-councillor-and-ontario-candidacies",
        preferred_name="Jonathan Tsao",
        occurrences=(
            _pinned_occurrence(
                "can_1068be2b81235a2196e20147795339d4",
                "on-2022-general",
                "ontario_legislative_assembly",
                "mpp",
                "Jonathan Tsao",
            ),
            _pinned_occurrence(
                "can_ec0723d4f3c85bf78278c2a004d2a597",
                "on-2025-general",
                "ontario_legislative_assembly",
                "mpp",
                "Jonathan Tsao",
            ),
        ),
        registry_person_ids=("per_c675142f1bab5e1db315a295f34a3dec",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/mmis/2019/ex/bgrd/backgroundfile-131208.pdf",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "The City records Jonathan Tsao's 2018 Ward 33 appointment and Elections "
            "Ontario records his 2022 and 2025 Don Valley North candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="lorenzo-berardinetti-city-council-and-ontario-candidacies",
        preferred_name="Lorenzo Berardinetti",
        occurrences=(
            *(
                _pinned_occurrence(
                    candidate_id,
                    event,
                    "ontario_legislative_assembly",
                    "mpp",
                    "Lorenzo Berardinetti",
                )
                for candidate_id, event in (
                    ("can_a6ac9c5ceb8854e0842dc3a1975656f6", "on-2003-general"),
                    ("can_686f27fbb2265097908a8b18cf8464d2", "on-2007-general"),
                    ("can_457a45ec4fad5464a425cfac59237bbd", "on-2011-general"),
                    ("can_c9902e7b84bd53fc999168e30cd8e2a8", "on-2014-general"),
                    ("can_575c78d43530584181c76e335793d966", "on-2018-general"),
                )
            ),
            _pinned_occurrence(
                "can_0e18e06954ae5f2caa65235b467f4983",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_city_council",
                "councillor",
                "Lorenzo Berardinetti",
            ),
        ),
        registry_person_ids=("per_dc7ee9fafb425c22819e7363edf5a27b",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/2001/minutes/council/cc010530.pdf",
            "https://results.elections.on.ca/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official City minutes identify Councillor Lorenzo Berardinetti; official "
            "provincial and City results enumerate the later candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="mario-silva-city-council-and-house-candidacies",
        preferred_name="Mario Silva",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "canada_house_of_commons", "mp", "Mario Silva")
            for candidate_id, event in (
                ("can_d333ff6babdf5925b14844063ad3e26c", "ec-ge-38"),
                ("can_dc3c86953e875f5498c0cd3c57ca41ea", "ec-ge-39"),
                ("can_eef9c1705b515912b1f2a00a2b584d1d", "ec-ge-40"),
                ("can_f6905f96b7af50eb820c17fb25068d35", "ec-ge-41"),
            )
        ),
        registry_person_ids=("per_0d095ab7d4b5554eb2322f446d56cf2a",),
        evidence_urls=(
            "https://www.ourcommons.ca/Content/Committee/381/CHPC/Evidence/EV1928325/CHPCEV45-E.PDF",
            "https://www.ourcommons.ca/members/en/mario-silva%2825455%29/roles",
        ),
        rationale=(
            "Official House evidence records Mario Silva's ten years on Toronto City "
            "Council and the House roles record enumerates his federal service."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="norm-kelly-council-roster-and-candidacies",
        preferred_name="Norm Kelly",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "toronto_city_council", "councillor", name)
            for candidate_id, event, name in (
                (
                    "can_ede4ece7eb2c5a22a6135cca6966054f",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "Norman Kelly",
                ),
                (
                    "can_330f0f883c9454fc8cbd19eb2ade80a5",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "Norm Kelly",
                ),
                (
                    "can_c96f679bbb2855409e9f26bad3952961",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "Norm Kelly",
                ),
                (
                    "can_397f372cc6d15e01a3a8dd86c2659956",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "Norm Kelly",
                ),
                (
                    "can_4185e2b2d994537280b8eae979cfdaec",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "Norm Kelly",
                ),
            )
        ),
        registry_person_ids=("per_631b41eec6f25d43828651db6312cd99",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/mmis/2010/zb/bgrd/backgroundfile-26580.pdf",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official City committee membership and election results enumerate Norm "
            "(Norman) Kelly's continuous Council identity."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="clifford-cliff-jenkins-council-candidacies",
        preferred_name="Cliff Jenkins",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "toronto_city_council", "councillor", name)
            for candidate_id, event, name in (
                (
                    "can_4706d53efef15d9db227fad597dfee5a",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "Clifford Jenkins",
                ),
                (
                    "can_f1ea2339e5d859a8bd4ec24487e8039e",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "Cliff Jenkins",
                ),
                (
                    "can_6fbfd3332c8258c9813f54eded8c8028",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "Cliff Jenkins",
                ),
            )
        ),
        evidence_urls=(
            "https://open.toronto.ca/dataset/election-results/",
            "https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/",
        ),
        rationale=(
            "The Clerk's official results enumerate Clifford (Cliff) Jenkins in the "
            "same Council office across the 2003, 2006, and 2010 elections."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="paul-sutherland-city-council-and-2003-ontario-candidacy",
        preferred_name="Paul Sutherland",
        occurrences=(
            _pinned_occurrence(
                "can_3d09522f664053e88d5c08a3945fdf63",
                "on-2003-general",
                "ontario_legislative_assembly",
                "mpp",
                "Paul Sutherland",
            ),
        ),
        registry_person_ids=("per_55e5ba9aff9750899ff1db70e5bc84ba",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/2001/minutes/committees/bud/bud010209.pdf",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "Official City minutes identify Councillor Paul Sutherland and the "
            "official 2003 provincial result records his Don Valley East candidacy."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="ron-moeser-council-roster-and-candidacies",
        preferred_name="Ron Moeser",
        occurrences=(
            _pinned_occurrence(
                "can_3e4fe8a5b21d52fa9570beb0b8b9af86",
                "evt_d89f777f34365c37b114ca39fb376591",
                "toronto_city_council",
                "councillor",
                "Ronald Moeser",
            ),
            _pinned_occurrence(
                "can_b69b4fdf315f59589b4537523c4adae5",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_city_council",
                "councillor",
                "Ron Moeser",
            ),
            _pinned_occurrence(
                "can_d76e7987ea595e31b06f1ca9b24926eb",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_city_council",
                "councillor",
                "Ron Moeser",
            ),
            _pinned_occurrence(
                "can_d1b1258e6c9556149fd7776be86ff175",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_city_council",
                "councillor",
                "Ron Moeser",
            ),
        ),
        registry_person_ids=("per_6943978961ef52d8bdedde8802fc8e04",),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/mmis/2007/sc/minutes/2007-11-27-sc11-mn.pdf",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Council minutes and Clerk results enumerate Ron (Ronald) "
            "Moeser's Ward 44 Council identity."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="sarmite-sam-bulte-federal-candidacies",
        preferred_name="Sarmite (Sam) Bulte",
        occurrences=(
            _pinned_occurrence(
                "can_9febe5510296550b9031c3322f9b8099",
                "ec-ge-38",
                "canada_house_of_commons",
                "mp",
                "Sarmite (Sam) Bulte",
            ),
            _pinned_occurrence(
                "can_c896fcfcd29058119787f6d27dc332da",
                "ec-ge-39",
                "canada_house_of_commons",
                "mp",
                "Sarmite Sam Bulte",
            ),
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/Members/en/sarmite-bulte%28894%29/roles",
            "https://www.ourcommons.ca/documentviewer/en/36-1/FAIT/meeting-109/evidence",
        ),
        rationale=(
            "The official House roles enumerate the 2004 and 2006 candidacies, and "
            "House evidence records the member's preferred '(Sam)' form."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="sean-michael-harrison-tdsb-candidacies",
        preferred_name="Sean-Michael Harrison",
        occurrences=(
            _pinned_occurrence(
                "can_1a22128f7b915f47af1afd81070d9ef3",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Sean-Michael Harrison",
            ),
            _pinned_occurrence(
                "can_c5f1a0af86bb5bf6ac61545fde03b622",
                "evt_0053e297e0b15f179a94dee854971a09",
                "toronto_district_school_board",
                "trustee",
                "Sean-Michael Harrison",
            ),
            _pinned_occurrence(
                "can_f1be821ed03f551b84e0a85efbff3638",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Sean-Michael Harrison",
            ),
            _pinned_occurrence(
                "can_b5dd69a8f97358f083e17a99575c3c89",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Sean Michael Harrison",
            ),
            _pinned_occurrence(
                "can_8c9ab67950735ffc85266a684977b012",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Sean Michael Harrison",
            ),
        ),
        evidence_urls=("https://open.toronto.ca/dataset/election-results/",),
        rationale=(
            "The Clerk's official results enumerate the same Sean-Michael Harrison "
            "trustee candidacy across punctuation and boundary-era display changes."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="gerard-kennedy-ontario-legislature-and-house",
        preferred_name="Gerard Kennedy",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, body, office, "Gerard Kennedy")
            for candidate_id, event, body, office in (
                (
                    "can_3084b64db8e3554f88aa630a3c6fa8da",
                    "on-2003-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_5f07089ba1e45e1bbc1f6063ba75143d",
                    "ec-ge-40",
                    "canada_house_of_commons",
                    "mp",
                ),
                (
                    "can_0a0972a1976951dba4d4b8751cf7803c",
                    "ec-ge-41",
                    "canada_house_of_commons",
                    "mp",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/gerard-kennedy%2859000%29/roles",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "The official House roles and Elections Ontario records enumerate Gerard "
            "Kennedy's provincial and federal service."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="han-dong-trustee-ontario-legislature-and-house",
        preferred_name="Han Dong",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, body, office, "Han Dong")
            for candidate_id, event, body, office in (
                (
                    "can_c062075c26065f4dab6f439b73ecf39c",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_district_school_board",
                    "trustee",
                ),
                (
                    "can_2c6da254cc975db7a6fc00da150021ea",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_b2e3d202a122562b844c8d1c9fc04219",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_f71288e1cb665b939808d61dfd404750",
                    "ec-ge-43",
                    "canada_house_of_commons",
                    "mp",
                ),
                (
                    "can_fa74370cc26e5df8b8f3b6fb23e5ad01",
                    "ec-ge-44",
                    "canada_house_of_commons",
                    "mp",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/han-dong%28105091%29/roles",
            "https://results.elections.on.ca/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official House, provincial, and City election records enumerate Han "
            "Dong's trustee, MPP, and MP candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="john-tory-ontario-legislature-and-toronto-mayor",
        preferred_name="John Tory",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, body, office, "John Tory")
            for candidate_id, event, body, office in (
                (
                    "can_b6ef5f14d0f9578f986e6ae34122b3e7",
                    "on-2007-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_b3ecaef663ba56adbab70efbcb5004da",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "mayor",
                ),
                (
                    "can_0101698bc62b5b279cd15537a2e12179",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "mayor",
                ),
                (
                    "can_1179f79bea135e8d82289930ed974496",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_city_council",
                    "mayor",
                ),
                (
                    "can_fa7dd6aa57a55b69828e69186f5a67cf",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "mayor",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Ontario Legislature and Toronto Clerk records enumerate John "
            "Tory's provincial candidacy and Toronto mayoral candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="jean-yip-house-candidacies",
        preferred_name="Jean Yip",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "canada_house_of_commons", "mp", "Jean Yip")
            for candidate_id, event in (
                ("can_fe72a4f99bfd59c8b8d64f119c67d8bb", "ec-be-2017-12-11"),
                ("can_c07f3382bb035ba4bee629df5a40fdfb", "ec-ge-43"),
                ("can_5c1f78de045455e7a4fce7fdb4aff80c", "ec-ge-44"),
                ("can_a1c90bd5a55d5a43bfc882dc76089300", "ec-ge-45"),
            )
        ),
        evidence_urls=("https://www.ourcommons.ca/members/en/jean-yip%2898747%29/roles",),
        rationale="The official House roles record enumerates Jean Yip's federal service.",
    ),
    CuratedIdentityAssertion(
        assertion_id="julie-dabrusin-house-candidacies",
        preferred_name="Julie Dabrusin",
        occurrences=tuple(
            _pinned_occurrence(
                candidate_id, event, "canada_house_of_commons", "mp", "Julie Dabrusin"
            )
            for candidate_id, event in (
                ("can_4921cbd3ca345f1db4854c2bbd04729b", "ec-ge-42"),
                ("can_331ef2ffb19a58b8ad3e30f8d4d45129", "ec-ge-43"),
                ("can_4f159c74fe7256af9044e4144d7e5b16", "ec-ge-44"),
                ("can_44f589040b5e536bb1c1d34a343d5f41", "ec-ge-45"),
            )
        ),
        evidence_urls=("https://www.ourcommons.ca/members/fr/julie-dabrusin%2888994%29/roles",),
        rationale=("The official House roles record enumerates Julie Dabrusin's federal service."),
    ),
    CuratedIdentityAssertion(
        assertion_id="julie-dzerowicz-house-candidacies",
        preferred_name="Julie Dzerowicz",
        occurrences=tuple(
            _pinned_occurrence(
                candidate_id, event, "canada_house_of_commons", "mp", "Julie Dzerowicz"
            )
            for candidate_id, event in (
                ("can_f31b75d7ca3454fdbb94a38ebe8cc8fb", "ec-ge-42"),
                ("can_6d258e50b5d7540dbc328775dca18060", "ec-ge-43"),
                ("can_7c9848520cb2574a936627b26de0fdc5", "ec-ge-44"),
                ("can_8c5ac8ffd8fb52a88773e667d1404b20", "ec-ge-45"),
            )
        ),
        evidence_urls=("https://www.ourcommons.ca/Members/fr/julie-dzerowicz%2888721%29/roles",),
        rationale=("The official House roles record enumerates Julie Dzerowicz's federal service."),
    ),
    CuratedIdentityAssertion(
        assertion_id="michael-coteau-trustee-ontario-legislature-and-house",
        preferred_name="Michael Coteau",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, body, office, "Michael Coteau")
            for candidate_id, event, body, office in (
                (
                    "can_189f3ed844395539ba1ba7252c8a16b6",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_district_school_board",
                    "trustee",
                ),
                (
                    "can_a5a37b975b5f51a5be0e4cf24b3c4927",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_district_school_board",
                    "trustee",
                ),
                (
                    "can_46b75df1af1e508aa80fcf80e3cf7f63",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_district_school_board",
                    "trustee",
                ),
                (
                    "can_f0705a4748b7506da15ddf6ea30ed275",
                    "on-2011-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_02834a0aee0f5d679ae8c6f1e5ad81b9",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_df083a50f56150aabc0cbd3cc2358127",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_44c2c1ff92a35fe198a4679339fdc07b",
                    "ec-ge-44",
                    "canada_house_of_commons",
                    "mp",
                ),
                (
                    "can_f173313a6ce15ad7b42303f26e0ed785",
                    "ec-ge-45",
                    "canada_house_of_commons",
                    "mp",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/MEMBERS/en/michael-coteau%28110373%29/roles",
            "https://results.elections.on.ca/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official House, provincial, and City election records enumerate Michael "
            "Coteau's trustee, MPP, and MP candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="rob-oliphant-house-candidacies",
        preferred_name="Rob Oliphant",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "canada_house_of_commons", "mp", "Rob Oliphant")
            for candidate_id, event in (
                ("can_72ae1a68c3c2512994f52e11dcca3ed3", "ec-ge-40"),
                ("can_a82dfe47accc58b9abd926429272f9e9", "ec-ge-41"),
                ("can_142d9c1ed4f35c9d9248ee1a48732fe3", "ec-ge-42"),
                ("can_5680ef0a50c35e618f8e0deb043dc200", "ec-ge-43"),
                ("can_db946a1db7195e3983c86ff54305b540", "ec-ge-44"),
                ("can_90d01019dd4c51ebb6cbdac8f9aa037c", "ec-ge-45"),
            )
        ),
        evidence_urls=("https://www.ourcommons.ca/Members/en/robert-oliphant%2858858%29/roles",),
        rationale=(
            "The official House roles record identifies Rob (Robert) Oliphant and "
            "enumerates his federal service."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="yasmin-ratansi-house-candidacies",
        preferred_name="Yasmin Ratansi",
        occurrences=tuple(
            _pinned_occurrence(
                candidate_id, event, "canada_house_of_commons", "mp", "Yasmin Ratansi"
            )
            for candidate_id, event in (
                ("can_8ee1d5dd41345c21a77c4499e4d7b280", "ec-ge-38"),
                ("can_29f8c9e96ed65a67b5e616a8936d0fdb", "ec-ge-39"),
                ("can_30cb7e77ec195f53b38577fa21092c7b", "ec-ge-40"),
                ("can_1341eeb37fac5f408d8759afd19b53a9", "ec-ge-41"),
                ("can_633d0dfcd6395f049670f5ff302d72bc", "ec-ge-42"),
                ("can_92781ea4a40d5db2b0fea17c6964b7a8", "ec-ge-43"),
            )
        ),
        evidence_urls=("https://www.ourcommons.ca/members/en/yasmin-ratansi%2825449%29",),
        rationale="The official House member record enumerates Yasmin Ratansi's service.",
    ),
    CuratedIdentityAssertion(
        assertion_id="nathaniel-nate-erskine-smith-house-candidacies",
        preferred_name="Nathaniel Erskine-Smith",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "canada_house_of_commons", "mp", name)
            for candidate_id, event, name in (
                (
                    "can_bc8a58862b015e2994d78cbad6c2e0a7",
                    "ec-ge-42",
                    "Nathaniel Erskine-Smith",
                ),
                (
                    "can_cf2b49e1b87b57a5b66383bead4a73ba",
                    "ec-ge-43",
                    "Nathaniel Erskine-Smith",
                ),
                (
                    "can_a347d205097255e8a99602b5ce98a588",
                    "ec-ge-44",
                    "Nathaniel Erskine-Smith",
                ),
                (
                    "can_2d13e1b9c2025217a924f44ed1c0acee",
                    "ec-ge-45",
                    "Nate Erskine-Smith",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/nathaniel-erskine-smith%2888687%29/roles",
        ),
        rationale=(
            "The official House roles record enumerates Nathaniel Erskine-Smith's "
            "four terms, including the 2025 ballot's shortened Nate form."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="joseph-joe-volpe-house-candidacies",
        preferred_name="Joseph Volpe",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "canada_house_of_commons", "mp", name)
            for candidate_id, event, name in (
                ("can_f5be4fcb924d5f5ea2727e8870412931", "ec-ge-38", "Joseph Volpe"),
                ("can_353dcc5369b85e309adfb3025e9bd446", "ec-ge-39", "Joe Volpe"),
                ("can_bb00615e173e5012a0c2a80af4bbd209", "ec-ge-40", "Joseph Volpe"),
                ("can_8d7e3d1643e3542190662b11ac261d9d", "ec-ge-41", "Joe Volpe"),
            )
        ),
        evidence_urls=("https://www.ourcommons.ca/members/en/joseph-volpe%28608%29/roles",),
        rationale=(
            "The official House roles record identifies the Joe and Joseph Volpe "
            "ballot forms as one continuous MP career."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="ted-opitz-house-candidacies",
        preferred_name="Ted Opitz",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, "canada_house_of_commons", "mp", "Ted Opitz")
            for candidate_id, event in (
                ("can_170e509cc71258e88e1efb5a0eb3e7e7", "ec-ge-41"),
                ("can_1c4dea510aae5edab6401e934ec98d6c", "ec-ge-42"),
                ("can_dc08d9922a47529fbed95a3be331de91", "ec-ge-43"),
                ("can_f34d3f0075eb57fbacdf120260fd827e", "ec-ge-45"),
            )
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/ted-opitz%2871625%29/roles",
            "https://www.elections.ca/content.aspx?dir=pas&document=ge&lang=e&section=ele",
        ),
        rationale=(
            "The official House tenure record and Elections Canada results enumerate "
            "Ted Opitz's Toronto federal candidacies without treating later runs as "
            "continued tenure."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="cheri-dinovo-ontario-candidacies",
        preferred_name="Cheri DiNovo",
        occurrences=tuple(
            _pinned_occurrence(
                candidate_id,
                event,
                "ontario_legislative_assembly",
                "mpp",
                name,
            )
            for candidate_id, event, name in (
                ("can_30726a7b4fb2564f8d7e3906e52c8f3e", "on-2006-09-14-by-064", "Cheri Di Novo"),
                ("can_5c5222cbc44b54aaa5bd234a726c11be", "on-2007-general", "Cheri DiNovo"),
                ("can_c198f61d6a6555ea8bb689b5239c7b0e", "on-2011-general", "Cheri DiNovo"),
                ("can_5530c172634d5eea975c65ab211f59e1", "on-2014-general", "Cheri DiNovo"),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/cheri-dinovo",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "Official Elections Ontario results and Legislature Hansard identify "
            "Cheri Di Novo/DiNovo as the same Parkdale-High Park MPP."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="michael-david-prue-ontario-candidacies",
        preferred_name="Michael Prue",
        occurrences=tuple(
            _pinned_occurrence(
                candidate_id,
                event,
                "ontario_legislative_assembly",
                "mpp",
                name,
            )
            for candidate_id, event, name in (
                ("can_73ec324d77d456dd96a873b4ff3c625d", "on-2003-general", "Michael David Prue"),
                ("can_bd0f438bcaf453d4bdff6e8e1166567b", "on-2007-general", "Michael Prue"),
                ("can_a7c6d96b470953b09f1e9ee2bcba4178", "on-2011-general", "Michael Prue"),
                ("can_14332595e942552fb259798ebe2c5666", "on-2014-general", "Michael Prue"),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/michael-prue",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "Official Elections Ontario results and Legislature evidence identify "
            "Michael David Prue and Michael Prue as the same MPP."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="mitzie-hunter-ontario-legislature-and-toronto-mayor",
        preferred_name="Mitzie Hunter",
        occurrences=tuple(
            _pinned_occurrence(candidate_id, event, body, office, "Mitzie Hunter")
            for candidate_id, event, body, office in (
                (
                    "can_9f08d6ba00f7571d87f66d649ee1fc63",
                    "on-2013-08-01-by-082",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_1bca00f0c0cf52409a1603a3c4175d37",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_6c9c9c980d6a5be6956cfc63412fe2cd",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_a6fbbafa08bc5b67b416f6f24c3affe8",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                ),
                (
                    "can_1257851764175049a664559b040ecafc",
                    "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                    "toronto_city_council",
                    "mayor",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/mitzie-hunter",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
        ),
        rationale=(
            "Official Legislature proceedings identify Mitzie Hunter's MPP service, "
            "and the Clerk's declaration records her 2023 mayoral candidacy."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="ausma-malik-tdsb-and-toronto-council",
        preferred_name="Ausma Malik",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_e4d08175b6bd5c89921dee59481c2daa",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Ausma Malik",
                ),
                (
                    "can_45aad11df89c511b88aed431e1b1be4e",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Ausma Malik",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-10/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "The official City profile identifies Councillor Ausma Malik as the elected "
            "2014-2018 TDSB trustee, and Clerk results enumerate both candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="bas-balkissoon-toronto-council-and-ontario-legislature",
        preferred_name="Bas Balkissoon",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_1c1054e3ef455df484dfe8f91a62e85a",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_city_council",
                    "councillor",
                    "Bas Balkissoon",
                ),
                (
                    "can_d7f0206711475b1cb961fdb5c53468f8",
                    "on-2005-11-24-by-076",
                    "ontario_legislative_assembly",
                    "mpp",
                    "BAS BALKISSOON",
                ),
                (
                    "can_2a3aecc9ea1b5fed8c501c9064aeb8f4",
                    "on-2007-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "BAS BALKISSOON",
                ),
                (
                    "can_53d309a3af4d551597b06f5c62642cac",
                    "on-2011-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "BAS BALKISSOON",
                ),
                (
                    "can_3b3ed51c87c25fe3b270e0ca57771e7d",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "BAS BALKISSOON",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/bas-balkissoon",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature service dates and City Clerk results establish Bas "
            "Balkissoon's transition from Toronto councillor to Scarborough-Rouge River MPP."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="chris-moise-tdsb-and-toronto-council",
        preferred_name="Chris Moise",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_5edfd4252e63599797d6fa50507614b8",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_district_school_board",
                    "trustee",
                    "Chris Moise",
                ),
                (
                    "can_a3934764eac55205b283a29d7ad5b765",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Chris Moise",
                ),
                (
                    "can_efbfd072697e527a85cde15216ef6df6",
                    "evt_8ca589beb65b56f5863df3f1f1b621fd",
                    "toronto_district_school_board",
                    "trustee",
                    "Moise Chris",
                ),
                (
                    "can_120961392f2050b5be1c5b0aee3d5b64",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_district_school_board",
                    "trustee",
                    "Chris Moise",
                ),
                (
                    "can_4b78f4587dab5e69b879563516563791",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Chris Moise",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-13/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "The official City profile records Chris Moise's six years as a TDSB trustee "
            "before his 2022 Council election; the reversed 2016 ballot form is included."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="cynthia-lai-ontario-and-toronto-council",
        preferred_name="Cynthia Lai",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_82f0e7d9eef258a8b71789ee8f2b5763",
                    "on-2005-11-24-by-076",
                    "ontario_legislative_assembly",
                    "mpp",
                    "CYNTHIA LAI",
                ),
                (
                    "can_0c874f38ed1255c6a9c41a580c133f51",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Cynthia Lai",
                ),
                (
                    "can_736c4515a83c5c4d99d7bbb1acdd5f7a",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Cynthia Lai",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/sites/default/files/node-files/hansard/document/pdf/2005/2005-11/house-document-hansard-transcript-2-fr-2005-11-03_pdfL015.pdf",
            "https://www.toronto.ca/legdocs/mmis/2023/rm/bgrd/backgroundfile-230112.pdf",
        ),
        rationale=(
            "Official Legislature proceedings and Toronto Council's condolence identify "
            "the same Cynthia Lai through her distinctive Toronto Real Estate Board presidency."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="dianne-saxe-ontario-and-toronto-council",
        preferred_name="Dianne Saxe",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_2c55bf181c19520ca4ce158d22331d3b",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "DIANNE SAXE",
                ),
                (
                    "can_a2952161428d58a396a575a9854b7616",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Dianne Saxe",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-11/",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "The official City profile records Dianne Saxe's Green Party leadership through "
            "August 2022, and official results enumerate her provincial and municipal races."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="doug-holyday-toronto-council-and-ontario-legislature",
        preferred_name="Doug Holyday",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_3f94a03e6dcc598d82f8d79d21d3bd10",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_city_council",
                    "councillor",
                    "Doug Holyday",
                ),
                (
                    "can_359c6f0578f45ef3a4cf038ad56e5a52",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_city_council",
                    "councillor",
                    "Doug Holyday",
                ),
                (
                    "can_529380293f3b58fba0c0897c393bbc06",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Doug Holyday",
                ),
                (
                    "can_35249e6524cc5ac7ab53b173ec15d334",
                    "on-2013-08-01-by-024",
                    "ontario_legislative_assembly",
                    "mpp",
                    "DOUG HOLYDAY",
                ),
                (
                    "can_6782da7c14e15e3b8dc5c3e20887f050",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "DOUG HOLYDAY",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/doug-holyday",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature and City Clerk records enumerate Doug Holyday's "
            "continuous municipal-to-provincial career in Etobicoke."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="gary-crawford-tdsb-council-and-ontario",
        preferred_name="Gary Crawford",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_edc9aa76603957f8b2b62c07f75cb370",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_district_school_board",
                    "trustee",
                    "Gary Crawford",
                ),
                (
                    "can_bb0852af66a159f7b906daa9ee14540a",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_district_school_board",
                    "trustee",
                    "Gary Crawford",
                ),
                (
                    "can_d14ac7953b295393bbd438dff56acc3d",
                    "on-2007-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "GARY CRAWFORD",
                ),
                (
                    "can_e36fa250b37056569224fde8f557d3a3",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Gary Crawford",
                ),
                (
                    "can_014994212b475ea8b674461d7c4ae48d",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Gary Crawford",
                ),
                (
                    "can_709e43151ddd5089b8c98b7291f7a5ca",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Gary Crawford",
                ),
                (
                    "can_4be13ddaed1f5fd69bb23af3743ef443",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Gary Crawford",
                ),
                (
                    "can_38c3d25683645708877b29f6a5d9cbab",
                    "on-2023-07-27-by-095",
                    "ontario_legislative_assembly",
                    "mpp",
                    "GARY CRAWFORD",
                ),
            )
        ),
        evidence_urls=(
            "https://open.toronto.ca/dataset/election-results/",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "Official City and Ontario results enumerate Gary Crawford's distinctive "
            "Scarborough trustee, councillor, and provincial candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="gord-perks-house-and-toronto-council",
        preferred_name="Gord Perks",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_f7c0eb84b8ec5019a254830c562d7d25",
                    "ec-ge-39",
                    "canada_house_of_commons",
                    "mp",
                    "Gord Perks",
                ),
                (
                    "can_8beb4a28087f5a58b667f68fdc297a43",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_city_council",
                    "councillor",
                    "Gord Perks",
                ),
                (
                    "can_531164ded0fe544494b2d2f5a84d639e",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Gord Perks",
                ),
                (
                    "can_eb15951728215f8ab958874d4a9f29ef",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Gord Perks",
                ),
                (
                    "can_f016d26c42dc5073b6e91d974223d0a7",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Gord Perks",
                ),
                (
                    "can_5d3cda342f5d5ce9a7bcb18578d4c2b7",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Gord Perks",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-4/",
            "https://www.elections.ca/content.aspx?section=ele&dir=pas&document=index&lang=e",
        ),
        rationale=(
            "Official federal results and the City profile enumerate Gord Perks's "
            "2006 federal candidacy and Council service beginning later that year."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="james-pasternak-tdsb-and-toronto-council",
        preferred_name="James Pasternak",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_23603e0f033f5d53adceae86b77499e9",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_district_school_board",
                    "trustee",
                    "James Pasternak",
                ),
                (
                    "can_f88f71f9c7545f00843d33367c97affe",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "James Pasternak",
                ),
                (
                    "can_856d4ee5096e513396905274d05cf7f7",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "James Pasternak",
                ),
                (
                    "can_56769676131c5f708884abdfea79deef",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "James Pasternak",
                ),
                (
                    "can_86b4a8b96048544897930f1f1cd40336",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "James Pasternak",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-6/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "The official City profile identifies Councillor James Pasternak as a former "
            "elected TDSB trustee, and Clerk results enumerate the career."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="jim-karygiannis-house-and-toronto-council",
        preferred_name="Jim Karygiannis",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_7727d9606e245998acd2afc85b0132b0",
                    "ec-ge-38",
                    "canada_house_of_commons",
                    "mp",
                    "Jim Karygiannis",
                ),
                (
                    "can_5423962cd05e5dde8f272ba11190058a",
                    "ec-ge-39",
                    "canada_house_of_commons",
                    "mp",
                    "Jim Karygiannis",
                ),
                (
                    "can_d2771c88bde4517d8cda13f513c2bd3c",
                    "ec-ge-40",
                    "canada_house_of_commons",
                    "mp",
                    "Jim Karygiannis",
                ),
                (
                    "can_5d5edae72eb55d0293328563e8444194",
                    "ec-ge-41",
                    "canada_house_of_commons",
                    "mp",
                    "Jim Karygiannis",
                ),
                (
                    "can_88b3844764dd5dd88e82c008ea736c9f",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Jim Karygiannis",
                ),
                (
                    "can_90703f4980675e04b76afb995545f0ef",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Jim Karygiannis",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/Members/en/Jim-Karygiannis%28946%29/Roles",
            "https://www.toronto.ca/legdocs/mmis/2020/cc/bgrd/backgroundfile-157017.pdf",
        ),
        rationale=(
            "Official House service and City Clerk records establish Jim Karygiannis's "
            "federal service and subsequent Toronto Council candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="joe-cressy-house-and-toronto-council",
        preferred_name="Joe Cressy",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_e0a028c2f20458cd81bedc516dac3410",
                    "ec-be-2014-06-30",
                    "canada_house_of_commons",
                    "mp",
                    "Joe Cressy",
                ),
                (
                    "can_ce513505751c5fccb73b36106b10ed4e",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Joe Cressy",
                ),
                (
                    "can_c17e828fbf045e0087095cfa28321105",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Joe Cressy",
                ),
            )
        ),
        evidence_urls=(
            "https://www.elections.ca/content.aspx?section=ele&dir=pas&document=index&lang=e",
            "https://www.toronto.ca/legdocs/mmis/2020/ra/comm/communicationfile-101734.pdf",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official federal results and City records enumerate Joe Cressy's 2014 "
            "federal by-election followed by his two Council candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="john-campbell-tdsb-council-and-ontario",
        preferred_name="John Campbell",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_bb00e56bd2a85b5b92bcc4dfdc30f9ff",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_district_school_board",
                    "trustee",
                    "John Campbell",
                ),
                (
                    "can_9e56f2c4d8c25531827aa728d365e9e4",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_district_school_board",
                    "trustee",
                    "John Campbell",
                ),
                (
                    "can_1fd2c30b34d15e9d944754561a4a9fb2",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "John Campbell",
                ),
                (
                    "can_0cfdf019986053d3b8d100be96affc39",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "John Campbell",
                ),
                (
                    "can_c2dcebb36674540fb4ff568b9601a8f4",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "John Campbell",
                ),
                (
                    "can_20457f117bb65087a63e259b524c4490",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "JOHN CAMPBELL",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/legdocs/mmis/2023/cc/bgrd/backgroundfile-237078.pdf",
            "https://results.elections.on.ca/",
        ),
        rationale=(
            "An official City appointment biography records John Campbell's TDSB and "
            "Council service; official Ontario results add his Etobicoke Centre candidacy."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="josh-matlow-tdsb-council-and-mayor",
        preferred_name="Josh Matlow",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_3dd78f34f1435a1e92fc95c696a84c3d",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_district_school_board",
                    "trustee",
                    "Josh Matlow",
                ),
                (
                    "can_5eb9f5cd6cd150c6a215d128a06384ef",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_district_school_board",
                    "trustee",
                    "Josh Matlow",
                ),
                (
                    "can_c7d68ddda26d5d3388726dcf769561a1",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Josh Matlow",
                ),
                (
                    "can_5cf9914b09975c18bcc88e097347be1b",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Josh Matlow",
                ),
                (
                    "can_959affa9be1555e5bc0612838e927027",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Josh Matlow",
                ),
                (
                    "can_a5a51a39a0825accaf1a1112adefeedf",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Josh Matlow",
                ),
                (
                    "can_86279ea21cd45f0aa99a14ac1c438362",
                    "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                    "toronto_city_council",
                    "mayor",
                    "Josh Matlow",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-12/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "The official City profile records Josh Matlow's 2003-2010 school-trustee "
            "service before Council; Clerk results also enumerate his mayoral candidacy."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="kristyn-wong-tam-council-and-ontario-legislature",
        preferred_name="Kristyn Wong-Tam",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_17380900981854e9b7a8873349f77f93",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Kristyn Wong-Tam",
                ),
                (
                    "can_0d15b129859b50f39c14ee0d4b5b0141",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Kristyn Wong-Tam",
                ),
                (
                    "can_c370bbf8fd765d9694fd4f089ba3d462",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Kristyn Wong-Tam",
                ),
                (
                    "can_edb6496df3fc5b4488aafabb86f74ad8",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "KRISTYN WONG-TAM",
                ),
                (
                    "can_56c633540fdb540b929245d6652335b2",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "KRISTYN WONG-TAM",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/kristyn-wong-tam",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature and City Clerk records enumerate Kristyn Wong-Tam's "
            "Toronto Council and Ontario Legislature candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="rachel-chernos-lin-tdsb-and-toronto-council",
        preferred_name="Rachel Chernos Lin",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_639fd0ca9a9b5b89bae10776187e87b8",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_district_school_board",
                    "trustee",
                    "Lin Rachel Chernos",
                ),
                (
                    "can_ffe4e7bf73405578ba3a683590294d80",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_district_school_board",
                    "trustee",
                    "Lin Rachel Chernos",
                ),
                (
                    "can_d76fc0919aba52d79fa61644ab457786",
                    "evt_af73d490abf95ffdae38ca2c830e51f4",
                    "toronto_city_council",
                    "councillor",
                    "Lin Rachel Chernos",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-15/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "The official City profile identifies Rachel Chernos Lin as the six-year "
            "TDSB trustee elected to Council; Clerk results use surname-first ballot order."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="mary-margaret-mcmahon-council-and-ontario-legislature",
        preferred_name="Mary-Margaret McMahon",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_c9296961f4af5a46874ce7428a5ef234",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Mary-Margaret Mcmahon",
                ),
                (
                    "can_101cffe6738b513b8c5049148f624dc5",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Mary-Margaret Mcmahon",
                ),
                (
                    "can_4d8dc54a33fd5c31b0e7f05ee858ecfc",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MARY-MARGARET MCMAHON",
                ),
                (
                    "can_b760aa686bf859f7aa4f2493a617f48e",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MARY-MARGARET MCMAHON",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/mary-margaret-mcmahon",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature and City Clerk records enumerate Mary-Margaret "
            "McMahon's Council and Ontario Legislature candidacies in east Toronto."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="michael-ford-tdsb-council-and-ontario-legislature",
        preferred_name="Michael Ford",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_19aa99d84a725f00b7cfceaa8e4887c3",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Michael Ford",
                ),
                (
                    "can_6144c5a90b155256a2d43c7a997028a3",
                    "evt_552c4874312956ae84afbbc5ee91b0f7",
                    "toronto_city_council",
                    "councillor",
                    "Michael Ford",
                ),
                (
                    "can_b52f6554caab5bc08b7deca203ffd5d5",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Michael Ford",
                ),
                (
                    "can_f7ad3840348f5b009bb14c453352c4ea",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MICHAEL FORD",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/michael-ford",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature and City Clerk records enumerate Michael Ford's "
            "trustee, councillor, and MPP career in west Toronto."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="mike-colle-ontario-legislature-and-toronto-council",
        preferred_name="Mike Colle",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_2f7221d8d9b15b028a2ce9aa13178c71",
                    "on-2003-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MIKE COLLE",
                ),
                (
                    "can_8fc3573dca815e5e9d516102bd61b02f",
                    "on-2007-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MIKE COLLE",
                ),
                (
                    "can_67da3175eae456cc83e33f96657c0ad8",
                    "on-2011-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MIKE COLLE",
                ),
                (
                    "can_ad377c3e1d415431a3668f9824811844",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MIKE COLLE",
                ),
                (
                    "can_9f9f88774d505566a07d28752201950a",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Mike Colle",
                ),
                (
                    "can_4f560ce4f469526a9aead47e762a7cd1",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Mike Colle",
                ),
                (
                    "can_1c713059ec0357ccb3294d4ec433ba51",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Mike Colle",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-8/",
            "https://www.ola.org/en/members/all/mike-colle",
        ),
        rationale=(
            "The official City profile explicitly records Mike Colle's long MPP and "
            "municipal career; the Legislature page supplies his service dates."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="neethan-shan-ontario-tdsb-and-toronto-council",
        preferred_name="Neethan Shan",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_16b9fa21f84e568885fef5ba20933fff",
                    "on-2007-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "NEETHAN SHAN",
                ),
                (
                    "can_17118493cdb85060a2d2685c20dcc532",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Neethan Shan",
                ),
                (
                    "can_80111774b24f54128f783f2225bca00d",
                    "on-2011-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "NEETHAN SHAN",
                ),
                (
                    "can_4de56dfafaf555e783ebc90ce06d2010",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "NEETHAN SHAN",
                ),
                (
                    "can_1b2e5192cb9552c08e983fae4c79036a",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Neethan Shan",
                ),
                (
                    "can_96bbbf817211526f81353abf3c8c140d",
                    "evt_3db5605f67e85c3a988ee6fcbcee0c3b",
                    "toronto_district_school_board",
                    "trustee",
                    "Neethan Shan",
                ),
                (
                    "can_18b256029a065277a9f83479760df9b6",
                    "on-2016-09-01-by-083",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Neethan Shan",
                ),
                (
                    "can_d32f7b73487a5b4b8a859a8b5f061ef2",
                    "evt_b8284a5341635f79babdf7ddc512c2f6",
                    "toronto_city_council",
                    "councillor",
                    "Neethan Shan",
                ),
                (
                    "can_8fba857b4440581999ddfd32c59ec62f",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Neethan Shan",
                ),
                (
                    "can_f144c9427d8f53b886a1a892f3774165",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "NEETHAN SHAN",
                ),
                (
                    "can_2c498ad7b98451f3841d359ad2ea2dfa",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_district_school_board",
                    "trustee",
                    "Neethan Shan",
                ),
                (
                    "can_2a0745629be0507080db6d72f4a6719b",
                    "evt_ca435dada07f5ed9b041b7c3d24de732",
                    "toronto_city_council",
                    "councillor",
                    "Neethan Shan",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-25/",
            "https://results.elections.on.ca/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "The official City profile records Neethan Shan's education and Council "
            "leadership, while official City and Ontario results enumerate every race."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="parthi-kandavel-tdsb-and-toronto-council",
        preferred_name="Parthi Kandavel",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_d1a540a1af765d2c9ad07f891b9ce4ad",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_district_school_board",
                    "trustee",
                    "Parthi Kandavel",
                ),
                (
                    "can_eec30336e5f655169d4d44e899be30f0",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Parthi Kandavel",
                ),
                (
                    "can_5c59730d115956838c05850a844c053d",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_district_school_board",
                    "trustee",
                    "Parthi Kandavel",
                ),
                (
                    "can_e978a37d2ea154dc805027bc3a8bac0a",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "councillor",
                    "Parthi Kandavel",
                ),
                (
                    "can_f1b42d3592b7525a8f115be4bfac3951",
                    "evt_ee5715a80b5a532c8b778d94f6b7c9b8",
                    "toronto_city_council",
                    "councillor",
                    "Parthi Kandavel",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-20/",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "The official City profile records Parthi Kandavel's 2014-2022 TDSB service "
            "before Council, and Clerk results enumerate both offices."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="peter-milczyn-toronto-council-and-ontario-legislature",
        preferred_name="Peter Milczyn",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_6e72b441059f50d0aea1839508bed40c",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_city_council",
                    "councillor",
                    "Peter Milczyn",
                ),
                (
                    "can_c255829bac5c5cde8fa8a9221390b2f1",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_city_council",
                    "councillor",
                    "Peter Milczyn",
                ),
                (
                    "can_e0998ace6afe5dbaafc18a2b31c0b812",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Peter Milczyn",
                ),
                (
                    "can_d90a09d26e075aa2a005677d8deafaa0",
                    "on-2013-08-01-by-024",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER MILCZYN",
                ),
                (
                    "can_dc1e0f7a3f31561b90058f15fdb5d0dc",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER MILCZYN",
                ),
                (
                    "can_81f1b976cea055ca8d4e77a06227af23",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Peter Milczyn",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/peter-milczyn",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature and City Clerk records enumerate Peter Milczyn's "
            "Etobicoke-Lakeshore Council and Ontario candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="raymond-cho-house-council-and-ontario-legislature",
        preferred_name="Raymond Cho",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_600ec65088db5187ad17909952b07cc0",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_city_council",
                    "councillor",
                    "Raymond Cho",
                ),
                (
                    "can_076030eee89e573cb699ae9ac3f6d6d7",
                    "ec-ge-38",
                    "canada_house_of_commons",
                    "mp",
                    "Raymond Cho",
                ),
                (
                    "can_422c97b4a4185ea09fb912aa8dedeca7",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_city_council",
                    "councillor",
                    "Raymond Cho",
                ),
                (
                    "can_51741eac631e59bdb399fce4c7c81686",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Raymond Cho",
                ),
                (
                    "can_c0207fc8c78357b1bf71664eeef7a19a",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "RAYMOND CHO",
                ),
                (
                    "can_9a9fedcc800858c0a0006939568cc607",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Raymond Cho",
                ),
                (
                    "can_5ceaef5de2cd5d15ba8bfe17ed0cff23",
                    "on-2016-09-01-by-083",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Raymond Cho",
                ),
                (
                    "can_8a7501cd489353118a6504929408958d",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Raymond Cho",
                ),
                (
                    "can_a44ea817ed6753e6814372fe826fc238",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "RAYMOND CHO",
                ),
                (
                    "can_746d0e3ec9ad502295fd5a24d8ad9874",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "RAYMOND CHO",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/raymond-cho",
            "https://open.toronto.ca/dataset/election-results/",
            "https://www.elections.ca/content.aspx?section=ele&dir=pas&document=index&lang=e",
        ),
        rationale=(
            "Official federal, City, and Legislature records enumerate Raymond Cho's "
            "federal candidacy, long Council service, and Ontario Legislature career."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="peter-tabuns-house-and-ontario-legislature",
        preferred_name="Peter Tabuns",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_f38e3b03a2aa5d3fb15a17ee44122ba3",
                    "ec-ge-38",
                    "canada_house_of_commons",
                    "mp",
                    "Peter Tabuns",
                ),
                (
                    "can_204a1c949cb55de0b68d06c11261b76b",
                    "on-2006-03-30-by-008",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER TABUNS",
                ),
                (
                    "can_55cf535ab16050c881e6a77bf35a28d4",
                    "on-2007-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER TABUNS",
                ),
                (
                    "can_a95f063774e852eb91f5a8d1cea4ce5e",
                    "on-2011-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER TABUNS",
                ),
                (
                    "can_14cb8a02ba88585bbe5e430d15d0b36a",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER TABUNS",
                ),
                (
                    "can_70eda15ce436548dbb4c3ce0d5cba7fa",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Peter Tabuns",
                ),
                (
                    "can_8fc36b0e7cd150e28e6536e334b1740b",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER TABUNS",
                ),
                (
                    "can_810fac56b1ff55168829588ef729fec2",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "PETER TABUNS",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/peter-tabuns",
            "https://www.elections.ca/content.aspx?section=ele&dir=pas&document=index&lang=e",
        ),
        rationale=(
            "Official federal results and the Legislature service record identify Peter "
            "Tabuns's 2004 House candidacy and continuous Toronto-Danforth MPP career."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="shaun-chen-tdsb-and-house",
        preferred_name="Shaun Chen",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_f8a40a8fa18d51919238143f9e290557",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_district_school_board",
                    "trustee",
                    "Shaun Chen",
                ),
                (
                    "can_8cd606911059554fa75b1b91f160cda7",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_district_school_board",
                    "trustee",
                    "Shaun Chen",
                ),
                (
                    "can_27fc9b138a1153bf80da7e241869d02b",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_district_school_board",
                    "trustee",
                    "Shaun Chen",
                ),
                (
                    "can_e144c275ed5054a2bbfa3b26820749cd",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Shaun Chen",
                ),
                (
                    "can_d15277b821b159aca74ef807704ab509",
                    "ec-ge-42",
                    "canada_house_of_commons",
                    "mp",
                    "Shaun Chen",
                ),
                (
                    "can_deda0685158c5f92b8995796bd979722",
                    "ec-ge-43",
                    "canada_house_of_commons",
                    "mp",
                    "Shaun Chen",
                ),
                (
                    "can_5667198ba19058028f6237c17567a0f4",
                    "ec-ge-44",
                    "canada_house_of_commons",
                    "mp",
                    "Shaun Chen",
                ),
                (
                    "can_b80ef7e47b7356e98b7a00dab311a4f3",
                    "ec-ge-45",
                    "canada_house_of_commons",
                    "mp",
                    "Shaun Chen",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ourcommons.ca/members/en/shaun-chen%2888953%29/roles",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official House roles and City Clerk results enumerate Shaun Chen's TDSB "
            "career and four consecutive Scarborough North House victories."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="chris-glover-tdsb-and-ontario-legislature",
        preferred_name="Chris Glover",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_ec1d9122800f5a578fc8cbfa7bcfec70",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_district_school_board",
                    "trustee",
                    "Chris Glover",
                ),
                (
                    "can_9c2c039e25215520b7ec7791ae1c287e",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Chris Glover",
                ),
                (
                    "can_2dba55c23d515c9f8a8dab60c82d7ade",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Chris Glover",
                ),
                (
                    "can_86170a2bce0558f5a4e743009f064384",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "CHRIS GLOVER",
                ),
                (
                    "can_58ad579555da59ae983dbd35a8fda9ae",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "CHRIS GLOVER",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/chris-glover",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature and City Clerk records enumerate Chris Glover's "
            "TDSB service followed by three Spadina-Fort York MPP victories."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="marit-stiles-tdsb-and-ontario-legislature",
        preferred_name="Marit Stiles",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_8e4a47a2e6a25c6db6c3ca38de4b8d29",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Marit Stiles",
                ),
                (
                    "can_324b2301e0f4545fad74ebaccde28118",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Marit Stiles",
                ),
                (
                    "can_62c3065af1b1545281f84e5e55372cf7",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MARIT STILES",
                ),
                (
                    "can_2d97552df0bf5a70bf71fc3acf89efcc",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "MARIT STILES",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/marit-stiles",
            "https://open.toronto.ca/dataset/election-results/",
        ),
        rationale=(
            "Official Legislature and City Clerk records enumerate Marit Stiles's TDSB "
            "candidacy and three consecutive Davenport MPP victories."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="doly-begum-ontario-legislature-and-house",
        preferred_name="Doly Begum",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_abb6faabbc065711b92ee3958ba76f2e",
                    "on-2018-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "Doly Begum",
                ),
                (
                    "can_8110023eb28f5154a1ed25bd78a610a1",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "DOLY BEGUM",
                ),
                (
                    "can_9fe8bd4e9c9a563ba441baf9fc4a5d5b",
                    "on-2025-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "DOLY BEGUM",
                ),
                (
                    "can_2690e670e97d5b9fb8ea0ee9d0fa4000",
                    "ec-be-2026-04-13",
                    "canada_house_of_commons",
                    "mp",
                    "Doly Begum",
                ),
            )
        ),
        evidence_urls=(
            "https://www.ola.org/en/members/all/doly-begum",
            "https://www.ourcommons.ca/members/en/doly-begum%28141713%29/roles",
        ),
        rationale=(
            "Official Legislature and House records enumerate Doly Begum's Scarborough "
            "Southwest MPP service and 2026 House by-election victory."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="mike-del-grande-council-and-tcdsb",
        preferred_name="Mike Del Grande",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_bd0921cb9ddf5bcba146356def6cd49e",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_city_council",
                    "councillor",
                    "Mike Del Grande",
                ),
                (
                    "can_5b097b27e81255779a7fa1be9aaa4766",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_city_council",
                    "councillor",
                    "Mike Del Grande",
                ),
                (
                    "can_318c114495bb5951a5a4b056d33958ba",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Mike Del Grande",
                ),
                (
                    "can_3fae5a4c073a5b7ba05b5c2a79ec8292",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "Mike Del Grande",
                ),
                (
                    "can_d573e0d5beaa582a92c83ba9848720d2",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "Mike Del Grande",
                ),
                (
                    "can_7696b48989c8537290cecffd1029c056",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "Mike Del Grande",
                ),
            )
        ),
        evidence_urls=("https://open.toronto.ca/dataset/election-results/",),
        rationale=(
            "Official City Clerk results enumerate Mike Del Grande's three Council and "
            "three Catholic school-board victories in adjacent Scarborough districts."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="michael-guenther-tdsb-ballot-order-alias",
        preferred_name="Michael Guenther",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_d9bcea92d50f5902a18dae2c8f890666",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "Michael Guenther",
                ),
                (
                    "can_b0e16ac4edef5ad59f1d7c1ca0355482",
                    "evt_8ca589beb65b56f5863df3f1f1b621fd",
                    "toronto_district_school_board",
                    "trustee",
                    "Guenther Michael",
                ),
            )
        ),
        evidence_urls=(
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/0190932e-d817-4d8e-8634-8a1cc8cf5a9d/download/2016-tdsb-ward-14.xlsx",
        ),
        rationale=(
            "Official Clerk files record Michael Guenther/Guenther Michael in the same "
            "TDSB Ward 14 general-election and ensuing by-election sequence."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="alain-masson-viamonde-ballot-order-alias",
        preferred_name="Alain Masson",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_7343d07b0cfd59c4bf15318716932095",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Masson Alain",
                ),
                (
                    "can_1552114e938f5a1090946e4911b0b40f",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Alain Masson",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
        ),
        rationale=(
            "Official Clerk declarations record consecutive Viamonde Ward 4 "
            "acclamations with only the ballot-name order reversed."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="genevieve-oger-viamonde-ballot-order-alias",
        preferred_name="Geneviève Oger",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_00add64fe81e53c5b8e79b1f96215e22",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Geneviève Oger",
                ),
                (
                    "can_b0d1c647178256309bb98544e892f006",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Oger Geneviève",
                ),
            )
        ),
        evidence_urls=(
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip",
            "https://www.toronto.ca/wp-content/uploads/2022/08/8e0d-Declaration-of-Acclamation.pdf",
        ),
        rationale=(
            "Official Clerk records identify the elected and then acclaimed Viamonde "
            "Ward 4 trustee with only the ballot-name order reversed."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="benoit-fortin-viamonde-ballot-order-alias",
        preferred_name="Benoit Fortin",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_743f820f19635d66a871a335827f1da0",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Benoit Fortin",
                ),
                (
                    "can_628f2c912c1c5b3481375b971c2d0965",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Fortin Benoit",
                ),
            )
        ),
        evidence_urls=(
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip",
            "https://www.toronto.ca/wp-content/uploads/2022/08/8e0d-Declaration-of-Acclamation.pdf",
        ),
        rationale=(
            "Official Clerk records identify the elected and then acclaimed Viamonde "
            "Ward 2 trustee with only the ballot-name order reversed."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="denys-begin-viamonde-name-aliases",
        preferred_name="Denys Bégin",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_733d7aab27a05f26ac3f9f859c22e362",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Begin Denys",
                ),
                (
                    "can_0c86cdbf79bf5fc2826273a25cca30bc",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Denys Begin",
                ),
                (
                    "can_733e4e9f1593577bb40718aef42b142e",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Denys Bégin",
                ),
                (
                    "can_5766cd7a70a4579692abeedf1050fd07",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Denys Bégin",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3fb1227c-a279-4523-a1aa-f00190ba717f/download/2006-results.zip",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip",
        ),
        rationale=(
            "Official Clerk records enumerate the same Viamonde Ward 3 trustee across "
            "four elections despite surname-first and accent variants."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="nathalie-dufour-seguin-monavenir-ballot-order-alias",
        preferred_name="Nathalie Dufour-Séguin",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_7b5ec59e565b5cdfb9767c7566927b16",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "conseil_scolaire_catholique_monavenir",
                    "trustee",
                    "Nathalie Dufour-Séguin",
                ),
                (
                    "can_6f46210505ba52b4bfb52811104c5d98",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "conseil_scolaire_catholique_monavenir",
                    "trustee",
                    "Séguin Nathalie Dufour",
                ),
                (
                    "can_eac6520df09c55148fb063fb0c80e4a5",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "conseil_scolaire_catholique_monavenir",
                    "trustee",
                    "Séguin Nathalie Dufour",
                ),
                (
                    "can_11ede9c2b79853e9a17c4972d0f34f08",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "conseil_scolaire_catholique_monavenir",
                    "trustee",
                    "Dufour Séguin Nathalie",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip",
            "https://www.toronto.ca/wp-content/uploads/2022/08/8e0d-Declaration-of-Acclamation.pdf",
        ),
        rationale=(
            "Official Clerk declarations enumerate Nathalie Dufour-Séguin as the same "
            "MonAvenir Ward 3 trustee under changing surname-first ballot order."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="chris-macdonald-toronto-council-name-alias",
        preferred_name="Chris Macdonald",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_b0b7cd558a5257dd8a7665e266f4b7b8",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Chris Macdonald",
                ),
                (
                    "can_b58a883a51da5cf88885ef127b9762b2",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Chris Mac Donald",
                ),
            )
        ),
        evidence_urls=("https://open.toronto.ca/dataset/election-results/",),
        rationale=(
            "Official Clerk results record Chris Macdonald/Mac Donald in the same "
            "Toronto Council ward in consecutive general elections."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="ana-bailao-toronto-council-and-mayor",
        preferred_name="Ana Bailão",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_e6c8120b0e0f5dd29b77e92143ebd30e",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "toronto_city_council",
                    "councillor",
                    "Ana Bailao",
                ),
                (
                    "can_8b6bf34be2875df09f7015637c112ccd",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Ana Bailão",
                ),
                (
                    "can_e20224e32d205d5f8ee21f1cba9c6661",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "councillor",
                    "Ana Bailão",
                ),
                (
                    "can_a9d93ea575e9511aad1985615dbd47f9",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "Ana Bailão",
                ),
                (
                    "can_f9c65b5f49305573ac4de1d27b1e8fca",
                    "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                    "toronto_city_council",
                    "mayor",
                    "Ana Bailão",
                ),
            )
        ),
        evidence_urls=(
            "https://open.toronto.ca/dataset/election-results/",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
        ),
        rationale=(
            "Official Clerk records enumerate Ana Bailão's Council career and 2023 "
            "mayoral candidacy despite the 2003 source omitting her accent."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="francois-guerin-viamonde-name-aliases",
        preferred_name="François Guérin",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_90f657c136335edeb00a8cc29149c879",
                    "evt_d89f777f34365c37b114ca39fb376591",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Guerin Francois",
                ),
                (
                    "can_b2d412b66c435cc9b7019dd07a9a3fa0",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "François Guérin",
                ),
                (
                    "can_c4dd83a96c0c5ee5b8228998e021129c",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "François Guérin",
                ),
            )
        ),
        evidence_urls=(
            "https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3fb1227c-a279-4523-a1aa-f00190ba717f/download/2006-results.zip",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip",
        ),
        rationale=(
            "Official Clerk records enumerate the same Viamonde Ward 2 trustee across "
            "three elections despite surname-first and accent variants."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="robert-rishchynski-house-name-alias",
        preferred_name="Robert Rishchynski",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_b96f90176e9b5cb1b2f3b421e3ff46f8",
                    "ec-ge-39",
                    "canada_house_of_commons",
                    "mp",
                    "Robert L. Rishchynski",
                ),
                (
                    "can_9243fc9d83715171ae5d5afac552f195",
                    "ec-ge-40",
                    "canada_house_of_commons",
                    "mp",
                    "Robert Rishchynski",
                ),
            )
        ),
        evidence_urls=(
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip",
        ),
        rationale=(
            "Official Elections Canada records identify the same Green candidate in "
            "Parkdale-High Park in consecutive elections with one middle initial omitted."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="silvio-ursomarzo-ontario-name-alias",
        preferred_name="Silvio Ursomarzo",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_9c8db00caa425cd19c4c5e2758ce717d",
                    "on-2003-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "SILVIO URSOMARZO",
                ),
                (
                    "can_d97fbc278da55333bb04ac1133ec3366",
                    "on-2006-09-14-by-064",
                    "ontario_legislative_assembly",
                    "mpp",
                    "SILVIO URSOMARZO",
                ),
                (
                    "can_3f272f46a83656d987a363d43d99903b",
                    "on-2007-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "SYLVIO URSOMARZO",
                ),
                (
                    "can_81440ac9b5fc574b954ec9ca1ed33ea3",
                    "on-2011-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "SILVIO URSOMARZO",
                ),
            )
        ),
        evidence_urls=(
            "https://results.elections.on.ca/api/report-groups/5/report-outputs/521/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/510/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
        ),
        rationale=(
            "Official Elections Ontario records enumerate the distinctive Freedom Party "
            "candidate across four Toronto races with a single Silvio/Sylvio variation."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="erwin-sniedzins-cross-office-name-alias",
        preferred_name="Erwin Sniedzins",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_26bc661e3752510c8b692d6eeed7b6a4",
                    "on-2014-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "ERWIN SNIEDZINS",
                ),
                (
                    "can_82d24823c9fb587586157f07a784f565",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_city_council",
                    "mayor",
                    "Erwin Sniedzins",
                ),
                (
                    "can_6ea1dce4d8445facbf414b2804469c32",
                    "on-2022-general",
                    "ontario_legislative_assembly",
                    "mpp",
                    "ERWIN E. SNIEDZINS",
                ),
                (
                    "can_17b9b1501a9f501192c5fb4475759209",
                    "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                    "toronto_city_council",
                    "mayor",
                    "Erwin Sniedzins",
                ),
            )
        ),
        evidence_urls=(
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
        ),
        rationale=(
            "Official Ontario and Toronto Clerk records enumerate the distinctive Erwin "
            "Sniedzins candidacies with one source adding a middle initial."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="george-smitherman-ontario-mayor-and-council-candidacies",
        preferred_name="George Smitherman",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_3d13fbd9fab452a5b347fb048574b6c4",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "mayor",
                    "George Smitherman",
                ),
                (
                    "can_9c393c7edd9a51abbf0033c980bdad32",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_city_council",
                    "councillor",
                    "George Smitherman",
                ),
            )
        ),
        registry_person_ids=("per_58016e26ffa55f6bbdc8f7490273a4a5",),
        evidence_urls=(
            "https://www.ola.org/members/all/george-smitherman",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf",
        ),
        rationale=(
            "The Ontario Legislature records George Smitherman's Toronto Centre service, "
            "and the Clerk's declarations enumerate his distinctive 2010 mayoral and 2018 "
            "Toronto Centre council candidacies."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="mark-saunders-ontario-and-2023-mayoral-candidacies",
        preferred_name="Mark Saunders",
        occurrences=(
            _pinned_occurrence(
                "can_b0b70cf1154d5e858ffac38014484f05",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Mark Saunders",
            ),
        ),
        registry_person_ids=("per_6df1a502d1b450369a2cc47794639812",),
        evidence_urls=(
            "https://results.elections.on.ca/",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
        ),
        rationale=(
            "The official Ontario and Toronto results enumerate former Toronto Police "
            "Chief Mark Saunders in the 2022 Don Valley West and 2023 mayoral contests."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="giorgio-mammoliti-2023-mayoral-candidacy",
        preferred_name="Giorgio Mammoliti",
        occurrences=(
            _pinned_occurrence(
                "can_730259967f36585598760e9f9f4b4cd8",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Giorgio Mammoliti",
            ),
        ),
        registry_person_ids=("per_3ec4e3ff861d57519f52e15b4a9449a7",),
        evidence_urls=(
            "https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
        ),
        rationale=(
            "The Clerk's official results enumerate the distinctive Giorgio Mammoliti "
            "council career and his 2023 mayoral candidacy."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="sarah-climenhaga-federal-and-mayoral-candidacies",
        preferred_name="Sarah Climenhaga",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_c334cb1e92d255c6a441a8867418a9b4",
                    "ec-ge-43",
                    "canada_house_of_commons",
                    "mp",
                    "Sarah Climenhaga",
                ),
                (
                    "can_95f6966eeeaf570994a1f923be18a673",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_city_council",
                    "mayor",
                    "Sarah Climenhaga",
                ),
                (
                    "can_e29a2b37b9395de1bcb1af5ea59e9dcf",
                    "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                    "toronto_city_council",
                    "mayor",
                    "Sarah Climenhaga",
                ),
            )
        ),
        registry_person_ids=("per_79d654cb934c519998b37e8bfc06f367",),
        evidence_urls=(
            "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip",
            "https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
        ),
        rationale=(
            "Elections Canada and the Toronto Clerk enumerate the distinctive Sarah "
            "Climenhaga candidacies in 2018, 2019, 2022, and 2023."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="blake-acton-consecutive-mayoral-candidacies",
        preferred_name="Blake Acton",
        occurrences=(
            _pinned_occurrence(
                "can_614e274e63b4587b90300c8c0e66cae3",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Blake Acton",
            ),
        ),
        registry_person_ids=("per_830dd3152c6253f7b9bf701d1527612e",),
        evidence_urls=(
            "https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
        ),
        rationale=(
            "The Clerk's official results enumerate Blake Acton in consecutive 2022 "
            "and 2023 Toronto mayoral contests."
        ),
    ),
    CuratedIdentityAssertion(
        assertion_id="rob-davis-council-trustee-and-2023-mayoral-candidacies",
        preferred_name="Rob Davis",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_eef751b2c751567ca5e2fef90195b6d1",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_city_council",
                    "councillor",
                    "Rob Davis",
                ),
                (
                    "can_75c8eb6bbeef5bedb5a843a5e5fbf76e",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "Rob Davis",
                ),
                (
                    "can_ed44c908817556eea92c054dd42725eb",
                    "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                    "toronto_city_council",
                    "mayor",
                    "Rob Davis",
                ),
            )
        ),
        registry_person_ids=("per_2a0809ffec18563292e0e1363aff66f6",),
        evidence_urls=(
            "https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf",
            "https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf",
            "https://www.excal.on.ca/news/2023/06/09/rob-davis-q-a-interview-2023-mayoral-by-election/",
            "https://thelocal.to/toronto-mayor-candidates-2023/",
        ),
        rationale=(
            "The Clerk's declarations enumerate each occurrence; the candidate interview "
            "records his former council and trustee service, and The Local's fact-checked "
            "biography explicitly identifies the 2003, 2010, 2018, and 2023 runs."
        ),
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_same_office_continuity_assertion(
        "dewitt-lee-municipal-exact-scope",
        "Dewitt Lee",
        "per_95aec9b2003e56e3a8c1ec0af4643dcb",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_044e84dcb5205ab4b02284c84e618507",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Dewitt Lee",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "isabella-gamk-municipal-exact-scope",
        "Isabella Gamk",
        "per_85df93151d89561a93343109120f7610",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_054eb2fc2e09599fb24638e8d9abbc2f",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Isabella Gamk",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "brenda-macdonald-municipal-exact-scope",
        "Brenda Macdonald",
        "per_1f8c7e0c542c5b0594ffd20412708283",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_0d28bf80198455f89a27b70fee1a2d66",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Brenda Macdonald",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "tushar-shah-municipal-exact-scope",
        "Tushar Shah",
        "per_1ef96557cdb55741aba382ef029439b8",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_16e02100d3f158169a503c56f96a79d5",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Tushar Shah",
            ),
            (
                "can_63a60345fb67570d88a6bbd77674d251",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Tushar Shah",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "christopher-ball-municipal-exact-scope",
        "Christopher Ball",
        "per_da0ef4d789325a28a1be943072e02556",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_185b0450b3f15892a40dd98dfec0c329",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Christopher Ball",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "andrei-zodian-municipal-exact-scope",
        "Andrei Zodian",
        "per_f2763cdb40aa5445a053a3c7a03ab974",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_188e925c39e15bee9e4ebf1072340f97",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Andrei Zodian",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "david-searle-municipal-exact-scope",
        "David Searle",
        "per_d920b79c56515f09adc77dd3a807662b",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_19272ccebd9f57b3ac6bd997be73fb9d",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "David Searle",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "gregory-wowchuk-municipal-exact-scope",
        "Gregory Wowchuk",
        "per_1e88dc187abc59569a7f2b123b976526",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_19870aafa99f59a1996cd855ab879e28",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Gregory Wowchuk",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "ross-vaughan-municipal-exact-scope",
        "Ross Vaughan",
        "per_48508e55df895324a7f1d9488e7bb639",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_1aa8e69f4f4953cebfd25910fccfd4cb",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Ross Vaughan",
            ),
            (
                "can_6ae83df880f259abb337baf5162e3584",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Ross Vaughan",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "charm-darby-municipal-exact-scope",
        "Charm Darby",
        "per_9aa7283fc19c5f5ea4d59648a8d88ce4",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_1d083e2aad665d829f701f70a848175a",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Charm Darby",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "gus-koutoumanos-municipal-exact-scope",
        "Gus Koutoumanos",
        "per_4da7b8716fca52c8ba22b456f88f84eb",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_1f8aa59ffb2453869c88d0f62586fa8a",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Gus Koutoumanos",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "bruce-baker-municipal-exact-scope",
        "Bruce Baker",
        "per_c420eef7408a5ba18fb38b9af7d34b5e",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_2664985b477c536fa506ae85f044300b",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Bruce Baker",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "igor-toutchinski-municipal-exact-scope",
        "Igor Toutchinski",
        "per_8764898413ab5d6c9b6a6c9c4fd950b2",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_269dbec235975e948104c0bc7fdc2457",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Igor Toutchinski",
            ),
            (
                "can_860e38a324115bfdb004feb01779d6a3",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Igor Toutchinski",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "frank-marra-municipal-exact-scope",
        "Frank Marra",
        "per_18b9831fdeae5ec0ada387c2e7cc366d",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_2f717d75299153299c40fb87dbf79c3c",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Frank Marra",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "glenn-kitchen-municipal-exact-scope",
        "Glenn Kitchen",
        "per_4c8a5911f9885151a78e4dc9a5feb8fd",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_3212e036085e5e0b95965279273429d4",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Glenn Kitchen",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-chiappetta-municipal-exact-scope",
        "John Chiappetta",
        "per_03601582a11a5435bafae7b459371a86",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_350b16f8451e567385d7988708055eae",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "John Chiappetta",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "liz-west-municipal-exact-scope",
        "Liz West",
        "per_771bc1c36d085a828fb946afb9dcc91b",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_360948fb737f5cc8af27f1ac2cd5af5c",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Liz West",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "cory-deville-municipal-exact-scope",
        "Cory Deville",
        "per_6dbd346ddaba5349b1188f1bbd6e5478",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_384b1c30cab156c8b03f1b8114f0d67a",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Cory Deville",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "daniel-walker-municipal-exact-scope",
        "Daniel Walker",
        "per_fcab4370a7af55018ff53e74fe336a1b",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_3a0998455d3d5407bba8815d842370ca",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Daniel Walker",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "leonard-subotich-municipal-exact-scope",
        "Leonard Subotich",
        "per_9f9efe37d6c257f48f14f063944cb0ba",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_3ad8d2d59f5d560d840ed68b85d88fe2",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Leonard Subotich",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "george-kash-municipal-exact-scope",
        "George Kash",
        "per_faa3b116a0fd53d893d1c16a6c367568",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_3e2ce89ef9b85e90b2671eedbaf9a606",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "George Kash",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "donald-blair-municipal-exact-scope",
        "Donald Blair",
        "per_b7e25c76766b5d0d9d113fe86e8b98d1",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_4412b17cb2895267abdf818d4269c5ba",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Donald Blair",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "cadigia-ali-municipal-exact-scope",
        "Cadigia Ali",
        "per_4affe1a2e0225d8f8da4de25810ca8f5",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_45b15eac7fae5421af50a0a12e1b27df",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Cadigia Ali",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "adam-smith-municipal-exact-scope",
        "Adam Smith",
        "per_a2a6d5049cb95d63abe9421192449873",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_465970bcaa3a54069be92ec8f08c0d6c",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Adam Smith",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "bob-smith-municipal-exact-scope",
        "Bob Smith",
        "per_17e2dabefe625e00b96160e3d410944a",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_48932970021a5fc68e44c30c115d9899",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Bob Smith",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "eddy-gasparotto-municipal-exact-scope",
        "Eddy Gasparotto",
        "per_084e1fd7935a5c9db865ff2fb335c178",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_4bc014c573a2509eb33be07746b91004",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Eddy Gasparotto",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "ashan-fernando-municipal-exact-scope",
        "Ashan Fernando",
        "per_ad24bac2b7595787a544b9f11c8f74bb",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_4db5697353ba5abcaa50be77d39d6115",
                "evt_ca435dada07f5ed9b041b7c3d24de732",
                "Ashan Fernando",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "donna-braniff-municipal-exact-scope",
        "Donna Braniff",
        "per_7b89d4ee41a9598891005444d4695c71",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_57b7d57810dc54a7a0aca1a2acf17a45",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Donna Braniff",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "arthur-smitherman-municipal-exact-scope",
        "Arthur Smitherman",
        "per_c3da58de499a5dae931ba05291323774",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_5db3f3a069335465a4133e603b3bef3f",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Arthur Smitherman",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "howard-bortenstein-municipal-exact-scope",
        "Howard Bortenstein",
        "per_3293b283161e5820ac2db9e1aa0714ad",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_62aaa059a2f557a292563921a067e74f",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Howard Bortenstein",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "chiara-padovani-municipal-exact-scope",
        "Chiara Padovani",
        "per_3d372d5668fa5a6f966616178c659706",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_6c6ffe1b743357a5b7e74c8e511ea2d9",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Chiara Padovani",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "kevin-rupasinghe-municipal-exact-scope",
        "Kevin Rupasinghe",
        "per_fb2ff1f6e9845d6c95c00b079d68dfac",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_710ea99956e75b6eb5ad0484b38a1172",
                "evt_ee5715a80b5a532c8b778d94f6b7c9b8",
                "Kevin Rupasinghe",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "ignacio-manlangit-municipal-exact-scope",
        "Ignacio Manlangit",
        "per_8541322847925446a16cea3514b60057",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_73143ac8a5a25373ac02b5f48bce79c4",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Ignacio Manlangit",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "barry-hubick-municipal-exact-scope",
        "Barry Hubick",
        "per_a825f17b2ec75c1ba46c10f210986af2",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_802279c1c5745c7a8394585b05f9ebd1",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Barry Hubick",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "anthony-caputo-municipal-exact-scope",
        "Anthony Caputo",
        "per_cde7712942e25a9faee86b66c8b801db",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_8701980add2d57a6816f24918ad1e41c",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Anthony Caputo",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "darren-atkinson-municipal-exact-scope",
        "Darren Atkinson",
        "per_a49b2b1d5390538b931d307bf5e340ce",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_89157cd83df2549390ae39ffbb9a8aa8",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Darren Atkinson",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "kirk-jensen-municipal-exact-scope",
        "Kirk Jensen",
        "per_82ee6b7d69235afd8bb9c5999b0b90ef",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_8e576cfe93f65a0c81cefb24ea94dced",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Kirk Jensen",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "gus-cusimano-municipal-exact-scope",
        "Gus Cusimano",
        "per_6b1c1a35839452c8a7c90c95104d12e9",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_99003a4aad175d408aa0e6e832a33e9f",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Gus Cusimano",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "enza-anderson-municipal-exact-scope",
        "Enza Anderson",
        "per_6748b30dace459e9b5118bc9f6f33f9b",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_9bf24221219c5b17bf34790baf38552f",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Enza Anderson",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-laforet-municipal-exact-scope",
        "John Laforet",
        "per_315d4642eea05bdab1e6ff51076acd6a",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_9d6ede0d3f7d515bb20565eaee91549c",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "John Laforet",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "george-maxwell-municipal-exact-scope",
        "George Maxwell",
        "per_89deabeb1f4d593992a7cfd4947fa391",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_af98dbfee77851d0b921b74a11550565",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "George Maxwell",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jim-mcmillan-municipal-exact-scope",
        "Jim Mcmillan",
        "per_fabe9f9b66715eaa94e6d36deafeae97",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_afeda32c9307596999bd3babab755d5a",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Jim Mcmillan",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "logan-choy-municipal-exact-scope",
        "Logan Choy",
        "per_5639f3389cb55fc2a2f0738002e3925f",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_b100c69f82125c7e802906fdc227b70a",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Logan Choy",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jim-conlon-municipal-exact-scope",
        "Jim Conlon",
        "per_c635284d534157a0a4f566bc99bd9f01",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_b46f915444465214937c1acb181d8f42",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Jim Conlon",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-richardson-municipal-exact-scope",
        "John Richardson",
        "per_608ec85707085c46ac38f31aca539d14",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_b63fb13e93c7599c839ddcd22b6f9081",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "John Richardson",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "duri-naimji-municipal-exact-scope",
        "Duri Naimji",
        "per_586f69cee3315f4dbc8ce7917366ab03",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_b82181f8dcfe53fe8736ddaeeb6467b1",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Duri Naimji",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "gary-leroux-municipal-exact-scope",
        "Gary Leroux",
        "per_3193666c7673506cb88380a3ac65cd05",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_b9f81ed4fda05579a76d3d2714f68d87",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Gary Leroux",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "brian-buffey-municipal-exact-scope",
        "Brian Buffey",
        "per_25eb809ff24a5bef9bad4993816a6bcf",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_bacc0872f1525963b0e79da95dd1bd4c",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Brian Buffey",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jason-woychesko-municipal-exact-scope",
        "Jason Woychesko",
        "per_45e0588e5a8255eea2c4833fd6d56ca0",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_c304d13a45035392beeb260cd709d476",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "Jason Woychesko",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "amanda-coombs-municipal-exact-scope",
        "Amanda Coombs",
        "per_32f55518c4a1543dbb58743229f418b7",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_c487b4a5208b591bbd88d3d48a212148",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Amanda Coombs",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "eva-tavares-municipal-exact-scope",
        "Eva Tavares",
        "per_cae0369228625c74937abe25003ac0b7",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_cad01477260e5a0b8f43865cd977a3d1",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Eva Tavares",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jason-carey-municipal-exact-scope",
        "Jason Carey",
        "per_c43f533311aa5f1db5dcd648f32b0260",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_cb5ba33d1c585f709bffa9dc34b6abde",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Jason Carey",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "drew-buckingham-municipal-exact-scope",
        "Drew Buckingham",
        "per_180777ad0c72588ab6a53ccfb7601ac3",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_d48dc317f8b55de5a5beadbedf5835d5",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Drew Buckingham",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "albert-pantaleo-municipal-exact-scope",
        "Albert Pantaleo",
        "per_2b3c86e4cf6f5bea80e9eebd4ed482e9",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_d9cc97a433c256c0bdab5b195144969e",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Albert Pantaleo",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "april-engelberg-municipal-exact-scope",
        "April Engelberg",
        "per_4436244498af51ae95e9fbbf93072903",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_db477a1eba435811bd6ac6188d0ebdbc",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "April Engelberg",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-papadakis-municipal-exact-scope",
        "John Papadakis",
        "per_ea45e9b94d525274a5445c574fd8e1f1",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_dc5bc7bac824535c9ce11e23c4830bd5",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "John Papadakis",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "david-vallance-municipal-exact-scope",
        "David Vallance",
        "per_3ff516049e055949b3339ede8711970a",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_df52aa10e7d35b06a2be8144c6842169",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "David Vallance",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "keiosha-ross-municipal-exact-scope",
        "Keiosha Ross",
        "per_a8fe9bd07c6556cc9a0f223ca60a5363",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_e76572afcc8358e9b1738284fb92818e",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Keiosha Ross",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jem-cain-municipal-exact-scope",
        "Jem Cain",
        "per_678f09f2c425597f97535fafcb3ace09",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_f21f5d081b005db5ab765afae7ebf9cb",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "Jem Cain",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "gary-walsh-municipal-exact-scope",
        "Gary Walsh",
        "per_d164ffb1233559b8ae457bea05732b18",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_fbaed08dbd0f5961b0339ee0f480c545",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "Gary Walsh",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected municipal occurrences, with no collision against the active Person registry.",
    ),
    CuratedIdentityAssertion(
        assertion_id="edward-xiao-hua-gong-2023-2026-candidacy-continuity",
        preferred_name="Edward Gong",
        occurrences=(
            _pinned_occurrence(
                "can_0c4d2f02396353048ccf398e170ccb59",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Xiao Hua Gong",
            ),
            _pinned_occurrence(
                "can_69f3b5c5b1f85d6db7db3003822c06a7",
                "ec-ge-45",
                "canada_house_of_commons",
                "mp",
                "Xiaohua Gong",
            ),
            _pinned_occurrence(
                "can_52f3f65dbd5a5867b98898a8500161d5",
                "evt_27c3a2e636a457f1b1f922774525b74a",
                "toronto_city_council",
                "mayor",
                "Edward Gong",
            ),
        ),
        evidence_urls=(
            "https://www.toronto.ca/data/elections/candidate_list/mayorCandidates_2026.json",
            "https://www.toronto.ca/wp-content/uploads/2023/06/900e-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor.pdf",
            "https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/pollresults_resultatsbureau35.zip",
            "https://nowtoronto.com/news/the-gong-show-is-back-edward-gong-is-officially-running-for-toronto-mayor-again-and-the-signs-are-everywhere/",
            "https://www.capitalmarketstribunal.ca/sites/default/files/2022-10/rad_20221005_gongx.pdf",
        ),
        rationale=(
            "Official election records preserve the exact Xiao Hua Gong, Xiaohua Gong, "
            "and Edward Gong candidate names. Contemporaneous reporting identifies the "
            "2026 Edward Gong candidacy as the same person who ran in the 2023 Toronto "
            "mayoral by-election and the 2025 federal election in Don Valley North, while "
            "an Ontario Capital Markets Tribunal decision independently records Xiao Hua "
            "Gong's Edward Gong alias. The exact three occurrences are enumerated and no "
            "name-only fallback is authorized."
        ),
        registry_person_ids=(
            "per_424fd6af33ed5e0bae4177a42cde6c21",
            "per_5067314c5e465bfb95ca0798e4854ea7",
            "per_c54d3412c98b57bbabd296e5fbb4dceb",
        ),
        canonical_person_id="per_424fd6af33ed5e0bae4177a42cde6c21",
    ),
)


DEFAULT_IDENTITY_ASSERTIONS += (
    CuratedIdentityAssertion(
        assertion_id="chloe-brown-2016-2026-toronto-candidacy-continuity",
        preferred_name="Chloe Brown",
        occurrences=(
            _pinned_occurrence(
                "can_c9c2e18dba7955429a08971f4d728751",
                "evt_552c4874312956ae84afbbc5ee91b0f7",
                "toronto_city_council",
                "councillor",
                "Chloe-Marie Brown",
            ),
            _pinned_occurrence(
                "can_0a4ce7edba2e522ca838be9dddcdecee",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_city_council",
                "mayor",
                "Chloe-Marie Brown",
            ),
            _pinned_occurrence(
                "can_f3c0829c97525d048039948585926327",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Chloe Brown",
            ),
            _pinned_occurrence(
                "can_e6be2215757451db85e79f587b054f77",
                "evt_27c3a2e636a457f1b1f922774525b74a",
                "toronto_city_council",
                "councillor",
                "Chloe Brown",
            ),
        ),
        evidence_urls=(
            "https://www.cb4ward1.ca/about",
            "https://www.toronto.ca/data/elections/candidate_list/councilorCandidates_2026.json",
            "https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf",
            "https://www.toronto.ca/wp-content/uploads/2023/06/900e-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/8e3a-2017-byelection-ward2-declarationofresults.pdf",
            "https://www.samaracentre.ca/articles/who-gets-a-platform-media-exposure-and-online-engagement",
            "https://www.stephentaylor.ca/data/political/canada/municipal/toronto/2022/",
        ),
        rationale=(
            "Brown's candidate-controlled 2026 Ward 1 biography explicitly says she ran "
            "for mayor in 2022 and 2023, while City declarations and the Samara Centre "
            "resolve the Chloe-Marie Brown/Chloe Brown ballot-name variation. The City "
            "also records the exact uncommon Chloe-Marie Brown name in the 2016 Ward 2 "
            "by-election, and independent election-history reporting plus distinctive "
            "biographical continuity explicitly bridge that occurrence to the 2022 mayoral "
            "candidate. The exact four occurrences are enumerated and no name-only fallback "
            "is authorized."
        ),
        registry_person_ids=(
            "per_3d3501723d055766800769f77751b3bf",
            "per_abd4663f08cb5b11bbe72c502697a809",
        ),
        canonical_person_id="per_3d3501723d055766800769f77751b3bf",
    ),
)


_CURRENT_MEMBERS_OF_COUNCIL_URL = (
    "https://www.toronto.ca/city-government/council/members-of-council/"
)
_PENDING_2026_MAYOR_CANDIDATES_URL = (
    "https://www.toronto.ca/data/elections/candidate_list/mayorCandidates_2026.json"
)
_PENDING_2026_COUNCILLOR_CANDIDATES_URL = (
    "https://www.toronto.ca/data/elections/candidate_list/councilorCandidates_2026.json"
)
_PENDING_2026_EVENT_ID = "evt_27c3a2e636a457f1b1f922774525b74a"


def _pending_2026_current_officeholder_assertion(
    assertion_id: str,
    preferred_name: str,
    registry_person_id: str,
    candidacy_id: str,
    office_type: str,
) -> CuratedIdentityAssertion:
    """Anchor a certified 2026 Candidacy to a current City officeholder."""

    candidate_feed = (
        _PENDING_2026_MAYOR_CANDIDATES_URL
        if office_type == "mayor"
        else _PENDING_2026_COUNCILLOR_CANDIDATES_URL
    )
    assertion = _anchored_same_office_continuity_assertion(
        assertion_id,
        preferred_name,
        registry_person_id,
        "toronto_city_council",
        office_type,
        ((candidacy_id, _PENDING_2026_EVENT_ID, preferred_name),),
        (_CURRENT_MEMBERS_OF_COUNCIL_URL, candidate_feed),
        "The City's current Members of Council roster identifies "
        f"{preferred_name} as a serving officeholder, and its certified 2026 "
        f"{office_type} candidate feed identifies the enumerated Candidacy; together "
        "the official records anchor that pending occurrence to the existing Person.",
    )
    return replace(assertion, canonical_person_id=registry_person_id)


DEFAULT_IDENTITY_ASSERTIONS += (
    _pending_2026_current_officeholder_assertion(
        "vincent-crisanti-2026-pending-continuity",
        "Vincent Crisanti",
        "per_bb140e42ff6750dc95adfa2785ffef68",
        "can_adcacf84e3005896a5c773986a552c96",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "ausma-malik-2026-pending-continuity",
        "Ausma Malik",
        "per_bfeb35d94dc45455987133a9e9091a58",
        "can_4e5688e335d85ba38dea71c20fc80f46",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "josh-matlow-2026-pending-continuity",
        "Josh Matlow",
        "per_69529146105a5d85ae577db19104ceed",
        "can_f0eef9233b0c57268fe3d1a894b0dc36",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "chris-moise-2026-pending-continuity",
        "Chris Moise",
        "per_f1f71e7ebd7157cda9b8d44c62c4c294",
        "can_d1f0d6ec825a5e8880c7a0127fb4c0cd",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "dianne-saxe-2026-pending-continuity",
        "Dianne Saxe",
        "per_4569490f5d825a0ca8c7320b499d8090",
        "can_49b595a977475ca1b7477b59834817c6",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "rachel-chernos-lin-2026-pending-continuity",
        "Rachel Chernos Lin",
        "per_2ca884fa7ffe5c61a4bd0afcbf153fed",
        "can_2bd1031bade45386afb939f58e00bc7c",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "jon-burnside-2026-pending-continuity",
        "Jon Burnside",
        "per_9387d636b99c5fdd8edee8549f902b74",
        "can_3d04d5bdb8ef5da8adb96314f7e9ccff",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "shelley-carroll-2026-pending-continuity",
        "Shelley Carroll",
        "per_4238a9a971965995ac6c577c126f8161",
        "can_0a3c62f981215bf2a20a08b3860f4f01",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "lily-cheng-2026-pending-continuity",
        "Lily Cheng",
        "per_93dd2a3cb85f59acb3d5ea5a67b3801e",
        "can_43b902d7e35c5ba797370fa0395d6d7a",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "stephen-holyday-2026-pending-continuity",
        "Stephen Holyday",
        "per_cb9a349d2c375d6ca82d06405b9986e0",
        "can_47bbbdf2085553daba34e5d65c24be5b",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "parthi-kandavel-2026-pending-continuity",
        "Parthi Kandavel",
        "per_a9f196f1be635c4eaf83ff095681fa79",
        "can_9fdda0e71bd5578dab7a9bab4d7f5d4d",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "michael-thompson-2026-pending-continuity",
        "Michael Thompson",
        "per_d6e9f3947fda53a490136416df97c3cf",
        "can_71d0b0ede70a5a45a0f3ca553a2c73b0",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "nick-mantas-2026-pending-continuity",
        "Nick Mantas",
        "per_fb6a517ea8b55026b7d6afdf59820e53",
        "can_4c18cca55e9d5f0a9574e97613157eee",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "jamaal-myers-2026-pending-continuity",
        "Jamaal Myers",
        "per_b5382bf239c9521faee4a4a38f1a7e1c",
        "can_7e48ff22e1285e67b903e960711b588f",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "paul-ainslie-2026-pending-continuity",
        "Paul Ainslie",
        "per_c0e1c9bb6045570b873969e4c462da62",
        "can_b575c3cad9c45924b9ab2fd40bf439bd",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "neethan-shan-2026-pending-continuity",
        "Neethan Shan",
        "per_19dc2d74394f53058376f79485db68e8",
        "can_a79a57064f7351fdb16759205a1efff7",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "amber-morley-2026-pending-continuity",
        "Amber Morley",
        "per_4df1127545935df6850849e0b72a8759",
        "can_10ee922a6726559e8a6169740c7e274c",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "frances-nunziata-2026-pending-continuity",
        "Frances Nunziata",
        "per_d476ff1e2e605a88914636edbdfcb79a",
        "can_f368a3e52d0e545bbb6ebae997fb1bdf",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "james-pasternak-2026-pending-continuity",
        "James Pasternak",
        "per_3f72f66a6a385b0eae3279e7de8d12a0",
        "can_0aee4bd40f7c5ca99c87bf0689ba951b",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "anthony-perruzza-2026-pending-continuity",
        "Anthony Perruzza",
        "per_18786ecd2dc7506794ac10340a5f68f6",
        "can_8164ef2b771950ebbe2913e7c4b5e8fd",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "mike-colle-2026-pending-continuity",
        "Mike Colle",
        "per_f560221dfe455207a9cc597093a3b671",
        "can_3934cc2ba6395449b323ba47fdc50951",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "alejandra-bravo-2026-pending-continuity",
        "Alejandra Bravo",
        "per_b3471e8be4765e51b0381303a6c7a36d",
        "can_06e9de5734dd5d97a4c2cde85a5ea016",
        "councillor",
    ),
    _pending_2026_current_officeholder_assertion(
        "brad-bradford-2026-pending-mayor-continuity",
        "Brad Bradford",
        "per_d8dfddfb642358e299f4b428292666bf",
        "can_b71a736235545b8f8df2a3e196126428",
        "mayor",
    ),
    _pending_2026_current_officeholder_assertion(
        "olivia-chow-2026-pending-mayor-continuity",
        "Olivia Chow",
        "per_a4291ca7539b53e2acc1c4f108bc73e6",
        "can_24054bba2bed56dab41293ec7d138d41",
        "mayor",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_same_office_continuity_assertion(
        "rosemary-waigh-ontario-exact-scope",
        "ROSEMARY WAIGH",
        "per_48886b5235cd5bf4abf25aa6a842231f",
        "ontario_legislative_assembly",
        "mpp",
        (("can_01cc13b2f4145f59a6d53441f74beffb", "on-2014-general", "ROSEMARY WAIGH"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "piravena-sathiyanantham-ontario-exact-scope",
        "Piravena Sathiyanantham",
        "per_5d870422141d582987e575c5ca4ac913",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_088ce24271135554bcb584773a258215",
                "evt_3db5605f67e85c3a988ee6fcbcee0c3b",
                "Piravena Sathiyanantham",
            ),
        ),
        (
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/7b83316d-f2a7-4dbe-9b67-08138178c739/download/2016-tdsb-ward-21.xlsx",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip :: TORONTO DISTRICT SCHOOL BOARD.xls",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-fagan-ontario-exact-scope",
        "JOHN FAGAN",
        "per_6e61c0559576559c822c37695c6b66b5",
        "ontario_legislative_assembly",
        "mpp",
        (("can_09f42c0754625b51be11a5e62fb43dda", "on-2014-general", "JOHN FAGAN"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "cristina-martins-ontario-exact-scope",
        "CRISTINA MARTINS",
        "per_89dfc328ae8952089fadab7b9c3a0832",
        "ontario_legislative_assembly",
        "mpp",
        (("can_0e54a4bd504f598f8f3c7c1e7d5e589b", "on-2011-general", "CRISTINA MARTINS"),),
        (
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "paul-fromm-ontario-exact-scope",
        "Paul Fromm",
        "per_ecea20b36c9059ba916a6b1930b67573",
        "ontario_legislative_assembly",
        "mpp",
        (("can_183b6c72c275503e81ff9d2ae2af8064", "on-2025-general", "PAUL FROMM"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/925/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/930/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "stan-grzywna-ontario-exact-scope",
        "STAN GRZYWNA",
        "per_e33403f4b85c50f398797c2582f79047",
        "ontario_legislative_assembly",
        "mpp",
        (("can_1eedba0392975511a141023184ee6834", "on-2006-09-14-by-064", "STAN GRZYWNA"),),
        (
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/510/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/503/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/508/csv",
            "https://results.elections.on.ca/api/report-groups/5/report-outputs/521/csv",
            "https://results.elections.on.ca/api/report-groups/5/report-outputs/514/csv",
            "https://results.elections.on.ca/api/report-groups/5/report-outputs/519/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "louis-fliss-ontario-exact-scope",
        "LOUIS FLISS",
        "per_98a0864f97a5530fb6300b93ea6b54d8",
        "ontario_legislative_assembly",
        "mpp",
        (("can_1fae8f378cb95a17a4bec729cf890cbc", "on-2014-general", "LOUIS FLISS"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-hastings-ontario-exact-scope",
        "John Hastings",
        "per_13c35326e35f5616b2b579c7af89ed3c",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_2342d508261f551eb150d609cdcc356f",
                "evt_ae45ae96069c5f2aacddabffa8135f7f",
                "John Hastings",
            ),
        ),
        (
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/836c4152-0603-4fd4-8ab4-a53cf386bc43/download/2016-tdsb-ward-1-.xlsx",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip :: TORONTO DISTRICT SCHOOL BOARD.xls",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "naomi-poley-fisher-ontario-exact-scope",
        "NAOMI POLEY-FISHER",
        "per_064e8dad1c7c57dcbebff3441903cf8f",
        "ontario_legislative_assembly",
        "mpp",
        (("can_2543144e2c1d5bfe92aefa873b9039c8", "on-2014-general", "NAOMI POLEY-FISHER"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "p-c-choo-ontario-exact-scope",
        "P. C. CHOO",
        "per_628e0ca495585a479f4a5faaa676dc20",
        "ontario_legislative_assembly",
        "mpp",
        (("can_279fdeaa899255b18656eb05045f0490", "on-2014-general", "P. C. CHOO"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "faisal-hassan-ontario-exact-scope",
        "Faisal Hassan",
        "per_f15ce6590bcb5250ae4aedeaaccb3431",
        "ontario_legislative_assembly",
        "mpp",
        (("can_2914183e13d656069bc07a2af76763d1", "on-2025-general", "FAISAL HASSAN"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/925/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/930/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "lilya-eklishaeva-ontario-exact-scope",
        "LILYA EKLISHAEVA",
        "per_ec06fbec009b5f868a4e323c41260d1f",
        "ontario_legislative_assembly",
        "mpp",
        (("can_2ae49e7f959058c49551e0f10a753c13", "on-2025-general", "LILYA EKLISHAEVA"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "khalid-ahmed-ontario-exact-scope",
        "KHALID AHMED",
        "per_37f7dad14c375a50af81a0802a124a64",
        "ontario_legislative_assembly",
        "mpp",
        (("can_2d5a48ab933358cca01c686d4d980e98", "on-2014-general", "KHALID AHMED"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "cathy-crowe-ontario-exact-scope",
        "CATHY CROWE",
        "per_2b8cb440427a559490a87bd65bee1f39",
        "ontario_legislative_assembly",
        "mpp",
        (("can_2f4b5ba1806f5bf4be2ab87f42362a6e", "on-2011-general", "CATHY CROWE"),),
        (
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "ken-kirupa-ontario-exact-scope",
        "KEN KIRUPA",
        "per_b1bc8bd75fd3574f97b3ebcf4ea70cc6",
        "ontario_legislative_assembly",
        "mpp",
        (("can_32fba9753d935dbbacbe1d0336310967", "on-2014-general", "KEN KIRUPA"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jordan-glass-ontario-exact-scope",
        "Jordan Glass",
        "per_4d93f4e78bb65d99aa7df216b16f89e0",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_32fbb073abac5d08826c2021e5650cf4",
                "evt_24ccf52d7b0f5fe39baf960f9ab5cb20",
                "Jordan Glass",
            ),
        ),
        (
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/25343469-085b-4c9f-8a36-7d7f9115c630/download/2016-tdsb-ward-5.xlsx",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip :: TORONTO DISTRICT SCHOOL BOARD.xls",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "harvey-rotenberg-ontario-exact-scope",
        "HARVEY ROTENBERG",
        "per_ae848bb37f1d568ebe7de16ec205feb0",
        "ontario_legislative_assembly",
        "mpp",
        (("can_356c94d6093652cc835678144bda5de0", "on-2014-general", "HARVEY ROTENBERG"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "matthew-oliver-ontario-exact-scope",
        "MATTHEW OLIVER",
        "per_5e04767597b8580a9f5eaa73a13ded4e",
        "ontario_legislative_assembly",
        "mpp",
        (("can_394f8aa92a615d0b8288217ab9611f11", "on-2013-08-01-by-082", "MATTHEW OLIVER"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "pamela-taylor-ontario-exact-scope",
        "PAMELA TAYLOR",
        "per_9b32e330a7e956b5b03bfc267b32bb6d",
        "ontario_legislative_assembly",
        "mpp",
        (("can_3a81f61b73585798ba9eff314487c465", "on-2010-02-04-by-094", "PAMELA TAYLOR"),),
        (
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/510/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/503/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/508/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "james-mcconnell-ontario-exact-scope",
        "JAMES MCCONNELL",
        "per_0169ee518f8e562493cda0d1e575a863",
        "ontario_legislative_assembly",
        "mpp",
        (("can_3cfec95b0e4058dcbc03b9acca96b9c1", "on-2014-general", "JAMES MCCONNELL"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "aasia-khatoon-ontario-exact-scope",
        "Aasia Khatoon",
        "per_01e55c64208d564aad668a9cbe1847a7",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_3e7c43e4158a5c73b0c9eae7532fb44b",
                "evt_3db5605f67e85c3a988ee6fcbcee0c3b",
                "Aasia Khatoon",
            ),
        ),
        (
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/7b83316d-f2a7-4dbe-9b67-08138178c739/download/2016-tdsb-ward-21.xlsx",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip :: TORONTO DISTRICT SCHOOL BOARD.xls",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "kate-dupuis-ontario-exact-scope",
        "KATE DUPUIS",
        "per_a665c94cf61850debe6bdad94260dc9e",
        "ontario_legislative_assembly",
        "mpp",
        (("can_43db70127c245b64bcfe96b1c674f641", "on-2025-general", "KATE DUPUIS"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "laurel-hobbs-ontario-exact-scope",
        "LAUREL HOBBS",
        "per_f0b5ed3bc86c5d3c9d4e09817210a6a5",
        "ontario_legislative_assembly",
        "mpp",
        (("can_4b8bb02c078755388337b307fb09c802", "on-2025-general", "LAUREL HOBBS"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "eric-compton-ontario-exact-scope",
        "ERIC COMPTON",
        "per_c33ad42dd30a5653ab78424037a10409",
        "ontario_legislative_assembly",
        "mpp",
        (("can_52d1a12ed1935ac297f7a2f31036de66", "on-2014-general", "ERIC COMPTON"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "julie-lutete-ontario-exact-scope",
        "JULIE LUTETE",
        "per_6803b6972bb75c26b1b74e56c433e7f0",
        "ontario_legislative_assembly",
        "mpp",
        (("can_5390003b75c154a29c8f363390684cf7", "on-2025-general", "JULIE LUTETE"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "paul-del-grande-ontario-exact-scope",
        "Paul Del Grande",
        "per_91f0a9fe37285a15b251bc6649b3252c",
        "toronto_catholic_district_school_board",
        "trustee",
        (
            (
                "can_562d8003dd815fd2bd3c2a6c99725e14",
                "evt_a87f3eb9595a59af890e07aadd93c89c",
                "Paul Del Grande",
            ),
        ),
        (
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/a75d576c-f315-4c90-b5c9-1ca7d9f8b51f/download/2012-tcdsb-ward-8.xls",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip :: 2010_Toronto_Poll_by_Poll_Toronto_Catholic_District_School_Board.xls",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "sheena-sharp-ontario-exact-scope",
        "SHEENA SHARP",
        "per_4fb75ca0f2ba54879735652aa701181a",
        "ontario_legislative_assembly",
        "mpp",
        (("can_56e242edf01a5ab4a883a179725eab61", "on-2025-general", "SHEENA SHARP"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "leah-tysoe-ontario-exact-scope",
        "LEAH TYSOE",
        "per_b5cd545fd51c5384952d5001cc1f1920",
        "ontario_legislative_assembly",
        "mpp",
        (("can_5723868e5e485f1bae3dfb1ee0627ee0", "on-2025-general", "LEAH TYSOE"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "andy-d-andrea-ontario-exact-scope",
        "ANDY D'ANDREA",
        "per_371b5bc9eb45536589fb1d6d13928109",
        "ontario_legislative_assembly",
        "mpp",
        (("can_5b42896e77fd53a3b5de0f231906cfef", "on-2025-general", "ANDY D'ANDREA"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "paul-saguil-ontario-exact-scope",
        "PAUL SAGUIL",
        "per_9dd6ab302580529dabb828aa6a33c01c",
        "ontario_legislative_assembly",
        "mpp",
        (("can_5b9703e089115bc4b769962525715a4d", "on-2025-general", "PAUL SAGUIL"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "steve-hoehlmann-ontario-exact-scope",
        "STEVE HOEHLMANN",
        "per_ebc61be1c80d52119571cef5b515bf8a",
        "ontario_legislative_assembly",
        "mpp",
        (("can_5d809cb6e609526f8aefb3aaad4c01bb", "on-2025-general", "STEVE HOEHLMANN"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "david-morris-ontario-exact-scope",
        "David Morris",
        "per_8ee6afe0b8d75fc08b2807fcbcf32c50",
        "ontario_legislative_assembly",
        "mpp",
        (("can_63adc4be15c3532d86ff554adc110ea6", "on-2022-general", "DAVID MORRIS"),),
        (
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/925/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/930/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "parviz-isgandarov-ontario-exact-scope",
        "PARVIZ ISGANDAROV",
        "per_99dd1f974c325bc1923981ec67f43f7d",
        "ontario_legislative_assembly",
        "mpp",
        (("can_63bdb6a1202059df958452339d2388e1", "on-2025-general", "PARVIZ ISGANDAROV"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "tim-grant-ontario-exact-scope",
        "TIM GRANT",
        "per_32814e1dbfe456938caee10e6e88c29c",
        "ontario_legislative_assembly",
        "mpp",
        (("can_6ba584bf802459cca519d15024f52c78", "on-2014-general", "TIM GRANT"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "felicia-samuel-ontario-exact-scope",
        "Felicia Samuel",
        "per_c0c43548a338562c880104909ca3de6c",
        "ontario_legislative_assembly",
        "mpp",
        (("can_7cdfe70ef6e654dab5e89790fc455bec", "on-2022-general", "FELICIA SAMUEL"),),
        (
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/925/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/930/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "vitas-naudziunas-ontario-exact-scope",
        "VITAS NAUDZIUNAS",
        "per_0dc4ea7aec155cae865249f3d069bfd7",
        "ontario_legislative_assembly",
        "mpp",
        (("can_7f85c588b2cf5bf9a7d1b9aa05c8b030", "on-2025-general", "VITAS NAUDZIUNAS"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "michael-bone-ontario-exact-scope",
        "MICHAEL BONE",
        "per_a6a03c99f49a52f3afcc68a49cfa8846",
        "ontario_legislative_assembly",
        "mpp",
        (("can_8a53076f190351328b16772e5dc16379", "on-2014-general", "MICHAEL BONE"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "joe-ring-ontario-exact-scope",
        "Joe Ring",
        "per_c0d42de7d644591db03dc3967abfc8b1",
        "ontario_legislative_assembly",
        "mpp",
        (("can_8d1634ac41f2580cb69d54a6c4f66136", "on-2022-general", "JOE RING"),),
        (
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/925/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/930/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "natalie-lochwin-ontario-exact-scope",
        "NATALIE LOCHWIN",
        "per_368bd3ed028f5336a8dccad33231e18e",
        "ontario_legislative_assembly",
        "mpp",
        (("can_929f1c475ff056bda40d9e0ea69c5caf", "on-2014-general", "NATALIE LOCHWIN"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "liang-chen-ontario-exact-scope",
        "LIANG CHEN",
        "per_d0f085059c8b5b2d8d281d43a01d43b0",
        "ontario_legislative_assembly",
        "mpp",
        (("can_9c9ac69b4f255d4f9ba063ec0bf7e61d", "on-2014-general", "LIANG CHEN"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "mike-rita-ontario-exact-scope",
        "MIKE RITA",
        "per_2457c7632d305cd49fb28e9392e42a39",
        "ontario_legislative_assembly",
        "mpp",
        (("can_a40e57b4704e5f3fa55bc19e7c2b4c42", "on-2014-general", "MIKE RITA"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "hans-kunov-ontario-exact-scope",
        "HANS KUNOV",
        "per_5260ce12be8a5e6b9f7173d8c1f7c181",
        "ontario_legislative_assembly",
        "mpp",
        (("can_b5a4dbe5770f5f999b48c8cfebcbe866", "on-2013-08-01-by-024", "HANS KUNOV"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "ebrahim-astaraki-ontario-exact-scope",
        "EBRAHIM ASTARAKI",
        "per_4c9cc2708d9a5352b620db66e6b2c566",
        "ontario_legislative_assembly",
        "mpp",
        (("can_b6b9153d4d835b03a61692b34f585f2e", "on-2025-general", "EBRAHIM ASTARAKI"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "leo-ng-ontario-exact-scope",
        "Leo Ng",
        "per_b92ca58d78b25d959e4bbb6dd86f1625",
        "toronto_catholic_district_school_board",
        "trustee",
        (
            (
                "can_bd7bdfc2593956d88faa8bb2f985fe05",
                "evt_a87f3eb9595a59af890e07aadd93c89c",
                "Leo Ng",
            ),
        ),
        (
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/a75d576c-f315-4c90-b5c9-1ca7d9f8b51f/download/2012-tcdsb-ward-8.xls",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip :: 2010_Toronto_Poll_by_Poll_Toronto_Catholic_District_School_Board.xls",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "sam-ghose-ontario-exact-scope",
        "Sam Ghose",
        "per_9516edddfa285c688082af434cc7bbe1",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_be3b5f6a1bfa586ca054313ba113fee0",
                "evt_0053e297e0b15f179a94dee854971a09",
                "Sam Ghose",
            ),
        ),
        (
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/79f831c8-48ec-45f2-a65e-3b514f877a93/download/2012-tdsb-wards-17-20.xls",
            "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip :: 2010_Toronto_Poll_by_Poll_Toronto_District_School_Board.xls",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "nadia-guerrera-ontario-exact-scope",
        "Nadia Guerrera",
        "per_744d9ac1a745593ab882663c817347a4",
        "ontario_legislative_assembly",
        "mpp",
        (("can_bf313aa8d51659ecbe46bbbca98477fe", "on-2025-general", "NADIA GUERRERA"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/925/csv",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/930/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "kathleen-mathurin-ontario-exact-scope",
        "KATHLEEN MATHURIN",
        "per_0369c3b1fbec5c0989e596413f7299ac",
        "ontario_legislative_assembly",
        "mpp",
        (("can_c4f90b7a4a1a5a488e24fce4d6d93e45", "on-2011-general", "KATHLEEN MATHURIN"),),
        (
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/510/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/503/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/508/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "mehmet-ali-yagiz-ontario-exact-scope",
        "MEHMET ALI YAGIZ",
        "per_34f86027a4e85065b3f8628892cf286b",
        "ontario_legislative_assembly",
        "mpp",
        (("can_d6173c194d4250bc8b0a18e97e1c7e3a", "on-2006-03-30-by-008", "MEHMET ALI YAGIZ"),),
        (
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/510/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/503/csv",
            "https://results.elections.on.ca/api/report-groups/4/report-outputs/508/csv",
            "https://results.elections.on.ca/api/report-groups/5/report-outputs/521/csv",
            "https://results.elections.on.ca/api/report-groups/5/report-outputs/514/csv",
            "https://results.elections.on.ca/api/report-groups/5/report-outputs/519/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "anita-anandarajan-ontario-exact-scope",
        "ANITA ANANDARAJAN",
        "per_93a61b01c6945ebeb43d590f8e3152bd",
        "ontario_legislative_assembly",
        "mpp",
        (("can_dffd2552594c5bd084b3ea3298e8e4c2", "on-2025-general", "ANITA ANANDARAJAN"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "mark-daye-ontario-exact-scope",
        "MARK DAYE",
        "per_00edf37e4f1b5989ac614ce909877abb",
        "ontario_legislative_assembly",
        "mpp",
        (("can_e53c0bb97b9c5fdca97601ea87ef951d", "on-2014-general", "MARK DAYE"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "kayla-baptiste-ontario-exact-scope",
        "KAYLA BAPTISTE",
        "per_66049dae698d5fa6886e599035c6a4fe",
        "ontario_legislative_assembly",
        "mpp",
        (("can_f1542e3acf2050ce982e29f81e5e1652", "on-2014-general", "KAYLA BAPTISTE"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "martin-abell-ontario-exact-scope",
        "MARTIN ABELL",
        "per_258e217e611e565493e9bf41c045ad69",
        "ontario_legislative_assembly",
        "mpp",
        (("can_f412d7be7cfe56d2bc1764adc2adfd73", "on-2014-general", "MARTIN ABELL"),),
        (
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/488/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/481/csv",
            "https://results.elections.on.ca/api/report-groups/2/report-outputs/486/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/499/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/492/csv",
            "https://results.elections.on.ca/api/report-groups/3/report-outputs/497/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "paul-nguyen-ontario-exact-scope",
        "PAUL NGUYEN",
        "per_b43db0bff82357e8b2431b88770cf65d",
        "ontario_legislative_assembly",
        "mpp",
        (("can_f8f5f0f29c18593b9743b25a1171a49a", "on-2025-general", "PAUL NGUYEN"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "richard-m-kiernicki-ontario-exact-scope",
        "RICHARD M. KIERNICKI",
        "per_93c855cab1405c5380ae4c7e1a3c7c25",
        "ontario_legislative_assembly",
        "mpp",
        (("can_ffa9176167ea55d69f0476947e9fa893", "on-2025-general", "RICHARD M. KIERNICKI"),),
        (
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
            "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1050/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1043/csv",
            "https://results.elections.on.ca/api/report-groups/45/report-outputs/1048/csv",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected Ontario occurrences, with no collision against the active Person registry.",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_same_office_continuity_assertion(
        "eugene-mcdermott-federal-exact-scope",
        "Eugene McDermott",
        "per_60d2a94d1c5e526e8e002be525315118",
        "canada_house_of_commons",
        "mp",
        (("can_029577c6553350c1a014e31c77c8fe75", "ec-ge-40", "Eugene McDermott"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "sarah-thompson-federal-exact-scope",
        "Sarah Thompson",
        "per_0e9435aafc59527b8d1e55a3466d4b95",
        "canada_house_of_commons",
        "mp",
        (
            ("can_0c3e82d7f9d25fbaa10bfaa64ebd8ab4", "ec-ge-39", "Sarah Thompson"),
            ("can_66c3ca87b17157819e3ef64bfcaade2d", "ec-ge-40", "Sarah Thompson"),
        ),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "bernadette-michael-federal-exact-scope",
        "Bernadette Michael",
        "per_6d9c0430feb150138c58adf6dad8280f",
        "canada_house_of_commons",
        "mp",
        (("can_0dfc20a85261550f88c49a8a343c9199", "ec-ge-40", "Bernadette Michael"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jay-sobel-federal-exact-scope",
        "Jay Sobel",
        "per_6d809da6b0a953e894b43462447d72af",
        "canada_house_of_commons",
        "mp",
        (("can_10ec971a446455aa8084c4e4c1c4770f", "ec-ge-44", "Jay Sobel"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "axel-kuhn-federal-exact-scope",
        "Axel Kuhn",
        "per_77af4e1b858455c5b8f31f2c81b5f9da",
        "canada_house_of_commons",
        "mp",
        (("can_15529166e1e652d1abf2978ecc4599db", "ec-ge-40", "Axel Kuhn"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "chuck-konkel-federal-exact-scope",
        "Chuck Konkel",
        "per_b49c6a493d3c5bd0be96dadab479542e",
        "canada_house_of_commons",
        "mp",
        (("can_233f09cc2d3156bcbf4ba75e94168277", "ec-ge-41", "Chuck Konkel"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "sandra-romano-anthony-federal-exact-scope",
        "Sandra Romano Anthony",
        "per_c1d93e5adbf1535384bf0334a01ab227",
        "canada_house_of_commons",
        "mp",
        (("can_24387066a1255dd1a7cf69cbb5eb1ce9", "ec-ge-39", "Sandra Romano Anthony"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "andrew-cash-federal-exact-scope",
        "Andrew Cash",
        "per_5e50494bdb4855d59ea7ed60abb82b40",
        "canada_house_of_commons",
        "mp",
        (("can_2a343ba77f8951488d98f0b489c9850c", "ec-ge-43", "Andrew Cash"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "michael-shapcott-federal-exact-scope",
        "Michael Shapcott",
        "per_dc3b218ba5ab57c8b698776f49fea13a",
        "canada_house_of_commons",
        "mp",
        (("can_2a7579a5bb675d40ad69b60d7a4d712b", "ec-ge-39", "Michael Shapcott"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "simon-luisi-federal-exact-scope",
        "Simon Luisi",
        "per_837198af1a5d5c99b41f8a0279577da0",
        "canada_house_of_commons",
        "mp",
        (("can_306a5968caa35b73addee5252e7e4caa", "ec-ge-41", "Simon Luisi"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "giulio-manfrini-federal-exact-scope",
        "Giulio Manfrini",
        "per_fa306329732e5c3fa75862dbb9b90608",
        "canada_house_of_commons",
        "mp",
        (("can_325ab48f988e50e081c38bde4e2d25b2", "ec-ge-41", "Giulio Manfrini"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "gus-stefanis-federal-exact-scope",
        "Gus Stefanis",
        "per_3f095562f28f555ea613e1e63d7436af",
        "canada_house_of_commons",
        "mp",
        (("can_4053c96a4b2053e28771da688f4ced39", "ec-ge-44", "Gus Stefanis"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "nick-capra-federal-exact-scope",
        "Nick Capra",
        "per_a3fafcf0b4a8541892bcd80fe171773d",
        "canada_house_of_commons",
        "mp",
        (("can_413d1dd08d605eeb97ea073a273f1f1c", "ec-ge-40", "Nick Capra"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "christine-innes-federal-exact-scope",
        "Christine Innes",
        "per_0fdf6c3381c0522398e0094848371fa2",
        "canada_house_of_commons",
        "mp",
        (("can_42507e2e8d0259a4bc9197d9d80a7bc3", "ec-ge-41", "Christine Innes"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "andrew-lang-federal-exact-scope",
        "Andrew Lang",
        "per_bf252c2da90f5a4fb0467118bef28547",
        "canada_house_of_commons",
        "mp",
        (("can_43069dd9256e5354b301afe2a90d4d38", "ec-ge-41", "Andrew Lang"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "asif-hossain-federal-exact-scope",
        "Asif Hossain",
        "per_8b90ff5d926e5887941e92362ab49043",
        "canada_house_of_commons",
        "mp",
        (("can_47e697f4f32752879be3a015a6855554", "ec-ge-39", "Asif Hossain"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "elizabeth-abbott-federal-exact-scope",
        "Elizabeth Abbott",
        "per_1e70691897205083b0aaa6fd6574f509",
        "canada_house_of_commons",
        "mp",
        (("can_495281e306c55f59985762f138d2b899", "ec-ge-43", "Elizabeth Abbott"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "alonzo-bartley-federal-exact-scope",
        "Alonzo Bartley",
        "per_005dc6272c20520eb038763ad9f9f723",
        "canada_house_of_commons",
        "mp",
        (("can_50bf0cb116b75329a22e1aedf83e228f", "ec-ge-41", "Alonzo Bartley"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-capobianco-federal-exact-scope",
        "John Capobianco",
        "per_98ba8b0d39815c81af80d02d496199e9",
        "canada_house_of_commons",
        "mp",
        (("can_56d6bfb57c8a5288a7969fb948d9f7e8", "ec-ge-39", "John Capobianco"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "natalie-hundt-federal-exact-scope",
        "Natalie Hundt",
        "per_76eed00ec59a54129938ada8f52ea0d3",
        "canada_house_of_commons",
        "mp",
        (("can_59a15a802b8653cd94bddab4515bddb5", "ec-ge-41", "Natalie Hundt"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "andrew-borkowski-federal-exact-scope",
        "Andrew Borkowski",
        "per_68f0c22952485f808b0ac1d864d2c3fe",
        "canada_house_of_commons",
        "mp",
        (("can_63a2b427e96651ad8a967068b2322818", "ec-ge-41", "Andrew Borkowski"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jovan-boseovski-federal-exact-scope",
        "Jovan Boseovski",
        "per_d06ad553490d58a7ac047e4d2ac81f81",
        "canada_house_of_commons",
        "mp",
        (("can_63d939888f385ce68a3324d358a0377f", "ec-ge-39", "Jovan Boseovski"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "brenda-thompson-federal-exact-scope",
        "Brenda Thompson",
        "per_56da9a0493e55855ab73ce3705394115",
        "canada_house_of_commons",
        "mp",
        (("can_661f760d07055e6e99328c3b1a55d765", "ec-ge-39", "Brenda Thompson"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "serena-purdy-federal-exact-scope",
        "Serena Purdy",
        "per_c476dde8149a570c85d544a10eaccae2",
        "canada_house_of_commons",
        "mp",
        (("can_6f6716a737b15f68876af33e491753c1", "ec-be-2026-04-13", "Serena Purdy"),),
        (
            "https://www.elections.ca/res/rep/off/ovr_2026/64/data_donnees/pollresults_resultatsbureau35112.csv"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "yvonne-robertson-federal-exact-scope",
        "Yvonne Robertson",
        "per_5c03574a8a185a99b0425bc91040576d",
        "canada_house_of_commons",
        "mp",
        (("can_7c579231782a575ca2525104b0f7d8db", "ec-ge-44", "Yvonne Robertson"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "bahman-yazdanfar-federal-exact-scope",
        "Bahman Yazdanfar",
        "per_0a7d82034a4554c2a6f261128a359a69",
        "canada_house_of_commons",
        "mp",
        (("can_7ee9ed4a17515d65b8816e66b6d37579", "ec-be-2012-03-19", "Bahman Yazdanfar"),),
        ("https://www.elections.ca/res/rep/off/ovr_2012/pollbypoll_bureauparbureau35094.csv"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "theresa-rodrigues-federal-exact-scope",
        "Theresa Rodrigues",
        "per_dadc78faef305b31864294d3bca0cf38",
        "canada_house_of_commons",
        "mp",
        (
            ("can_7f9898c19fe35102a34a5caa6ee003a8", "ec-ge-40", "Theresa Rodrigues"),
            ("can_979abd4958f658d181306b84ce909ca7", "ec-ge-41", "Theresa Rodrigues"),
            ("can_fe2c893bda9854bb9a8a75163f353c75", "ec-ge-39", "Theresa Rodrigues"),
        ),
        (
            "https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip",
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "chester-brown-federal-exact-scope",
        "Chester Brown",
        "per_49e321400a025b90a04d99571cfba25e",
        "canada_house_of_commons",
        "mp",
        (("can_845e9f5049745706b000af455b081aeb", "ec-ge-41", "Chester Brown"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "justin-chatwin-federal-exact-scope",
        "Justin Chatwin",
        "per_4dd6c5d01a69569297bb113ee56e624a",
        "canada_house_of_commons",
        "mp",
        (("can_84dbd024d79755b891aebad5bba57b59", "ec-ge-41", "Justin Chatwin"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "bruce-griffin-federal-exact-scope",
        "Bruce Griffin",
        "per_d7c95d3a5f6554568e36cf386c3e485d",
        "canada_house_of_commons",
        "mp",
        (("can_879125c5da045c629178ad16fa5c8eef", "ec-ge-44", "Bruce Griffin"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "georgina-wilcock-federal-exact-scope",
        "Georgina Wilcock",
        "per_d9f66e41731c52feb0b822f5fef097ed",
        "canada_house_of_commons",
        "mp",
        (("can_8911efa825635031a0c7e1c23c069f94", "ec-ge-41", "Georgina Wilcock"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "steve-rutchinski-federal-exact-scope",
        "Steve Rutchinski",
        "per_205383728e5c5198ac4afe12dbdb00da",
        "canada_house_of_commons",
        "mp",
        (("can_8b633a2690aa5a028ed0b1dfa672d492", "ec-ge-43", "Steve Rutchinski"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "rosemary-frei-federal-exact-scope",
        "Rosemary Frei",
        "per_1f71ee369104529a8de9e692d96ff7ce",
        "canada_house_of_commons",
        "mp",
        (("can_916927f50e205b25a31c22cddf7af79f", "ec-ge-41", "Rosemary Frei"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jurij-klufas-federal-exact-scope",
        "Jurij Klufas",
        "per_87fb66d7d9ec5e8f8ca755ecd326ea87",
        "canada_house_of_commons",
        "mp",
        (("can_934d04afda5951d7b2122f01cfe141f8", "ec-ge-39", "Jurij Klufas"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "lou-carcasole-federal-exact-scope",
        "Lou Carcasole",
        "per_bb2a062efe4452edb315ae29f4f1265b",
        "canada_house_of_commons",
        "mp",
        (("can_994b5efa89c6572e9a2614d904655755", "ec-ge-40", "Lou Carcasole"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "judi-falardeau-federal-exact-scope",
        "Judi Falardeau",
        "per_347c82802924528995ecb19724ca7a5c",
        "canada_house_of_commons",
        "mp",
        (("can_99d8ff40c7e95fcaa31920d94d7d60e0", "ec-be-2013-11-25", "Judi Falardeau"),),
        ("https://www.elections.ca/res/rep/off/ovr_2013b2/csv/35093_e.csv"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "fatima-shaban-federal-exact-scope",
        "Fatima Shaban",
        "per_baea45166fb358f39552b7d1dccd9e1b",
        "canada_house_of_commons",
        "mp",
        (("can_9bca62cedaeb50e39b98cfb76182af5f", "ec-be-2026-04-13", "Fatima Shaban"),),
        (
            "https://www.elections.ca/res/rep/off/ovr_2026/64/data_donnees/pollresults_resultatsbureau35096.csv"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "dave-corail-federal-exact-scope",
        "Dave Corail",
        "per_b1362624b0bc586a97f25d3b1dc582ee",
        "canada_house_of_commons",
        "mp",
        (("can_a40b278bbb7154379dc498b2ee191675", "ec-ge-41", "Dave Corail"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "ellen-michelson-federal-exact-scope",
        "Ellen Michelson",
        "per_00e64e17c11c53dda58b84c32f908dba",
        "canada_house_of_commons",
        "mp",
        (("can_aca5b035c26456e4b8a5292ece4114aa", "ec-ge-41", "Ellen Michelson"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "liam-mchugh-russell-federal-exact-scope",
        "Liam McHugh-Russell",
        "per_3b35cade2cf05a2bb9b18878143216af",
        "canada_house_of_commons",
        "mp",
        (("can_b0145c44c6c75e6283e3ae8cb3ac742e", "ec-ge-40", "Liam McHugh-Russell"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "paul-taylor-federal-exact-scope",
        "Paul Taylor",
        "per_43f18c4b0a0b506d8e9cd3faa2cadd6a",
        "canada_house_of_commons",
        "mp",
        (("can_bac43645ee855957af7ceb55dab750e9", "ec-ge-44", "Paul Taylor"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "adriana-mugnatto-hamu-federal-exact-scope",
        "Adriana Mugnatto-Hamu",
        "per_25c50ab98b10591b9838b90f57681d00",
        "canada_house_of_commons",
        "mp",
        (("can_c0cb038769f45e64aa3a0f985ae98f8b", "ec-be-2012-03-19", "Adriana Mugnatto-Hamu"),),
        ("https://www.elections.ca/res/rep/off/ovr_2012/pollbypoll_bureauparbureau35094.csv"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "faiz-kamal-federal-exact-scope",
        "Faiz Kamal",
        "per_c491e64d9f5c5777bc2cc21fd8584f6b",
        "canada_house_of_commons",
        "mp",
        (("can_ca871a7630e451668c28aa95f194523f", "ec-ge-44", "Faiz Kamal"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "france-tremblay-federal-exact-scope",
        "France Tremblay",
        "per_22625040c957553ca9d048b6bfd37d57",
        "canada_house_of_commons",
        "mp",
        (("can_cd0dedd9fb5b575b83a7765f797e337b", "ec-ge-39", "France Tremblay"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "david-thomas-federal-exact-scope",
        "David Thomas",
        "per_99e7c7fb654e5a6caf9b4d82439eea03",
        "canada_house_of_commons",
        "mp",
        (("can_d1d65038fa835d4798ae869ebc3ca63a", "ec-ge-39", "David Thomas"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "jerry-bance-federal-exact-scope",
        "Jerry Bance",
        "per_430680107a2a58579192ba50d1a17942",
        "canada_house_of_commons",
        "mp",
        (("can_d2d84b7f44d15f3789b696e7408d8457", "ec-ge-40", "Jerry Bance"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "chris-tolley-federal-exact-scope",
        "Chris Tolley",
        "per_d521628f80ce542b955e43ce68f6bf7b",
        "canada_house_of_commons",
        "mp",
        (("can_d6cb7f9acae35fb288e2e3f2950808fb", "ec-ge-43", "Chris Tolley"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "daniel-lee-federal-exact-scope",
        "Daniel Lee",
        "per_02e00c77047c5d41b5dfced8cb84fa02",
        "canada_house_of_commons",
        "mp",
        (("can_d9219bc39e3a549cb52d48089e1a750c", "ec-ge-44", "Daniel Lee"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "joe-oliver-federal-exact-scope",
        "Joe Oliver",
        "per_6e69f959e7b6537bb4bb95220d6f82d9",
        "canada_house_of_commons",
        "mp",
        (("can_d93d5c54623551f1a4f893e98155497b", "ec-ge-40", "Joe Oliver"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "syeda-riaz-federal-exact-scope",
        "Syeda Riaz",
        "per_e89288f7c3565df2b34b13af8d5adec8",
        "canada_house_of_commons",
        "mp",
        (("can_dcbbc40c58b55188b5f0757f189012fe", "ec-ge-44", "Syeda Riaz"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "michael-mostyn-federal-exact-scope",
        "Michael Mostyn",
        "per_87d8be48db395ec188284c64c2b44d4f",
        "canada_house_of_commons",
        "mp",
        (("can_dd0e4567d75c5189aeaf1ac0280254eb", "ec-ge-39", "Michael Mostyn"),),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "chris-tindal-federal-exact-scope",
        "Chris Tindal",
        "per_8e507945855c517594e6cfb5279f9fde",
        "canada_house_of_commons",
        "mp",
        (("can_e1d5fbbd3069514cbeeb1539df3dd33d", "ec-be-2008-03-17", "Chris Tindal"),),
        ("https://www.elections.ca/ele/pas/2008/csv/pollbypoll35093.csv"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "marie-crawford-federal-exact-scope",
        "Marie Crawford",
        "per_732571318fd45e5eae65586773b23024",
        "canada_house_of_commons",
        "mp",
        (("can_e8966e7143a6501e85aa1e6230d01619", "ec-ge-41", "Marie Crawford"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "mike-sullivan-federal-exact-scope",
        "Mike Sullivan",
        "per_5c16add0f57c57ffb6108decd999bb64",
        "canada_house_of_commons",
        "mp",
        (("can_ebec5c13fe4a5cb089a178f0775a9f19", "ec-ge-40", "Mike Sullivan"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "birinder-singh-ahluwalia-federal-exact-scope",
        "Birinder Singh Ahluwalia",
        "per_8a84600de31d56439c7749dddcd6ad2e",
        "canada_house_of_commons",
        "mp",
        (("can_ece01c9256305255963e8dcb7bd5395d", "ec-ge-43", "Birinder Singh Ahluwalia"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "larisa-julius-federal-exact-scope",
        "Larisa Julius",
        "per_75c291e4a0b95f53b332f81bbc8b4422",
        "canada_house_of_commons",
        "mp",
        (("can_ee021e6787ab5fdeaecb4b5fff692665", "ec-ge-44", "Larisa Julius"),),
        (
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "ella-ng-federal-exact-scope",
        "Ella Ng",
        "per_ac5b27e161535c5dae987e0063fad532",
        "canada_house_of_commons",
        "mp",
        (("can_f3b9b78c16585bb5893cc9ae30d7ddde", "ec-ge-41", "Ella Ng"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "wayne-scott-federal-exact-scope",
        "Wayne Scott",
        "per_e826505ef3e65cd9bb799b5ca0a054ec",
        "canada_house_of_commons",
        "mp",
        (("can_f691eb0f97d650d291a33c26f3628fc4", "ec-ge-41", "Wayne Scott"),),
        (
            "https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip"
        ),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
    _anchored_same_office_continuity_assertion(
        "wayne-clements-federal-exact-scope",
        "Wayne Clements",
        "per_5021cb88bc9355c5903f6b653b5bb979",
        "canada_house_of_commons",
        "mp",
        (("can_ff0361f2e7f758fb80bbfaee1072767b", "ec-ge-40", "Wayne Clements"),),
        ("https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip"),
        "Independent same-body/same-office/exact-district/party adjudication for the selected federal occurrences, with no collision against the active Person registry.",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "maria-rizzo-tcdsb-continuity",
        "Maria Rizzo",
        "per_398a476f8e6a527f9ca5370d45d41886",
        (
            (
                "can_da4dfb33dd805a20a24c29da67639008",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Maria Rizzo",
            ),
            (
                "can_a8f58a0dbfcd5094841787f63d4029fe",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_catholic_district_school_board",
                "trustee",
                "Maria Rizzo",
            ),
            (
                "can_fff1d15b3b6c55bc80ba31df065a86a3",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Maria Rizzo",
            ),
            (
                "can_d7a1c3e6049f5ddf9d210c0a209eabf0",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Maria Rizzo",
            ),
            (
                "can_7d3ab8fc934c55baaafe77f9832d48a1",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Maria Rizzo",
            ),
        ),
        ("https://www.tcdsb.org/page/ward-5-north-york",),
        "TCDSB's Ward 5 biography says Maria Rizzo was elected to the board in 2003 and has served continuously since, explicitly bridging the later Ward 5 candidacies.",
    ),
    _anchored_continuity_assertion(
        "barbara-poplawski-tcdsb-ward10-continuity",
        "Barbara Poplawski",
        "per_00f30ea06d545d1fb20b7892d7427a36",
        (
            (
                "can_3a34abb64daa5e04bba34412ff259955",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Barbara Poplawski",
            ),
            (
                "can_ed836dbd65cb5757ae74edc1d545cb0c",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_catholic_district_school_board",
                "trustee",
                "Barbara Poplawski",
            ),
            (
                "can_235c471e15ee58229e23aeaaf7c3a403",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Barbara Poplawski",
            ),
            (
                "can_5e123b4a8c045894970c606b4305efb1",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Barbara Poplawski",
            ),
        ),
        (
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
            "https://assets.tcdsb.org/TCDSB/2335249/brochure-supporting-student-achievement-and-well-being-by-addressing-parent-concerns.pdf",
            "https://assets.tcdsb.org/specialservices/2372943/3-final-klp-brochure-2015.pdf",
            "https://assets.tcdsb.org/stmartin/2370342/board-learning-improvement-plan-2018-2021.pdf",
        ),
        "Official TCDSB trustee rosters span Poplawski's Ward 10 service and identify the same trustee through the 2006-2018 candidacy sequence; the unbridged 2022 Ward 4 occurrence remains excluded.",
    ),
    _anchored_continuity_assertion(
        "ann-andrachuk-tcdsb-continuity",
        "Ann Andrachuk",
        "per_e1d35233bba7537b9184c4fa0b02f461",
        (
            (
                "can_813b6beac4f05d368671e0e8cbcf94eb",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Ann Andrachuk",
            ),
            (
                "can_9d0c2c8d696058d6ba508f19d8d51a06",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_catholic_district_school_board",
                "trustee",
                "Ann Andrachuk",
            ),
            (
                "can_be2b2297f03e5b968257866036d019f9",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Ann Andrachuk",
            ),
            (
                "can_01c172762cb255aca15957c336de6eac",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Ann Andrachuk",
            ),
        ),
        (
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
            "https://assets.tcdsb.org/TCDSB/2335249/brochure-supporting-student-achievement-and-well-being-by-addressing-parent-concerns.pdf",
            "https://assets.tcdsb.org/specialservices/2372943/3-final-klp-brochure-2015.pdf",
            "https://assets.tcdsb.org/stmartin/2370342/board-learning-improvement-plan-2018-2021.pdf",
        ),
        "Official TCDSB rosters document Ann Andrachuk's continuous trustee service across the four election cycles; no Rose Andrachuk occurrence is included.",
    ),
    _anchored_continuity_assertion(
        "joseph-martino-tcdsb-continuity",
        "Joseph Martino",
        "per_09a4cbae05385a73bdd309e7d767549f",
        (
            (
                "can_7cf3b696eeda5403a73c66c682c40bb0",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_catholic_district_school_board",
                "trustee",
                "Joseph Martino",
            ),
            (
                "can_d91a2d0305225718a8eb9a0d2fd12fa7",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Joseph Martino",
            ),
            (
                "can_73151af786f654b6b7d50a55debef8a6",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Joseph Martino",
            ),
            (
                "can_43338fc65096563f8617ecb364446c6c",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Joseph Martino",
            ),
        ),
        (
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
            "https://assets.tcdsb.org/specialservices/2372943/3-final-klp-brochure-2015.pdf",
            "https://www.tcdsb.org/page/board-of-trustees",
        ),
        "Official TCDSB records place Joseph Martino in Ward 1 before and after the 2010 candidacy and continue the same service through 2022.",
    ),
    _anchored_continuity_assertion(
        "sal-piccininni-tcdsb-continuity",
        "Sal Piccininni",
        "per_33b580c9ef4e56dcaafdaad27e3ce44a",
        (
            (
                "can_c1d06b1c39fe5425988e94e58a4f9479",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Sal Piccininni",
            ),
            (
                "can_50af0a6208835ca8a028b30e07c36f74",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_catholic_district_school_board",
                "trustee",
                "Sal Piccininni",
            ),
            (
                "can_a7f7196d483154fa973d2af37d4fba7e",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Sal Piccininni",
            ),
            (
                "can_d45b5733be5852ab84b7ae2e0b75aa3a",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Sal Piccininni",
            ),
        ),
        (
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
            "https://assets.tcdsb.org/TCDSB/2335249/brochure-supporting-student-achievement-and-well-being-by-addressing-parent-concerns.pdf",
            "https://assets.tcdsb.org/specialservices/2372943/3-final-klp-brochure-2015.pdf",
        ),
        "Official TCDSB rosters document Sal Piccininni's Ward 3 trustee service across the 2006-2018 candidacies.",
    ),
    _anchored_continuity_assertion(
        "chris-tonks-tdsb-continuity",
        "Chris Tonks",
        "per_85053a5781615b0cbe1083d5d681780c",
        (
            (
                "can_d7e805bfa9fc5cfba0c440e8242831f7",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Chris Tonks",
            ),
            (
                "can_78706cc207f85562b25fce05dff083b6",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Chris Tonks",
            ),
            (
                "can_daf41395e6755a4ba174f8e96593fd80",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Chris Tonks",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Boardroom/Agenda-Minutes/Type/M/Year/2007?Filename=71128_30.pdf",
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=110518+Min+final.pdf&Type=M&Year=2011",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
            "https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf",
        ),
        "TDSB minutes and Clerk declarations form a continuous official record for Chris Tonks's Ward 6 trustee candidacies.",
    ),
    _anchored_continuity_assertion(
        "garry-tanuan-tcdsb-continuity",
        "Garry Tanuan",
        "per_c6100ed1c5a25fcdaa2206d06b752405",
        (
            (
                "can_6d6672ac8bfc5ea4b3c7b91bfb1283f9",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Garry Tanuan",
            ),
            (
                "can_9d1d855d56815f85b0c82967a0bfdfa3",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Garry Tanuan",
            ),
            (
                "can_c1106e6150a75e0f8d2bd928a7de189e",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Garry Tanuan",
            ),
        ),
        ("https://www.tcdsb.org/page/ward-8-scarborough",),
        "TCDSB's Ward 8 biography says Garry Tanuan was first elected in the December 2012 by-election, directly bridging his later Ward 8 candidacies.",
    ),
    _anchored_continuity_assertion(
        "gerri-gershon-tdsb-continuity",
        "Gerri Gershon",
        "per_5b554d6233315b2a966642bc6c5d7ea4",
        (
            (
                "can_ee5dd02e0e0f553db7e1f58980cb805a",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Gerri Gershon",
            ),
            (
                "can_ccdb5b8cf971566ebd64cd887fb0c0c5",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Gerri Gershon",
            ),
            (
                "can_d16bb00ef3ff5ad6a038c8eed83b1ce7",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Gerri Gershon",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=70921.pdf&Type=M&Year=2007",
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=110518+Min+final.pdf&Type=M&Year=2011",
            "https://www.tdsb.on.ca/Leadership/Boardroom/Agenda-Minutes/Type/M/Year/2014?Filename=140704.pdf",
        ),
        "Official TDSB minutes identify Gerri Gershon throughout the terms adjoining her 2006, 2010, and 2014 candidacies.",
    ),
    _anchored_continuity_assertion(
        "nancy-crawford-tcdsb-continuity",
        "Nancy Crawford",
        "per_9d4819cd2db25de88900ee46712abd36",
        (
            (
                "can_f4a2030cdfee58cbbdc863553e268a85",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Nancy Crawford",
            ),
            (
                "can_92baf10ba94b5df39662155583b59fd6",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Nancy Crawford",
            ),
            (
                "can_64330bb55f1f5892bc559f26ce79522b",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Nancy Crawford",
            ),
        ),
        (
            "https://www.tcdsb.org/page/ward-12-scarborough",
            "https://www.tcdsb.org/page/board-of-trustees",
        ),
        "TCDSB's biography says Nancy Crawford was first elected in Ward 12 in 2010 and the board roster documents her continuing Ward 12 service.",
    ),
    _anchored_continuity_assertion(
        "sheila-cary-meagher-tdsb-continuity",
        "Sheila Cary-Meagher",
        "per_4b54fe14d808502d8acc539a4ff0c26e",
        (
            (
                "can_1a904970bb505bbe8392988385f60345",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Sheila Cary-Meagher",
            ),
            (
                "can_15d57725a0645c6ea1862bb6abca4105",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Sheila Cary-Meagher",
            ),
            (
                "can_15fbf628e4005cc9b1cb8e10127de312",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Sheila Cary-Meagher",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=111_112.pdf&Type=M&Year=2001",
            "https://www.tdsb.on.ca/Leadership/Boardroom/Agenda-Minutes/Type/M/Year/2007?Filename=71128_30.pdf",
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=111005.pdf&Type=M&Year=2011",
            "https://www.tdsb.on.ca/Leadership/Boardroom/Agenda-Minutes/Type/M/Year/2014?Filename=140704.pdf",
        ),
        "Official TDSB minutes document Sheila Cary-Meagher's continuous trustee service across the 2006-2014 election sequence.",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "alexander-brown-tdsb-ward12-continuity",
        "Alexander Brown",
        "per_d1cba76fb5ec5c9a9bf3d280053bee28",
        (
            (
                "can_c2728294334554bfa8a091e98c50a147",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "BROWN ALEXANDER",
            ),
            (
                "can_6592bf58e54e53b48ba7554f979ac2a9",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Brown Alexander",
            ),
            (
                "can_2785e4d3334c5919a7559ba3c2b42958",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Brown Alexander",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=141201+Org.pdf&Type=M&Year=2014",
            "https://www.tdsb.on.ca/Portals/0/AboutUs/Director/AnnualReport2016FINAL.pdf",
            "https://www.tdsb.on.ca/Portals/0/docs/DirectorsAnnualReport2020_FINAL_AODA.pdf",
        ),
        "TDSB's organizational minutes and annual reports document Alexander Brown's continuing Ward 12 service from the 2010 candidacy through the 2014, 2018, and 2022 occurrences. The separate 2012 Ward 17 namesake is excluded.",
    ),
    _anchored_continuity_assertion(
        "manna-wong-tdsb-continuity",
        "Manna Wong",
        "per_cbad12eb2bc15f4fb7ba5a96bd68dec9",
        (
            (
                "can_871623e7a85953069355be7eececa1a8",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "WONG MANNA",
            ),
            (
                "can_e2f3d124f709514aba2a4a7615ac1dea",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Wong Manna",
            ),
            (
                "can_51e46003d79f5791ac854d8c532ca69c",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Wong Manna",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=141201+Org.pdf&Type=M&Year=2014",
            "https://www.tdsb.on.ca/Portals/ward20/docs/2018%2011%20-%20Ward%2020%20Report%20%28Wong%29%281%29.pdf",
            "https://tdsbwwwtst.tdsb.on.ca/Leadership/Boardroom/Municipal-Election-2018",
        ),
        "Official TDSB records identify Manna Wong's election in 2014, her 2018 re-election, and her 2022 Ward 20 election, continuing from the 2012 Ward 20 anchor.",
    ),
    _anchored_continuity_assertion(
        "ken-lister-tdsb-continuity",
        "Ken Lister",
        "per_fd89e2daa64b5513ba56eb9e1c8b51f7",
        (
            (
                "can_7f8eb7ee36b95463a276aa95bea28690",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "LISTER KEN",
            ),
        ),
        (
            "https://www.tdsb.on.ca/ward17/Ward17/KenListerBio.aspx",
            "https://www.kenlister.ca/aboutken",
        ),
        "TDSB and candidate-authored biographies identify Ken Lister's 2014 election and four-year Ward 17 trustee service, continuing from the 2012 Ward 17 candidacy.",
    ),
    _anchored_continuity_assertion(
        "avtar-minhas-council-to-tdsb-continuity",
        "Avtar Minhas",
        "per_194efd592b915c2ca63859d3ebbef5e0",
        (
            (
                "can_ec9483b40b5053fba035f30b3cd7cdcf",
                "evt_ae45ae96069c5f2aacddabffa8135f7f",
                "toronto_district_school_board",
                "trustee",
                "Minhas Avtar",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas-Minutes-Decisions/Type/M/Year/2016?Filename=160728+Sp.pdf",
            "https://www.campaignlifecoalition.com/public-trustee-voting-records/id/13507",
        ),
        "TDSB records establish Avtar Minhas's 2016 Ward 1 election, and the contemporaneous candidate record explicitly identifies him as the 2014 Ward 1 council candidate.",
    ),
    CuratedIdentityAssertion(
        assertion_id="alexandra-lulka-rotman-tdsb-continuity",
        preferred_name="Alexandra Lulka Rotman",
        occurrences=(
            _pinned_occurrence(
                "can_192d59806abb57e78a9db2dce7fa38e9",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Lulka Alexandra",
            ),
        ),
        evidence_urls=(
            "https://www.tdsb.on.ca/Leadership/Agendas-Minutes-Decisions/Type/M/Year/2016?Filename=160728+Sp.pdf",
            "https://www.tdsb.on.ca/portals/_default/ARC_helpful_info_docs/May%2021%2C%202025%20summary%20decisions.pdf",
        ),
        rationale=(
            "TDSB records cover Alexandra Lulka's 2016 and 2018 Ward 5 service and later identify the serving trustee as Alexandra Lulka Rotman, proving the 2022 surname-expanded record is the same Person."
        ),
        registry_person_ids=(
            "per_41f18773bdf258f1b2bda351d34274e3",
            "per_8d7b15e532d653528a8ec8cededad6fe",
        ),
    ),
    _anchored_continuity_assertion(
        "anu-sriskandarajah-tdsb-continuity",
        "Anu Sriskandarajah",
        "per_3c246b205ffd55298633b81a804f8b82",
        (
            (
                "can_541a4a3ffff1502ca1432322205bed36",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Sriskandarajah Anu",
            ),
        ),
        (
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2018Election/Query.aspx?board=Toronto+District+School+Board&lang=en",
            "https://tdsbwwwtst.tdsb.on.ca/Leadership/Boardroom/Municipal-Election-2018",
        ),
        "Official trustee election records identify Anu Sriskandarajah as the elected Ward 22 trustee in both 2018 and 2022.",
    ),
    _anchored_continuity_assertion(
        "matias-de-dovitiis-tdsb-continuity",
        "Matias De Dovitiis",
        "per_a7d99bd4713856f0b911d07aef6c31ef",
        (
            (
                "can_7b48e33d718e5d10885d66a8e2cbf866",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "de Dovitiis Matias",
            ),
            (
                "can_b24bddf41ee8563aa8ec49eab0492a17",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "de Dovitiis Matias",
            ),
        ),
        (
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Toronto+District+School+Board&lang=en",
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2018Election/Query.aspx?board=Toronto+District+School+Board&lang=en",
            "https://www.tdsb.on.ca/ward4/Ward-4/Trustee-Bio",
        ),
        "Official candidate profiles and TDSB's trustee biography document Matias De Dovitiis's Ward 4 candidacies in 2014 and 2018 and his 2022 election.",
    ),
    CuratedIdentityAssertion(
        assertion_id="sam-sotiropoulos-tdsb-ward20-continuity",
        preferred_name="Sam Sotiropoulos",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_ab2b73442bbe5f3d87554b942bb06971",
                    "evt_159f073fa6f15c23a840651723d3c3af",
                    "toronto_district_school_board",
                    "trustee",
                    "SOTIROPOULOS SAM",
                ),
                (
                    "can_e00c40f5098c5b63b8434c8f2785cf55",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_district_school_board",
                    "trustee",
                    "SOTIROPOULOS SAM",
                ),
                (
                    "can_a0e7810d53a45c36a06748e513455d8c",
                    "evt_0053e297e0b15f179a94dee854971a09",
                    "toronto_district_school_board",
                    "trustee",
                    "Sotiropoulos Sam",
                ),
                (
                    "can_4ca9fe6f01ce56fe9404f8918691dbf2",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_district_school_board",
                    "trustee",
                    "SOTIROPOULOS SAM",
                ),
            )
        ),
        evidence_urls=(
            "https://www.tdsb.on.ca/Leadership/Agendas-Minutes-Decisions/Type/M/Year/2012?Filename=120306.pdf",
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Toronto+District+School+Board&lang=en",
            "https://www.armenianclub.com/2012/03/06/two-new-trustees-elected-electrical-engineer-and-it-specialist-win/",
        ),
        rationale=(
            "TDSB records and contemporary reporting identify Sam Sotiropoulos's 2006, 2010, and 2012 Ward 20 campaigns, his 2012 election, and his 2014 Ward 20 candidacy. These form one Person; the separate 2003 Ward 15 occurrence remains unmerged because the 2012 report calls that election his third run."
        ),
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "chi-nguyen-ontario-to-house-continuity",
        "Chi Nguyen",
        "per_744d98dde3d2548e8dc2c809972b9fca",
        (
            (
                "can_325858ee95bc5848b692b3a8ba3a037c",
                "ec-ge-45",
                "canada_house_of_commons",
                "mp",
                "Chi Nguyen",
            ),
        ),
        ("https://chinguyen.libparl.ca/",),
        "The MP's official biography explicitly says that Chi Nguyen ran as the Ontario Liberal candidate in Spadina-Fort York in 2022 before her 2025 federal election.",
    ),
    _anchored_continuity_assertion(
        "leslie-church-house-2024-2025-continuity",
        "Leslie Church",
        "per_56963b4350105041aef2536725521738",
        (
            (
                "can_6021699c0f0a5f96ae2a257de4636a84",
                "ec-ge-45",
                "canada_house_of_commons",
                "mp",
                "Leslie Church",
            ),
        ),
        ("https://www.ourcommons.ca/Members/en/leslie-church%28119705%29/roles",),
        "The House of Commons profile records one Leslie Church as the defeated 2024 Toronto-St. Paul's by-election candidate and the elected 2025 candidate.",
    ),
    _anchored_continuity_assertion(
        "jean-francois-lheureux-viamonde-continuity",
        "Jean-François L'Heureux",
        "per_752b7d7461ed56958c2f8873b66356d2",
        (
            (
                "can_75f75a2e8ab551a5a37b7341592f7003",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "conseil_scolaire_viamonde",
                "trustee",
                "L'HEUREUX JEAN-FRANÇOIS",
            ),
        ),
        (
            "https://secure.toronto.ca/council/report.do?meeting=2011.CC8&type=minutes",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9757-election-2014-declaration-trustee-ward4.pdf",
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Conseil+scolaire+Viamonde&lang=fr",
        ),
        "Official City records and the 2014 trustee profile identify Jean-François L'Heureux's Viamonde service beginning with his 2010 election and continuing through the 2014 occurrence.",
    ),
    _anchored_continuity_assertion(
        "angela-kennedy-tcdsb-and-ontario-continuity",
        "Angela Kennedy",
        "per_5853689b88db555ca8a9431a01bdd81a",
        (
            (
                "can_4530bf242cbc556390628a343148ef87",
                "evt_d89f777f34365c37b114ca39fb376591",
                "toronto_catholic_district_school_board",
                "trustee",
                "Kennedy, Angela",
            ),
            (
                "can_95582b1a01945c5b99db848de8ca660e",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "KENNEDY ANGELA",
            ),
            (
                "can_5e0395b75a0e5398a87499c8186b3f84",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_catholic_district_school_board",
                "trustee",
                "KENNEDY ANGELA",
            ),
            (
                "can_cbe7c3fac3865ab7aea6c777394d5824",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "KENNEDY ANGELA",
            ),
            (
                "can_43eebe9be3135abbaba1c40faa937b5a",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_catholic_district_school_board",
                "trustee",
                "Kennedy Angela",
            ),
            (
                "can_a71b65a22e155617a798d15a30a3b348",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Kennedy Angela",
            ),
        ),
        (
            "https://www.tcdsb.org/board/trusteesoftheboard/ward11trustee/Pages/default.aspx",
            "https://www.ola.org/sites/default/files/node-files/hansard/document/pdf/2003/2003-05/house-document-hansard-transcript-4-en-2003-05-29_pdfL017.pdf",
        ),
        "TCDSB documents Angela Kennedy's Ward 11 service from 2000 onward, while Ontario Hansard explicitly identifies that trustee in Beaches-East York, bridging the 2003 provincial candidacy to the six elected trustee occurrences. The separate 2010 Ward 9 namesake is excluded.",
    ),
    CuratedIdentityAssertion(
        assertion_id="frank-damico-tcdsb-2010-2022-continuity",
        preferred_name="Frank D'Amico",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_643ef4ba05a85a99b80f35f11b217164",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "D'AMICO FRANK",
                ),
                (
                    "can_d035d9ceab5c5838a266f98209ff2c3b",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "D'AMICO FRANK",
                ),
                (
                    "can_686a839bd2c459f3bd5974baaa8ed8de",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "D'Amico Frank",
                ),
                (
                    "can_a36063df8c4a52deb9d37ad8546619a2",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "D'Amico Frank",
                ),
                (
                    "can_6e420426261f5f3d9a66e8fdcc5b59e3",
                    "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                    "toronto_city_council",
                    "mayor",
                    "D'Amico Frank",
                ),
            )
        ),
        evidence_urls=(
            "https://www.tcdsb.org/page/ward-6-york/",
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Toronto+Catholic+District+School+Board&lang=en",
            "https://thelocal.to/toronto-mayor-candidates-2023/",
        ),
        rationale=(
            "TCDSB's biography and the candidate-authored 2014 profile say Frank D'Amico was first elected in 2010 and document his continuing Ward 6 service. The Local's 2023 candidate profile explicitly identifies the mayoral candidate as that Ward 6 TCDSB trustee. These five occurrences form one Person; no claim is made about the separate 2003 TDSB Ward 5 candidate."
        ),
    ),
    _anchored_continuity_assertion(
        "jo-ann-davis-tcdsb-continuity",
        "Jo-Ann Davis",
        "per_c44cdf5cda645b059a05ad1d6ccd697d",
        (
            (
                "can_e77b2a4e56505467a31aec16646db650",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "DAVIS JO-ANN",
            ),
        ),
        (
            "https://tcdsbpublishing.escribemeetings.com/filestream.ashx?DocumentId=10248",
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Toronto+Catholic+District+School+Board&lang=en",
        ),
        "Official TCDSB material and Jo-Ann Davis's 2014 candidate biography identify her as the Ward 9 trustee for the four years following her 2010 election.",
    ),
    _anchored_continuity_assertion(
        "john-del-grande-tcdsb-continuity",
        "John Del Grande",
        "per_06c593495da95ae0ab273e23c22b243f",
        (
            (
                "can_e042df88e4ed5d2f938f420dcef7c9e7",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "DEL GRANDE JOHN",
            ),
            (
                "can_4737b10c1bf85d78aed6c3aa26329249",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_catholic_district_school_board",
                "trustee",
                "DEL GRANDE JOHN",
            ),
        ),
        ("https://assets.tcdsb.org/TCDSB/3117096/april-2023-approved-motions.pdf",),
        "TCDSB's approved motions identify John Del Grande as a trustee from 2003 through 2014, directly covering the 2003 anchor and the 2006 and 2010 occurrences.",
    ),
    CuratedIdentityAssertion(
        assertion_id="kevin-morrison-tcdsb-ward11-to-ward9-continuity",
        preferred_name="Kevin Morrison",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_73d21b8470c95525a69fdc672f3b24b7",
                    "evt_5a786c1da7ec5e758036205f04351fc5",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "MORRISON KEVIN",
                ),
                (
                    "can_ffef03abc52b5228b9656cb56adaef00",
                    "evt_a87f3eb9595a59af890e07aadd93c89c",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "Morrison Kevin",
                ),
                (
                    "can_2ee9207379325ea1a586f18e401d4d8a",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "MORRISON KEVIN",
                ),
                (
                    "can_682b73ddcce75912bce6d2469ac3d2cd",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "Morrison Kevin",
                ),
                (
                    "can_b23049d23ba45712aac7d6a5e69cce08",
                    "evt_a52ef78967f05336bdb5d591fd50f122",
                    "toronto_catholic_district_school_board",
                    "trustee",
                    "Morrison Kevin",
                ),
            )
        ),
        evidence_urls=(
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Toronto+Catholic+District+School+Board&lang=en",
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2018Election/Query.aspx?board=Toronto+Catholic+District+School+Board&lang=en",
            "https://elections.ontarioschooltrustees.org/2022Election/Query.aspx?board=Toronto+Catholic+District+School+Board&lang=en",
            "https://thelocal.to/ward-12-toronto-st-pauls/",
        ),
        rationale=(
            "Successive candidate biographies repeat Kevin Morrison's CPIC and school-council history, and The Local explicitly enumerates his 2010, 2012, 2014, 2018, and 2022 runs. These occurrences form one Person. The simultaneous 2010 Ward 9 candidate is excluded as a distinct unresolved namesake."
        ),
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "jerry-chadwick-tdsb-continuity",
        "Jerry Chadwick",
        "per_c4a68f2add495ccb935f7ce38bed6234",
        (
            (
                "can_735a78fe77315564ae6590c52015ca51",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Jerry Chadwick",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas-Minutes-Decisions/Type/M/Year/2010?Filename=101110.pdf",
            "https://www.tdsb.on.ca/portals/0/aboutus/Director/Annual_Report_2014.pdf",
        ),
        "TDSB records identify Jerry Chadwick's 2010 election and continuing Ward 22 trustee service through the 2014-2018 term.",
    ),
    _anchored_continuity_assertion(
        "markus-de-domenico-tcdsb-continuity",
        "Markus De Domenico",
        "per_708b2db06a7a5192842e697cc167a88b",
        (
            (
                "can_1a5a34b15e6d553ca9c9c800d009aa0e",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Markus De Domenico",
            ),
        ),
        ("https://www.tcdsb.org/page/ward-2-etobicoke",),
        "TCDSB's Ward 2 biography says Markus de Domenico was first elected in 2018, directly bridging the 2018 and 2022 candidacies.",
    ),
    _anchored_continuity_assertion(
        "mary-cicogna-tcdsb-continuity",
        "Mary Cicogna",
        "per_d234955535db5b95b087546388610857",
        (
            (
                "can_55b08f2148b057d0848eaa2cd19edede",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Mary Cicogna",
            ),
        ),
        (
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
        ),
        "TCDSB's 2007-2008 roster identifies Mary Cicogna as Ward 4 trustee, bridging the 2003 and 2006 candidacies.",
    ),
    _anchored_continuity_assertion(
        "michael-feldman-council-continuity",
        "Michael Feldman",
        "per_a91b6e0f34fc5ad894ceeecfe6f286ca",
        (
            (
                "can_21292996478554dd9696fe813d2bee9c",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_city_council",
                "councillor",
                "Michael Feldman",
            ),
        ),
        ("https://www.toronto.ca/legdocs/2005/agendas/council/cc050504/admcl015a.pdf",),
        "A City financial record identifies Councillor Michael Feldman in Ward 10 between the 2003 and 2006 candidacies; the separate Mike Feldman Person is not included.",
    ),
    _anchored_continuity_assertion(
        "michelle-aarts-tdsb-continuity",
        "Michelle Aarts",
        "per_d800d5cd92e45eb6b2c8e441d1cab51b",
        (
            (
                "can_23282d07e6c056e9964f98879893a2c2",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Michelle Aarts",
            ),
        ),
        ("https://www.tdsb.on.ca/Portals/0/docs/DirectorAnnualReport2022.pdf",),
        "TDSB's 2022 annual report places Michelle Aarts in Ward 16 in both the 2018-2022 and 2022-2026 trustee rosters.",
    ),
    _anchored_continuity_assertion(
        "oliver-carroll-tcdsb-continuity",
        "Oliver Carroll",
        "per_6ed61afed8795c4db18a72e48c38d2d5",
        (
            (
                "can_1ad66db634385751a2715440a92e02d8",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Oliver Carroll",
            ),
        ),
        (
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
        ),
        "TCDSB's 2007-2008 roster identifies Oliver Carroll as Ward 8 chair, bridging the 2003 and 2006 candidacies.",
    ),
    _anchored_continuity_assertion(
        "patrick-nunziata-tdsb-continuity",
        "Patrick Nunziata",
        "per_40f2f4c013685e38a8d8d9b497878d9f",
        (
            (
                "can_9ee55bc1847b5c9d9e6596d71401bb36",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Patrick Nunziata",
            ),
        ),
        ("https://www.tdsb.on.ca/Portals/0/docs/DirectorAnnualReport2022.pdf",),
        "TDSB's 2022 annual report places Patrick Nunziata in Ward 3 in both the 2018-2022 and 2022-2026 trustee rosters.",
    ),
    _anchored_continuity_assertion(
        "patrizia-bottoni-tcdsb-continuity",
        "Patrizia Bottoni",
        "per_b02a57f69e6355e19f28d962858058d8",
        (
            (
                "can_460b406f30135a54b0b2c83e387fe9d4",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_catholic_district_school_board",
                "trustee",
                "Patrizia Bottoni",
            ),
        ),
        (
            "https://assets.tcdsb.org/TCDSB/2335249/brochure-supporting-student-achievement-and-well-being-by-addressing-parent-concerns.pdf",
            "https://assets.tcdsb.org/specialservices/2372928/2015-li-booklet-for-secondary-students.pdf",
        ),
        "Official TCDSB rosters identify Patrizia Bottoni as Ward 4 trustee across the 2010-2014 term and following the 2014 election.",
    ),
    _anchored_continuity_assertion(
        "paul-crawford-tcdsb-continuity",
        "Paul Crawford",
        "per_f7326d0501bf5e08b813252dbd7bd1ff",
        (
            (
                "can_5b93cdd6de195584b45b31317c47e120",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Paul Crawford",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
        ),
        "The Clerk declaration and TCDSB's following-year roster identify Paul Crawford's continuing Ward 12 service across the 2003 and 2006 candidacies.",
    ),
    _anchored_continuity_assertion(
        "preti-ida-li-tcdsb-continuity",
        "Ida Li Preti",
        "per_4fd87e6b870e500d92009bb5ce7af7c1",
        (
            (
                "can_5c3184d5ed0559e5ba6a449b1196e8dc",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Preti Ida Li",
            ),
        ),
        (
            "https://assets.tcdsb.org/nurturingourcatholiccommunity/2376050/faith-talk-digital-scrapbook.pdf",
            "https://assets.tcdsb.org/TCDSB/2973539/trustee-li-preti-newsletter-april-2023-2.pdf",
        ),
        "TCDSB records identify Ida Li Preti as Ward 3 trustee in 2018-2019 and again after the 2022 election, resolving the source's reordered display name.",
    ),
    _anchored_continuity_assertion(
        "robin-pilkey-tdsb-continuity",
        "Robin Pilkey",
        "per_a525b55e76a05e579852c2e6934cdc8e",
        (
            (
                "can_b576b1647a475155afdfa36f82d842d8",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Robin Pilkey",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas-Minutes-Decisions/Type/M/Year/2014?Filename=141201+Org.pdf",
            "https://schoolweb.tdsb.on.ca/Portals/presteign/docs/December%202018%20Newsletter%20.pdf",
        ),
        "A TDSB newsletter says Robin Pilkey entered her second Ward 7 term in 2018, directly bridging the 2014 and 2018 candidacies.",
    ),
    _anchored_continuity_assertion(
        "teresa-lubinski-tcdsb-continuity",
        "Teresa Lubinski",
        "per_0277eb81ad4d5dc7a2bc6e55e4756875",
        (
            (
                "can_ad899be19f1b5edda69a263eabc60032",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Teresa Lubinski",
            ),
        ),
        (
            "https://assets.tcdsb.org/nurturingourcatholiccommunity/2376050/faith-talk-digital-scrapbook.pdf",
            "https://www.tcdsb.org/page/ward-4-parkdale-high-park-etobicoke-lakeshore",
        ),
        "TCDSB records identify Teresa Lubinski as Ward 4 trustee in 2018-2019 and after the 2022 election.",
    ),
    _anchored_continuity_assertion(
        "vince-gasparro-ontario-to-house-continuity",
        "Vince Gasparro",
        "per_bcc1ca15f7be54a4acb9d6147c561069",
        (
            (
                "can_f4687de35afb5afeae90ceccab3fa0bf",
                "ec-ge-45",
                "canada_house_of_commons",
                "mp",
                "Vince Gasparro",
            ),
        ),
        (
            "https://ontarioliberal.ca/non-profit-leader-vince-gasparro-officially-nominated-as-ontario-liberal-candidate-in-eglinton-lawrence/",
            "https://www.canada.ca/en/government/management/vince-gasparro.html",
        ),
        "First-party Ontario and federal biographies identify Vince Gasparro as the 2025 provincial candidate and the subsequently elected federal MP for Eglinton-Lawrence.",
    ),
    _anchored_continuity_assertion(
        "yalini-rajakulasingam-tdsb-continuity",
        "Yalini Rajakulasingam",
        "per_15b215e7a52958939d9332cff8cd9990",
        (
            (
                "can_d6b92c58def4588591493c6e2dc53d89",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Yalini Rajakulasingam",
            ),
        ),
        ("https://www.tdsb.on.ca/Portals/0/docs/DirectorAnnualReport2022.pdf",),
        "TDSB's 2022 annual report places Yalini Rajakulasingam in Ward 21 in both the 2018-2022 and 2022-2026 trustee rosters.",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "borys-wrzesnewskyj-house-continuity",
        "Borys Wrzesnewskyj",
        "per_5f9ff0988c5d5bb8aa289e250cd144b0",
        (
            (
                "can_8f5eac0d20e35562816d2733e76ec2f8",
                "ec-ge-42",
                "canada_house_of_commons",
                "mp",
                "Borys Wrzesnewskyj",
            ),
        ),
        ("https://www.ourcommons.ca/Members/en/borys-wrzesnewskyj%2825468%29/roles",),
        "The House of Commons service record enumerates Borys Wrzesnewskyj's Etobicoke Centre candidacies and service through his return in the 2015 election.",
    ),
    _anchored_continuity_assertion(
        "pamela-gough-tdsb-continuity",
        "Pamela Gough",
        "per_b94977f840da534caf789477d036ee8c",
        (
            (
                "can_9abb3035e6bf5fb4bc4a86c1f67fcf32",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Pamela Gough",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=101201.pdf&Type=M&Year=2010",
            "https://www.tdsb.on.ca/Portals/trusteeorientation/docs/SchoolListingFOS.pdf",
        ),
        "TDSB's organizational record and 2014-2015 directory identify Pamela Gough as Ward 3 trustee across the 2010 and 2014 candidacies.",
    ),
    _anchored_continuity_assertion(
        "zakir-patel-tdsb-continuity",
        "Zakir Patel",
        "per_353b9c4a63ac57ab9ee85eb011797754",
        (
            (
                "can_a481eaafdaba515bb8888ad573a443b3",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Zakir Patel",
            ),
        ),
        ("https://www.tdsb.on.ca/Portals/0/docs/DirectorAnnualReport2022.pdf",),
        "TDSB's 2022 annual report places Zakir Patel in Ward 19 in both the 2018-2022 and 2022-2026 trustee rosters.",
    ),
    _anchored_continuity_assertion(
        "lee-fairclough-ontario-continuity",
        "Lee Fairclough",
        "per_c84fd6c4e07659928fdeb07cf9c45a9c",
        (
            (
                "can_84a391e1208f50afa5fe100e89b2dff9",
                "on-2025-general",
                "ontario_legislative_assembly",
                "mpp",
                "LEE FAIRCLOUGH",
            ),
        ),
        (
            "https://ontarioliberal.ca/ontario-liberal-health-care-candidates/",
            "https://www.ola.org/sites/default/files/node-files/hansard/document/pdf/2025/2025-12/03-DEC-2025_L046-I.pdf",
        ),
        "Ontario Liberal and Legislature records identify Lee Fairclough as the Etobicoke-Lakeshore candidate in 2022 and the elected MPP in 2025.",
    ),
    _anchored_continuity_assertion(
        "karim-bardeesy-ontario-to-house-continuity",
        "Karim Bardeesy",
        "per_5086953fe96a54ae86350a60c4cf4063",
        (
            (
                "can_a50e1d801ae0522bbd6f5af9495a92d8",
                "ec-ge-45",
                "canada_house_of_commons",
                "mp",
                "Karim Bardeesy",
            ),
        ),
        (
            "https://www.ola.org/fr/affaires-legislatives/documents-chambre/legislature-44/session-1/2025-04-29/journal-debats",
        ),
        "The Legislature's official journal identifies the prior provincial candidate Karim Bardeesy as the newly elected federal representative, explicitly bridging the two offices.",
    ),
    _anchored_continuity_assertion(
        "roman-baber-ontario-to-house-continuity",
        "Roman Baber",
        "per_038cc72298e557cf8090e925c2f00de0",
        (
            (
                "can_42dc2b02126e545292b363c25b90842d",
                "ec-ge-45",
                "canada_house_of_commons",
                "mp",
                "Roman Baber",
            ),
        ),
        (
            "https://romanbabermp.ca/about/",
            "https://www.ola.org/en/members/all/roman-baber",
        ),
        "Roman Baber's parliamentary biography explicitly identifies his prior 2018-2022 York Centre provincial service, bridging the MPP and MP candidacies.",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "john-hastings-tdsb-2006-2014-continuity",
        "John Hastings",
        "per_13c35326e35f5616b2b579c7af89ed3c",
        (
            (
                "can_122cebab7cd954d4881ddef08d47b21a",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "John Hastings",
            ),
            (
                "can_2fac6a1d01db57c1aaa9b689d02f2ede",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "John Hastings",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Boardroom/Agenda-Minutes/Type/M/Year/2012?Filename=121121.pdf",
            "https://tdsb.on.ca/Portals/0/SEAC%20Minutes%20Dec%209%202013.pdf",
        ),
        "Official TDSB records document John Hastings's Ward 1 service during the terms adjoining his 2006-2014 candidacies; the later unbridged by-election occurrence remains excluded.",
    ),
    CuratedIdentityAssertion(
        assertion_id="julien-baeta-viamonde-2014-2018-continuity",
        preferred_name="Julien Baeta",
        occurrences=tuple(
            _pinned_occurrence(*occurrence)
            for occurrence in (
                (
                    "can_ce04f3c93539593284aefaf7ccfe8511",
                    "evt_54673fd104ab5ef08eb865e162ac040c",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Julien Baeta",
                ),
                (
                    "can_5b4cf46d3cd05cf5ba9dd88152cb298b",
                    "evt_e4fe1909276b5fbd91057022b350fff3",
                    "conseil_scolaire_viamonde",
                    "trustee",
                    "Julien Baeta",
                ),
            )
        ),
        evidence_urls=(
            "https://csviamonde.ca/fileadmin/viamonde/Documentation_Conseil/pv_19_juin_2015.pdf",
            "https://csviamonde.ca/fileadmin/viamonde/Documentation_Conseil/pv_22_septembre_2017.pdf",
            "https://csviamonde.ca/fileadmin/viamonde/Documentation_Conseil/pv_16_novembre_2018.pdf",
        ),
        rationale=(
            "Viamonde minutes document Julien Baeta's service through the 2014-2018 "
            "term. The unbridged 2010 same-name candidacy is deliberately left on its "
            "separate Person rather than used as an anchor."
        ),
    ),
    _anchored_continuity_assertion(
        "bruce-davis-tdsb-continuity",
        "Bruce Davis",
        "per_ae47e3a37afe5307bc5363e16d53189a",
        (
            (
                "can_92d0c0f1aca95861869b67d54f124916",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Bruce Davis",
            ),
        ),
        ("https://www.toronto.ca/legdocs/mmis/2017/cd/bgrd/backgroundfile-102629.pdf",),
        "A City report identifies Bruce Davis's TDSB trustee service from 2000 through 2010, directly spanning the 2003 and 2006 Ward 3 candidacies.",
    ),
    _anchored_continuity_assertion(
        "chloe-robert-viamonde-continuity",
        "Chloë Robert",
        "per_373e53e422af5351aedffbbde80bc8c7",
        (
            (
                "can_98bcd98e4d8655649b773c44eb9496a9",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "conseil_scolaire_viamonde",
                "trustee",
                "Chloë Robert",
            ),
        ),
        (
            "https://csviamonde.ca/fileadmin/viamonde/Documentation_Conseil/pv_19_juin_2015.pdf",
            "https://csviamonde.ca/fileadmin/viamonde/Documentation_Conseil/pv_22_septembre_2017.pdf",
            "https://csviamonde.ca/fileadmin/viamonde/Documentation_Conseil/pv_16_novembre_2018.pdf",
        ),
        "Viamonde minutes identify Chloë Robert throughout the term bridging her 2014 and 2018 Ward 3 candidacies.",
    ),
    _anchored_continuity_assertion(
        "christine-nunziata-tcdsb-continuity",
        "Christine Nunziata",
        "per_97b71e58ad4350f28248fbedf76c816b",
        (
            (
                "can_863e353e5d4b5ba8a461b0551484bdf4",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_catholic_district_school_board",
                "trustee",
                "Christine Nunziata",
            ),
        ),
        (
            "https://web1.tcdsb.org/Conference/images/registrationsite.pdf",
            "https://assets.tcdsb.org/TCDSB/2235180/S17-Related-Procedures-for-the-Investigation-and-Reporting-of-Child-Abuse.pdf",
        ),
        "Official TCDSB rosters identify Christine Nunziata's Ward 6 service across the 2003 and 2006 candidacies.",
    ),
    _anchored_continuity_assertion(
        "dan-maclean-tdsb-continuity",
        "Dan Maclean",
        "per_a625ee27dc485039bcf9ecdce91b4493",
        (
            (
                "can_c9eeae375f4a529983a5624d8db57d5e",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Dan Maclean",
            ),
        ),
        ("https://www.tdsb.on.ca/Portals/0/docs/DirectorAnnualReport2022.pdf",),
        "TDSB's 2022 annual report places Dan MacLean in Ward 2 in both the 2018-2022 and 2022-2026 trustee rosters.",
    ),
    _anchored_continuity_assertion(
        "daniel-di-giorgio-tcdsb-to-ontario-continuity",
        "Daniel Di Giorgio",
        "per_c420decb6687572fa82550c1eae3dd23",
        (
            (
                "can_3d74199a42e355229d905c877cb43cb5",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_catholic_district_school_board",
                "trustee",
                "Daniel Di Giorgio",
            ),
            (
                "can_bffad4cefed953139bb60bb451bf5fb3",
                "on-2025-general",
                "ontario_legislative_assembly",
                "mpp",
                "DANIEL DI GIORGIO",
            ),
        ),
        (
            "https://assets.tcdsb.org/nurturingourcatholiccommunity/2376050/faith-talk-digital-scrapbook.pdf",
            "https://ontarioliberal.ca/daniel-di-giorgio-ward-10-toronto-catholic-district-school-board-trustee-officially-the-ontario-liberal-candidate-for-york-south-weston/",
        ),
        "The Ontario Liberal nomination biography explicitly identifies Ward 10 trustee Daniel Di Giorgio as its York South-Weston candidate, while TCDSB records document his trustee service.",
    ),
    _anchored_continuity_assertion(
        "howard-kaplan-tdsb-continuity",
        "Howard Kaplan",
        "per_83dbfa7d4e6453c3ba386fc67ca673d7",
        (
            (
                "can_940566486a6154baafc54fd7f8ee7f1c",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Howard Kaplan",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=101201.pdf&Type=M&Year=2010",
            "https://www.tdsb.on.ca/portals/0/aboutus/Director/Annual_Report_2014.pdf",
        ),
        "TDSB's organizational record and 2014 annual report document Howard Kaplan's Ward 5 trustee service through the 2010-2014 term.",
    ),
    _anchored_continuity_assertion(
        "james-li-tdsb-continuity",
        "James Li",
        "per_53d97dd7efbc521c92f62ab92fac1946",
        (
            (
                "can_62e3b56e1d3f5cc8b63b6100dea30fe8",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "James Li",
            ),
        ),
        ("https://www.tdsb.on.ca/Portals/0/docs/DirectorAnnualReport2022.pdf",),
        "TDSB's 2022 annual report places James Li in Ward 13 in both the 2018-2022 and 2022-2026 trustee rosters.",
    ),
    _anchored_continuity_assertion(
        "jennifer-story-tdsb-continuity",
        "Jennifer Story",
        "per_35b194cd4a6a521fabd4c79afeaa0913",
        (
            (
                "can_65a78e867a86523a9857a861ef1f1d8d",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Jennifer Story",
            ),
        ),
        (
            "https://www.tdsb.on.ca/portals/0/aboutus/Director/Annual_Report_2014.pdf",
            "https://www.tdsb.on.ca/Portals/0/docs/DirectorAnnualReport2022.pdf",
        ),
        "TDSB annual reports identify Jennifer Story as Ward 15 trustee in the 2014-2018 and 2018-2022 terms.",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "adrian-heaps-council-continuity",
        "Adrian Heaps",
        "per_9074ce6d34475a738c239ee5c8847102",
        (
            (
                "can_85e98fc56eac54c39d4b9cc70b1017ae",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_city_council",
                "councillor",
                "Adrian Heaps",
            ),
            (
                "can_e9906b69c72d5566b85bddc4bb613e4a",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_city_council",
                "councillor",
                "Adrian Heaps",
            ),
        ),
        ("https://secure.toronto.ca/council/agenda-item.do?item=2009.PG24.1",),
        "Toronto's official council record identifies Councillor Adrian Heaps in Ward 35 during the term bridging his 2003, 2006, and 2010 candidacies.",
    ),
    _anchored_continuity_assertion(
        "david-smith-tdsb-to-ontario-continuity",
        "David Smith",
        "per_35a74b64eea251898e6dec4a1aa09483",
        (
            (
                "can_96c50cc2c8085178a47c5aad6692882c",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "David Smith",
            ),
            (
                "can_54ecfb313aef53a48156901c593a909b",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "David Smith",
            ),
            (
                "can_efdf7e99d9b456ea84c3af0dc6ede024",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "David Smith",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas-Minutes-Decisions/Type/M/Year/2022?Filename=220831.pdf",
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=220629.pdf&Type=M&Year=2022",
        ),
        "TDSB's vacancy records say David Smith served twelve years as trustee before becoming an Ontario MPP, directly bridging his 2010-2018 trustee service to the existing MPP Person; earlier same-name candidacies remain excluded.",
    ),
    _anchored_continuity_assertion(
        "scott-harrison-tdsb-2003-2010-continuity",
        "Scott Harrison",
        "per_cf67e953cc5d5813be347c92214ea37d",
        (
            (
                "can_63d254b2dd5f55dc8083db5c2c5e8064",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Scott Harrison",
            ),
            (
                "can_d293fa069b1d54e7ab7c1af4be6ed32a",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Scott Harrison",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=101110.pdf&Type=M&Year=2010",
        ),
        "Scott Harrison's official TDSB farewell states that he had served as a trustee for ten years, directly bridging the 2003, 2006, and 2010 Ward 19 candidacies; later unbridged occurrences remain excluded.",
    ),
    _anchored_continuity_assertion(
        "cathy-dandy-tdsb-continuity",
        "Cathy Dandy",
        "per_c76f34963771501abedcfe5fd440cf14",
        (
            (
                "can_b43576c9e2d45f53ab5e5b427da76c4e",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Cathy Dandy",
            ),
            (
                "can_3697a017e36e5348a61ac953f28abf3f",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Cathy Dandy",
            ),
        ),
        (
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Toronto+District+School+Board&lang=en",
        ),
        "Cathy Dandy's candidate-supplied 2014 trustee biography says she was first elected in 2006 and was seeking re-election, explicitly bridging all three Ward 15 candidacies.",
    ),
)

DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "sheila-ward-tdsb-continuity",
        "Sheila Ward",
        "per_6b4982e52b7e55fc9db4ceb7fbcbb550",
        (
            (
                "can_5a4e006bf5b053e1b8db02eb04db2a7e",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Sheila Ward",
            ),
            (
                "can_47a14c76b2dd58619a842cb43ad605b4",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Sheila Ward",
            ),
            (
                "can_1411a30ee5f45f5e975ffa73fa5d3149",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Sheila Ward",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=71217.pdf&Type=M&Year=1997",
            "https://www.tdsb.on.ca/Portals/0/Nursing/4g%20School%20Matters%20Parent%20Guide_2010-2011.pdf",
            "https://www.tdsb.on.ca/Leadership/Boardroom/Agenda-Minutes/Type/M/Year/2014?Filename=140618+Sp.pdf",
        ),
        "Official TDSB records identify Sheila Ward as the Ward 14 trustee from before 2003 through the terms adjoining her 2006-2014 candidacies.",
    ),
    _anchored_continuity_assertion(
        "shelley-laskin-tdsb-continuity",
        "Shelley Laskin",
        "per_2a75be47f516520a93a4beded8ac6546",
        (
            (
                "can_1803540bb4d452a2b972def3b0b00c36",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Shelley Laskin",
            ),
            (
                "can_eb8f2d9e38f357bab66c4ae335425f07",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_district_school_board",
                "trustee",
                "Shelley Laskin",
            ),
            (
                "can_08429fd737df56b39ecfbf80b11ec95d",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_district_school_board",
                "trustee",
                "Shelley Laskin",
            ),
        ),
        (
            "https://schoolweb.tdsb.on.ca/westprep/Trustee-Updates",
            "https://www.tdsb.on.ca/About-Us/Strategy-Planning/Search-All-Reviews/id/158",
        ),
        "TDSB records identify Shelley Laskin's Ward 11 service and explicitly carry her into Ward 8 after the 2018 boundary change, bridging the 2014-2022 sequence.",
    ),
    _anchored_continuity_assertion(
        "mari-rutka-tdsb-continuity",
        "Mari Rutka",
        "per_0a10c6351b6c5f80a14c8edd8bf91742",
        (
            (
                "can_e5e66d8a56e25ef8836091a074b57e7b",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Mari Rutka",
            ),
            (
                "can_87231e3184125ce59d549f8966ee533b",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Mari Rutka",
            ),
            (
                "can_9edfa1319d7f52f8a02e4ba2dbae4917",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_district_school_board",
                "trustee",
                "Mari Rutka",
            ),
        ),
        (
            "https://schoolweb.tdsb.on.ca/Portals/lesterbpearsones/docs/LBP%20September%20Newsletter.pdf",
            "https://schoolweb.tdsb.on.ca/portals/Churchill/docs/Oct%205%202010%20Council%20Minutes%20Final.pdf",
        ),
        "A TDSB-hosted 2013 notice identifies Mari Rutka as Ward 12 trustee in her third term, directly bridging the 2003-2014 election sequence.",
    ),
    _anchored_continuity_assertion(
        "chris-bolton-tdsb-continuity",
        "Chris Bolton",
        "per_e614a3c2a971580a82446f7a9a026572",
        (
            (
                "can_814e8a8e93005642ae632b63673877ea",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Chris Bolton",
            ),
            (
                "can_c4139b10cbdd5fe39c77d186d5efcefd",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Chris Bolton",
            ),
        ),
        (
            "https://schoolweb.tdsb.on.ca/Portals/banting/docs/Fall%202012.pdf",
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=60920.pdf&Type=M&Year=2006",
        ),
        "Official TDSB records identify Chris Bolton as Ward 10 trustee throughout the 2003-2010 service period.",
    ),
    _anchored_continuity_assertion(
        "howard-goodman-tdsb-continuity",
        "Howard Goodman",
        "per_80ff0cfe7b7c5ae4bfac6c0d46a461ee",
        (
            (
                "can_25b50eb206195f0b925dbbc58dc6cefa",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Howard Goodman",
            ),
            (
                "can_10bc5f7506f653f4926958af70d54899",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Howard Goodman",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=41215.pdf&Type=M&Year=2004",
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=120404.pdf&Type=M&Year=2012",
        ),
        "TDSB minutes identify Howard Goodman as a trustee before and after the 2006 and 2010 Ward 8 candidacies.",
    ),
    _anchored_continuity_assertion(
        "irene-atkinson-tdsb-continuity",
        "Irene Atkinson",
        "per_4fce2dffe8095bee8c68ca1d2c8ac324",
        (
            (
                "can_85347c7d52b55d2bba3a77d1f1469511",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Irene Atkinson",
            ),
            (
                "can_aee8a5d409595b2e8bcf5e83b774b92e",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Irene Atkinson",
            ),
        ),
        (
            "https://schoolweb.tdsb.on.ca/Portals/humbercrestps/docs/april%20newsletter.pdf",
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=120404.pdf&Type=M&Year=2012",
        ),
        "Official TDSB records identify Irene Atkinson as Ward 7 trustee across the 2003-2010 election sequence.",
    ),
    _anchored_continuity_assertion(
        "maria-rodrigues-tdsb-continuity",
        "Maria Rodrigues",
        "per_3a2015e6fb2e56a4af60d7b8f9248eef",
        (
            (
                "can_236558822f4a5c18a783fb92721521a6",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Maria Rodrigues",
            ),
            (
                "can_1091e883590953caa42736be735e4658",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Maria Rodrigues",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Portals/0/Nursing/4g%20School%20Matters%20Parent%20Guide_2010-2011.pdf",
            "https://www.tdsb.on.ca/DesktopModules/Tdsb.Webteam.Modules.SPC/schoolprofile.aspx?schno=5209",
        ),
        "TDSB's official trustee guide and school history identify Maria Rodrigues's Ward 9 service through the 2003-2010 sequence.",
    ),
    _anchored_continuity_assertion(
        "soo-wong-tdsb-and-ontario-continuity",
        "Soo Wong",
        "per_1cd576998bf25df0b9f1e4ab31842e5d",
        (
            (
                "can_3c7e5e971a6d5fb7adc3d0e5525f6bd1",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Soo Wong",
            ),
            (
                "can_dff503b5422452ccbfd42e2f53fa38ca",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Soo Wong",
            ),
            (
                "can_02b28158ee555630b51271f3b37d7c30",
                "on-2022-general",
                "ontario_legislative_assembly",
                "mpp",
                "SOO WONG",
            ),
        ),
        (
            "https://www.ola.org/sites/default/files/node-files/hansard/document/pdf/2012/2012-06/house-document-hansard-transcript-1-EN-13-JUN-2012_L066.pdf",
            "https://ontarioliberal.ca/scarborough-agincourt-nomination/",
        ),
        "Soo Wong's Legislature statement identifies her prior TDSB service, and the Ontario Liberal nomination biography explicitly joins that trustee service, her MPP career, and her 2022 candidacy.",
    ),
    _anchored_continuity_assertion(
        "stephnie-payne-tdsb-continuity",
        "Stephnie Payne",
        "per_a7badd21391e5d63b1661d0519a7d7d2",
        (
            (
                "can_c4de7031f0e35d9f987297cff36c50bd",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_district_school_board",
                "trustee",
                "Stephnie Payne",
            ),
            (
                "can_530f3dc85c045cb2826dcc1146242e6b",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_district_school_board",
                "trustee",
                "Stephnie Payne",
            ),
        ),
        (
            "https://www.tdsb.on.ca/Leadership/Agendas%2CMinutesDecisions.aspx?Filename=71217.pdf&Type=M&Year=1997",
            "https://www.tdsb.on.ca/portals/_default/ARC_helpful_info_docs/Minutes%20of%20the%20Board%20Meeting%20held%20on%20May%2016%2C%202012.pdf",
        ),
        "TDSB minutes identify Stephnie Payne's trustee service before and after the 2006 and 2010 Ward 4 candidacies.",
    ),
)


DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_continuity_assertion(
        "kevin-clarke-adjudicated-mayor-and-house-continuity",
        "Kevin Clarke",
        "per_546a50310fbe5401a126a3864d97fbb3",
        (
            (
                "can_50a87c1dd3135b5196c56ae9fbffab40",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "toronto_city_council",
                "mayor",
                "CLARKE KEVIN",
            ),
            (
                "can_a50571b31442526fb62e5372faa1b461",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "toronto_city_council",
                "mayor",
                "CLARKE KEVIN",
            ),
            (
                "can_329c2467ea155894a20286ed200f141c",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_city_council",
                "mayor",
                "CLARKE KEVIN",
            ),
            (
                "can_bbaaeed26d235604acd532cfefb2f67f",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_city_council",
                "mayor",
                "Clarke Kevin",
            ),
            (
                "can_d8bba3b6e65c59f8beb96d5d964b2430",
                "ec-be-2020-10-26",
                "canada_house_of_commons",
                "mp",
                "Kevin Clarke",
            ),
            (
                "can_bc9f34ff3dd256879043a52494da0738",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_city_council",
                "mayor",
                "Clarke Kevin",
            ),
            (
                "can_4d0948a9ba985ca4a64164460023422b",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Clarke Kevin",
            ),
        ),
        (
            "https://thelocal.to/toronto-mayor-candidates-2023/",
            "https://www.elections.ca/res/rep/off/ovr_2020/52/data_donnees/pollresults_resultatsbureau35108.csv",
        ),
        "The Local's fact-checked candidate history explicitly enumerates Clarke's selected mayoral runs and identifies the same candidate in the 2020 Toronto Centre federal by-election; other Kevin Clarke occurrences remain excluded.",
    ),
    _anchored_same_office_continuity_assertion(
        "monowar-hossain-mayoral-continuity",
        "Monowar Hossain",
        "per_ca6dcba1d1715eab92254efbd75b26ff",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_2840fa08985b510ba3f8a28b634b2167",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "HOSSAIN MONOWAR",
            ),
            (
                "can_f7aa12abf34b52ff87c49333ca787bdb",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "HOSSAIN MONOWAR",
            ),
            (
                "can_3414f35b848f5f879407d53641dc6d8d",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "HOSSAIN MONOWAR",
            ),
            (
                "can_3cb61d3ff58c59a280c20f1bf86a2bd2",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "Hossain Monowar",
            ),
            (
                "can_4e4757eb72875b8cbd6c93b346cba8aa",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Hossain Monowar",
            ),
            (
                "can_48ab7053d8815ec1b65ae755836745c4",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Hossain Monowar",
            ),
        ),
        (
            "https://thelocal.to/toronto-mayor-candidates-2023/",
            "https://thelocal.to/mayoral-candidates-toronto-2022-elections/",
        ),
        "Fact-checked candidate histories explicitly join Hossain's selected recurring Toronto mayoral campaigns to the existing 2003 anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "roger-carter-house-continuity",
        "Roger Carter",
        "per_bd699c148fd850939f7f512754a50ae0",
        "canada_house_of_commons",
        "mp",
        (
            ("can_86f4ce6130f15317aa8708d1a966ef72", "ec-ge-39", "Roger Carter"),
            ("can_c8eb38199f205a81a876e7b3274d3eb2", "ec-ge-40", "Roger Carter"),
            ("can_6fe32f62f04c57769ef350b012ba6bfc", "ec-ge-41", "Roger Carter"),
            ("can_15e228e844b559c8b7937d56d111ac26", "ec-ge-42", "Roger Carter"),
        ),
        (
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35005_e.html",
            "https://www.elections.ca/res/rep/off/ovr2015app/41/9988e.html",
        ),
        "Elections Canada's official records preserve Carter's identity, affiliation, and Beaches—East York candidacy sequence through the selected elections.",
    ),
    _anchored_same_office_continuity_assertion(
        "renee-dionne-mayoral-continuity",
        "Renée D!ONNE",
        "per_9f197100b236547bb471a62dbdb08798",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_dc72236addcc53f3badb735518d8d5b4",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "Renée D!ONNE",
            ),
            (
                "can_75dd17d6d7ea59149fcedfa76cef185d",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Renée D!ONNE",
            ),
            (
                "can_462942e8539a5209aa2cc674dc1dc32b",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Renée D!ONNE",
            ),
        ),
        ("https://thelocal.to/toronto-mayor-candidates-2023/",),
        "The Local's fact-checked biography explicitly enumerates D!ONNE's selected 2014, 2018, 2022, and anchored 2023 mayoral history.",
    ),
    _anchored_same_office_continuity_assertion(
        "annamie-paul-house-continuity",
        "Annamie Paul",
        "per_e79b38b37df4599cbcb1d59e95bb7cad",
        "canada_house_of_commons",
        "mp",
        (
            ("can_1302663bc4fc5b7781e970a0a5265de4", "ec-be-2020-10-26", "Annamie Paul"),
            ("can_2f25fbd276b65ced93c71bfb0933df7f", "ec-ge-44", "Annamie Paul"),
        ),
        (
            "https://www.elections.ca/res/rep/off/ovr2019app/51/table12E.html",
            "https://www.elections.ca/res/rep/off/ovr_2020/52/table12E.html",
            "https://www.elections.ca/ele/pas/44ge/can/CoGE44.pdf",
        ),
        "Elections Canada's official candidate records directly document Paul's successive Toronto Centre general- and by-election candidacies.",
    ),
    _anchored_same_office_continuity_assertion(
        "kris-langenfeld-mayoral-continuity",
        "Kris Langenfeld",
        "per_1fb558ab3343524eb3d4a8e94e6e615b",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_ebac9ff292ca598b90556a3b08dedc65",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Langenfeld Kris",
            ),
            (
                "can_78d59ab784595398a3087c86149267da",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Langenfeld Kris",
            ),
        ),
        ("https://thelocal.to/toronto-mayor-candidates-2023/",),
        "The Local's fact-checked 2023 biography explicitly identifies Langenfeld's selected 2018 and 2022 mayoral runs.",
    ),
    _anchored_same_office_continuity_assertion(
        "roxanne-james-house-continuity",
        "Roxanne James",
        "per_829a9d92988c50a8874e1d470c8b9ada",
        "canada_house_of_commons",
        "mp",
        (
            ("can_22f17c8be9095924ad4fa434813e0098", "ec-ge-39", "Roxanne James"),
            ("can_123ba6c64b7b5c48b7b4e153ba1cc47c", "ec-ge-40", "Roxanne James"),
        ),
        ("https://www.ourcommons.ca/members/en/roxanne-james%2835707%29/roles",),
        "The House of Commons roles record joins James's selected Scarborough Centre candidacies to her later parliamentary service.",
    ),
    _anchored_continuity_assertion(
        "john-letonja-adjudicated-council-and-mayor-continuity",
        "John Letonja",
        "per_3bcca97368575b6f819b1259f8c0327c",
        (
            (
                "can_66ee74fb4d44523c95f7badaff598865",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "toronto_city_council",
                "councillor",
                "LETONJA JOHN",
            ),
            (
                "can_3c14428ce7385032aa39ab128b26d4b1",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "toronto_city_council",
                "councillor",
                "Letonja John",
            ),
            (
                "can_380135c2a5da5cde812257188413521c",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "toronto_city_council",
                "mayor",
                "Letonja John",
            ),
            (
                "can_54d16546baa1501db86daaed8677a0b8",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "toronto_city_council",
                "mayor",
                "Letonja John",
            ),
        ),
        ("https://thelocal.to/toronto-mayor-candidates-2023/",),
        "The Local's fact-checked candidate history explicitly enumerates Letonja's selected 2010 mayoral, 2014 Ward 6, 2018 Ward 20, 2022 mayoral, and anchored 2023 mayoral campaigns.",
    ),
    _anchored_same_office_continuity_assertion(
        "jack-weenen-mayoral-continuity",
        "Jack Weenen",
        "per_2d58661c3d25577680d67e2f3fde5c30",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_63168d1227785df587cf35db2408f880",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "Weenen Jack",
            ),
            (
                "can_e9ffbd2dfbf659fa869445254d9435c3",
                "evt_eabc9f0a14165449acd2f9a1e7d557ce",
                "Weenen Jack",
            ),
        ),
        ("https://thelocal.to/toronto-mayor-candidates-2023/",),
        "The Local's fact-checked biography identifies Weenen as the selected 2014 and 2018 mayoral candidate and the existing 2023 anchor.",
    ),
)


DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_same_office_continuity_assertion(
        "terry-parker-house-continuity",
        "Terry Parker",
        "per_432ecd5805715b9591c55a2b1d511a2f",
        "canada_house_of_commons",
        "mp",
        (
            ("can_5c9a3fe3c63550e28334783467cfbc77", "ec-ge-39", "Terry Parker"),
            ("can_3914536ab6905ad89d662a9c542f5f4c", "ec-ge-40", "Terry Parker"),
            ("can_9bd19daacb235a07bc393d40477169a3", "ec-ge-41", "Terry Parker"),
            ("can_466e23199b7e5671b420b2504ad414d6", "ec-ge-42", "Terry Parker"),
            ("can_3f35f869b7a7523eafcb16a534f0600a", "ec-ge-43", "Terry Parker"),
            ("can_7031db4973e3551ebcd7793e8463a161", "ec-ge-44", "Terry Parker"),
        ),
        (
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35068_e.html",
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip",
        ),
        "Elections Canada's official records preserve Parker's distinctive Parkdale—High Park Marijuana candidacy sequence from the existing anchor through these six selected elections.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-kittredge-ontario-continuity",
        "John Kittredge",
        "per_64b4963bd07c52f68aa4ed27565d2e10",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_6d8c5cba21dc592bb0d873a5f1f5f37b", "on-2009-09-17-by-077", "JOHN KITTREDGE"),
            ("can_dd557e6e5f0d5b58aa33d4ad6d6f4938", "on-2011-general", "JOHN KITTREDGE"),
            ("can_7c8248eeac3c537bbb33957ba608bbdc", "on-2014-general", "JOHN KITTREDGE"),
        ),
        ("https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",),
        "Elections Ontario's official records preserve Kittredge's Libertarian identity across the selected provincial sequence and its existing registry anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "ratan-wadhwa-mayoral-continuity",
        "Ratan Wadhwa",
        "per_0517e294728a58aa874e4aabcca03521",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_6b182dbf16b355cc92b62cc0a6c61754",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "WADHWA RATAN",
            ),
            (
                "can_fc7ba687a69254fb9296a9bb33f842f2",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "WADHWA RATAN",
            ),
            (
                "can_9b1a76189fa65047abc2642669568227",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "WADHWA RATAN",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations document Wadhwa's recurring city-wide mayoral candidacies from the existing 2003 anchor through the selected 2006, 2010, and 2014 elections.",
    ),
    _anchored_same_office_continuity_assertion(
        "jaime-castillo-mayoral-continuity",
        "Jaime Castillo",
        "per_8e1056bd79e75f908e9dc80651f3db3c",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_901408e169b75b1193145b9ce628d9d7",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "CASTILLO JAIME",
            ),
            (
                "can_b9a30dd5f92a5fa1ac98b3c55832c90f",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "CASTILLO JAIME",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
        ),
        "The City Clerk's declarations and the adjudicated same-office sequence join Castillo's selected 2006 and 2010 mayoral candidacies to the existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "christine-nugent-house-continuity",
        "Christine Nugent",
        "per_88833869308b5906b67035397250de33",
        "canada_house_of_commons",
        "mp",
        (
            ("can_bc8c9b350e0f5a068c1536cd5465c05a", "ec-ge-43", "Christine Nugent"),
            ("can_1c59b8a1d5a15b74b4f91a3cd4530148", "ec-ge-44", "Christine Nugent"),
        ),
        (
            "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip",
        ),
        "Elections Canada's official records preserve Nugent's name, affiliation, and district continuity across the selected 2019 and 2021 candidacies and the existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "gerald-derome-mayoral-continuity",
        "Gerald Derome",
        "per_3b5c691ecc49595daa1d84a97b6544de",
        "toronto_city_council",
        "mayor",
        (
            (
                "can_d19749aa88cb58a09f4bf091f698ad70",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "DEROME GERALD",
            ),
            (
                "can_29dcaef6aa775e838987f76e9c298b71",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "DEROME GERALD",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
        ),
        "The City Clerk's official declarations and the adjudicated same-office sequence join Derome's selected 2006 and 2010 mayoral occurrences to the existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "nick-dominelli-council-continuity",
        "Nick Dominelli",
        "per_cd8a4fdd446b5e84b2a3a5a8335a5f92",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_bd71429c6a9e5a76910184187daa3a85",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "DOMINELLI NICK",
            ),
            (
                "can_800ffd8dd6d854bc88c3ea5ee3c4b920",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "DOMINELLI NICK",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations preserve Dominelli's same-office and same-district council candidacy sequence across the selected elections and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "nha-le-council-continuity",
        "Nha Le",
        "per_7bb161ef71975c6fb377dfd3dbe9df2d",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_8cb09be00f5c5e20acb08cc3e41c877a",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "LE NHA",
            ),
            (
                "can_9b5f8ace35fb5c8ba5deabeb4efff8d5",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "LE NHA",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
        ),
        "The City Clerk's declarations preserve Le's same-office and same-district council candidacy sequence across the selected elections and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "liz-white-house-continuity",
        "Liz White",
        "per_7ebba43960555aac869a894b7d989baf",
        "canada_house_of_commons",
        "mp",
        (
            ("can_faa2a0ac9b2c5f42907a4920441478df", "ec-be-2008-03-17", "Liz White"),
            ("can_2dd67a9a1d4c5ad797aa774e37ed0c0f", "ec-ge-40", "Liz White"),
        ),
        (
            "https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/content.aspx?section=ele&dir=pas&document=index&lang=e",
        ),
        "Elections Canada's official records preserve White's name, affiliation, and Toronto candidacy continuity across the selected by-election and general-election occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "paul-ferreira-ontario-continuity",
        "Paul Ferreira",
        "per_3ec6d8e61c565378ae90753ba7c51ab9",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_0cc5dc3a02b15a95954e028eca4e180d", "on-2011-general", "PAUL FERREIRA"),
            ("can_7fae5ecc2b535fcaa72a2a79e36765b9", "on-2014-general", "PAUL FERREIRA"),
        ),
        (
            "https://www.ola.org/en/members/all/paul-ferreira",
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
        ),
        "The Legislature profile and Elections Ontario records join Ferreira's selected provincial candidacies to his existing York South—Weston service anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "larry-perlman-council-continuity",
        "Larry Perlman",
        "per_87aea303fe7b5cd48dfdf69cb0eba4c2",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_5ec80b2bd0ae52ef817f16eb7be56d5b",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "PERLMAN LARRY",
            ),
            (
                "can_0124a3d729c95efca34f66b48f795136",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "PERLMAN LARRY",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations preserve Perlman's same-office and same-district council candidacy sequence across the selected elections and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "joe-renda-council-continuity",
        "Joe Renda",
        "per_7da89655143a57d3bcc26ad7b6159f57",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_f106a435ee12570b9788d3b96a9c2906",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "RENDA JOE",
            ),
            (
                "can_4b1888ed06a659328a3024df9e427730",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "RENDA JOE",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
        ),
        "The City Clerk's declarations preserve Renda's same-office and same-district council candidacy sequence across the selected elections and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "ahmad-tahir-tdsb-continuity",
        "Tahir Ahmad",
        "per_7003c6c13d0e5483a2bfe9a210876145",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_c5f3ccb9d8cf551ba376343fc304c0fc",
                "evt_ae45ae96069c5f2aacddabffa8135f7f",
                "Ahmad Tahir",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/",),
        "The official Toronto trustee by-election record preserves Tahir's same-board, same-office, and same-district continuity with the existing registry anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "george-szebik-house-continuity",
        "George Szebik",
        "per_8da31055b44052e1a7a0c99b3ec529d6",
        "canada_house_of_commons",
        "mp",
        (
            ("can_a0e3e8ab5f135e219e2a765edcc7335c", "ec-ge-39", "George Szebik"),
            ("can_e4c1a405feb851dba9465e1ffb1ef677", "ec-ge-42", "George Szebik"),
        ),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/res/rep/off/ovr2015app/41/data_donnees/pollresults_resultatsbureau35.zip",
        ),
        "Elections Canada's official records preserve Szebik's name and distinctive candidacy attributes across the selected federal occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "king-kim-tdsb-continuity",
        "Kim King",
        "per_b50c46c6e53b5293887c79647c07cdda",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_f787ec4a9d7d55ea93819d501b5cd6ca",
                "evt_ae45ae96069c5f2aacddabffa8135f7f",
                "King Kim",
            ),
            (
                "can_472c2677235952c693076453c31c227b",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "King Kim",
            ),
        ),
        (
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2018Election/Query.aspx?board=Toronto+District+School+Board&lang=en",
            "https://www.toronto.ca/city-government/elections/election-results-reports/",
        ),
        "Official trustee election records preserve Kim's same-board, same-office, and same-district continuity across the selected occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "dave-mckee-ontario-continuity",
        "Dave McKee",
        "per_887b8e6940ba560eb483a93dcb49848f",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_8797ef8c726c57f89ea5872871921c9f", "on-2018-general", "Dave McKee"),
            ("can_451c4db51696534bb4c37e1a797c5a5f", "on-2025-general", "DAVE MCKEE"),
        ),
        ("https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",),
        "Elections Ontario's official records preserve McKee's identity and distinctive affiliation across the selected provincial occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "julian-heller-ontario-continuity",
        "Julian Heller",
        "per_ca97342fa4a85117ba21fde778700d73",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_d915416caefe59198083756e9d173132", "on-2007-general", "JULIAN HELLER"),
            ("can_6d34bead3ca35674a4918c9be982f31c", "on-2009-09-17-by-077", "JULIAN HELLER"),
        ),
        ("https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",),
        "Elections Ontario's official records preserve Heller's identity and distinctive affiliation across the selected provincial occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "ram-maharaj-tdsb-continuity",
        "Ram Maharaj",
        "per_c4e03c616eee5ddc9842c396e18cdbc0",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_433235f813b055b8a3776e0a695f5f1e",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "MAHARAJ RAM",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
        ),
        "The City Clerk's trustee declaration preserves Maharaj's same-board, same-office, and same-district continuity with the existing registry anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "noah-ng-tdsb-continuity",
        "Noah Ng",
        "per_104453d2f1f8529d8a895a9cff4f8a84",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_821976c977a659d3bdfe7ef6105d1b08",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "NG NOAH",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
        ),
        "The City Clerk's trustee declaration preserves Ng's same-board, same-office, and same-district continuity with the existing registry anchor.",
    ),
)


DEFAULT_IDENTITY_ASSERTIONS += (
    _anchored_same_office_continuity_assertion(
        "lorne-gershuny-house-continuity",
        "Lorne Gershuny",
        "per_970295c941de5158932c51498c713b00",
        "canada_house_of_commons",
        "mp",
        (
            ("can_581f5f90c4885eb1b2b23c1f2ac94320", "ec-ge-39", "Lorne Gershuny"),
            ("can_10fd7e7f85d65640b4c91d4bf46fbc45", "ec-ge-40", "Lorne Gershuny"),
            ("can_cc810e6403d258b4ada8e6431e81c733", "ec-ge-41", "Lorne Gershuny"),
            ("can_51c100e6944a56b4bff3a072e102eaab", "ec-ge-42", "Lorne Gershuny"),
            ("can_04f974a908ef5aeda5184b8a9ad209a1", "ec-ge-43", "Lorne Gershuny"),
            ("can_a21d32e40dbc5dbcb700d513bfae309c", "ec-ge-44", "Lorne Gershuny"),
            ("can_46b77b5d8c885992a07271a191192cbf", "ec-ge-45", "Lorne Gershuny"),
        ),
        (
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35068_e.html",
            "https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/pollresults_resultatsbureau35.zip",
        ),
        "Elections Canada's official records preserve Gershuny's distinctive Parkdale—High Park Marxist-Leninist candidacy sequence from the existing anchor through all seven selected elections.",
    ),
    _anchored_same_office_continuity_assertion(
        "anna-di-carlo-house-continuity",
        "Anna Di Carlo",
        "per_a350bd52f6f05303aa964794fa870141",
        "canada_house_of_commons",
        "mp",
        (
            ("can_5bc71705d867592bbcf1abaacfe7b643", "ec-ge-39", "Anna Di Carlo"),
            ("can_f6bb633b6fdf595389850084d93af8f3", "ec-ge-40", "Anna Di Carlo"),
            ("can_927ac5c5ca5851d1ac9acea0c2eacc4c", "ec-ge-41", "Anna Di Carlo"),
            ("can_838f2824a48251c98819912319b6b9ec", "ec-ge-42", "Anna Di Carlo"),
            ("can_2e12ccf89df25985b22c00c06222276c", "ec-ge-44", "Anna Di Carlo"),
        ),
        (
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35024_e.html",
            "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureau35.zip",
        ),
        "Elections Canada's official records preserve Di Carlo's name, profession, and Marxist-Leninist affiliation across the selected federal occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "marcell-rodden-house-continuity",
        "Marcell Rodden",
        "per_3f95bc6d19675a809a78bbbc3fd61003",
        "canada_house_of_commons",
        "mp",
        (
            ("can_8595ffb4b565529a8f7c1359807beec5", "ec-ge-39", "Marcell Rodden"),
            ("can_776257cbd48e5ca4bb4202530f5714eb", "ec-ge-40", "Marcell Rodden"),
        ),
        (
            "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/pollresults_resultatsbureau35.zip",
            "https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip",
        ),
        "Elections Canada's official records preserve Rodden's name and distinctive candidacy attributes across the selected federal occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "dan-harris-house-continuity",
        "Dan Harris",
        "per_9357f8bf332550b6af971c04eafa3dbd",
        "canada_house_of_commons",
        "mp",
        (
            ("can_d3ca1352f9b1540ba3e1f454583fdcb0", "ec-ge-38", "Dan Harris"),
            ("can_81e31ebdfb825611a66fc33b20bbd64d", "ec-ge-39", "Dan Harris"),
        ),
        ("https://www.ourcommons.ca/members/en/dan-harris%2830428%29/roles",),
        "The House of Commons roles record explicitly enumerates Harris's 2004 and 2006 Scarborough Southwest defeats before his 2011 election.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-carmichael-house-continuity",
        "John Carmichael",
        "per_33d6e2b27ccc5a80a8ab679c25df5526",
        "canada_house_of_commons",
        "mp",
        (
            ("can_900cb2b69ea75df797053866fbdd2401", "ec-ge-39", "John Carmichael"),
            ("can_e03516a4ce805d868343b23ed6b14a8f", "ec-ge-40", "John Carmichael"),
        ),
        ("https://www.ourcommons.ca/Members/en/john-carmichael%2835555%29/roles",),
        "The House of Commons roles record explicitly enumerates Carmichael's 2006 and 2008 Don Valley West defeats before his 2011 election.",
    ),
    _anchored_same_office_continuity_assertion(
        "john-vassal-tdsb-continuity",
        "John Vassal",
        "per_4b96f894a15d5a12b2949bbfa78433bc",
        "toronto_district_school_board",
        "trustee",
        (
            (
                "can_8b84d6731cfd5c1f9985c1ad66b9b811",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "VASSAL JOHN",
            ),
            (
                "can_3b055889396b5c4197691d7355fa6e85",
                "evt_e4fe1909276b5fbd91057022b350fff3",
                "Vassal John",
            ),
            (
                "can_ecb9c751999855838847c6ea154a5f85",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Vassal John",
            ),
        ),
        (
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2014ElectionResults/Query.aspx?board=Toronto+District+School+Board&lang=en",
            "https://elections.ontarioschooltrustees.org/ResourceToolKit/2018Election/Query.aspx?board=Toronto+District+School+Board&lang=en",
            "https://elections.ontarioschooltrustees.org/2022Election/Query.aspx?board=Toronto+District+School+Board&lang=en",
        ),
        "The official Ontario trustee election archive preserves Vassal's same-board, same-office, and same-district candidacy continuity across the selected 2014, 2018, and 2022 elections and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "angela-salewsky-ontario-continuity",
        "Angela Salewsky",
        "per_561845b4a2305303a01cfcb2140c023c",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_310b726bfb595889a7dbcd1329f146b0", "on-2013-08-01-by-024", "ANGELA SALEWSKY"),
            ("can_d2b28f5376de5a99b2124208ed0d8eba", "on-2014-general", "ANGELA SALEWSKY"),
        ),
        ("https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",),
        "Elections Ontario's official records preserve Salewsky's identity and affiliation across the selected 2013 by-election and 2014 general-election occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "alejandra-bravo-council-continuity",
        "Alejandra Bravo",
        "per_b3471e8be4765e51b0381303a6c7a36d",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_ea146d9cbad959179dd04dbfb037d648",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "BRAVO ALEJANDRA",
            ),
            (
                "can_1f117e090c2855258c47189504fd41ce",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "BRAVO ALEJANDRA",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations preserve Bravo's Ward 17 council candidacy continuity across the selected 2006 and 2014 occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "alan-burke-council-continuity",
        "Alan Burke",
        "per_3b515950560656eb99d50260596bf3c0",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_da9814962775583fbf675e80aa04b730",
                "evt_159f073fa6f15c23a840651723d3c3af",
                "BURKE ALAN",
            ),
            (
                "can_7f932249e362534d826e376baad85736",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "BURKE ALAN",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations preserve Burke's same-office and same-district council candidacy continuity across the selected occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "diana-hall-council-continuity",
        "Diana Hall",
        "per_a68ce4440ecb53909b63decb6ff47e53",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_e2975b624cc053808bf8af2a0d68d1e3",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "HALL DIANA",
            ),
            (
                "can_c7df068f3b2f55b996869eef64e44f66",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "HALL DIANA",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations preserve Hall's same-office and same-district council candidacy continuity across the selected occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "roland-lin-council-continuity",
        "Roland Lin",
        "per_7f16f04b79e654249cc57c71d9c4067e",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_3147322cca885b70832fdcebb3cdb6af",
                "evt_50c15fe55fa753fba75abfada8da3c38",
                "Lin Roland",
            ),
            (
                "can_4571a25bd3ba5aeab301fb652162679c",
                "evt_a52ef78967f05336bdb5d591fd50f122",
                "Lin Roland",
            ),
        ),
        ("https://www.toronto.ca/city-government/elections/election-results-reports/",),
        "The City Clerk's official records preserve Lin's same-office and same-district council candidacy continuity across the selected 2021 and 2022 occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "mazhar-shafiq-ontario-continuity",
        "Mazhar Shafiq",
        "per_ebc96bc18f7256ee8fd66e2c80cdaef7",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_1070791a7f3c5cb08487e1676802ae64", "on-2022-general", "MAZHAR SHAFIQ"),
            ("can_1f70f3ed5cf25273875ed37f89441d9c", "on-2025-general", "MAZHAR SHAFIQ"),
        ),
        ("https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",),
        "Elections Ontario's official records preserve Shafiq's identity, affiliation, and district continuity from the existing anchor through the selected 2022 and 2025 candidacies.",
    ),
    _anchored_same_office_continuity_assertion(
        "mohammed-mirza-council-continuity",
        "Mohammed Mirza",
        "per_e2d46923cf4c58af906b6bfbb8ffc6ea",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_71dca1bd9b98520f892bab5c08a8f1c5",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "MIRZA MOHAMMED",
            ),
            (
                "can_662816308a7e5235b9d6ad5e69a3b002",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "MIRZA MOHAMMED",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations preserve Mirza's same-office and same-district council candidacy continuity across the selected occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "jimmy-talpa-council-continuity",
        "Jimmy Talpa",
        "per_d8ea7abcdbca51aa8972a43c151bd5d0",
        "toronto_city_council",
        "councillor",
        (
            (
                "can_e1d0b69607ee57f58756f389241487a4",
                "evt_5a786c1da7ec5e758036205f04351fc5",
                "TALPA JIMMY",
            ),
            (
                "can_2267495f8c53525faa69c6217b095fb9",
                "evt_54673fd104ab5ef08eb865e162ac040c",
                "TALPA JIMMY",
            ),
        ),
        (
            "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
            "https://www.toronto.ca/wp-content/uploads/2017/08/9059-election-2014-clerksofficialdeclarationofresults.pdf",
        ),
        "The City Clerk's declarations preserve Talpa's same-office and same-district council candidacy continuity across the selected occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "mariangela-sanabria-ontario-continuity",
        "Mariangela Sanabria",
        "per_ebab0c212826591caf49b1538b5eb261",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_12fec9bb28e15a8fb8a342d4e3b166c0", "on-2007-02-08-by-102", "MARIANGELA SANABRIA"),
            ("can_c9c870344b1f5fdd880b405b264ffb0d", "on-2007-general", "MARIANGELA SANABRIA"),
        ),
        ("https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",),
        "Elections Ontario's official records preserve Sanabria's identity and affiliation across the selected 2007 by-election and general-election occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "ryan-kidd-ontario-continuity",
        "Ryan Kidd",
        "per_956a8be294385cdd947b0e836f4184be",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_b3615f199add52ca86e3b995837e5933", "on-2007-general", "RYAN KIDD"),
            ("can_e37ea9a1774a558397423712f693541c", "on-2011-general", "RYAN KIDD"),
        ),
        ("https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",),
        "Elections Ontario's official records preserve Kidd's identity and distinctive affiliation across the selected provincial occurrences and existing anchor.",
    ),
    _anchored_same_office_continuity_assertion(
        "wayne-simmons-ontario-continuity",
        "Wayne Simmons",
        "per_43973d2507a655e1b18d6fbcec100522",
        "ontario_legislative_assembly",
        "mpp",
        (
            ("can_14fe7feb962a5279b138727dff87af93", "on-2005-11-24-by-076", "WAYNE SIMMONS"),
            ("can_8b5fe4d6e75e5ac7a9e826b58e755c32", "on-2007-02-08-by-102", "WAYNE SIMMONS"),
            ("can_adffc951e31751c4b4dcdfda84259c76", "on-2007-general", "WAYNE SIMMONS"),
            ("can_98a108ef9a655421bbef2480f0eddab1", "on-2010-02-04-by-094", "WAYNE SIMMONS"),
            ("can_01e35757d63f5cbe9d25e592c1f3c803", "on-2011-general", "WAYNE SIMMONS"),
            ("can_284bed2868fe5f5e914d3b8b6eb04e94", "on-2013-08-01-by-024", "WAYNE SIMMONS"),
            ("can_115c3a323cdd56dea6f693cc4b51f4f0", "on-2014-general", "WAYNE SIMMONS"),
            ("can_2710ccb731ac51d8b80dc35f492c103a", "on-2016-09-01-by-083", "Wayne Simmons"),
            ("can_788217a71a985d4295149315811cc4ef", "on-2018-general", "Wayne Simmons"),
            ("can_2f1ae38bf3d656b69e9afc6b36677690", "on-2022-general", "WAYNE SIMMONS"),
        ),
        (
            "https://results.elections.on.ca/api/report-groups/1/report-outputs/932/csv",
            "https://freedomparty.on.ca/",
        ),
        "Elections Ontario and Freedom Party records preserve Simmons's distinctive Freedom Party candidacy identity across the ten selected provincial occurrences and existing anchor.",
    ),
)
