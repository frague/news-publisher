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

# Constants & precompiled values
months = ["деабря", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября"]
monthsEng = ["December", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November"]

skipers = {"##>##": "[^>]*", "##<##": "[^<]*"}
chunk = re.compile("##([a-z_]*)(:([^#]+)){0,1}##")

deRegex = re.compile("[\[\]\{\}\(\)\|\$\^\+\*]");
deTag = re.compile("</{0,1}[a-z]+[^>]*>")
deSpace = re.compile("\s+")
newLines = re.compile("[\n\r]")

baseURL = "http://www.saratovsport.ru"

titleTemplate = "<a href=\"##url:\"##\">Основные ##title:<##</a>"
newsTemplate = """<tr>##<##
<td##>##>##date:</td>##</td>##<##
<td##>##>##time:</td>##</td>##<##
<td##>##>##title:</td>##</td>##<##
<td##>##>##opening:</td>##</td>##<##
<td##>##>##responsible:</td>##</td>##<##
<td##>##>##where:</td>##</td>##<##
<td##>##>##participants:</td>##</td>##<##
</tr>"""

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
			finding = deSpace.sub(" ", deTag.sub("", match.group(i))).strip()
			result1[chunks[i - 1]] = finding
#		print result1
		result.append(result1)

   	return result
			
def MakeDates(date, time):
	Month = ""
	for i for 0 in len(months):
		if re.match("^[\d \-]+([%s]+)$" % months[i]:
			Month = monthsEng[i]

	
	
	if not re.match("^[\d \-]+([%s])$" % "]+|[".join(month for month in months), date):
		return []

	return date


# Main logic

'''
# Login
calendar_service = gdata.calendar.service.CalendarService()
calendar_service.email = 'nikolay.bogdanov@gmail.com'
calendar_service.password = '5002202653'
calendar_service.source = 'Calendar automated updater'
calendar_service.ProgrammaticLogin()
'''

# Retrieve events
last = ""
for t in GetTemplateMatches(GetWebPage(baseURL), titleTemplate):
	for p in GetTemplateMatches(GetWebPage("%s%s" % (baseURL, t["url"].replace("&amp;", "&"))), newsTemplate):
		print "%s: %s" % (MakeDates(p["date"], p["time"]), p["title"])
		last = p



#################### Google Calendar API ####################
'''

#  Create Quick Event
event = gdata.calendar.CalendarEventEntry()
event.content = atom.Content(text = ToUnicode("%s on %s at %s" % (last["title"], last["date"], last["where"])))
event.quick_add = gdata.calendar.QuickAdd(value='true')

# Send the request and receive the response:
new_event = calendar_service.InsertEvent(event, '/calendar/feeds/a6q29gg4ttg0mn4j6f13rhltog@group.calendar.google.com/private/full')

'''