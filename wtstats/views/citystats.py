from pyramid.view import (
	view_config,
	view_defaults,
)

from pyramid.httpexceptions import HTTPNotFound, HTTPClientError
from wtstats.models import DBSession, City, Tip, Measurement, ValueType, TipValue, Player
from sqlalchemy import func, or_
from scipy.stats import gaussian_kde
from pyramid_dogpile_cache import get_region

import datetime
import json
import numpy as np
import pandas as pd


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

def get_weekend(date):
	if (date.weekday() < 4):
		date_weekend = get_friday_before(date)
	else:
		date_weekend = date - datetime.timedelta(days=date.weekday() - 4)
		
	return date_weekend, date_weekend + datetime.timedelta(days=1), date_weekend + datetime.timedelta(days=2) 
	
@view_defaults(renderer='templates/base.jinja2', permission='view')
class CityStatsView:
	def __init__(self, request):
		self.request = request
		
		
	def _city_from_matchdict(self):
		city = DBSession.query(City).filter_by(name=self.request.matchdict.get('city')).first()
		if not city:
			raise HTTPNotFound('City not found')
		
		return city

	@view_config(route_name='citystat_plots', renderer="templates/citystats/citystats_plots.jinja2")
	def citystat_plots(self):
		date = parse_datestr(self.request.matchdict.get('date', 'current'))
		city = self._city_from_matchdict()
		stat = DBSession.query(ValueType).filter_by(name = self.request.matchdict.get('stat', 'TTm')).first()
		
		cache_key = 'citystat_plots-{}.{}.{}'.format(city.name, date, stat)
		cache = get_region('views')
		cached_value = cache.get(cache_key, expiration_time=(datetime.datetime.utcnow() - city.last_fetch).total_seconds())
		if cached_value:
			return cached_value
		
		
		stats = DBSession.query(ValueType).all()

		
		if not stat:
			raise HTTPNotFound('Unknown stat') 
		
		date_weekend, date_saturday, date_sunday = get_weekend(date)		
		if date == date_weekend:
			date = date_saturday

		tips = DBSession.query(Player.name, TipValue.value)\
		                       .join(Tip, TipValue.tip)\
		                       .join(City, Tip.city)\
		                       .filter(City.id == city.id, TipValue.valuetype_id == stat.id, Tip.date == date)\
		                       .join(Player, Tip.player)\
		                       .order_by(func.lower(Player.name))\
		                       .all()

		if len(tips) == 0:
			raise HTTPNotFound('No tips for given date')

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

		
		offset = (y_max - y_min) * 0.1
		kde_pos = []
		kde_values = []
		try:
			kde_func = gaussian_kde(tip_values)
			kde_pos = np.arange(y_min-offset, y_max+offset, (y_max - y_min + 2*offset)/100.0)
			kde_values = kde_func(kde_pos)
		except:
			pass

		result = {
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
		
		cache.set(cache_key, result)
		return result
		
	
	@view_config(route_name='citystat_overview', renderer='templates/citystats/citystats.jinja2')
	def citystats_overview(self):
		date = parse_datestr(self.request.matchdict.get('date', 'current'))
		city = self._city_from_matchdict()
		friday, saturday, sunday = get_weekend(date)
		
		cache_key = 'citystats_overview-{}.{}'.format(city.name, date)
		cache = get_region('views')
		cached_value = cache.get(cache_key, expiration_time=(datetime.datetime.utcnow() - city.last_fetch).total_seconds())
		if cached_value:
			return cached_value
		
		stats = DBSession.query(ValueType).all()
		sq_tips = DBSession.query(Player.name, Tip.date, ValueType.name, TipValue.value, TipValue.diff, TipValue.points)\
		                   .join(Tip, TipValue.tip)\
		                   .join(Player, Tip.player)\
		                   .join(ValueType, TipValue.valuetype)\
		                   .filter(Tip.city_id == city.id, or_(Tip.date == saturday, Tip.date == sunday))\
		                   .all()
	
		players, dates, types, values, diffs, points = zip(*sq_tips)
		tips = pd.DataFrame({
			'player': players,
			'date': dates,
			'type': types,
			'value': values,
			'difference': diffs,
			'points': points,
		})
		
		leaders = []
		for date in [saturday, sunday]:
			tips_date = tips[tips.date == date]
			date_stats = []
			date_leaders = {}
			for stat in stats:
				t = tips_date[tips_date.type == stat.name]
				max_points = t.points.max()
				idx_max = np.where(t.points == max_points)[0]
				
				if len(idx_max) == 0:
					print(date, stat.name, len(idx_max))
					continue
				
				stat_leaders = t.iloc[idx_max]
				stat_leaders_players = []
				for w in stat_leaders.iterrows():
					w = w[1]
					stat_leaders_players.append({
						'name': w.player,
					})
				
				data_stat_leaders = {
					'type': stat,
					'points': stat_leaders.iloc[0].points,
					'avg_points': t.points.mean(),
					'avg_diff': t.difference.mean(),
					'players': stat_leaders_players,
					'diff': stat_leaders.iloc[0].difference,
				}
				
				date_stats.append(data_stat_leaders)
			
			date_leaders = {
				'date': date,
				'stats': date_stats,
			}
			leaders.append(date_leaders)
			
			
		measurements = DBSession.query(Measurement.date, Measurement.station_name, ValueType.name, TipValue.value)\
		                        .join(Measurement, TipValue.measurement)\
		                        .join(ValueType, TipValue.valuetype)\
		                        .filter(Measurement.city_id == city.id, or_(Measurement.date == saturday, Measurement.date == sunday), TipValue.value != None)\
		                        .all()

		measured_dict = {}
		if len(measurements):
			measurements_dates, measurements_stations, measurements_valuetypes, measurements_values = zip(*measurements)
			measurements = pd.DataFrame({
				'date': measurements_dates,
				'station': measurements_stations,
				'stat': measurements_valuetypes,
				'value': measurements_values,
			})
			
			stats = DBSession.query(ValueType).all()
			measured_dict = {}
			for stat in stats:
				m = measurements[measurements.stat == stat.name]
				values_sat = m[m.date == saturday]
				values_sun = m[m.date == sunday]
				
				measured_dict[stat.name] = {
					saturday: list(values_sat.value),
					sunday: list(values_sun.value)
				}
		
		tips_sums = tips.groupby(['player']).sum()	
		tips_days_sums = tips.groupby(['player', 'date']).sum()
		top_player_saturday = tips_days_sums.xs(saturday, level='date').points.idxmax()
		top_player_sunday = tips_days_sums.xs(sunday, level='date').points.idxmax()
		top_player_weekend = tips_sums.points.idxmax()
		
		top_players = {
			'saturday': {
				'player': top_player_saturday,
				'points': tips_days_sums.loc[top_player_saturday, saturday].points,
			},
			'sunday': {
				'player': top_player_sunday,
				'points': tips_days_sums.loc[top_player_sunday, sunday].points,
			},
			'weekend': {
				'player': top_player_weekend,
				'points': tips_sums.loc[top_player_weekend].points,
			}
		} 
		
		result = {
			'stats': stats,
			'measurements': measured_dict,
			'city': city,
			'date_friday': friday,
			'date_saturday': saturday,
			'date_sunday': sunday,
			'leaders_per_stat': leaders,
			'top_players': top_players,
		}
		
		cache.set(cache_key, result)
		
		return result