"""add offers table

Revision ID: 000000000010
Revises:
Create Date: 2025-04-25 17:14:43.240492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '000000000010'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'offers',
        sa.Column('id', sa.BigInteger, nullable=False),
        sa.Column('guild_id', sa.BigInteger, nullable=False),
        sa.Column('item_ticker', sa.String(255), nullable=False),
        sa.Column('item_price', sa.Float, nullable=False),
        sa.Column('item_location', sa.String(255), nullable=False),
        sa.Column('item_reserve_percent', sa.Float, nullable=False),
        sa.Column('item_reserve', sa.Integer, nullable=False),
        sa.Column('display_if_zero', sa.Boolean, nullable=False, server_default="1"),
        sa.Column('item_notes', sa.String(255), nullable=True),
        sa.Column('item_created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('item_updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'guild_id', 'item_ticker', 'item_location'),
        sa.UniqueConstraint('id', 'guild_id', 'item_ticker', 'item_location', name='uq_offers_id_guild_id_item_ticker_item_location'),

    )
    op.create_table(
        'inventory',
        sa.Column('id', sa.Integer, autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger, nullable=False),
        sa.Column('item_ticker', sa.String(255), nullable=False),
        sa.Column('item_location', sa.String(255), nullable=False),
        sa.Column('item_quantity', sa.Integer, nullable=False),
        sa.Column('item_age', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'item_ticker', 'item_location', name='uq_inventory_user_id_item_ticker_item_location'),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger, nullable=False),
        sa.Column('prun_user', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', name='uq_users_id'),
        sa.UniqueConstraint('prun_user', name='uq_users_prun_user'),
    )
    # op.create_index("users_idx", 'users', ['id', 'guild_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('offers')
    op.drop_table('inventory')
    op.drop_table('users')
