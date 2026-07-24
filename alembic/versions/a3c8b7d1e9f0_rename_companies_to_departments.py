"""rename companies → departments, company_id → department_id

Revision ID: a3c8b7d1e9f0
Revises: cb0990d55c7d
Create Date: 2026-07-23 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a3c8b7d1e9f0'
down_revision: Union[str, None] = 'cb0990d55c7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop FK constraints referencing companies.id
    op.drop_constraint(
        op.f('interview_sessions_company_id_fkey'),
        'interview_sessions',
        type_='foreignkey',
    )
    op.drop_constraint(
        op.f('candidate_invitations_company_id_fkey'),
        'candidate_invitations',
        type_='foreignkey',
    )
    op.drop_constraint(
        op.f('company_documents_company_id_fkey'),
        'company_documents',
        type_='foreignkey',
    )
    op.drop_constraint(
        op.f('interview_templates_company_id_fkey'),
        'interview_templates',
        type_='foreignkey',
    )

    # 2. Rename tables
    op.rename_table('companies', 'departments')
    op.rename_table('company_documents', 'department_documents')

    # 3. Rename company_id → department_id on all tables
    op.alter_column('interview_sessions', 'company_id', new_column_name='department_id')
    op.alter_column('candidate_invitations', 'company_id', new_column_name='department_id')
    op.alter_column('department_documents', 'company_id', new_column_name='department_id')
    op.alter_column('interview_templates', 'company_id', new_column_name='department_id')

    # 4. Recreate FK constraints pointing to departments.id
    op.create_foreign_key(
        op.f('interview_sessions_department_id_fkey'),
        'interview_sessions', 'departments',
        ['department_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('candidate_invitations_department_id_fkey'),
        'candidate_invitations', 'departments',
        ['department_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('department_documents_department_id_fkey'),
        'department_documents', 'departments',
        ['department_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('interview_templates_department_id_fkey'),
        'interview_templates', 'departments',
        ['department_id'], ['id'],
        ondelete='CASCADE',
    )

    # 5. Rename indexes
    op.execute('ALTER INDEX IF EXISTS idx_companies_org RENAME TO idx_departments_org')
    op.execute('ALTER INDEX IF EXISTS idx_documents_company RENAME TO idx_documents_department')
    op.execute('ALTER INDEX IF EXISTS idx_sessions_company RENAME TO idx_sessions_department')
    op.execute('ALTER INDEX IF EXISTS idx_invitations_company RENAME TO idx_invitations_department')


def downgrade() -> None:
    # 1. Drop new FK constraints
    op.drop_constraint(
        op.f('interview_sessions_department_id_fkey'),
        'interview_sessions',
        type_='foreignkey',
    )
    op.drop_constraint(
        op.f('candidate_invitations_department_id_fkey'),
        'candidate_invitations',
        type_='foreignkey',
    )
    op.drop_constraint(
        op.f('department_documents_department_id_fkey'),
        'department_documents',
        type_='foreignkey',
    )
    op.drop_constraint(
        op.f('interview_templates_department_id_fkey'),
        'interview_templates',
        type_='foreignkey',
    )

    # 2. Rename department_id → company_id
    op.alter_column('interview_sessions', 'department_id', new_column_name='company_id')
    op.alter_column('candidate_invitations', 'department_id', new_column_name='company_id')
    op.alter_column('department_documents', 'department_id', new_column_name='company_id')
    op.alter_column('interview_templates', 'department_id', new_column_name='company_id')

    # 3. Rename tables back
    op.rename_table('departments', 'companies')
    op.rename_table('department_documents', 'company_documents')

    # 4. Recreate old FK constraints
    op.create_foreign_key(
        op.f('interview_sessions_company_id_fkey'),
        'interview_sessions', 'companies',
        ['company_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('candidate_invitations_company_id_fkey'),
        'candidate_invitations', 'companies',
        ['company_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('company_documents_company_id_fkey'),
        'company_documents', 'companies',
        ['company_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('interview_templates_company_id_fkey'),
        'interview_templates', 'companies',
        ['company_id'], ['id'],
        ondelete='CASCADE',
    )

    # 5. Rename indexes back
    op.execute('ALTER INDEX IF EXISTS idx_departments_org RENAME TO idx_companies_org')
    op.execute('ALTER INDEX IF EXISTS idx_documents_department RENAME TO idx_documents_company')
    op.execute('ALTER INDEX IF EXISTS idx_sessions_department RENAME TO idx_sessions_company')
    op.execute('ALTER INDEX IF EXISTS idx_invitations_department RENAME TO idx_invitations_company')
