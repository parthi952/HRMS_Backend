"""add attendance day_type, settings, and regularization requests

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('attendance') as batch_op:
        batch_op.add_column(sa.Column('day_type', sa.String(), nullable=True, server_default='Pending'))

    op.create_table(
        'attendance_settings',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('full_day_hours', sa.Float(), nullable=False, server_default='8.5'),
        sa.Column('half_day_hours', sa.Float(), nullable=False, server_default='4.0'),
    )

    op.create_table(
        'attendance_regularizations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('Emp_id', sa.String(), sa.ForeignKey('employees.Emp_id'), nullable=False),
        sa.Column('employee_name', sa.String()),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('requested_check_in', sa.String(), nullable=True),
        sa.Column('requested_check_out', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='Pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('decided_by', sa.String(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('attendance_regularizations')
    op.drop_table('attendance_settings')
    with op.batch_alter_table('attendance') as batch_op:
        batch_op.drop_column('day_type')
