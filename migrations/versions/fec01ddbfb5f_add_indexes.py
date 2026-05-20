"""add indexes

Revision ID: fec01ddbfb5f
Revises: 95875a91bdfc
Create Date: 2026-05-19 19:25:09.880852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fec01ddbfb5f'
down_revision: Union[str, Sequence[str], None] = '95875a91bdfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_index("idx_audit_board_uid", "audits", ["board_uid"])
    op.create_index("idx_audit_user_uid", "audits", ["user_uid"])
    op.create_index("idx_boarduser_user_board", "boardusers", ["user_uid", "board_uid"])
    op.create_index("idx_notification_user_uid", "notifications", ["user_uid"])
    op.create_index("idx_unread_notifications", "notifications", ["user_uid"], postgresql_where="is_read = false")
    op.create_index("idx_invitation_recipient", "invitations", ["recipient_uid"])
    op.create_index("idx_request_board_uid", "requests", ["board_uid"])


def downgrade():
    op.drop_index("idx_audit_board_uid")
    op.drop_index("idx_audit_user_uid")
    op.drop_index("idx_boarduser_user_board")
    op.drop_index("idx_notification_user_uid")
    op.drop_index("idx_unread_notifications")
    op.drop_index("idx_invitation_recipient")
    op.drop_index("idx_request_board_uid")