from pyramid.paster import bootstrap
from wtstats.statfetcher import Fetcher
from wtstats.models import DBSession, City

import transaction

env = bootstrap('development.ini')
cities = DBSession.query(City).all()

fetcher = Fetcher()
for city in cities:
	print('Fetching {}'.format(city.name))
	fetcher.fetch_data(city)

transaction.commit()
env['closer']()