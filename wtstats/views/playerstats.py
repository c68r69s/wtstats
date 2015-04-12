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
		
		player_ids = [p.id for p in players]
		data = DBSession.query(Player.id, City.id, func.count(City.name))\
		                             .join(Player, Tip.player)\
		                             .filter(Player.id.in_(player_ids))\
		                             .join(City, Tip.city)\
		                             .group_by(Player.id, City.name)\
		                             .order_by(func.lower(Player.name))\
		                             .all()

		player_data = {}
		for d in data:
			player_id = d[0]
			city_id = d[1]
			tip_count = d[2]
			
			tips = player_data.get(player_id, {})
			tips[city_id] = tip_count
			
			player_data[player_id] = tips
			
		
		return {
			'page_current': page,
			'players_totoal': players_count,
			'players': players,
			'player_data': player_data,
			'pages_total': math.ceil(players_count / entries_per_page),
			'cities': DBSession.query(City).order_by(City.name).all(),
		}


	def compare_to(self, player1, player2 = None):
		cities = DBSession.query(City).all()
		stat_types = DBSession.query(ValueType).all()
		
		avg_points_per_stat_p2 = {}
		avg_points_per_stat_p1 = {}
		
		for city in cities:
			city_stat_p2 = {}
			city_stat_p1 = {}
			
			player1_tips = DBSession.query(Tip.date, ValueType.name, TipValue.value, TipValue.points, TipValue.diff)\
			                       .join(ValueType, TipValue.valuetype)\
			                       .join(Tip, TipValue.tip)\
			                       .join(City, Tip.city)\
			                       .join(Player, Tip.player)\
			                       .filter(Player.id == player1.id, City.id == city.id).all()

			if len(player1_tips) == 0:
				continue
			
			measurements = DBSession.query(Measurement.date, ValueType.name, func.avg(TipValue.value))\
			                        .join(ValueType, TipValue.valuetype)\
			                        .join(Measurement, TipValue.measurement)\
			                        .join(City, Measurement.city)\
			                        .group_by(Measurement.date, ValueType.id)\
			                        .filter(City.id == city.id).all()

			player2_tips = DBSession.query(Tip.date, ValueType.name, func.avg(TipValue.value), func.avg(TipValue.points), func.avg(TipValue.diff))\
			                       .join(ValueType, TipValue.valuetype)\
			                       .join(Tip, TipValue.tip)\
			                       .join(City, Tip.city)\
			                       .group_by(Tip.date, ValueType.id)\
			                       .filter(City.id == city.id)

			if player2 != None:
				player2_tips = player2_tips.join(Player, Tip.player).filter(Player.id == player2.id)
				
			player2_tips = player2_tips.all()
			if len(player2_tips) == 0:
				continue

			measurements_dates, measurements_types, measurements_values = zip(*measurements)
			md = pd.DataFrame({
				'date': measurements_dates,
				'type': measurements_types,
				'value_measured': measurements_values
			})
			
			p2_dates, p2_types, p2_values, p2_points, p2_diff = zip(*player2_tips)
			p2d = pd.DataFrame({
				'date': p2_dates,
				'type': p2_types,
				'all_value': p2_values,
				'all_points': p2_points,
				'all_diff': p2_diff,
			})
			
			p1_dates, p1_types, p1_values, p1_points, p1_diff = zip(*player1_tips)
			p1d = pd.DataFrame({
				'date': p1_dates,
				'type': p1_types,
				'player_value': p1_values,
				'player_points': p1_points,
				'player_diff': p1_diff,
			})
			
			data = pd.merge(md, p1d, on=['date', 'type'])
			data = pd.merge(data, p2d, on=['date', 'type'])
			
			for stat in stat_types:
				stat_data = data[data.type == stat.name]
				data_p1 = {
					'points_avg': stat_data.player_points.mean(),
					'diff_avg': stat_data.player_diff.mean(),
				}
				
				data_p2 = {
					'points_avg': stat_data.all_points.mean(),
					'diff_avg': stat_data.all_diff.mean(),
				}
				
				city_stat_p1[stat.name] = data_p1
				city_stat_p2[stat.name] = data_p2

			
			city_stat_p1['tip_count'] = int(len(player1_tips) / len(stat_types))
			city_stat_p2['tip_count'] = int(len(player2_tips) / len(stat_types))
			avg_points_per_stat_p2[city.name] = city_stat_p2
			avg_points_per_stat_p1[city.name] = city_stat_p1
		
	
		return {
			'player1': player1,
			'player2': player2,
			'stat_types': stat_types,
			'avg_points_per_stat_p2': avg_points_per_stat_p2,
			'avg_points_per_stat_p1': avg_points_per_stat_p1, 
		}


	@view_config(route_name='playerstats', renderer='templates/playerstats/player.jinja2')
	def player(self):
		name1 = self.request.matchdict.get('name')
		name2 = self.request.params.get('compare_to', None)
		
		p1 = DBSession.query(Player).filter(Player.name == name1).first()
		p2 = None
		if name2 != None and name2 != '':
			p2 = DBSession.query(Player).filter(Player.name == name2).first()
			if not p2:
				self.request.session.flash('Spieler für den Vergleich nicht gefunden', 'errors')
		
		if not p1:
			raise HTTPNotFound('Player not found')
			
		return self.compare_to(p1, p2)
	
		
	@view_config(route_name='player_get_names', renderer='json')
	def get_player_names(self):
		name = self.request.params.get('name', '')
		if len(name) < 2:
			return {}
		
		players = list(zip(*DBSession.query(Player.name).filter(Player.name.like('%{}%'.format(name))).limit(20).all()))
		if len(players):
			players = players[0]
			players = [{'name': p} for p in players]
		
		return {
			'players': players
		}
	
