from pyramid.view import (
	view_config,
	view_defaults,
)


@view_defaults(renderer='templates/base.jinja2', permission='view')
class IndexView:
	def __init__(self, request):
		self.request = request
	
	@view_config(route_name='home')
	def index(self):
		return {}
