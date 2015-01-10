from sqlalchemy import (
	Column,
	Text,
	Integer,
	DateTime
)

from .meta import Base

class City(Base):
	__tablename__ = 'cities'

	id = Column(Integer, primary_key=True)
	name = Column(Text)
	fetch_url = Column(Text)
	last_fetch = Column(DateTime)

	def __init__(self, name, url):
		self.name = name
		self.fetch_url = url
