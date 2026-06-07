"""add due_date to loans

Revision ID: d4e1f2a3b5c6
Revises: c6b7da6debc2
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e1f2a3b5c6'
down_revision: Union[str, None] = 'c6b7da6debc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('loans', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_loans_due_date', 'loans', ['due_date'])


def downgrade() -> None:
    op.drop_index('idx_loans_due_date', table_name='loans')
    op.drop_column('loans', 'due_date')
