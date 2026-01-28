"""Rename model_config to llm_config

Revision ID: 84ff28d6e50e
Revises: cf16da3b3148
Create Date: 2026-01-28 13:50:38.474919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84ff28d6e50e'
down_revision: Union[str, None] = 'cf16da3b3148'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('agents', 'model_config', new_column_name='llm_config')


def downgrade() -> None:
    op.alter_column('agents', 'llm_config', new_column_name='model_config')
