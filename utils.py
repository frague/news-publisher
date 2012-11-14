from logging import getLogger
import datetime
import urllib2
import yaml
import re
import os

LOGGER = getLogger()

# Expressions
tag_expr = re.compile("<[^>]+>", re.MULTILINE)
regexp_reserved = re.compile("([\[\]\{\}\.\?\*\+\-])")


# Methods
def header(text, char = '='):
  """ Prints fixed-length header
  """
  a = "%s %s " % (2 * char, text)
  print a + char * (115 - len(a))

def printable_date(date):
  try:
    return date.strftime("%b, %d")
  except:
    return "<Invalid date>"

# Searches haystack for expression, trying to return requested group string
# if not found - emty string will be returned
def get_match_group(haystack, expr, group):
  a = expr.search(haystack)
  if a:
    return a.group(group)
  return ""
               
# Slashes reserved regexp chars
def de_regexp(text):
  return regexp_reserved.sub("\\\\\\1", text)

# Removes html tags from the text provided (w/ some extentions)
def strip_tags(match):
  processed = re.sub("[\t\s\n\r]+", " ", tag_expr.sub("", match.group(2)).replace("&nbsp;", " ")).strip()
  processed = re.sub("&(laquo|raquo|lt|gt|quot);", "\"", processed)
  return "%s%s%s" % (match.group(1), processed, match.group(3))

#Creates RegExp for matching text until given word will be met
def not_equal_expr(word):
  collector = ""
  result = ""
  for char in word:
    char = de_regexp(char)
    if result:
      result += "|"
    if collector:
      result += collector
    result += "[^%s]" % char
    collector += char
  return "(%s)" % result

def to_unicode(text):
  try:
    return unicode(text, 'utf-8', 'replace')
  except:
    raise Exception("Error converting to unicode: '%s'" % text)

def get_web_page(url):

  LOGGER.debug("Getting web page by URL: %s" % url)

  website = urllib2.urlopen(url)
  charset = website.headers.getparam("charset")
  LOGGER.debug("Charset detected: %s" % charset)

  website_html = website.read()
  website.close()
  return website_html

# File operations
def read_file(file_name, open_type="r"):
  LOGGER.debug("Reading file \"%s\"" % file_name)
  result = ""
  if os.path.exists(file_name):
    rf = file(file_name, open_type)
    result = rf.read()
    rf.close()
  LOGGER.debug("%s bytes read" % len(result))
  return result

def write_file(file_name, contents, open_type="w"):
  LOGGER.debug("Writing %s bytes to file \"%s\"" % (len(content), file_name))
  wf = file(file_name, open_type)
  wf.write(contents)
  wf.close()

config = yaml.load(read_file("config.yaml"))


# Date&time methods
def detect_date(date, year):
  ''' Attempts to find date string in text. Returns datetime object '''

  LOGGER.debug("Searching for a date in '%s'" % date)
  for i in range(0, len(config["months"])):
    if re.match("^(\d+)[ \-]*([%s]*)$" % config["months"][i], date):
      day = int(re.sub("[^\d]", "", date))
      return datetime.datetime(year, i + 1, day, 0, 0)
  return None


def dates_range(date_string, year):
  ''' Attempts to find dates range in text '''

  LOGGER.debug("Parsing dates range: '%s'" % date_string)

  dates = re.split("-", date_string)
  if len(dates) == 1:
    # Single date
    return detect_date(date_string, year), None
  else:
    if len(dates) == 2:
      # Dates range
      month = get_match_group(date_string, re.compile("\d+-\d+\s([^\d]+)$"), 1)
      if month:
        # Same month
        start_date = detect_date("%s %s" % (dates[0], month), year)
        end_date = detect_date(dates[1], year)
      else:
        # Different months
        start_date = detect_date(dates[0].strip(), year)
        end_date = detect_date(dates[1].strip(), year)
      return start_date, end_date
  return None, None

