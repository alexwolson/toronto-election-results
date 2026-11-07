"""Published locations of the City of Toronto files the build reads.

`source_detail` names the file a Candidacy came from by its published URL, not by its path in
this repository's download cache: a general election's poll-by-poll workbook as the results ZIP's
URL followed by `::` and the workbook's path inside the ZIP, and a by-election workbook by its own
URL. Council roster tenures cite the attendance and voting records the same way. Every file named
here is on the City's Open Data portal.
"""

from __future__ import annotations

_PORTAL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset"
_RESULTS = f"{_PORTAL}/96d35404-44d9-49d8-95bb-fb1e5489240d/resource"
_BY_ELECTIONS = f"{_PORTAL}/97d72233-8681-4b3d-828e-4929d40d122c/resource"

GENERAL_RESULT_URLS = {
    2003: f"{_RESULTS}/1ed53c9d-a316-465e-96ce-e72be74f8aa9/download/2003-results.zip",
    2006: f"{_RESULTS}/3fb1227c-a279-4523-a1aa-f00190ba717f/download/2006-results.zip",
    2010: f"{_RESULTS}/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip",
    2014: f"{_RESULTS}/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip",
    2018: f"{_RESULTS}/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip",
    2022: f"{_RESULTS}/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip",
}

# Mayor and council by-election workbooks, keyed by the file name the download cache uses, which is
# the last part of the URL.
BY_ELECTION_RESULT_URLS = {
    filename: f"{_BY_ELECTIONS}/{resource}/download/{filename}"
    for filename, resource in (
        ("2016-councillor-ward-2.xlsx", "389e00d1-8637-4e6f-88bc-7f6936a2a150"),
        ("2017-councillor-ward-42.xlsx", "edf3e37a-b416-47f6-9cef-d7369a1b4553"),
        (
            "2021-councillor-ward-22-scarborough-agincourt-1.xlsx",
            "287f8b0d-dde8-4ebd-887c-bd9f628a2e3c",
        ),
        ("2023_office_of_the_mayor.xlsx", "868f890d-5432-432b-823c-c6a6fafa2f63"),
        (
            "2023-office-of-the-councillor-ward-20-poll-by-poll.xlsx",
            "5ced6a0b-1f7a-4717-b522-da02a4d916ab",
        ),
        ("2024-councillor-ward-15-poll-by-poll.xlsx", "7e64ea38-c3a4-4b1f-a68e-4127dfca6430"),
        ("2025-councillor-ward25-poll-by-poll.xlsx", "1a29cfb8-0ee8-4e7d-b415-f07963d5a436"),
    )
}


def general_result_source(year: int, member: str) -> str:
    """The published location of one workbook inside a general election's results ZIP."""

    return f"{GENERAL_RESULT_URLS[year]} :: {member}"


def by_election_result_source(filename: str) -> str:
    """The published location of a mayor or council by-election workbook."""

    try:
        return BY_ELECTION_RESULT_URLS[filename]
    except KeyError:
        raise ValueError(f"no published URL recorded for by-election file {filename!r}") from None


_ATTENDANCE = f"{_PORTAL}/9426c94d-abdb-45fe-9a81-79be40d204d2/resource"
_VOTING = f"{_PORTAL}/7f5232d6-0d2a-4f95-864a-417cbf341cc4/resource"

# The City Council attendance and voting records behind the Council rosters, by file name.
COUNCIL_RECORD_URLS = {
    filename: f"{base}/{resource}/download/{filename}"
    for base, filename, resource in (
        (
            _ATTENDANCE,
            "councillors-meeting-attendance-2006-2010.csv",
            "28c4b513-4210-4ea4-9454-839d57e55d98",
        ),
        (
            _ATTENDANCE,
            "councillors-meeting-attendance-2010-2014.csv",
            "34d61725-e383-4633-ab5e-c7b6d639fad9",
        ),
        (
            _ATTENDANCE,
            "councillors-meeting-attendance-2014-2018.csv",
            "76c23b41-d5e5-44b6-b5fd-e40c6409b1e3",
        ),
        (
            _ATTENDANCE,
            "councillors-meeting-attendance-2018-2022.csv",
            "05449b17-32bf-4329-8558-5167a960ea56",
        ),
        (
            _ATTENDANCE,
            "councillors-meeting-attendance-2022-2026.csv",
            "073189ce-951e-4a18-a466-705abf3802d1",
        ),
        (_VOTING, "member-voting-record-2006-2010.csv", "01655cbd-dc66-4339-9f27-891e64413cbf"),
        (_VOTING, "member-voting-record-2010-2014.csv", "6c7dd98b-08d0-4f68-bee7-a0ba77a7da92"),
        (_VOTING, "member-voting-record-2014-2018.csv", "11d89d61-24c3-4241-8194-04b22098745e"),
        (_VOTING, "member-voting-record-2018-2022.csv", "373390e9-af88-4b58-a6a4-6863e3606a4b"),
        (_VOTING, "member-voting-record-2022-2026.csv", "c4feb78c-c867-42a9-b803-7c6d859df969"),
    )
}
