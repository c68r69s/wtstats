from pyramid.view import (
	view_config,
	view_defaults,
)

from pyramid.httpexceptions import HTTPNotFound, HTTPClientError
from pyramid.response import Response
from wtstats.models import DBSession, City, Tip, Measurement, ValueType, TipValue, Player
from sqlalchemy import func

import matplotlib.pyplot as plt
import datetime
import pandas as pd
import io
import numpy as np
import seaborn as sns
import pyramid_dogpile_cache as dp



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
		
		if (date.weekday() < 4):
			date_weekend = get_friday_before(date)
		else:
			date_weekend = date - datetime.timedelta(days=date.weekday() - 4)
		
		date_saturday = date_weekend + datetime.timedelta(days=1)
		date_sunday = date_weekend + datetime.timedelta(days=2)
		
		if date == date_weekend:
			date = date_saturday
		
		return {
			'city': city,
			'stats': stats,
			'stat': stat,
			'date': date,
			'date_weekend': date_weekend,
			'date_saturday': date_saturday,
			'date_sunday': date_sunday,
		}
	
	
	def plot_for_stat(self, plottype):
		city_name = self.request.matchdict['city']
		date_str = self.request.matchdict['date']
		stat_name = self.request.matchdict['stat']
	
		city = DBSession.query(City).filter_by(name=city_name).first()
		if not city:
			raise HTTPNotFound('Unknown city')
		
		cache = dp.get_region('plots')
		key = '{}.{}.{}.{}'.format(city_name, date_str, stat_name, plottype)
		buf = cache.get(key, expiration_time=(datetime.datetime.utcnow() - city.last_fetch).total_seconds()) 
		if buf:
			return Response(
				body_file = buf,
				request = self.request,
				content_type = 'image/png',
			)
			
			
		stat = DBSession.query(ValueType).filter_by(name=stat_name).first()
		date = parse_datestr(date_str)
		
		if not stat:
			raise HTTPNotFound('Unknown stat')
		
		
		measurements = DBSession.query(Measurement).filter_by(city=city, date=date).all()
		tips = DBSession.query(Tip).filter_by(city=city, date=date).all()
		
		if len(tips) == 0:
			raise HTTPNotFound('No data for given date')
		
		tip_ids = [x.id for x in tips]
		players, values = zip(*DBSession.query(Player, TipValue).join(Tip, TipValue.tip).join(Player, Tip.player).filter(TipValue.valuetype == stat, Tip.id.in_(tip_ids)).order_by(func.lower(Player.name)).all())
		values = np.array([x.value for x in values])
		players =  [x.name for x in players]
		
		fig = plt.figure(frameon = False)
		try:
			ax = fig.add_subplot(111)
	
			frame = pd.DataFrame(values, index=players, columns=['Tips'])
			frame.plot(kind=plottype, ax=ax, legend=False)
			
			pal = sns.color_palette("bright", len(measurements))
			minimum = min(values)
			maximum = max(values)
			for measured in measurements:
				station_name = measured.station_name
				value = DBSession.query(TipValue).join(Measurement, TipValue.measurement).filter(TipValue.valuetype==stat, 
																								TipValue.measurement_id == measured.id).first().value
				col = pal.pop()
				if value == None:
					continue
				
				minimum = min(minimum, value)
				maximum = max(maximum, value)
				if (plottype == 'kde'):
					ax.axvline(value, label=station_name, color=col, linestyle='dashed')
				else:
					ax.axhline(value, label=station_name, color=col, linestyle='dashed')
	
			if (plottype != 'kde'):
				ax.set_ylabel(stat.unit)
				offset = (maximum - minimum)*0.05
				ax.set_ylim(minimum-offset, maximum+offset)
			else:
				ax.set_xlabel(stat.unit)
				
			ax.legend(loc='best')
			ax.set_title('{} ({}, {}-plot)'.format(stat.longname, stat.name, plottype))
			ax.yaxis.get_major_formatter().set_useOffset(0)
			
			fig.tight_layout()
			fig.set_size_inches((10, 6 if plottype == 'kde' else 8))
			
			buf = io.BytesIO()
			fig.savefig(buf, format='png')
			buf.seek(0)
			cache.set(key, buf)
		finally:
			plt.close(fig)
		
		return Response(
			body_file = buf,
			request = self.request,
			content_type = 'image/png',
		)
		
	@view_config(route_name='citystat_plot_density')
	def densityplot_for_stat(self):
		return self.plot_for_stat('kde')
		
	@view_config(route_name='citystat_plot_bar')
	def barplot_for_stat(self):
		return self.plot_for_stat('bar')
