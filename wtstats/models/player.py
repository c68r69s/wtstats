from sqlalchemy import (
	Column,
	Text,
	Integer,
)

from .meta import Base

class Player(Base):
	__tablename__ = 'players'

	id = Column(Integer, primary_key=True)
	name = Column(Text)

	def __init__(self, name):
		self.name = name

