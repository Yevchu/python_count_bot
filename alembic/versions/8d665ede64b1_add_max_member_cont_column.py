"""add max_member_cont column

Revision ID: 8d665ede64b1
Revises: 38a11d83afa2
Create Date: 2024-11-24 13:39:09.417109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d665ede64b1'
down_revision: Union[str, None] = '38a11d83afa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('groups', sa.Column('max_member_count', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('groups', 'max_member_count')
    # ### end Alembic commands ###