"""Cross-verify the parsed 2000 City results against Wikipedia's independent tables.

Wikipedia's 2000 article lists most councillor wards as bulleted ``*Name votes`` lines (given-first
names, votes with commas, ``acclaimed`` for uncontested seats). Four wards (8, 10, 13, 15) are
transcluded templates whose data is not in the article wikitext, so they are cross-checked only at
winner level elsewhere; this module reports them as un-cross-checked rather than pretending to
verify them. Candidates are matched by identity key so name-order/case differences don't matter.
"""

from __future__ import annotations

import re

import pandas as pd

from .candidates import match_key

# Ward headers appear two ways: "'''Ward 34 - [[...]]:'''" and, when the number is inside a
# link, "'''[[Ward 20 ...|Ward 36 - Scarborough Southwest]]:'''". Capture the displayed number.
_WARD_SPLIT = re.compile(r"'''(?:\[\[[^|\]]*\|)?\s*Ward (\d+)\b[^\n]*?'''")
_WIKILINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]")
_TRAILING_VOTES = re.compile(r"([\d,]+)\s*$")


def parse_wikipedia_wards(wikitext: str) -> dict[int, dict[str, int | None]]:
    """Return {ward -> {candidate_key -> votes (None = acclaimed)}} for bullet-format wards."""
    parts = _WARD_SPLIT.split(wikitext)
    wards: dict[int, dict[str, int | None]] = {}
    for i in range(1, len(parts), 2):
        ward, body = int(parts[i]), parts[i + 1]
        candidates: dict[str, int | None] = {}
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line.startswith("*"):
                continue
            line = line[1:].replace("(incumbent)", "").replace("\t", " ").strip()
            if line.lower().endswith("acclaimed"):
                name, votes = line[: -len("acclaimed")], None
            else:
                match = _TRAILING_VOTES.search(line)
                if not match:
                    continue
                name, votes = line[: match.start()], int(match.group(1).replace(",", ""))
            name = _WIKILINK.sub(r"\1", name).replace("'''", "").strip()
            if name:
                candidates[match_key(name)] = votes
        if candidates:
            wards[ward] = candidates
    return wards


def crosscheck_2000(city_df: pd.DataFrame, wikitext: str) -> dict:
    """Compare parsed City councillor results to Wikipedia. Returns a report dict."""
    wiki = parse_wikipedia_wards(wikitext)
    council = city_df[city_df["office"] == "councillor"]

    checked, uncrosschecked, mismatches = [], [], []
    for ward, group in council.groupby("ward_number"):
        ward = int(ward)
        city = {match_key(n): int(v) for n, v in zip(group["candidate_name_raw"], group["votes"])}
        if ward not in wiki:
            uncrosschecked.append(ward)
            continue
        checked.append(ward)
        wiki_ward = wiki[ward]
        for key, city_votes in city.items():
            if key not in wiki_ward:
                mismatches.append((ward, key, "only in City", city_votes, None))
            elif wiki_ward[key] is not None and city_votes != wiki_ward[key]:
                mismatches.append((ward, key, "vote mismatch", city_votes, wiki_ward[key]))
        for key, wiki_votes in wiki_ward.items():
            if key not in city:
                mismatches.append((ward, key, "only in Wikipedia", None, wiki_votes))

    return {
        "wards_checked": sorted(checked),
        "wards_uncrosschecked": sorted(uncrosschecked),
        "candidates_compared": sum(len(wiki[w]) for w in checked),
        "mismatches": mismatches,
    }


if __name__ == "__main__":
    from pathlib import Path

    from .parse_2000 import parse_2000_results

    wikitext = Path("data/reference/wikipedia_2000.wikitext").read_text()
    report = crosscheck_2000(parse_2000_results(), wikitext)
    print(f"wards cross-checked (candidate-level): {len(report['wards_checked'])}/44")
    print(f"  candidates compared: {report['candidates_compared']}")
    print(f"  un-cross-checked (template wards): {report['wards_uncrosschecked']}")
    print(f"  mismatches: {len(report['mismatches'])}")
    for m in report["mismatches"]:
        print(f"    ward {m[0]} {m[1]}: {m[2]} (City={m[3]}, Wiki={m[4]})")
