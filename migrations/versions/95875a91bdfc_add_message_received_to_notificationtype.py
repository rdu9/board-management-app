"""add message_received to notificationtype

Revision ID: 95875a91bdfc
Revises: 8eabcc7cbf80
Create Date: 2026-05-18 20:19:00.700228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95875a91bdfc'
down_revision: Union[str, Sequence[str], None] = '8eabcc7cbf80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TYPE notificationtype ADD VALUE 'message_received'")

def downgrade():
    pass