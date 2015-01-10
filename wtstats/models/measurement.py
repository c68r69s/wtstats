from sqlalchemy import (
	Column,
	Integer,
	Date,
	ForeignKey,
	Text,
)

from sqlalchemy.orm import relationship
from .meta import Base

class Measurement(Base):
	__tablename__ = 'measurements'

	id = Column(Integer, primary_key=True)
	city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
	date = Column(Date)
	station_name = Column(Text)
	
	city = relationship('City')

	def __init__(self, name, date, city):
		self.station_name = name
		self.city = city
		self.date = date