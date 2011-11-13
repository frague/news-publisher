#!/usr/local/bin/python
# coding: windows-1251

from elementtree import ElementTree
import gdata.calendar.service
import gdata.service
import atom.service
import gdata.calendar
import atom
import getopt
import sys
import string
import time
import urllib2
import re
import datetime
from credentials import *

# Constants & precompiled values
debug = 0

months = [u"января", u"февраля", u"марта", u"апреля", u"мая", u"июня", u"июля", u"августа", u"сентября", u"октября", u"ноября", u"декабря"]
monthsEng = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
replaces = {"&minus;": "-", "&mdash;": "-", "&quot;": "\"", "&ndash;": "-"}
colnames = {u"Мероприятие": [u"Название мероприятия"], u"Открытие": [u"Время открытия", u"Начало"], u"Место проведения": [u"Место проведения>"]}

skipers = {"##>##": "[^>]*", "##<##": "[^<]*"}
chunk = re.compile("##([a-z_]*)(:([^#]+)){0,1}##")

deRegex = re.compile("[\[\]\{\}\(\)\|\$\^\+\*]")
deTag  = re.compile("</{0,1}[a-z]+[^>]*>")
clean = re.compile("[<>]")
deWhitespace = re.compile("\s+")
deSpace = re.compile("(\s+|&nbsp;)")
deQuotes = re.compile("&[lgr](aquo|t);")
newLines = re.compile("[\n\r]")
regexpReserved = re.compile("([\[\]\{\}\.\?\*\+\-])")

event_titles = {}
requested = False

#baseURL = "http://www.sport.saratov.gov.ru/news/events/"
#baseURL = "http://www.sport.saratov.gov.ru/news/sport/"
baseURL = "http://www.sport.saratov.gov.ru/news/"
baseURLs = ["http://www.sport.saratov.gov.ru/news/sport/", "http://www.sport.saratov.gov.ru/news/"]
#baseURL = "http://www.sport.saratov.gov.ru/"
linkedURL = "http://www.sport.saratov.gov.ru"

eventLength = datetime.timedelta(hours=4)
dayLength = datetime.timedelta(days=1)

titleTemplates = [
	"<a href=\"##url:\"##\">План ##shit:<## на ##title:<## года</a>",
	"<a href=\"##url:\"##\">##shit:<##ероприятия##shit:<##министерства##title:<##</a>",
	"<a href=\"##url:\"##\">План спортивных ##shit:<## на ##title:<## года</a>", 
	"<a href=\"##url:\"##\">ПЛАН мероприятий министерства по развитию спорта, физической культуры и туризма  Саратовской области</a>", 
	"<a href=\"##url:\"##\" title=\"##skip:\"##\">ПЛАН мероприятий министерства ##shit:<## на период с ##title:<## года</a>", 
	"<a href=\"##url:\"##\">Мероприятия##shit:<## области ##title:<## г.</a>", 
	"<a href=\"##url:\"##\">##shit:<## мероприяти##shit:<## министерства ##title:<##</a>",
]

newsTemplate = """<tr>##<##
<td##>##>##datetime:</td>##</td>##<##
<td##>##>##title:</td>##</td>##<##
<td##>##>##opening:</td>##</td>##<##
<td##>##>##responsible:</td>##</td>##<##
<td##>##>##where:</td>##</td>##<##
</tr>"""

# Subs

def header(text, char = '='):
	""" Prints fixed-length header
	"""
	a = "%s %s " % (2*char, text)
	print a + char * (115 - len(a))

def debug_line(text):
	global debug

	if debug:
		print "[INFO] %s" % text

# Searches haystack for expression, trying to return requested group string
# if not found - emty string will be returned
def GetMatchGroup(haystack, expr, group):
	a = expr.search(haystack)
	if a:
		return a.group(group)
	return ""

# Slashes reserved regexp chars
def deRegexp(text):
	return regexpReserved.sub("\\\\\\1", text)

# Returns date in printable format
def PrintableDate(date):
	try:
		return date.strftime("%b, %d")
	except:
		return "<Invalid date>";

# Creates RegExp for matching text until given word will be met
def NotEqualExpression(word):
	collector = ""
	result = ""
	for char in word:
		char = deRegexp(char)
		if result:
			result += "|"
		if collector:
			result += collector
		result += "[^%s]" % char
		collector += char
	return "(%s)" % result

# Clean up HTML table markup
cellExpression = re.compile("(<t[rdh])[^>]*>", re.IGNORECASE)
def CleanHtmlTable(markup):
	markup = re.sub("</{0,1}tbody>", "", markup).strip()
	return cellExpression.sub("\\1>", markup)

tagExpr = re.compile("<[^>]+>", re.MULTILINE)
def StripTags(match):
	processed = re.sub("[\t\s\n\r]+", " ", tagExpr.sub("", match.group(2)).replace("&nbsp;", " ")).strip()
	processed = re.sub("&(laquo|raquo|lt|gt|quot);", "\"", processed)
	return "%s%s%s" % (match.group(1), processed, match.group(3))

tdExpr = re.compile("(<td>)(%s+)(</td>)" % NotEqualExpression("</td>"))
thExpr = re.compile("(<th>)(%s+)(</th>)" % NotEqualExpression("</th>"))
def CleanTableCells(markup):
	markup = thExpr.sub(StripTags, markup)
	return tdExpr.sub(StripTags, markup)

# Parses table with header into a set of dectionaries, one per each row
def ParseHeadedTable(markup):
	global debug

	cols = []
	result = []
	isHeader = False
	for row in markup.strip().split("<tr>"):
		if not row:
			continue

		values = []
		for v in re.split("<t[dh]>", re.sub("</(tr|td|th)>", "", row).strip()):
			values.append(ToUnicode(v).strip())

		if not isHeader:
			for col in values:
				col = clean.sub("", deWhitespace.sub(" ", col.strip()))
				for name in colnames:
					for item in colnames[name]:
						if col == item:
							col = name
							break
				cols.append(col)
			isHeader = True

			debug_line("Columns: " + "|".join(cols))
		else:
			item = {}
			if len(cols) != len(values):
				continue

			for i in range(len(cols)):
				item[cols[i]] = values[i]
			result.append(item)
	return result
				





def ToUnicode(text):
	try:
		return unicode(text, 'cp1251')
	except:
		print "[!] Error converting to unicode: %s" % text
		exit(0)

def GetWebPage(url):

	debug_line("URL: %s" % url)

	website = urllib2.urlopen(url)
	website_html = website.read()
	website.close()
	return website_html

def DeChunk(match):
	m = match.group(3)
	if m:
		if len(m) > 1:
			return "((%s)*)" % "|".join("%s[^%s]" % (m[0:i], m[i]) for i in range(0, len(m)))
		else:
			return "([^%s]*)" % m
	return "(.*)"

def ReplaceSpecials(text):
	for needle in replaces.keys():
		text = text.replace(needle, replaces[needle])
	return text

def GetTemplateMatches(haystack, template, result):
	global debug

	chunks = []
	for c in chunk.finditer(template):
		chunks.append(c.group(1))
		if c.group(3) and len(c.group(3)) > 1:
			chunks.append("")

	debug_line("Chunks: %s" % chunks)
	
	pattern = newLines.sub(" ", deRegex.sub("\\\\1", template))
	for k in skipers.keys():
		pattern = pattern.replace(k, skipers[k])

	debug_line("Chunked: %s" % chunk.sub(DeChunk, pattern))

	pattern = re.compile(chunk.sub(DeChunk, pattern), re.DOTALL)

	for match in pattern.finditer(haystack):

		debug_line("Pattern match found: \"%s\"" % match.group(0))

		result1 = {}
		for i in range(1, len(chunks) + 1):
			finding = deWhitespace.sub(" ", deSpace.sub(" ", deQuotes.sub('"', deTag.sub("", match.group(i))))).strip()
			result1[chunks[i - 1]] = finding

		debug_line("Result: %s" % result1)

		result.append(result1)

   	return result

def MultipleMatches(haystack, templates):
	result = []
	for i in templates:
		GetTemplateMatches(haystack, i, result)
	return result
	
def DetectDate(date, time):
	global year

	dat = ""

	debug_line("Date & time: %s, %s" % (date, time))

	for i in range(0, len(months)):
		if re.match("^(\d+)[ \-]*([%s]+)$" % months[i], date):
			day = int(re.sub("[^\d]", "", date))
			return datetime.datetime(year, i+1, day, time[0], time[1])

	return ""

def gcDate(d):
	return d.strftime("%Y-%m-%dT%H:%M:%S")

def gcRecurrentDate(d):
#	return (d - datetime.timedelta(hours=4)).strftime("%Y%m%dT%H%M%SZ")
#	return d.strftime("%Y%m%dT%H%M%S")
	return d.strftime("%Y%m%dT%H%M%SZ")

justDate = re.compile(u"[^\d\-\,а-я]")
def DatesRange(date_string, time):
	global year

	time = re.split("[^\d]", time)
	if len(time) >= 2:
		time = [int(time[0]), int(time[1])]
	else:
		time = [0, 0]

	dates = re.split("-", date_string)
	if len(dates) == 1:
		# Single date
		return [DetectDate(date_string, time)]
	else:
		if len(dates) == 2:
			# Dates range
			month = GetMatchGroup(date_string, re.compile("\d+-\d+\s([^\d]+)$"), 1)
			if month:
				# Same month
				fr = DetectDate("%s %s" % (dates[0], month), time)
				to = DetectDate(dates[1], time)
			else:
				# Different months
				fr = DetectDate(dates[0].strip(), time)
				to = DetectDate(dates[1].strip(), time)

			return [fr, to]
  	return []

# Login
def gcLogin():
	global calendar_service, email, password

	calendar_service = gdata.calendar.service.CalendarService()
	calendar_service.email = email
	calendar_service.password = password
	calendar_service.source = 'Calendar automated updater'
	calendar_service.ProgrammaticLogin()

# Create Quick Event
def gcCreateEvent(e, start_date, end_date=None):
	global calendar_service, calendar

	result = True

	title = ReplaceSpecials(e[u"Мероприятие"])
	place = ReplaceSpecials(e[u"Место проведения"])

	if not title:
		return False

	event = gdata.calendar.CalendarEventEntry()
	event.title = atom.Title(text = title)
	
	content = u"%s\nМесто проведения: %s" % (title, place)

	event.content = atom.Content(text = content)
	event.where.append(gdata.calendar.Where(value_string = place))

	try:
		if end_date:
			recurrence_data = "DTSTART;TZID=Europe/Moscow:%s\r\nDURATION:PT4H\r\nRRULE:FREQ=DAILY;UNTIL=%s\r\n" % (gcRecurrentDate(start_date), gcRecurrentDate(end_date + eventLength))
			#print recurrence_data
			event.recurrence = gdata.calendar.Recurrence(text=recurrence_data)
		else:
			event.when.append(gdata.calendar.When(start_time=gcDate(start_date), end_time=gcDate(start_date + eventLength)))

		new_event = calendar_service.InsertEvent(event, '/calendar/feeds/%s@group.calendar.google.com/private/full' % calendar)
		return True
	except:
		return False

def gcEventDoesExist(title):
	global calendar_service, event_titles, requested, debug

	if not requested:
		requested = True

		query = gdata.calendar.service.CalendarEventQuery('%s@group.calendar.google.com' % calendar, 'private', 'full')
		today = datetime.date.today()
		query.start_min = gcDate(today - datetime.timedelta(days=70))
		query.start_max = gcDate(today + datetime.timedelta(days=70))
		query.max_results = 200 
		feed = calendar_service.CalendarQuery(query)

		for i, an_event in enumerate(feed.entry):
			event_titles[an_event.title.text.decode("utf-8")] = 1

			debug_line("Event '%s'" % an_event.title.text.decode("utf-8"))

		if len(event_titles) == 0:
			print "[x] Unable to read existing events cache!"
			exit(1)	

	result = event_titles.has_key(title)
	event_titles[title] = 1
	return result


################################################################
# Main logic


print "- Start parsing"
tableExpr = re.compile("<table[^>]*>(%s+)</table>" % NotEqualExpression("</table>"), re.MULTILINE)

print "- Login to Google Calendar"
gcLogin()

# Retrieve events
for url in baseURLs:
	pages = 1

	print "\n"
	header("Iterating through the recent %s pages in %s:" % (pages, url))
	for t in MultipleMatches(GetWebPage(url), titleTemplates):
		if pages == 0:
			break
		pages -= 1

		header("Match found \"%s\"" % (ToUnicode(t["title"])), '-')

		year = GetMatchGroup(t["title"], re.compile("(2\d{3})"), 1)
		if not year or year < 2000:
			year = datetime.date.today().year
		else:
			year = int(year)

		page = GetWebPage("%s%s" % (linkedURL, t["url"].replace("&amp;", "&")))

		table = []
		for tableGroup in tableExpr.finditer(page):
			table = ParseHeadedTable(CleanTableCells(CleanHtmlTable(tableGroup.group(1))))
			if len(table) and table[0][u"Время"]:
				break


		for row in table:
			row[u"Время"] = re.sub(u"\s*ч.$", "", row[u"Время"])
			title = ReplaceSpecials(row[u"Мероприятие"])

			try:
				dates = DatesRange(row[u"Дата"], row[u"Время"])

				debug_line("Dates: %s" % dates)
			except:
				print "[!] Unable to parse date (%s) for event \"%s\"" % (row[u"Дата"], title)

			if dates and title:
				if not gcEventDoesExist(title):
					action = "!"

					end_date = None
					if len(dates) > 1:
						end_date = dates[1]

					for i in range(0, 5):
						if gcCreateEvent(row, dates[0], end_date):
							action = "+"
							break;	
						else:
							time.sleep(5)
					print "[%s] %s: '%s'" % (action, PrintableDate(dates[0]), title[0:100])
				else:
					print "[ ] %s: '%s'" % (PrintableDate(dates[0]), title[0:100])
