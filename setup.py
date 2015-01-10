from setuptools import setup

requires = [
	'pyramid',
	'pyramid_jinja2',
	'sqlalchemy',
	'pyramid_tm',
	'zope.sqlalchemy',
	'pyramid_debugtoolbar',
	'pandas',
	'seaborn',
]

setup(
	name = 'wtstats',
	install_requires=requires,
	entry_points="""\
      [paste.app_factory]
      main = wtstats:main
      [console_scripts]
      initialize_wtstats_db= wtstats.initialize_db:main
      """,
)
