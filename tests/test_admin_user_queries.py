"""The admin user list/count must compile: they once failed with 'returned no FROM clauses due to auto-correlation'."""
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

from app.admin import service
from app.models.db import Organization, User


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_user_list_query_compiles_and_filters_to_hiring_accounts():
    query = (
        select(User, Organization.name.label("org_name"))
        .outerjoin(Organization, Organization.owner_user_id == User.id)
        .where(service._HIRING_ACCOUNT)
        .order_by(User.created_at.desc())
    )
    sql = _sql(query)
    assert "EXISTS" in sql and "is_admin" in sql


def test_user_count_query_compiles():
    assert "count" in _sql(select(func.count(User.id)).where(service._HIRING_ACCOUNT)).lower()
