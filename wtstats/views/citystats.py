from pyramid.view import (
	view_config,
	view_defaults,
)

from pyramid.httpexceptions import HTTPNotFound, HTTPClientError
from wtstats.models import DBSession, City, Tip, Measurement, ValueType, TipValue, Player
from sqlalchemy import func
from scipy.stats import gaussian_kde

import datetime
import json
import numpy as np


def get_friday_before(date):
	if date.weekday() >= 5:
		return date - datetime.timedelta(date.weekday()-5)
	return date -datetime.timedelta(days=date.weekday() + 3)

def parse_datestr(date_str):
	if (date_str == 'current'):
		tip = DBSession.query(Tip).order_by(Tip.date.desc()).first()
		if tip:
			return get_friday_before(tip.date)
		
		return get_friday_before(datetime.datetime.utcnow().date())
	else:
		try:
			return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
		except:
			raise HTTPClientError('Invalid date')


@view_defaults(renderer='templates/base.jinja2', permission='view')
class CityStatsView:
	def __init__(self, request):
		self.request = request
	
	@view_config(route_name='citystat_plots', renderer="templates/citystats/citystats_plots.jinja2")
	def citystat_plots(self):
		date = parse_datestr(self.request.matchdict.get('date', 'current'))
		city = DBSession.query(City).filter_by(name=self.request.matchdict.get('city')).first()
		stat = DBSession.query(ValueType).filter_by(name = self.request.matchdict.get('stat', 'TTm')).first()
		stats = DBSession.query(ValueType).all()
		
		if not city:
			raise HTTPNotFound('Unknown city')
		
		if not stat:
			raise HTTPNotFound('Unknown stat') 
		
		if (date.weekday() < 4):
			date_weekend = get_friday_before(date)
		else:
			date_weekend = date - datetime.timedelta(days=date.weekday() - 4)
		
		date_saturday = date_weekend + datetime.timedelta(days=1)
		date_sunday = date_weekend + datetime.timedelta(days=2)
		
		if date == date_weekend:
			date = date_saturday
		
		tips = DBSession.query(Player.name, TipValue.value)\
		                       .join(Tip, TipValue.tip)\
		                       .join(City, Tip.city)\
		                       .filter(City.id == city.id, TipValue.valuetype_id == stat.id, Tip.date == date)\
		                       .join(Player, Tip.player)\
		                       .order_by(func.lower(Player.name))\
		                       .all()

		measurements = DBSession.query(Measurement.station_name, TipValue.value)\
		                        .join(Measurement, TipValue.measurement)\
		                        .join(City, Measurement.city)\
		                        .filter(City.id == city.id, TipValue.valuetype_id == stat.id, Measurement.date == date, TipValue.value != None)\
		                        .all()

		_, tip_values = zip(*tips)
		
		y_min = min(tip_values)
		y_max = max(tip_values)
		if len(measurements):
			_, measurements_values = zip(*measurements)
			y_min = min(y_min, min(measurements_values))
			y_max = max(y_max, max(measurements_values))

		kde_func = gaussian_kde(tip_values)
		offset = (y_max - y_min) * 0.1
		kde_pos = np.arange(y_min-offset, y_max+offset, (y_max - y_min + 2*offset)/100.0)
		kde_values = kde_func(kde_pos)

		return {
			'city': city,
			'stats': stats,
			'stat': stat,
			'date': date,
			'date_weekend': date_weekend,
			'date_saturday': date_saturday,
			'date_sunday': date_sunday,
			'tips': tips,
			'measurements': measurements,
			'to_json': json.dumps,
			'y_min': y_min,
			'y_max': y_max,
			'kde_values': list(kde_values),
			'kde_pos': list(kde_pos),
			'kde_data': list(zip(kde_pos, kde_values)),
		}