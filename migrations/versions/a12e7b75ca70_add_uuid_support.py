"""Add UUID support (no-op)

Revision ID: a12e7b75ca70
Revises: 4bc091b23dae
Create Date: 2025-08-17 13:02:17.140112"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "a12e7b75ca70"
down_revision = "4bc091b23dae"
branch_labels = None
depends_on = None


def upgrade():
    """No-op: UUID changes are handled in 4bc091b23dae."""
    pass


def downgrade():
    """No-op."""
    pass
