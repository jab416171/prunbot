import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging
from models import Base

handler = logging.FileHandler("sql.log")
logging.getLogger("sqlalchemy.engine").addHandler(handler)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.pool").addHandler(handler)
logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)


class DB():
    __engine = None
    lock = asyncio.Lock()
    dbname = os.environ['SQL_DB']

    async def create_engine(self):
        """ create a database connection to a sqlite database """
        engine = create_async_engine(f"sqlite+aiosqlite:///{self.dbname}", logging_name='sqlite', future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return engine

    async def getSession(self):
        engine = await self.getEngine()
        async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        return async_session

    async def getEngine(self):
        async with self.lock:
            if not self.__engine:
                self.__engine = await self.create_engine()
            return self.__engine
