"""Regression tests for the organization-only surface.

The department API and UI were removed, so these tests guard the replacement
routes and the response shapes that no longer carry department fields.
"""
import uuid
from types import SimpleNamespace

from app.api.v1.org_content import _template_response
from app.main import app


def test_organization_content_routes_replace_departments():
    paths = app.openapi()["paths"]

    assert "/api/v1/orgs/{org_id}/documents" in paths
    assert "/api/v1/orgs/{org_id}/sessions" in paths
    assert "/api/v1/orgs/{org_id}/templates" in paths
    assert "/api/v1/orgs/{org_id}/members" in paths
    assert "/api/v1/departments" not in paths


def test_analytics_uses_it_roles_not_departments():
    paths = app.openapi()["paths"]

    assert "/api/v1/analytics/sessions/by-it-role" in paths
    assert "/api/v1/analytics/sessions/by-department" not in paths


def test_scorecard_results_route_is_registered():
    paths = app.openapi()["paths"]

    assert "/api/v1/orgs/{org_id}/scorecards/results" in paths


def test_admin_pages_have_platform_endpoints():
    paths = app.openapi()["paths"]

    for path in (
        "/api/v1/admin/audit-logs",
        "/api/v1/admin/llm-status",
        "/api/v1/admin/llm-usage",
        "/api/v1/admin/email-templates",
    ):
        assert path in paths


def test_template_response_has_no_department_field():
    template = SimpleNamespace(
        id=uuid.uuid4(),
        it_role_id=uuid.uuid4(),
        name="Backend interview",
        job_role_snapshot="Backend Developer",
        level_code=None,
        description=None,
        interview_style="STANDARD",
        competencies=[],
        total_questions=10,
        scorecard_template_id=None,
        created_at=None,
    )

    response = _template_response(template)

    assert response.job_role == "Backend Developer"
    assert response.total_questions == 10
    assert "department_id" not in response.model_dump()
