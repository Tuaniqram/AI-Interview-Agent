"""add v4 evidence-driven tables + profile_data to candidate_profiles

Revision ID: f0a1b2c3d4e5
Revises: e9f8d7c6b5a4
Create Date: 2026-07-24 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'e9f8d7c6b5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add profile_data column to candidate_profiles
    op.add_column(
        'candidate_profiles',
        sa.Column('profile_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Create evidence_store table
    op.create_table(
        'evidence_store',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('competency', sa.Text(), nullable=False),
        sa.Column('dimension', sa.Text(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('evidence_text', sa.Text(), nullable=False),
        sa.Column('source_question', sa.Text(), nullable=False),
        sa.Column('question_number', sa.Integer(), nullable=False),
        sa.Column('hypothesis_id', sa.UUID(), nullable=True),
        sa.Column('hypothesis_relevance', sa.Float(), nullable=True),
        sa.Column('evidence_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_check_constraint(
        'evidence_score_check', 'evidence_store',
        'score >= 0 AND score <= 10',
    )
    op.create_check_constraint(
        'evidence_confidence_check', 'evidence_store',
        'confidence >= 0 AND confidence <= 1',
    )
    op.create_check_constraint(
        'evidence_dimension_check', 'evidence_store',
        "dimension IN ('technical','communication','reasoning','behavioral','confidence','completeness')",
    )
    op.create_index('idx_evidence_session', 'evidence_store', ['session_id'])
    op.create_index('idx_evidence_session_competency', 'evidence_store', ['session_id', 'competency'])
    op.create_index('idx_evidence_session_dimension', 'evidence_store', ['session_id', 'dimension'])
    op.create_index('idx_evidence_hypothesis', 'evidence_store', ['hypothesis_id'])

    # Create hypotheses table
    op.create_table(
        'hypotheses',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('direction', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('supporting_evidence', postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column('contradicting_evidence', postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='untested'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_check_constraint(
        'hypothesis_direction_check', 'hypotheses',
        "direction IN ('positive', 'negative')",
    )
    op.create_check_constraint(
        'hypothesis_confidence_check', 'hypotheses',
        'confidence >= 0 AND confidence <= 1',
    )
    op.create_check_constraint(
        'hypothesis_status_check', 'hypotheses',
        "status IN ('untested', 'testing', 'confirmed', 'refuted')",
    )
    op.create_index('idx_hypotheses_session', 'hypotheses', ['session_id'])
    op.create_index('idx_hypotheses_session_status', 'hypotheses', ['session_id', 'status'])

    # Create interview_objectives table
    op.create_table(
        'interview_objectives',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('competency', sa.Text(), nullable=False),
        sa.Column('dimension', sa.Text(), nullable=False),
        sa.Column('hypothesis_id', sa.UUID(), nullable=True),
        sa.Column('hypothesis_statement', sa.Text(), nullable=True),
        sa.Column('hypothesis_confidence', sa.Float(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('evidence_ids', postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_check_constraint(
        'objective_status_check', 'interview_objectives',
        "status IN ('pending', 'probed', 'satisfied')",
    )
    op.create_index('idx_objectives_session', 'interview_objectives', ['session_id'])
    op.create_index('idx_objectives_session_status', 'interview_objectives', ['session_id', 'status'])

    # Create consistency_checks table
    op.create_table(
        'consistency_checks',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('dimension', sa.Text(), nullable=False),
        sa.Column('answers_compared', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('consistency_score', sa.Float(), nullable=False),
        sa.Column('contradictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_check_constraint(
        'consistency_score_check', 'consistency_checks',
        'consistency_score >= 0 AND consistency_score <= 1',
    )
    op.create_index('idx_consistency_session', 'consistency_checks', ['session_id'])

    # Create observations table
    op.create_table(
        'observations',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('question_number', sa.Integer(), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=False),
        sa.Column('pattern', sa.Text(), nullable=True),
        sa.Column('risk_signal', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_check_constraint(
        'observation_value_check', 'observations',
        'value >= 0 AND value <= 1',
    )
    op.create_index('idx_observations_session', 'observations', ['session_id'])
    op.create_index('idx_observations_session_type', 'observations', ['session_id', 'type'])


def downgrade() -> None:
    op.drop_table('observations')
    op.drop_table('consistency_checks')
    op.drop_table('interview_objectives')
    op.drop_table('hypotheses')
    op.drop_table('evidence_store')
    op.drop_column('candidate_profiles', 'profile_data')
