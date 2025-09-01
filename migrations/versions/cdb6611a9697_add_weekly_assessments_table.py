"""add weekly_assessments table

Revision ID: cdb6611a9697
Revises: 4fb09da0541d
Create Date: 2025-08-31 23:59:31.338208
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cdb6611a9697'
down_revision = '4fb09da0541d'  # parent is the notification migration
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'weekly_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('week_date', sa.Date(), nullable=False),

        sa.Column('glucose_frequency', sa.Integer(), nullable=True),
        sa.Column('range_compliance', sa.Integer(), nullable=True),      # 0–100 or score
        sa.Column('energy_level', sa.Integer(), nullable=True),          # 1–5
        sa.Column('sleep_quality', sa.Integer(), nullable=True),         # 1–5
        sa.Column('medication_adherence', sa.Integer(), nullable=True),  # 1–5
        sa.Column('concerns', sa.Text(), nullable=True),
        sa.Column('overall_feeling', sa.Integer(), nullable=True),       # 1–5

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'week_date', name='uq_weekly_assessments_user_week')
    )

def downgrade():
    op.drop_table('weekly_assessments')
