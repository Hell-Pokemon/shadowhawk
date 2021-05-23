import os
import sys
import logging
import datetime
from sqlalchemy import Column, ForeignKey, BigInteger, String, UnicodeText, DateTime
from sqlalchemy import ext
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import relationship, sessionmaker, scoped_session, backref
from sqlalchemy.future import select
from shadowhawk import ObjectProxy as SessionProxy
from shadowhawk import config, ee

Base = declarative_base()

session = SessionProxy()
session_factory = SessionProxy()

from .pmpermit import AuthorizedUsers

#########
# Models
#
class StickerSet(Base):
	__tablename__ = 'StickerSet'
	id = Column(BigInteger, primary_key=True)
	sticker = Column(UnicodeText)

	def __init__(self, id, sticker):
		self.id = id
		self.sticker = str(sticker)

	def __repr__(self):
		return f"<Sticker {self.id}>"

class AnimatedStickerSet(Base):
	__tablename__ = 'AnimatedStickerSet'
	id = Column(BigInteger, primary_key=True)
	sticker = Column(UnicodeText)

	def __init__(self, id, sticker):
		self.id = id
		self.sticker = str(sticker)

	def __repr__(self):
		return f"<Sticker {self.id}>"

class AutoScroll(Base):
	__tablename__ = 'AutoScroll'
	id = Column(BigInteger, primary_key=True)

	def __init__(self, id):
		self.id = id

	def __repr__(self):
		return f"<AutoScroll {self.id}>"

class AutoBanSpammers(Base):
	__tablename__ = 'AutoBanSpammers'
	id = Column(BigInteger, primary_key=True)

	def __init__(self, id):
		self.id = id

	def __repr__(self):
		return f"<AutoBanSpammers {self.id}>"

# we're british I guess
async def innit():
	# Initialize SQL
	sqlengine = create_async_engine(config['sql']['uri'], pool_size=config['sql']['poolsize'], echo=config['sql']['debug'])
	Base.metadata.bind = sqlengine

	# Create the tables if they don't already exist
	try:
		async with sqlengine.begin() as conn:
			await conn.run_sync(Base.metadata.create_all)
			await conn.commit()
	except ext.OperationalError:
		return False

	# TODO: find a way to get scoped_session to work?
	session_maker = sessionmaker(sqlengine, autoflush=False, future=True, class_=AsyncSession)
	session_factory.set_thing(session_maker)
	sesh = session_maker()
	session.set_thing(sesh)
	ee.emit('OnDatabaseStart')
	return True

async def get_sticker_set(user_id):
	global session
	try:
		return (await session.execute(select(StickerSet).where(StickerSet.id == user_id))).scalars().one_or_none()
	except:
		logging.exception("Exception in get_sticker_set")
		await session.rollback()
		return None

async def get_animated_set(user_id):
	global session
	try:
		return (await session.execute(select(AnimatedStickerSet).where(AnimatedStickerSet.id == user_id))).scalars().one_or_none()
	except:
		logging.exception("Exception in get_animated_set")
		await session.rollback()
		return None

