"""add storefront messages

Revision ID: 000000000020
Revises: 000000000010
Create Date: 2025-04-25 19:17:22.608236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '000000000020'
down_revision: Union[str, None] = '000000000010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'storefront_messages',
        sa.Column('id', sa.BigInteger, nullable=False),
        sa.Column('guild_id', sa.BigInteger, nullable=False),
        sa.Column('channel_id', sa.BigInteger, nullable=False),
        sa.Column('message_id', sa.BigInteger, nullable=False),
        sa.PrimaryKeyConstraint('id', 'guild_id'),
        sa.UniqueConstraint('id', 'guild_id', name='uq_storefront_messages_id_guild_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('storefront_messages')
