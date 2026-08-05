"""add_v5_intelligence_tables

Revision ID: b7c9d1e2f3a4
Revises: a7f3c2e1b9d4
Create Date: 2026-08-05 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7c9d1e2f3a4'
down_revision: Union[str, None] = 'a7f3c2e1b9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('company_brains',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.BigInteger(), nullable=True),
    sa.Column('company_name', sa.Text(), nullable=False),
    sa.Column('industry', sa.Text(), nullable=True),
    sa.Column('company_vision', sa.Text(), nullable=True),
    sa.Column('values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('technical_stack', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('culture', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('success_signals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('red_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('source_documents', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('source_version', sa.Text(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_company_brains_department', 'company_brains', ['department_id'], unique=False)
    op.create_index('idx_company_brains_session', 'company_brains', ['session_id'], unique=False)
    op.create_table('scorecards',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.BigInteger(), nullable=True),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('competencies', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('required_level', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scorecards_department', 'scorecards', ['department_id'], unique=False)
    op.create_index('idx_scorecards_session', 'scorecards', ['session_id'], unique=False)
    op.create_table('interview_blueprints',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.BigInteger(), nullable=True),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('objectives', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('phases', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('hypothesis_template', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('evidence_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_interview_blueprints_department', 'interview_blueprints', ['department_id'], unique=False)
    op.create_index('idx_interview_blueprints_session', 'interview_blueprints', ['session_id'], unique=False)
    op.create_table('candidate_brains',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('candidate_id', sa.UUID(), nullable=True),
    sa.Column('full_name', sa.Text(), nullable=False),
    sa.Column('resume_summary', sa.Text(), nullable=True),
    sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('strengths', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('weaknesses', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('work_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('inferred_seniority', sa.Text(), nullable=True),
    sa.Column('persona', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('source_version', sa.Text(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_candidate_brains_candidate', 'candidate_brains', ['candidate_id'], unique=False)
    op.create_index('idx_candidate_brains_session', 'candidate_brains', ['session_id'], unique=False)
    op.create_table('candidate_documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('candidate_id', sa.UUID(), nullable=True),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('filename', sa.Text(), nullable=False),
    sa.Column('document_type', sa.Text(), server_default='resume', nullable=False),
    sa.Column('content_hash', sa.Text(), nullable=True),
    sa.Column('extracted_text', sa.Text(), nullable=True),
    sa.Column('document_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_candidate_documents_candidate', 'candidate_documents', ['candidate_id'], unique=False)
    op.create_index('idx_candidate_documents_session', 'candidate_documents', ['session_id'], unique=False)
    op.create_table('candidate_evidence_requirements',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('competency', sa.Text(), nullable=False),
    sa.Column('dimension', sa.Text(), nullable=False),
    sa.Column('required_probes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('evidence_level', sa.Text(), server_default='behavioral', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_candidate_evidence_requirements_session', 'candidate_evidence_requirements', ['session_id'], unique=False)
    op.create_table('interview_brain',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('current_hypotheses', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('evidence_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('competency_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('difficulty_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('decision_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('brain_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id')
    )
    op.create_index('idx_interview_brain_session', 'interview_brain', ['session_id'], unique=False)
    op.create_table('evidence_graph',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('nodes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('edges', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id')
    )
    op.create_index('idx_evidence_graph_session', 'evidence_graph', ['session_id'], unique=False)
    op.create_table('interview_timeline',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.Text(), nullable=False),
    sa.Column('question_number', sa.Integer(), nullable=True),
    sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_interview_timeline_session', 'interview_timeline', ['session_id'], unique=False)
    op.create_index('idx_interview_timeline_session_event', 'interview_timeline', ['session_id', 'event_type'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_interview_timeline_session_event', table_name='interview_timeline')
    op.drop_index('idx_interview_timeline_session', table_name='interview_timeline')
    op.drop_table('interview_timeline')
    op.drop_index('idx_evidence_graph_session', table_name='evidence_graph')
    op.drop_table('evidence_graph')
    op.drop_index('idx_interview_brain_session', table_name='interview_brain')
    op.drop_table('interview_brain')
    op.drop_index('idx_candidate_evidence_requirements_session', table_name='candidate_evidence_requirements')
    op.drop_table('candidate_evidence_requirements')
    op.drop_index('idx_candidate_documents_session', table_name='candidate_documents')
    op.drop_index('idx_candidate_documents_candidate', table_name='candidate_documents')
    op.drop_table('candidate_documents')
    op.drop_index('idx_candidate_brains_session', table_name='candidate_brains')
    op.drop_index('idx_candidate_brains_candidate', table_name='candidate_brains')
    op.drop_table('candidate_brains')
    op.drop_index('idx_interview_blueprints_session', table_name='interview_blueprints')
    op.drop_index('idx_interview_blueprints_department', table_name='interview_blueprints')
    op.drop_table('interview_blueprints')
    op.drop_index('idx_scorecards_session', table_name='scorecards')
    op.drop_index('idx_scorecards_department', table_name='scorecards')
    op.drop_table('scorecards')
    op.drop_index('idx_company_brains_session', table_name='company_brains')
    op.drop_index('idx_company_brains_department', table_name='company_brains')
    op.drop_table('company_brains')
