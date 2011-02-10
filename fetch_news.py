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
months = [u"января", u"февраля", u"марта", u"апреля", u"мая", u"июня", u"июля", u"августа", u"сентября", u"октября", u"ноября", u"декабря"]
monthsEng = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
replaces = {"&minus;": "-", "&mdash;": "-", "&quot;": "\""}
colnames = {u"Мероприятие": [u"Название мероприятия"], u"Открытие": [u"Время открытия", u"Начало"]}

skipers = {"##>##": "[^>]*", "##<##": "[^<]*"}
chunk = re.compile("##([a-z_]*)(:([^#]+)){0,1}##")

deRegex = re.compile("[\[\]\{\}\(\)\|\$\^\+\*]");
deTag  = re.compile("</{0,1}[a-z]+[^>]*>")
deWhitespace = re.compile("\s+")
deSpace = re.compile("(\s+|&nbsp;)")
deQuotes = re.compile("&[lgr](aquo|t);")
newLines = re.compile("[\n\r]")
regexpReserved = re.compile("([\[\]\{\}\.\?\*\+\-])")

event_titles = {}
requested = False

#baseURL = "http://saratovsport.ru/index.php?mod=article&cid=19"
baseURL = "http://www.sport.saratov.gov.ru/news/events/"
linkedURL = "http://www.sport.saratov.gov.ru"

eventLength = datetime.timedelta(hours=4)
dayLength = datetime.timedelta(days=1)

titleTemplate1 = "<a href=\"##url:\"##\">План спортивных ##shit:<## на ##title:<##</a>"
titleTemplate2 = "<a href=\"##url:\"##\">ПЛАН мероприятий министерства по развитию спорта, физической культуры и туризма  Саратовской области</a>"
titleTemplate3 = "<a href=\"##url:\"##\" title=\"##skip:\"##\">ПЛАН мероприятий министерства ##shit:<## на период с ##title:<## года</a>"


#<a href="/news/detailed.php?SECTION_ID=&amp;ELEMENT_ID=10655" title="ПЛАН мероприятий министерства по развитию спорта, физической культуры и туризма  Саратовской области  на период с 14 по 20 февраля 2011 года">ПЛАН мероприятий министерства по развитию спорта, физической культуры и туризма  Саратовской области  на период с 14 по 20 февраля 2011 года</a>

newsTemplate = """<tr>##<##
<td##>##>##datetime:</td>##</td>##<##
<td##>##>##title:</td>##</td>##<##
<td##>##>##opening:</td>##</td>##<##
<td##>##>##responsible:</td>##</td>##<##
<td##>##>##where:</td>##</td>##<##
</tr>"""

# Subs

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
	return date.strftime("%b, %d")

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
				col = deWhitespace.sub(" ", col.strip())
				for name in colnames:
					for item in colnames[name]:
						if col == item:
							col = name
							break
				cols.append(col)
			isHeader = True
#			print "-".join(cols)
		else:
			item = {}
			for i in range(len(cols)):
				item[cols[i]] = values[i]
			result.append(item)
	return result
				





def ToUnicode(text):
	return unicode(text, 'cp1251')

def GetWebPage(url):
#	print "\n\n URL: %s" % url

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

def GetTemplateMatches(haystack, template):
	result = []

	chunks = []
	for c in chunk.finditer(template):
		chunks.append(c.group(1))
		if c.group(3) and len(c.group(3)) > 1:
			chunks.append("")

#	print chunks
	
	pattern = newLines.sub(" ", deRegex.sub("\\\\1", template))
	for k in skipers.keys():
		pattern = pattern.replace(k, skipers[k])

#	print chunk.sub(DeChunk, pattern)
	pattern = re.compile(chunk.sub(DeChunk, pattern), re.DOTALL)

	for match in pattern.finditer(haystack):
#		print "---\n%s\n---" % match.group(0)
		result1 = {}
		for i in range(1, len(chunks) + 1):
			finding = deWhitespace.sub(" ", deSpace.sub(" ", deQuotes.sub('"', deTag.sub("", match.group(i))))).strip()
			result1[chunks[i - 1]] = finding
#		print result1
		result.append(result1)

   	return result

def MultipleMatches(haystack, templates):
	for i in templates:
		result = GetTemplateMatches(haystack, i)
		if len(result) == 0:
			continue
		return result
	return result
	
def DetectDate(date, time):
	global year

	dat = ""
#	print "> %s, %s" % (date, time)
	for i in range(0, len(months)):
		if re.match("^(\d+)[ \-]*([%s]+)$" % months[i], date):
			day = int(re.sub("[^\d]", "", date))
			return datetime.datetime(year, i+1, day, time[0], time[1])

	return ""

def gcDate(d):
	return d.strftime("%Y-%m-%dT%H:%M:%S")

justDate = re.compile(u"[^\d\-\,а-я]")
def DatesRange(date_string, time):
	global year

	#print "%s, %s" % (date_string, time)

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
			result = []
			while fr < to:
				result.append(fr)
				fr = fr + datetime.timedelta(days=1)
			return result
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
def gcCreateEvent(e, dates):
	global calendar_service, calendar

	for date in dates:
		title = ReplaceSpecials(e[u"Мероприятие"])
		place = ReplaceSpecials(e[u"Место проведения"])

		event = gdata.calendar.CalendarEventEntry()
		event.title = atom.Title(text = title)

		content = u"%s\nМесто проведения: %s" % (title, place)

		event.content = atom.Content(text = content)
		event.where.append(gdata.calendar.Where(value_string = place))

		event.when.append(gdata.calendar.When(start_time=gcDate(date), end_time=gcDate(date + eventLength)))
#		print gcDate(date)
		try:
			new_event = calendar_service.InsertEvent(event, '/calendar/feeds/%s@group.calendar.google.com/private/full' % calendar)
			return True
		except:
			return False

def gcEventDoesExist(title):
	global calendar_service, event_titles, requested

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
			#print "'%s'" % an_event.title.text.decode("utf-8")
		if len(event_titles) == 0:
			print "[x] Unable to read existing events cache!"
			exit(0)	

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
pages = 0
print "- Iterating through the recent 2 pages:"
for t in MultipleMatches(GetWebPage(baseURL), [titleTemplate3, titleTemplate1, titleTemplate2]):
	if pages == 5:
		break
	pages += 1

	print "\n----------- Page \"%s\"" % ToUnicode(t["title"])

	year = int(GetMatchGroup(t["title"], re.compile("(2\d{3})"), 1))
	if not year or year < 2000:
		year = datetime.date.today().year

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
			#print dates
		except:
			print "[!] Unable to parse date (%s) for event \"%s\"" % (row[u"Дата"], title)

		if dates:
			if not gcEventDoesExist(title):
				action = "!"
				if gcCreateEvent(row, dates):
					action = "+"
				print "[%s] %s: '%s'" % (action, PrintableDate(dates[0]), title)
			else:
				print "[ ] %s: '%s'" % (PrintableDate(dates[0]), title)
