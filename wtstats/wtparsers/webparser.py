import urllib.request
import re
import datetime

match_listings = re.compile(r'<pre class="listing">(.*)</pre>', re.DOTALL)
match_header = re.compile(r'Prognose ([0-9.]*), Spieler ([\w()/.+-]*):')
match_station_names = re.compile(r'Wert *Vorhers\. *([\w./-]*) *([\w/.-]*) *Abweich *Punkte')

def parse_day(data, stat1, stat2):
	tip = {}
	measured = {
		stat1: {},
		stat2: {},
	}

	def conv_float(x):
		try:
			return float(x)
		except:
			return None

	for line in data.split('\n'):
		parts = [x for x in line.split(' ') if x]
		t =  parts[0]
		tip_element = {
			'value':  conv_float(parts[1]),
			'diff': conv_float(parts[-2]),
			'points': conv_float(parts[-1]), 
		}
		
		measured[stat1][t] = conv_float(parts[2])
		measured[stat2][t] = conv_float(parts[3]) 
		tip[t] = tip_element

	return measured, tip

def find_station_names(data):
	matches = match_station_names.search(data)
	return matches.group(1), matches.group(2)

def fetch_data(url):
	res = urllib.request.urlopen(url)
	data = res.readall().decode('latin-1')
	
	stat1, stat2 = find_station_names(data)
	
	matches = match_listings.search(data)
	data = matches.group(1).strip()
	data = data.split('Auswertung')

	measured_sat = None
	measured_sun = None
	date = None
	tips_sat = {}
	tips_sun = {}
	for tip in data:
		tip = tip.strip()
		if (len(tip) == 0):
			continue

		header = match_header.search(tip)
		date = datetime.datetime.strptime(header.group(1), '%d.%m.%Y').date()
		player = header.group(2)

		days_data = tip.split('Sonntag:')
		saturday = days_data[0].split('Samstag:')[1].strip()
		sunday = days_data[1].split('Punktzahl')[0].strip()

		measured_sat, tips_sat[player] = parse_day(saturday, stat1, stat2)
		measured_sun, tips_sun[player] = parse_day(sunday, stat1, stat2)
		

	return { 
		'Date': date,
		'Measured': {
			'Saturday': measured_sat,
			'Sunday': measured_sun,
		},
		'Tips': {
			'Saturday': tips_sat, 
			'Sunday': tips_sun
		} 
	}
	
