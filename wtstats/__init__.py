from pyramid.config import Configurator
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import unauthenticated_userid

from wtstats.models import DBSession, City
from wtstats.models.meta import Base

from sqlalchemy import engine_from_config

from pyramid.events import subscriber
from pyramid.events import BeforeRender

@subscriber(BeforeRender)
def add_global(event):
	event['cities'] = DBSession.query(City).all()

def main(global_config, **settings):
	engine = engine_from_config(settings, 'sqlalchemy.')
	DBSession.configure(bind=engine)
	Base.metadata.bind = engine
	
	session_factory = UnencryptedCookieSessionFactoryConfig('65fg4h56744sg6544()/')
	config = Configurator(
		settings=settings, 
		session_factory=session_factory,
	)
	config.include('pyramid_jinja2')
	config.include('pyramid_dogpile_cache')
	
	config.add_route('home', '/')
	config.add_route('citystat_plot_bar', '/stats/{date}/{city}/{stat}/bar')
	config.add_route('citystat_plot_density', '/stats/{date}/{city}/{stat}/density')
	config.add_route('citystat_plots', '/stats/{date}/{city}/{stat}')
	
	config.add_route('playerstats_list', '/players/list')
	config.add_route('playerstats', '/player/{name}')
	
	config.add_static_view(name='static', path='wtstats:static')
	config.scan()

	return config.make_wsgi_app()
