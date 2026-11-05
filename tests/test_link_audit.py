"""The audit of Person links: its samples, its results and the fixes it led to."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parents[1]
AUDIT_DIR = REPO_ROOT / "docs" / "verification" / "link-audit-2026-11-03"


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(AUDIT_DIR / name, dtype="string", keep_default_na=False)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Sat K. Singh Khalsa", ("sat", "khalsa")),
        ("STAN J. GRZYWNA", ("stan", "grzywna")),
        ("Nicolò Fortunato", ("nicolo", "fortunato")),
        ("Magda Gondor Berkovits", ("magda", "berkovits")),
    ],
)
def test_same_name_frame_ignores_middle_names_and_initials(name, expected):
    assert _load_script("draw_link_audit_sample").first_last(name) == expected


def test_audit_results_cover_every_sampled_pair():
    joins = _read("joins_results.csv")
    assert joins["pair_id"].tolist() == _read("joins_sample.csv")["pair_id"].tolist()
    assert set(joins["verdict"]) <= {"CONFIRMED", "CONTRADICTED", "NOT_CONFIRMED"}
    assert joins["stratum"].value_counts().to_dict() == {
        "assertion": 40,
        "review": 40,
        "incumbency": 15,
        "official_record": 15,
        "roster": 10,
    }

    splits = _read("splits_results.csv")
    assert splits["pair_id"].tolist() == _read("splits_sample.csv")["pair_id"].tolist()
    assert set(splits["frame_size"]) == {"196"}
    # A pair counts as one person only if the second check accepted the auditor's evidence.
    same = splits["final_verdict"].eq("SAME_PERSON")
    assert splits.loc[same, "verdict"].eq("SAME_PERSON").all()
    assert splits.loc[same, "second_check"].isin({"ACCEPT", "PARTIAL"}).all()
    assert splits.loc[splits["verdict"].eq("SAME_PERSON"), "second_check"].ne("").all()
    assert int(same.sum()) == 15


def test_audit_results_carry_no_contact_details():
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    phone = re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b")
    for path in AUDIT_DIR.glob("*.csv"):
        text = path.read_text(encoding="utf-8")
        assert not email.search(text), path.name
        assert not phone.search(text), path.name
        assert "file://" not in text, path.name


def test_audit_summary_reports_no_false_merge(capsys):
    summary = _load_script("summarize_link_audit")
    summary.summarize_joins(AUDIT_DIR / "joins_results.csv")
    summary.summarize_splits(AUDIT_DIR / "splits_results.csv")
    out = capsys.readouterr().out
    assert "join two different people: 0.0% (one-sided 95% upper bound 3.9%)" in out
    assert "independently confirmed: 73.0% (95% interval 64.2% to 79.4%)" in out
    assert "one person: 37.5% (95% interval 23.8% to 52.9%), about 74 of 196 pairs" in out


# Each Person the audit's fixes complete, with every run it now holds.
AUDIT_CAREERS = {
    # Stan Grzywna: Parkdale—High Park (Ontario) 1999, 2003 and 2006.
    "per_e33403f4b85c50f398797c2582f79047": [
        "can_cfbcd44125c65ff79bceec985eabe1f9",
        "can_fab6f9aa995059c2a4a6535ce68e2b94",
        "can_1eedba0392975511a141023184ee6834",
    ],
    # Gloria Lindsay Luby: 1994 Etobicoke Ward 7 and Toronto council 1997 to 2010.
    "per_3d8c75381a6d5544ba55fe80cb5f946a": [
        "can_572737c50518516580a34182f24278e3",
        "can_348faeabab7b57fca4aceaba95fe953e",
        "can_3cabbdabad7853088eb90fb4fe3985dc",
        "can_7289eff0d5a85eefb326bf0da85e2dd3",
        "can_d952200c6b98509a8f450d5ea8996147",
        "can_2d8a010807df53428503c231896a8f5c",
    ],
    # Sat K. Singh Khalsa: three Persons became one.
    "per_20abb57696a05b379248b3518ceefa7b": [
        "can_9d895812674e548e98c43fd3015c7f03",
        "can_1593aabe54775efeb5f4c1c6a4fbda36",
        "can_2e5047e364ed5e10b340f41bd227e1a4",
    ],
    # Maria Saras-Voutsinas: 2014 trustee and 2026 council.
    "per_4a892ba346045b789ee04703cebc7b14": [
        "can_d1a699a5bfd95bca9a48d13a12e6e1ed",
        "can_f2571c0845b95d6d9a3dd7cf0b241af4",
    ],
    # Unblind Tibbin: 2011 York West and 2021 Humber River—Black Creek.
    "per_e1856222b9d95f5da5263eeced739fb2": [
        "can_2d2962fa4ccf574d95196373c476c840",
        "can_b002c481c5d6500b8ffffec3c1c3f1ee",
    ],
    # John Nunziata: York South—Weston 1993 to 2000, 2003 mayor and 2014 Ward 12.
    "per_1c7a0a36928b5fb69f0d5a1e10be2fb1": [
        "can_a5f7f4d2638751afbb0d6a793783fba7",
        "can_12de8bcb2bb9574fb350ab92971e8ec7",
        "can_dbe163a5bef35e50b8862e64d59abc9d",
        "can_775dea313a5f5a43b2db1ce993fe6a03",
        "can_0cd830441bb059bab3011ae788b8401e",
    ],
    # Judith Snow: federal runs 1993 to 2000 and 1999 Don Valley West (Ontario).
    "per_18c7eb195c9955af91a398f9110f4453": [
        "can_734e154cbbf556409dae5a8d3d728686",
        "can_1eb781bc6ddf53ecacdd40080bbb9124",
        "can_f1d4389f228c5a53ae8d8de538300761",
        "can_b7d326a678ad5a7997773173b98c01dc",
    ],
    # John Sewell: 1999 Toronto Centre—Rosedale (Ontario) and 2006 Ward 21.
    "per_f53e7a2010255ceb8116a7558b6a04bd": [
        "can_c6fb75a0c3d254a6aa82b704a7ed1ab0",
        "can_78c48a55ebd5557595f36c7ab7a4a60a",
    ],
    # Terry Parker: Parkdale—High Park (federal) 2000 and 2004 to 2025.
    "per_432ecd5805715b9591c55a2b1d511a2f": [
        "can_4868493642c5548c999f13e8742b7938",
        "can_94a9c8ff4fa65e819587107d420ff3ec",
        "can_83c8c927b9a85e2081f8ede388a0d2a6",
    ],
    # Jim Conrad: 1993 St. Paul's (federal) and 1999 Willowdale (Ontario).
    "per_78c7e136429251fdbb7cbedbd5f77fd3": [
        "can_294d1eba8cb754a3ae7bd3efb8410d0c",
        "can_7a8def9ad9e05037bdafbf441e589a15",
    ],
    # Mehmet Ali Yagiz: Toronto—Danforth 2003 and 2006 and the 2003 and 2006 mayoral runs.
    "per_34f86027a4e85065b3f8628892cf286b": [
        "can_857ec522e88b57a8b2ee98346cfe6cca",
        "can_d6173c194d4250bc8b0a18e97e1c7e3a",
        "can_e2d51cef44a75de6885ff72fcf18184b",
        "can_457a50afc38158a2a80231ae7ad4632d",
    ],
    # John Steele: 1994 and 2000 mayoral runs and 2006 Eglinton—Lawrence (federal).
    "per_d0086333d4765d6e8698f919c23a2826": [
        "can_bd305cd075c9575e8712a875b83681f5",
        "can_2fe5215fa60e5a369a3fea55f59955bc",
        "can_62e91ad5c738554d8348cbab799ad8ec",
    ],
    # Pauline Browes: 1993 Scarborough Centre and 2006 Scarborough—Guildwood.
    "per_78d4e5acfd9154fa9cf60977cf897754": [
        "can_be2acc3455635298a878a8be3dbc747c",
        "can_6ff814cbdd5a5fbb85a58f52f9b896ee",
    ],
    # Ellery Hollingsworth: 1994 Scarborough board trustee and 2000 Scarborough Southwest.
    "per_678a6c155c045a00b7c635042c911899": [
        "can_e37964d0dfdb5d0fbbf9f45175a83dc0",
        "can_d4b6cc7f80cd578da531dba52f601694",
    ],
    # Magda Gondor Berkovits: Ward 10 council 2006 and 2010.
    "per_409d52e4e60e55ba991e2eb85acf7bf6": [
        "can_71af1bd2472d51ada5407e4478b6c2d8",
        "can_f7b8dd8cc12a51308b221f47e5f0a289",
    ],
}


def test_link_audit_fixes_join_the_missed_links():
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    for person_id, candidacy_ids in AUDIT_CAREERS.items():
        assert results.loc[candidacy_ids, "person_id"].eq(person_id).all(), person_id
        assert people.loc[person_id, "identity_status"] == "active"
    assert people.loc["per_409d52e4e60e55ba991e2eb85acf7bf6", "preferred_name"] == (
        "Magda Gondor Berkovits"
    )
    assert people.loc["per_e33403f4b85c50f398797c2582f79047", "preferred_name"] == "Stan Grzywna"


def test_link_audit_keeps_party_label_pairs_apart():
    """A shared Marxist-Leninist candidacy is not a distinctive fact, so these stay apart.

    Julie Northrup's 1993 and 1995 runs, the other pair the second check rejected, were later
    joined by the same-name review on an occupation: Elections Canada gives the 1993 candidate as
    a sales representative and the Toronto Star's 1995 profile calls her a sales rep.
    """

    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    for person_id in (
        # Diane Johnston, 1993 federal and 1995 and 1999 provincial.
        "per_62d320a0d0675e4fa19f854fab58d8bd",
        "per_a8ae022c8024542997fcd84b36b6f9c5",
    ):
        assert people.loc[person_id, "identity_status"] == "active"
