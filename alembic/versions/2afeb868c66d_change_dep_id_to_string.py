"""change dep_id to string

Revision ID: 2afeb868c66d
Revises: 6e55d3d88293
Create Date: 2026-05-03 16:05:35.415947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2afeb868c66d'
down_revision: Union[str, Sequence[str], None] = '6e55d3d88293'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
