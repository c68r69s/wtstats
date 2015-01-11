import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
	get_appsettings,
	setup_logging,
)

from .models.meta import Base
from .models import *

def usage(argv):
	cmd = os.path.basename(argv[0])
	print('usage: %s <config_uri>\n'
		'(example: "%s development.ini")' % (cmd, cmd))
	sys.exit(1)


def main(argv=sys.argv):
	if len(argv) != 2:
		usage(argv)

	config_uri = argv[1]
	setup_logging(config_uri)
	settings = get_appsettings(config_uri)
	engine = engine_from_config(settings, 'sqlalchemy.')
	DBSession.configure(bind=engine)

	Base.metadata.create_all(engine)
	
	with transaction.manager:
		DBSession.add(City('Innsbruck', 'http://prognose.met.fu-berlin.de/wertungen/einzelwert_i.php'))
		DBSession.add(City('Wien', 'http://prognose.met.fu-berlin.de/wertungen/einzelwert_w.php'))
		DBSession.add(City('Berlin', 'http://prognose.met.fu-berlin.de/wertungen/einzelwert_b.php'))
		DBSession.add(City('Zürich', 'http://prognose.met.fu-berlin.de/wertungen/einzelwert_z.php'))
		DBSession.add(City('Leipzig', 'http://prognose.met.fu-berlin.de/wertungen/einzelwert_l.php'))
		
		DBSession.add(ValueType('N', 'Bedeckungsgrad', '1/8'))
		DBSession.add(ValueType('Sd','Sonnenscheindauer', '%'))
		DBSession.add(ValueType('dd','Windrichtung', 'deg'))
		DBSession.add(ValueType('ff', 'Windgeschwindigkeit', 'Knoten'))
		DBSession.add(ValueType('fx', 'Böen', 'Knoten'))
		DBSession.add(ValueType('Wv', 'Wetter Vormittag', ''))
		DBSession.add(ValueType('Wn', 'Wetter Nachmittag', ''))
		DBSession.add(ValueType('PPP', 'Druck', 'hPa'))
		DBSession.add(ValueType('TTm', 'Max. Temperatur', 'deg. C'))
		DBSession.add(ValueType('TTn', 'Min. Temperatur', 'deg. C'))
		DBSession.add(ValueType('TTd', 'Taupunkttemperatur', 'deg. C'))
		DBSession.add(ValueType('RR', 'Niederschlag', 'mm/h'))
		
		
