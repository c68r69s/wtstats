from pyramid.view import (
	view_config,
	view_defaults,
)

import math

from pyramid.httpexceptions import HTTPNotFound
from sqlalchemy import func
from wtstats.models import DBSession, Player, City, Tip, ValueType, Measurement
from wtstats.models.tipvalue import TipValue

import pandas as pd

@view_defaults(permission='view')
class PlayerStats:
	def __init__ (self, request):
		self.request = request
		
	@view_config(route_name='playerstats_list', renderer='templates/playerstats/list.jinja2')
	def list(self):
		page = int(self.request.params.get('page', 0))
		entries_per_page = 10
		players = DBSession.query(Player).order_by(func.lower(Player.name))
		players = players.offset(page * entries_per_page).limit(entries_per_page)
		players_count = DBSession.query(Player).count()
		
		def tips_for_city(player, city):
			return DBSession.query(Tip).filter(Tip.player_id == player.id, Tip.city_id == city.id).count()
		
		return {
			'page_current': page,
			'players_totoal': players_count,
			'players': players,
			'pages_total': math.ceil(players_count / entries_per_page),
			'cities': DBSession.query(City).order_by(City.name).all(),
			'tips_for_city': tips_for_city,
		}


	@view_config(route_name='playerstats', renderer='templates/playerstats/player.jinja2')
	def player(self):
		name = self.request.matchdict.get('name')
		player = DBSession.query(Player).filter(Player.name == name).first()
		
		if not player:
			raise HTTPNotFound('Player {} not found'.format(name))
		
		cities = DBSession.query(City).all()
		stat_types = DBSession.query(ValueType).all()
		tips_total= len(player.tips)
		
		avg_points_per_stat_all = {}
		avg_points_per_stat_player = {}
		
		for city in cities:
			city_stat_all = {}
			city_stat_player = {}
			
			player_tips = DBSession.query(Tip.date, ValueType.name, TipValue.value, TipValue.points, TipValue.diff)\
			                       .join(ValueType, TipValue.valuetype)\
			                       .join(Tip, TipValue.tip)\
			                       .join(City, Tip.city)\
			                       .join(Player, Tip.player)\
			                       .filter(Player.id == player.id, City.id == city.id).all()

			if len(player_tips) == 0:
				continue
			
			measurements = DBSession.query(Measurement.date, ValueType.name, func.avg(TipValue.value))\
			                        .join(ValueType, TipValue.valuetype)\
			                        .join(Measurement, TipValue.measurement)\
			                        .join(City, Measurement.city)\
			                        .group_by(Measurement.date, ValueType.id)\
			                        .filter(City.id == city.id).all()

			all_tips = DBSession.query(Tip.date, ValueType.name, func.avg(TipValue.value), func.avg(TipValue.points), func.avg(TipValue.diff))\
			                       .join(ValueType, TipValue.valuetype)\
			                       .join(Tip, TipValue.tip)\
			                       .join(City, Tip.city)\
			                       .group_by(Tip.date, ValueType.id)\
			                       .filter(City.id == city.id).all()

			measurements_dates, measurements_types, measurements_values = zip(*measurements)
			md = pd.DataFrame({
				'date': measurements_dates,
				'type': measurements_types,
				'value_measured': measurements_values
			})
			
			all_dates, all_types, all_values, all_points, all_diff = zip(*all_tips)
			ad = pd.DataFrame({
				'date': all_dates,
				'type': all_types,
				'all_value': all_values,
				'all_points': all_points,
				'all_diff': all_diff,
			})
			
			player_dates, player_types, player_values, player_points, player_diff = zip(*player_tips)
			pld = pd.DataFrame({
				'date': player_dates,
				'type': player_types,
				'player_value': player_values,
				'player_points': player_points,
				'player_diff': player_diff,
			})
			
			data = pd.merge(md, pld, on=['date', 'type'])
			data = pd.merge(data, ad, on=['date', 'type'])
			
			for stat in stat_types:
				stat_data = data[data.type == stat.name]
				data_player = {
					'points_avg': stat_data.player_points.mean(),
					'diff_avg': stat_data.player_diff.mean(),
				}
				
				data_all = {
					'points_avg': stat_data.all_points.mean(),
					'diff_avg': stat_data.all_diff.mean(),
				}
				
				city_stat_player[stat.name] = data_player
				city_stat_all[stat.name] = data_all

			
			avg_points_per_stat_all[city.name] = city_stat_all
			avg_points_per_stat_player[city.name] = city_stat_player
		
	
		return {
			'player': player,
			'tips_total': tips_total,
			'stat_types': stat_types,
			'avg_points_per_stat_all': avg_points_per_stat_all,
			'avg_points_per_stat_player': avg_points_per_stat_player, 
		}