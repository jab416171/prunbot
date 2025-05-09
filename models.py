import sqlalchemy
from sqlalchemy import Column, BigInteger, DateTime, String, Enum, Integer, Index, Boolean, ForeignKey, Sequence, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
# from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Offer(Base):
    __tablename__ = 'offers'
    id = Column(BigInteger, primary_key=True, nullable=False)
    guild_id = Column(BigInteger, primary_key=True, nullable=False)
    item_ticker = Column(String(255), primary_key=True, nullable=False)
    item_price = Column(Integer, nullable=False)
    item_location = Column(String(255), primary_key=True, nullable=False)
    item_reserve_percent = Column(Integer, nullable=False)
    item_reserve = Column(Integer, nullable=False)
    display_if_zero = Column(Boolean, nullable=False, server_default="1")
    item_notes = Column(String(255), nullable=True)
    item_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    item_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        Index('uq_offers_id_guild_id_item_ticker_item_location', 'id', 'guild_id', 'item_ticker', 'item_location', unique=True),
    )

class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    item_ticker = Column(String(255), nullable=False)
    item_location = Column(String(255), nullable=False)
    item_quantity = Column(Integer, nullable=False)
    item_age = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        Index('uq_inventory_user_id_item_ticker_item_location', 'user_id', 'item_ticker', 'item_location', unique=True),
    )


class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True, nullable=False)
    prun_user = Column(String(255), primary_key=True, nullable=False)
    __table_args__ = (
        Index('uq_users_id', 'id', unique=True),
    )

class StorefrontMessages(Base):
    __tablename__ = 'storefront_messages'
    id = Column(BigInteger, primary_key=True, nullable=False)
    guild_id = Column(BigInteger, primary_key=True, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    __table_args__ = (
        Index('uq_storefront_messages_id_guild_id', 'id', 'guild_id', unique=True),
    )
