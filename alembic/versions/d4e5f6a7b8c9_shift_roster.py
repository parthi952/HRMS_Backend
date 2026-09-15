"""add shift roster and per-employee shift assignment

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'shifts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('start_time', sa.String(), nullable=False),
        sa.Column('end_time', sa.String(), nullable=False),
        sa.Column('full_day_hours', sa.Float(), nullable=False, server_default='8.5'),
        sa.Column('half_day_hours', sa.Float(), nullable=False, server_default='4.0'),
    )

    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('shift_id', sa.Integer(), sa.ForeignKey('shifts.id'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('employees') as batch_op:
        batch_op.drop_column('shift_id')
    op.drop_table('shifts')
