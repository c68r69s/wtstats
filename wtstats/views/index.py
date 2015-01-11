from pyramid.view import (
	view_config,
	view_defaults,
)

from wtstats.models import DBSession, City


@view_defaults(renderer='templates/index.jinja2', permission='view')
class IndexView:
	def __init__(self, request):
		self.request = request
	
	@view_config(route_name='home')
	def index(self):
		cities = DBSession.query(City).order_by(City.name).all()
		return {
			'cities': cities
		}
