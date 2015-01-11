import datetime

from wtstats.models import DBSession, Tip, Player, Measurement, TipValue, ValueType
import wtstats.wtparsers as parsers

class Fetcher:
	def __init__(self):
		pass
	
	def fetch_data(self, city):
		if city.last_fetch and False:
			time_passed = datetime.datetime.utcnow() - city.last_fetch
			if time_passed.total_seconds() < 60*5:
				print('TIME NOT PASSED')
				return
			
		print('TIME PASSED, IMPORT')
		self._do_fetch(city)


	def _import_tips(self, city, date, data):
		for playername in data.keys():
			values = data[playername]
			player = DBSession.query(Player).filter_by(name = playername).first()
			if not player:
				player = Player(playername)
				DBSession.add(player)
				DBSession.flush()
			
			tip = DBSession.query(Tip).filter_by(player = player, city = city, date=date).first()
			if not tip:
				tip = Tip()
				tip.city = city
				tip.player = player
				tip.date = date
				DBSession.add(tip)
				DBSession.flush()
			
			tipvalues = {}
			for tv in tip.values:
				tipvalues[tv.valuetype.name] = tv
			
			valuetypes = DBSession.query(ValueType).all()
			for valuetype in valuetypes:
				value = values[valuetype.name]['value'] 
				diff = values[valuetype.name]['diff']
				points = values[valuetype.name]['points']
				tv = tipvalues.get(valuetype.name, None)
				if not tv:
					tv = TipValue(valuetype, value, tip=tip)
					tip.values.append(tv)
				else:
					tv.value = value
				
				tv.diff = diff
				tv.points = points
				DBSession.add(tv)
			
			DBSession.add(tip)
	
	
	def _import_measured(self, city, date, data):
		for station_name in data.keys():
			values = data[station_name]
			measurement = DBSession.query(Measurement).filter_by(city = city, date=date, station_name=station_name).first()
			if not measurement:
				measurement = Measurement(station_name, date, city)
			
			valuetypes = DBSession.query(ValueType).all()
			tipvalues = {}
			for tv in measurement.values:
				tipvalues[tv.valuetype.name] = tv
				
			valuetypes = DBSession.query(ValueType).all()
			for valuetype in valuetypes:
				value = values[valuetype.name]
				tv = tipvalues.get(valuetype.name, None)
				if not tv:
					tv = TipValue(valuetype, value, measurement=measurement)
					measurement.values.append(tv)
				else:
					tv.value = value
				
				DBSession.add(tv)
			
			DBSession.add(measurement)
	
	
	
	def _do_fetch(self, city):
		tips = parsers.webparser.fetch_data(city.fetch_url)
		date = tips['Date']
		self._import_measured(city, date + datetime.timedelta(days=1), tips['Measured']['Saturday'])
		self._import_measured(city, date + datetime.timedelta(days=2), tips['Measured']['Sunday'])
		self._import_tips(city, date + datetime.timedelta(days=1), tips['Tips']['Saturday'])
		self._import_tips(city, date + datetime.timedelta(days=2), tips['Tips']['Sunday'])
		city.last_fetch = datetime.datetime.utcnow()
		DBSession.add(city)
