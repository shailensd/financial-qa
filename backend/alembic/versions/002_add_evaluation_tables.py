"""Add evaluation tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create evaluation_results table
    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_case_id', sa.String(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('faithfulness', sa.Float(), nullable=False),
        sa.Column('answer_relevancy', sa.Float(), nullable=False),
        sa.Column('refusal_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expected_refusal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('refusal_correct', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_results_id'), 'evaluation_results', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_results_test_case_id'), 'evaluation_results', ['test_case_id'], unique=False)
    op.create_index(op.f('ix_evaluation_results_model_used'), 'evaluation_results', ['model_used'], unique=False)
    op.create_index(op.f('ix_evaluation_results_created_at'), 'evaluation_results', ['created_at'], unique=False)

    # Create evaluation_aggregates table
    op.create_table(
        'evaluation_aggregates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('mean_faithfulness', sa.Float(), nullable=False),
        sa.Column('mean_answer_relevancy', sa.Float(), nullable=False),
        sa.Column('test_cases_count', sa.Integer(), nullable=False),
        sa.Column('refusal_accuracy', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_aggregates_id'), 'evaluation_aggregates', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_aggregates_model_used'), 'evaluation_aggregates', ['model_used'], unique=False)
    op.create_index(op.f('ix_evaluation_aggregates_created_at'), 'evaluation_aggregates', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_evaluation_aggregates_created_at'), table_name='evaluation_aggregates')
    op.drop_index(op.f('ix_evaluation_aggregates_model_used'), table_name='evaluation_aggregates')
    op.drop_index(op.f('ix_evaluation_aggregates_id'), table_name='evaluation_aggregates')
    op.drop_table('evaluation_aggregates')
    
    op.drop_index(op.f('ix_evaluation_results_created_at'), table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_model_used'), table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_test_case_id'), table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_id'), table_name='evaluation_results')
    op.drop_table('evaluation_results')
