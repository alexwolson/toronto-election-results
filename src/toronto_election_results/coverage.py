"""Inclusive election-date scope for the 2026 Toronto forecasting archive."""

from datetime import date

ELECTION_DAY = date(2026, 10, 26)

# The window opens with each level's last general election before amalgamation (ADR 0010).
COVERAGE_START_BY_LEVEL = {
    "federal": date(1993, 10, 25),
    "municipal": date(1994, 11, 14),
    "provincial": date(1995, 6, 8),
}
_LEVEL_BY_AUTHORITY = {"elections_canada": "federal", "elections_ontario": "provincial"}


def coverage_level(election_authority: object) -> str:
    """Return the government level whose window applies to an Election authority."""

    return _LEVEL_BY_AUTHORITY.get(str(election_authority), "municipal")
