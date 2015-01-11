from sqlalchemy import (
	Column,
	Integer,
	Date,
	ForeignKey,
)

from sqlalchemy.orm import relationship
from .meta import Base



class Tip(Base):
	__tablename__ = 'tips'

	id = Column(Integer, primary_key=True)
	player_id = Column(Integer, ForeignKey('players.id'))
	city_id = Column(Integer, ForeignKey('cities.id'))
	date = Column(Date)

	player = relationship('Player', backref='tips')
	city = relationship('City', backref='tips')

	def __init__(self):
		pass