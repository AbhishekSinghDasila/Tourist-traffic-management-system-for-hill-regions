"""create alert tables

Revision ID: c1a2b3d4e5f6
Revises: 
Create Date: 2026-06-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('emergency_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('triggered_by', sa.UUID(), nullable=False),
        sa.Column('alert_type', sa.String(length=30), nullable=False),
        sa.Column('description', sa.String(length=300), nullable=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('district', sa.String(length=80), nullable=True),
        sa.Column('radius_km', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('recipient_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_emergency_alerts_created_at', 'emergency_alerts', ['created_at'])
    op.create_index('ix_emergency_alerts_district', 'emergency_alerts', ['district'])
    op.create_index('ix_emergency_alerts_status', 'emergency_alerts', ['status'])

    op.create_table('user_locations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('district', sa.String(length=80), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_locations_user_id', 'user_locations', ['user_id'])

    op.create_table('alert_recipients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('alert_id', sa.UUID(), nullable=False),
        sa.Column('recipient_type', sa.String(length=20), nullable=False),
        sa.Column('recipient_id', sa.String(length=100), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('delivery_status', sa.String(length=20), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['emergency_alerts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_recipients_alert_id', 'alert_recipients', ['alert_id'])


def downgrade() -> None:
    op.drop_index('ix_alert_recipients_alert_id', table_name='alert_recipients')
    op.drop_table('alert_recipients')
    op.drop_index('ix_user_locations_user_id', table_name='user_locations')
    op.drop_table('user_locations')
    op.drop_index('ix_emergency_alerts_status', table_name='emergency_alerts')
    op.drop_index('ix_emergency_alerts_district', table_name='emergency_alerts')
    op.drop_index('ix_emergency_alerts_created_at', table_name='emergency_alerts')
    op.drop_table('emergency_alerts')
