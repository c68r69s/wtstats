from sqlalchemy import (
	Column,
	Integer,
	Text,
)

from .meta import Base

class ValueType(Base):
	__tablename__ = 'valuetypes'

	id = Column(Integer, primary_key=True)
	name = Column(Text)
	unit  = Column(Text)
	longname = Column(Text)

	def __init__(self, name, longname, unit):
		self.name = name
		self.unit = unit
		self.longname = longname