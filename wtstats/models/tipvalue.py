from sqlalchemy import (
	Column,
	Integer,
	Float,
	ForeignKey,
)

from sqlalchemy.orm import relationship
from .meta import Base

class TipValue(Base):
	__tablename__ = 'tipvalues'

	id = Column(Integer, primary_key=True)
	tip_id = Column(Integer, ForeignKey('tips.id'), nullable=True)
	measurement_id = Column(Integer, ForeignKey('measurements.id'), nullable=True)
	valuetype_id = Column(Integer, ForeignKey('valuetypes.id'))
	value = Column(Float, nullable=True)
	
	points = Column(Float)
	diff = Column(Float)
		
	valuetype = relationship('ValueType')
	tip = relationship('Tip', backref='values')
	measurement = relationship('Measurement', backref='values')

	def __init__(self, valuetype, value, tip = None, measurement = None):
		self.valuetype = valuetype
		self.value = value

		if tip and measurement:
			raise ValueError('Either tip or measurement required')
		elif tip:
			tip = tip
		elif measurement:
			measurement = measurement
		else:
			raise ValueError('Either tip or measurement required')