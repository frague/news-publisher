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
from credentials import email, password, calendar
from logger import get_logger
from utils import *
from html_table_parser import * 
from columns import *
from google_calendar import gcalendar


LOGGER = get_logger(__name__)
config = yaml.load(read_file("config.yaml"))

# Constants & precompiled values

chunk = re.compile("##([a-z_]*)(:([^#]+)){0,1}##")
de_regex = re.compile("[\[\]\{\}\(\)\|\$\^\+\*]")
deTag  = re.compile("</{0,1}[a-z]+[^>]*>")
deWhitespace = re.compile("\s+")
deSpace = re.compile("(\s+|&nbsp;)")
deQuotes = re.compile("&[lgr](aquo|t);")
newLines = re.compile("[\n\r]")
regexpReserved = re.compile("([\[\]\{\}\.\?\*\+\-])")
table_expr = re.compile("<table[^>]*>(%s+)</table>" % not_equal_expr("</table>"), re.MULTILINE)

dayLength = datetime.timedelta(days=1)

# Subs

def de_chunk(match):
  m = match.group(3)
  if m:
    if len(m) > 1:
      return "((%s)*)" % "|".join("%s[^%s]" % (m[0:i], m[i]) for i in range(0, len(m)))
    else:
      return "([^%s]*)" % m
  return "(.*)"

def replace_specials(text):
  for needle in config["replaces"].keys():
    text = text.replace(needle, config["replaces"][needle])
  return text

def get_template_matches(haystack, template, result):
  LOGGER.debug("Searching for matches for template '%s'" % template)
  chunks = []
  for c in chunk.finditer(template):
    chunks.append(c.group(1))
    if c.group(3) and len(c.group(3)) > 1:
      chunks.append("")

  LOGGER.debug("Chunks found: %s" % chunks)
  
  pattern = newLines.sub(" ", de_regex.sub("\\\\1", template))
  for k in config["skipers"].keys():
    pattern = pattern.replace(k, config["skipers"][k])

  pattern = re.compile(chunk.sub(de_chunk, pattern), re.DOTALL)

  for match in pattern.finditer(haystack):
    LOGGER.debug("Pattern match found: \"%s\"" % match.group(0))
    result1 = {}
    for i in range(1, len(chunks) + 1):
      finding = deWhitespace.sub(" ", deSpace.sub(" ", deQuotes.sub('"', deTag.sub("", match.group(i))))).strip()
      result1[chunks[i - 1]] = finding
    LOGGER.debug("Result: %s" % result1)
    result.append(result1)
  return result

def multiple_matches(haystack, templates):
  result = []
  for i in templates:
    get_template_matches(haystack, i, result)
  return result
  

def save_table_events(columns, contents, cal, year):
  ''' Attempts to parse provided table as the one
      that contains events
  '''
  LOGGER.debug("Saving table events")
  for row in contents:
    LOGGER.debug("New event:")
    cal.create_event()
    try:
      for i in range(0, len(columns)):
        for column_class in columns[i]:
          column_class.update_event(cal, replace_specials(row[i]))
      cal.adjust_event_time(year)

      result = False
      if not cal.event_exists:
        result = cal.save_event()

      LOGGER.info("[%s] %s: '%s'" % ("+" if result else " ", 
        printable_date(cal.event.start_date), 
        cal.event.name[0:100]))
    except Exception, error:
      LOGGER.error("Unable to create event - \"%s\"" % unicode(error))


################################################################
# Main logic


LOGGER.info("Start parsing")

cal = gcalendar(email, password, calendar)
cal.login()

# Retrieve events
for url in config["base_urls"]:
  pages = 1

  LOGGER.info("Iterating through the recent %s pages in %s:" % (pages, url))
  web_page = to_unicode(get_web_page(url)) 
  for t in multiple_matches(web_page, config["title_templates"]):
    if pages == 0:
      break
    pages -= 1

    LOGGER.info("Match found \"%s\"" % (t["title"]))

    year = get_match_group(t["title"], re.compile("(2\d{3})"), 1)
    if not year or year < 2000:
      year = datetime.date.today().year
    else:
      year = int(year)

    web_page = get_web_page("%s%s" % (config["linked_url"], t["url"].replace("&amp;", "&")))

    table = []
    for table_group in table_expr.finditer(web_page):
      columns, contents = parse_headed_table(clean_cells(clean_table(table_group.group(1))))
      if columns:
        LOGGER.debug("Processing table with columns '%s'" % columns)
        save_table_events(columns, contents, cal, year)

