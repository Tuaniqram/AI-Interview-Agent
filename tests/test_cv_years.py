from datetime import date

import pytest

from app.intelligence.cv_years import explain_years, years_of_experience

TODAY = date(2026, 11, 27)

BRIAN = """Brian Osei
Python Developer | brian.osei@test.com | +1 555 010 0101
Summary
Junior Python developer with about one year of experience. I have worked on
a few small internal projects and a customer support tool.
Skills
Python, basic Django, SQL, HTML, Git
Experience
Junior Developer -- TechHelp Services (2024 -- 2025)
 - Helped maintain an internal ticket system built with Django.
Education
B.S. Information Technology, local college (2020 -- 2024)
"""

PRIYA = """Priya Nair - Backend Developer (5 years)
Skills: Python, FastAPI, PostgreSQL, Redis, Docker, AWS (ECS, RDS, SQS), Celery
Experience:
- Payments platform at a fintech (3 yrs): built the ledger service in FastAPI/PostgreSQL, moved
  nightly settlement from a cron script to idempotent Celery jobs, cut settlement time from 4h to 35min.
- E-commerce startup (2 yrs): owned the order API, added Redis caching for catalog reads.
Education: B.Tech Computer Science.
"""

RAHUL = """Rahul Verma - Aspiring Backend Developer
Skills: Python, Django, MySQL, Git, HTML/CSS
Experience:
- 6-month internship at a small agency: fixed bugs in a Django admin panel and wrote a few CRUD pages.
- College project: a library management website (Django + MySQL).
Education: BCA, 2024. Completed an online Python course.
"""


def test_year_only_range_counts_one_year_and_skips_education():
    est = explain_years(BRIAN, TODAY)
    assert (est.years, est.source) == (1, "ranges")


def test_title_line_total_when_there_are_no_dates():
    est = explain_years(PRIYA, TODAY)
    assert (est.years, est.source) == (5, "statement")


def test_six_month_internship_is_zero_years():
    est = explain_years(RAHUL, TODAY)
    assert (est.years, est.source) == (0, "durations")


@pytest.mark.parametrize(
    "line, years",
    [
        ("Backend Engineer, Acme  Jan 2019 - Mar 2022", 3),
        ("Engineer, Acme  March 2020 – present", 6),
        ("Developer  03/2021 - 08/2023", 2),
        ("Developer  2021-03 to 2023-09", 2),
        ("Lead  Sept 2015 — Dec 2016", 1),
    ],
)
def test_range_formats(line, years):
    assert years_of_experience("Experience\n" + line, TODAY) == years


def test_overlapping_jobs_are_not_double_counted():
    cv = "Experience\nAcme  Jan 2018 - Dec 2021\nSide gig at Beta  Jan 2020 - Dec 2020\n"
    assert years_of_experience(cv, TODAY) == 4


def test_gaps_between_jobs_are_not_counted():
    cv = "Experience\nAcme  Jan 2015 - Dec 2016\nBeta  Jan 2020 - Dec 2021\n"
    assert years_of_experience(cv, TODAY) == 4


def test_future_end_is_capped_at_today():
    assert years_of_experience("Experience\nAcme  Jan 2024 - Dec 2030", TODAY) == 2


@pytest.mark.parametrize(
    "text, years",
    [
        ("Senior engineer with 8+ years of experience in payments.", 8),
        ("Over 3 years' experience building APIs.", 3),
        ("Two years of backend development experience.", 2),
    ],
)
def test_explicit_statement(text, years):
    est = explain_years(text, TODAY)
    assert (est.years, est.source) == (years, "statement")


def test_dates_win_over_a_stated_total():
    cv = "10 years of experience.\nExperience\nAcme  Jan 2022 - Dec 2023\n"
    assert explain_years(cv, TODAY).source == "ranges"
    assert years_of_experience(cv, TODAY) == 2


def test_nothing_usable_is_none():
    assert explain_years("Jane Doe\nSkills: Python, SQL\n", TODAY) == (None, "none", None)
    assert years_of_experience("", TODAY) is None


def test_study_lines_outside_education_are_ignored():
    cv = "Experience\nMSc Computer Science, Some University  2018 - 2020\nAcme  Jan 2021 - Dec 2021\n"
    assert years_of_experience(cv, TODAY) == 1


def test_a_job_at_a_university_still_counts():
    cv = "Experience\nIT Support, City University  Jan 2019 - Dec 2021\n"
    assert years_of_experience(cv, TODAY) == 3


def test_words_that_look_like_degrees_do_not_drop_a_job():
    cv = "Experience\nBeta Corp  Jan 2020 - Dec 2021\nMS SQL Server admin, Gamma  Jan 2022 - Dec 2022\n"
    assert years_of_experience(cv, TODAY) == 3


async def test_profile_upload_parse_uses_cv_dates_not_the_llm(monkeypatch):
    from types import SimpleNamespace

    from app.candidates import resume_service

    class FakeLLM:
        async def ainvoke(self, messages):
            return SimpleNamespace(content='{"skills": ["python"], "years_of_experience": 12}')

    async def no_cache(*a, **k):
        return None

    monkeypatch.setattr(resume_service, "llm", FakeLLM())
    monkeypatch.setattr(resume_service.content_cache, "get", no_cache)
    monkeypatch.setattr(resume_service.content_cache, "put", no_cache)
    data = await resume_service.parse_resume("Experience\nAcme  Jan 2022 - Dec 2023\n")
    assert data["skills"] == ["python"]
    assert data["years_of_experience"] == 2
