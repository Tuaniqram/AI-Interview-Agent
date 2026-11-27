"""Years of professional experience read from CV text, without an LLM.

Deterministic and explainable: the same CV always gives the same number, and ``explain_years`` says where it came from.
Sources, in order of trust:

1. ``ranges``    date ranges on work lines ("Jan 2019 - Mar 2022", "2024 -- 2025", "03/2020 - present"); overlapping jobs
                 are merged so they are not counted twice; education and certification lines are skipped.
2. ``statement`` an explicit total ("5 years of experience", "8+ yrs", "about one year of experience", or a duration in the
                 CV's title line such as "Backend Developer (5 years)").
3. ``durations`` per-role durations on work lines ("(3 yrs)", "6-month internship"), added up.

The result is rounded DOWN to whole years, so a 6-month internship is 0 years. ``None`` when the CV states nothing usable.
"""
from __future__ import annotations

import re
from datetime import date
from typing import NamedTuple, Optional

MAX_YEARS = 50

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5,
    "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}

_MONTH_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
_YEAR_RE = r"(?:19[7-9]\d|20\d\d)"
# One end of a range: "Mar 2019", "March 2019", "03/2019", "3.2019", "2019-03" or "2019".
_POINT_RE = rf"(?:{_MONTH_RE}\s*,?\s*{_YEAR_RE}|\d{{1,2}}\s*[/.]\s*{_YEAR_RE}|{_YEAR_RE}\s*[-/.]\s*\d{{1,2}}(?!\d)|{_YEAR_RE})"
_OPEN_END_RE = r"(?:present|current|currently|now|today|ongoing|date)"
_RANGE_RE = re.compile(
    rf"(?P<start>{_POINT_RE})\s*(?:-{{1,2}}|–|—|to|until|till|through)\s*(?P<end>{_POINT_RE}|{_OPEN_END_RE})",
    re.IGNORECASE,
)

_NUMBER_RE = r"(?:\d+(?:\.\d+)?|" + "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True)) + r")"
_YEARS_UNIT_RE = r"(?:years?|yrs?)"
_MONTHS_UNIT_RE = r"(?:months?|mos?)"
# "5 years of experience", "8+ yrs experience", "over 3 years' experience", "about one year of experience".
_STATEMENT_RE = re.compile(
    rf"(?P<n>{_NUMBER_RE})\s*\+?\s*(?:-\s*)?{_YEARS_UNIT_RE}['’]?\s+(?:of\s+)?(?:\w+\s+){{0,3}}?experience",
    re.IGNORECASE,
)
# "(5 years)", "(3 yrs)", "2 years", "6-month", "18 months".
_DURATION_RE = re.compile(
    rf"(?<![\w.])(?P<n>{_NUMBER_RE})\s*\+?\s*-?\s*(?P<unit>{_YEARS_UNIT_RE}|{_MONTHS_UNIT_RE})\b",
    re.IGNORECASE,
)

# Headings that start a section whose dates are not work experience.
_NON_WORK_HEADING_RE = re.compile(
    r"^\s*(education|academic|qualifications?|certifications?|courses?|training|awards?|publications?|"
    r"languages?|interests?|hobbies|references?|volunteer(?:ing)?)\b[\s:]*$",
    re.IGNORECASE,
)
_WORK_HEADING_RE = re.compile(
    r"^\s*((?:work|professional|employment|career)?\s*(?:experience|history)|employment|work|projects?)\b[\s:]*$",
    re.IGNORECASE,
)
# A line that is about study, not a job, even outside an Education section. Only degree words count: a job AT a university
# or college ("IT support, City University, 2019 - 2022") is still work.
_STUDY_LINE_RE = re.compile(
    r"(?<![a-z])(?:b\.\s?s\.?|b\.?\s?sc|b\.?\s?tech|b\.\s?e\.|bca|mca|m\.\s?s\.?|m\.?\s?sc|m\.?\s?tech|mba|ph\.?\s?d)(?![a-z])"
    r"|\b(?:bachelor|master'?s|degree|diploma|graduated|gpa|cgpa|high school|bootcamp)\b",
    re.IGNORECASE,
)


class YearsEstimate(NamedTuple):
    years: Optional[int]
    source: str  # "ranges" | "statement" | "durations" | "none"
    months: Optional[float]


def _to_number(token: str) -> Optional[float]:
    token = (token or "").strip().lower()
    if token in _WORD_NUMBERS:
        return float(_WORD_NUMBERS[token])
    try:
        return float(token)
    except ValueError:
        return None


def _parse_point(text: str, today: date, is_end: bool) -> Optional[tuple[int, int]]:
    """(year, month) for one end of a range. A bare year means January for a start and December for an end."""
    t = text.strip().lower().rstrip(".")
    if re.fullmatch(_OPEN_END_RE, t):
        return today.year, today.month
    m = re.fullmatch(rf"({_MONTH_RE})\s*,?\s*({_YEAR_RE})", t)
    if m:
        return int(m.group(2)), _MONTHS[m.group(1).rstrip(".")[:3]]
    m = re.fullmatch(rf"(\d{{1,2}})\s*[/.]\s*({_YEAR_RE})", t)
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(2)), int(m.group(1))
    m = re.fullmatch(rf"({_YEAR_RE})\s*[-/.]\s*(\d{{1,2}})", t)
    if m and 1 <= int(m.group(2)) <= 12:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(_YEAR_RE, t)
    if m:
        return int(t), (12 if is_end else 1)
    return None


def _work_lines(text: str) -> list[str]:
    """Lines that may describe jobs: everything outside non-work sections, minus lines about study."""
    lines: list[str] = []
    in_non_work = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if _NON_WORK_HEADING_RE.match(line):
            in_non_work = True
            continue
        if _WORK_HEADING_RE.match(line):
            in_non_work = False
            continue
        # "Education: B.Tech Computer Science." is a one-line section of its own.
        if re.match(r"^\s*(education|certifications?|courses?)\s*:", line, re.IGNORECASE):
            continue
        if in_non_work or _STUDY_LINE_RE.search(line):
            continue
        lines.append(line)
    return lines


def _months_from_ranges(lines: list[str], today: date) -> Optional[float]:
    intervals: list[tuple[int, int]] = []  # month indexes (year * 12 + month - 1), end exclusive
    for line in lines:
        for m in _RANGE_RE.finditer(line):
            start = _parse_point(m.group("start"), today, is_end=False)
            end = _parse_point(m.group("end"), today, is_end=True)
            if not start or not end:
                continue
            s = start[0] * 12 + start[1] - 1
            e = end[0] * 12 + end[1]  # through the end month
            # A bare-year range like "2024 -- 2025" means about a year, not 24 months: use January to January.
            if re.fullmatch(_YEAR_RE, m.group("end").strip()) and re.fullmatch(_YEAR_RE, m.group("start").strip()):
                e = end[0] * 12 if end[0] > start[0] else s + 6
            now = today.year * 12 + today.month
            e = min(e, now)
            if e <= s or (e - s) > MAX_YEARS * 12:
                continue
            intervals.append((s, e))
    if not intervals:
        return None
    intervals.sort()
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return float(sum(e - s for s, e in merged))


def _months_from_statement(text: str) -> Optional[float]:
    best: Optional[float] = None
    for m in _STATEMENT_RE.finditer(text or ""):
        n = _to_number(m.group("n"))
        if n is not None and 0 <= n <= MAX_YEARS:
            best = max(best or 0.0, n * 12)
    if best is not None:
        return best
    # A total in the title line: "Priya Nair - Backend Developer (5 years)".
    first = next((ln for ln in (text or "").splitlines() if ln.strip()), "")
    m = re.search(rf"\(\s*(?P<n>{_NUMBER_RE})\s*\+?\s*{_YEARS_UNIT_RE}\s*\)", first, re.IGNORECASE)
    if m:
        n = _to_number(m.group("n"))
        if n is not None and 0 <= n <= MAX_YEARS:
            return n * 12
    return None


def _months_from_durations(lines: list[str]) -> Optional[float]:
    total = 0.0
    found = False
    for line in lines[1:] if lines else []:  # the title line's total is a statement, not a role
        for m in _DURATION_RE.finditer(line):
            n = _to_number(m.group("n"))
            if n is None or n > MAX_YEARS * 12:
                continue
            unit = m.group("unit").lower()
            total += n * 12 if unit.startswith(("y",)) else n
            found = True
    return total if found else None


def explain_years(text: str, today: Optional[date] = None) -> YearsEstimate:
    """Years of experience plus where the number came from (see the module docstring)."""
    today = today or date.today()
    lines = _work_lines(text)
    for source, months in (
        ("ranges", _months_from_ranges(lines, today)),
        ("statement", _months_from_statement(text)),
        ("durations", _months_from_durations(lines)),
    ):
        if months is not None:
            years = int(min(MAX_YEARS * 12, months) // 12)
            return YearsEstimate(years, source, round(months, 1))
    return YearsEstimate(None, "none", None)


def years_of_experience(text: str, today: Optional[date] = None) -> Optional[int]:
    """Whole years of professional experience in a CV (rounded down), or None when the CV states nothing usable."""
    return explain_years(text, today).years
