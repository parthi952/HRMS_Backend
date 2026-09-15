"""add employee device_pin for biometric attendance sync

Revision ID: a1b2c3d4e5f6
Revises: b7c1d2e3f4a5
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b7c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('device_pin', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_employees_device_pin', ['device_pin'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('employees') as batch_op:
        batch_op.drop_constraint('uq_employees_device_pin', type_='unique')
        batch_op.drop_column('device_pin')
