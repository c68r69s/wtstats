from pyramid.view import (
	view_config,
	view_defaults,
)

import math
from sqlalchemy import func
from wtstats.models import DBSession, Player, City, Tip, ValueType
from wtstats.models.tipvalue import TipValue

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
		
		cities = DBSession.query(City).all()
		stat_types = DBSession.query(ValueType).all()
		tips_total= len(player.tips)
		
		avg_points_all = DBSession.query(func.avg(TipValue.points)).first()[0]
		avg_points_player = DBSession.query(func.avg(TipValue.points)).join(Tip, TipValue.tip).join(Player, Tip.player).filter(Player.id == player.id).first()[0]
		avg_points_per_stat_all = {}
		avg_points_per_stat_player = {}
		
		for city in cities:
			city_stat_all = {}
			city_stat_player = {}
			for stat in stat_types:
				player_stats = DBSession.query(func.avg(TipValue.points)).join(Tip, TipValue.tip).join(City, Tip.city).join(Player, Tip.player).filter(Player.id == player.id, TipValue.valuetype_id == stat.id, Tip.city_id == city.id).first()[0]
				if not player_stats:
					break
				
				city_stat_player[stat.name] = player_stats
				city_stat_all[stat.name] = DBSession.query(func.avg(TipValue.points)).join(Tip, TipValue.tip).join(City, Tip.city).filter(TipValue.valuetype_id == stat.id, Tip.city_id == city.id).first()[0]
				
			
			avg_points_per_stat_all[city.name] = city_stat_all
			avg_points_per_stat_player[city.name] = city_stat_player
		
	
		return {
			'player': player,
			'tips_total': tips_total,
			'stat_types': stat_types,
			'avg_points_player': avg_points_player,
			'avg_points_all': avg_points_all,
			'avg_points_per_stat_all': avg_points_per_stat_all,
			'avg_points_per_stat_player': avg_points_per_stat_player, 
		}