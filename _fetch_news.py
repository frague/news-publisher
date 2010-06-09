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

from saratovsport_source import *

# Constants & precompiled values
months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "деабря"]
monthsEng = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

skipers = {"##>##": "[^>]*", "##<##": "[^<]*"}
chunk = re.compile("##([a-z_]*)(:([^#]+)){0,1}##")

deRegex = re.compile("[\[\]\{\}\(\)\|\$\^\+\*]");
deTag = re.compile("</{0,1}[a-z]+[^>]*>")
deWhitespace = re.compile("\s+")
deSpace = re.compile("(\s+|&nbsp;)")
deQuotes = re.compile("&[lgr](aquo|t);")
newLines = re.compile("[\n\r]")
justDate = re.compile("[^\d\-\,а-я]")

event_titles = {}
requested = False

eventLength = datetime.timedelta(hours=4)
dayLength = datetime.timedelta(days=1)

# Subs

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

	
def DetectDate(date, time):
	dat = ""
	for i in range(0, len(months)):
		if re.match("^(\d+)[ \-]*([%s]+)$" % months[i], date):
#			Month = monthsEng[i]
			day = int(re.sub("[^\d]", "", date))
			return datetime.datetime(datetime.date.today().year, i+1, day, int(time[0]), int(time[1]))

	return ""

def gcDate(d):
	return d.strftime("%Y-%m-%dT%H:%M:%S")

def DatesRange(datesText, time):
	year = datetime.date.today().year
	time = re.split("[^\d]", time)
	if len(time) != 2:
		time = ["0", "0"]

	dates = []
	datesText = justDate.sub("", datesText)
	prevDate = ""
	for d in datesText.split("-"):
		if re.match("^\d+$", d):
			prevDate = int(d)
		else:
			dat = DetectDate(d, time)
			if dat:
				if prevDate:
					dates.append(datetime.datetime(dat.year, dat.month, prevDate, dat.hour, dat.minute))
					prevDate = ""
				dates.append(dat)
			else:
				prevDate = ""

	lastDate = ""
	result = []
	for date in dates:
		if lastDate:
			while lastDate < date:
				lastDate = lastDate + dayLength
				result.append(lastDate)
			lastDate = ""
		else:
			lastDate = date
			result.append(lastDate)
  	return result

# Login
def gcLogin():
	global calendar_service, email, password

	calendar_service = gdata.calendar.service.CalendarService()
	calendar_service.email = email
	calendar_service.password = password
	calendar_service.source = 'Calendar automated updater'
	calendar_service.ProgrammaticLogin()

# Create Quick Event
def gcCreateEvent(e):
	global calendar_service, calendar

	for date in DatesRange(e["date"], e["time"]):
		event = gdata.calendar.CalendarEventEntry()
		event.title = atom.Title(text = ToUnicode(e["title"]))

		content = "%s\nОткрытие: %s\nОтветственные: %s\nУчастников: %s" % (e["title"], e["opening"], e["responsible"], e["participants"])

		event.content = atom.Content(text = ToUnicode(content))
		event.where.append(gdata.calendar.Where(value_string = ToUnicode(e["where"])))

		event.when.append(gdata.calendar.When(start_time=gcDate(date), end_time=gcDate(date + eventLength)))
#		print gcDate(date)
		new_event = calendar_service.InsertEvent(event, '/calendar/feeds/%s@group.calendar.google.com/private/full' % calendar)

def gcEventDoesExist(title):
	global calendar_service, event_titles, requested

	title = title.decode("windows-1251")

	if not requested:
		requested = True

		query = gdata.calendar.service.CalendarEventQuery('%s@group.calendar.google.com' % calendar, 'private', 'full')
		today = datetime.date.today()
		query.start_min = gcDate(today - datetime.timedelta(days=30))
		query.start_max = gcDate(today + datetime.timedelta(days=30))
		query.max_results = 200 
		feed = calendar_service.CalendarQuery(query)

		for i, an_event in enumerate(feed.entry):
			event_titles[an_event.title.text.decode("utf-8")] = 1
#			print "'%s'" % an_event.title.text.decode("utf-8")

	result = event_titles.has_key(title)
	event_titles[title] = 1
	return result




################################################################
# Main logic

gcLogin()

s = Saratovsport()
s.Retrieve()