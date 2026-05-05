"""Initial schema with all 7 tables

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('filing_type', sa.String(), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('filing_date', sa.Date(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_company'), 'documents', ['company'], unique=False)
    op.create_index(op.f('ix_documents_fiscal_year'), 'documents', ['fiscal_year'], unique=False)

    # Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('section_label', sa.String(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chunks_id'), 'chunks', ['id'], unique=False)
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)

    # Create queries table
    op.create_table(
        'queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_queries_id'), 'queries', ['id'], unique=False)
    op.create_index(op.f('ix_queries_session_id'), 'queries', ['session_id'], unique=False)
    op.create_index(op.f('ix_queries_timestamp'), 'queries', ['timestamp'], unique=False)

    # Create responses table
    op.create_table(
        'responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_id', sa.Integer(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('refusal_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('refusal_reason', sa.String(), nullable=True),
        sa.Column('repair_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['query_id'], ['queries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_responses_id'), 'responses', ['id'], unique=False)
    op.create_index(op.f('ix_responses_query_id'), 'responses', ['query_id'], unique=False)

    # Create citations table
    op.create_table(
        'citations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('response_id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['response_id'], ['responses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citations_id'), 'citations', ['id'], unique=False)
    op.create_index(op.f('ix_citations_response_id'), 'citations', ['response_id'], unique=False)
    op.create_index(op.f('ix_citations_chunk_id'), 'citations', ['chunk_id'], unique=False)

    # Create memory_summaries table
    op.create_table(
        'memory_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('turn_range_start', sa.Integer(), nullable=False),
        sa.Column('turn_range_end', sa.Integer(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_summaries_id'), 'memory_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_memory_summaries_session_id'), 'memory_summaries', ['session_id'], unique=False)
    op.create_index(op.f('ix_memory_summaries_created_at'), 'memory_summaries', ['created_at'], unique=False)

    # Create logs table
    op.create_table(
        'logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('query_id', sa.Integer(), nullable=False),
        sa.Column('log_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['query_id'], ['queries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_logs_id'), 'logs', ['id'], unique=False)
    op.create_index(op.f('ix_logs_session_id'), 'logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_logs_query_id'), 'logs', ['query_id'], unique=False)
    op.create_index(op.f('ix_logs_created_at'), 'logs', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order to respect foreign key constraints
    op.drop_index(op.f('ix_logs_created_at'), table_name='logs')
    op.drop_index(op.f('ix_logs_query_id'), table_name='logs')
    op.drop_index(op.f('ix_logs_session_id'), table_name='logs')
    op.drop_index(op.f('ix_logs_id'), table_name='logs')
    op.drop_table('logs')
    
    op.drop_index(op.f('ix_memory_summaries_created_at'), table_name='memory_summaries')
    op.drop_index(op.f('ix_memory_summaries_session_id'), table_name='memory_summaries')
    op.drop_index(op.f('ix_memory_summaries_id'), table_name='memory_summaries')
    op.drop_table('memory_summaries')
    
    op.drop_index(op.f('ix_citations_chunk_id'), table_name='citations')
    op.drop_index(op.f('ix_citations_response_id'), table_name='citations')
    op.drop_index(op.f('ix_citations_id'), table_name='citations')
    op.drop_table('citations')
    
    op.drop_index(op.f('ix_responses_query_id'), table_name='responses')
    op.drop_index(op.f('ix_responses_id'), table_name='responses')
    op.drop_table('responses')
    
    op.drop_index(op.f('ix_queries_timestamp'), table_name='queries')
    op.drop_index(op.f('ix_queries_session_id'), table_name='queries')
    op.drop_index(op.f('ix_queries_id'), table_name='queries')
    op.drop_table('queries')
    
    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_id'), table_name='chunks')
    op.drop_table('chunks')
    
    op.drop_index(op.f('ix_documents_fiscal_year'), table_name='documents')
    op.drop_index(op.f('ix_documents_company'), table_name='documents')
    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')
