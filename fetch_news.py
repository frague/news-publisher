#!/usr/local/bin/python
# coding: windows-1251

from elementtree import ElementTree
import getopt
import sys
import string
import time
import urllib2
import re
import datetime
from credentials import *
from logger import get_logger
from utils import *
from html_table_parser import * 
from columns import *
from google_calendar import *


LOGGER = get_logger(__name__)

# Constants & precompiled values

months = [u"января", u"февраля", u"марта", u"апреля", u"мая", u"июня", u"июля", u"августа", u"сентября", u"октября", u"ноября", u"декабря"]
monthsEng = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
replaces = {"&minus;": "-", "&mdash;": "-", "&quot;": "\"", "&ndash;": "-"}


skipers = {"##>##": "[^>]*", "##<##": "[^<]*"}
chunk = re.compile("##([a-z_]*)(:([^#]+)){0,1}##")

de_regex = re.compile("[\[\]\{\}\(\)\|\$\^\+\*]")
deTag  = re.compile("</{0,1}[a-z]+[^>]*>")
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
# Slashes reserved regexp chars
def de_regexp(text):
  return regexpReserved.sub("\\\\\\1", text)

# Returns date in printable format
def printable_date(date):
  try:
    return date.strftime("%b, %d")
  except:
    return "<Invalid date>";





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
  chunks = []
  for c in chunk.finditer(template):
    chunks.append(c.group(1))
    if c.group(3) and len(c.group(3)) > 1:
      chunks.append("")

  LOGGER.debug("Chunks: %s" % chunks)
  
  pattern = newLines.sub(" ", de_regex.sub("\\\\1", template))
  for k in skipers.keys():
    pattern = pattern.replace(k, skipers[k])

  LOGGER.debug("Chunked: %s" % chunk.sub(DeChunk, pattern))

  pattern = re.compile(chunk.sub(DeChunk, pattern), re.DOTALL)

  for match in pattern.finditer(haystack):
    LOGGER.debug("Pattern match found: \"%s\"" % match.group(0))
    result1 = {}
    for i in range(1, len(chunks) + 1):
      finding = deWhitespace.sub(" ", deSpace.sub(" ", deQuotes.sub('"', deTag.sub("", match.group(i))))).strip()
      result1[chunks[i - 1]] = finding
    LOGGER.debug("Result: %s" % result1)
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

  LOGGER.debug("Date & time: %s, %s" % (date, time))

  for i in range(0, len(months)):
    if re.match("^(\d+)[ \-]*([%s]+)$" % months[i], date):
      day = int(re.sub("[^\d]", "", date))
      return datetime.datetime(year, i+1, day, time[0], time[1])

  return ""


def save_table_events(table):
  ''' Attempts to parse provided table as the one
      that contains events
  '''
  for row in table:
    row[u"Время"] = re.sub(u"\s*ч.$", "", row[u"Время"])
    try:
      title = ReplaceSpecials(row[u"Мероприятие"])
    except:
      raise Exception("Unable to find 'Event' column")

    try:
      dates = DatesRange(row[u"Дата"], row[u"Время"])

      LOGGER.debug("Dates: %s" % dates)
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
        print "[%s] %s: '%s'" % (action, printable_date(dates[0]), title[0:100])
      else:
        print "[ ] %s: '%s'" % (printable_date(dates[0]), title[0:100])
  


################################################################
# Main logic


print "- Start parsing"
table_expr = re.compile("<table[^>]*>(%s+)</table>" % not_equal_expr("</table>"), re.MULTILINE)

print "- Login to Google Calendar"
gcLogin()

# Retrieve events
for url in baseURLs:
  pages = 1

  print "\n"
  header("Iterating through the recent %s pages in %s:" % (pages, url))
  for t in MultipleMatches(get_web_page(url), titleTemplates):
    if pages == 0:
      break
    pages -= 1

    header("Match found \"%s\"" % (to_unicode(t["title"])), '-')

    year = get_match_group(t["title"], re.compile("(2\d{3})"), 1)
    if not year or year < 2000:
      year = datetime.date.today().year
    else:
      year = int(year)

    page = get_web_page("%s%s" % (linkedURL, t["url"].replace("&amp;", "&")))

    table = []
    for table_group in table_expr.finditer(page):
      columns, contents = parse_headed_table(clean_cells(clean_table(table_group.group(1))))
      if columns:
        LOGGER.debug("Processing table with columns '%s'" % columns)
        save_table_events()

