"""add shift timing and weekly off day to attendance settings

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('attendance_settings') as batch_op:
        batch_op.add_column(sa.Column('shift_start', sa.String(), nullable=False, server_default='09:30 AM'))
        batch_op.add_column(sa.Column('shift_end', sa.String(), nullable=False, server_default='06:30 PM'))
        batch_op.add_column(sa.Column('weekly_off_days', sa.String(), nullable=False, server_default='Sunday'))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('attendance_settings') as batch_op:
        batch_op.drop_column('weekly_off_days')
        batch_op.drop_column('shift_end')
        batch_op.drop_column('shift_start')
