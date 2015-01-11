from dogpile.cache import make_region
import datetime

class PlotCache:
	def __init__(self):
		self._plot_region = make_region('plots')
		self._plot_region.configure(backend='file', arguments = { 'filename': 'cache/plots.cache' })
		
	def _make_key(self, city, date, stat, plot_type):
		return '{}.{}.{}.{}'.format(city.name, str(date), stat.name, plot_type)
	
	def get_plot(self, city, date, stat, plot_type):
		key = self._make_key(city, date, stat, plot_type)
		now = datetime.datetime.utcnow()
		diff = now - city.last_fetch
		plot = self._plot_region.get(key, expiration_time=diff.total_seconds())
		if not plot:
			return plot
		
		return plot
		
	def set_plot(self, city, date, stat, plot_type, plot):
		key = self._make_key(city, date, stat, plot_type)
		self._plot_region.set(key, plot)
