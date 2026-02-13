"""Add model_configs table for dynamic routing

Revision ID: 20260211_add_model_configs
Revises: 20260211_add_search_vector
Create Date: 2026-02-11 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260211_add_model_configs'
down_revision = '20260211_add_search_vector'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create model_configs table
    op.create_table(
        'model_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('context_window', sa.Integer(), nullable=False),
        sa.Column('max_output_tokens', sa.Integer(), nullable=False),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('cost_per_1k_input', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('cost_per_1k_output', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes concurrently
    # Note: Alembic's op.create_index doesn't support postgresql_concurrently directly in a transaction.
    # We would usually use op.execute("CREATE UNIQUE INDEX CONCURRENTLY ...") but standard alembic
    # runs in a transaction. For this AI environment, we'll use standard index creation.
    op.create_index('uq_model_provider_name', 'model_configs', ['provider', 'model_name'], unique=True)
    op.create_index('ix_model_configs_active_priority', 'model_configs', ['is_active', 'priority'])
    op.create_index('ix_model_configs_capabilities', 'model_configs', ['capabilities'], postgresql_using='gin')

    # Seed data
    # (id, provider, model_name, display_name, context_window, max_output_tokens, capabilities, cost_per_1k_input, cost_per_1k_output, priority)
    seed_data = [
        ('550e8400-e29b-41d4-a716-446655440000', 'openai', 'gpt-4o', 'GPT-4o', 128000, 4096, '["streaming", "tools", "vision", "json_mode"]', 0.005, 0.015, 0),
        ('550e8400-e29b-41d4-a716-446655440001', 'openai', 'gpt-4o-mini', 'GPT-4o Mini', 128000, 4096, '["streaming", "tools", "vision", "json_mode"]', 0.00015, 0.0006, 0),
        ('550e8400-e29b-41d4-a716-446655440002', 'openai', 'gpt-4-turbo', 'GPT-4 Turbo', 128000, 4096, '["streaming", "tools", "vision"]', 0.01, 0.03, 1),
        ('550e8400-e29b-41d4-a716-446655440003', 'anthropic', 'claude-3-5-sonnet-latest', 'Claude 3.5 Sonnet', 200000, 8192, '["streaming", "tools", "vision"]', 0.003, 0.015, 0),
        ('550e8400-e29b-41d4-a716-446655440004', 'anthropic', 'claude-3-opus-latest', 'Claude 3 Opus', 200000, 4096, '["streaming", "tools", "vision"]', 0.015, 0.075, 1),
        ('550e8400-e29b-41d4-a716-446655440005', 'anthropic', 'claude-3-haiku-latest', 'Claude 3 Haiku', 200000, 4096, '["streaming", "tools"]', 0.00025, 0.00125, 0),
    ]

    for data in seed_data:
        op.execute(
            f"INSERT INTO model_configs (id, provider, model_name, display_name, context_window, max_output_tokens, capabilities, cost_per_1k_input, cost_per_1k_output, priority) "
            f"VALUES ('{data[0]}', '{data[1]}', '{data[2]}', '{data[3]}', {data[4]}, {data[5]}, '{data[6]}', {data[7]}, {data[8]}, {data[9]}) "
            f"ON CONFLICT (provider, model_name) DO NOTHING"
        )


def downgrade() -> None:
    op.drop_table('model_configs')
