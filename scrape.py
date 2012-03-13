import scraperwiki

try:
	swutils = scraperwiki.utils
except AttributeError:
	import gasp_helper
else:
	swutils.swimport("gasp_helper")

API_KEY = '' # sunlight api key here
BIOGUIDE_ID = '' # bioguide id here

gasp = gasp_helper.GaspHelper(API_KEY, BIOGUIDE_ID)

