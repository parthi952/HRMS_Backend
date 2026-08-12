"""add birthday wish delivery logs

Revision ID: b7c1d2e3f4a5
Revises: 935db1e717a3
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "935db1e717a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "birthday_wish_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("emp_id", sa.String(), nullable=False),
        sa.Column("employee_name", sa.String(), nullable=True),
        sa.Column("to_email", sa.String(), nullable=False),
        sa.Column("birthday_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "emp_id",
            "birthday_date",
            name="uq_birthday_wish_employee_date",
        ),
    )
    op.create_index(
        op.f("ix_birthday_wish_logs_id"),
        "birthday_wish_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_birthday_wish_logs_emp_id"),
        "birthday_wish_logs",
        ["emp_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_birthday_wish_logs_birthday_date"),
        "birthday_wish_logs",
        ["birthday_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_birthday_wish_logs_birthday_date"),
        table_name="birthday_wish_logs",
    )
    op.drop_index(
        op.f("ix_birthday_wish_logs_emp_id"),
        table_name="birthday_wish_logs",
    )
    op.drop_index(
        op.f("ix_birthday_wish_logs_id"),
        table_name="birthday_wish_logs",
    )
    op.drop_table("birthday_wish_logs")
