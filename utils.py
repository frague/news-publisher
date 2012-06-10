from logger import get_logger
import urllib2
import re
import os

LOGGER = get_logger(__name__)

# Expressions
tag_expr = re.compile("<[^>]+>", re.MULTILINE)
regexp_reserved = re.compile("([\[\]\{\}\.\?\*\+\-])")


# Methods
def header(text, char = '='):
  """ Prints fixed-length header
  """
  a = "%s %s " % (2 * char, text)
  print a + char * (115 - len(a))

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
    return unicode(text, 'cp1251', 'replace')
  except:
    raise Exception("Error converting to unicode: '%s'" % text)

def get_web_page(url):

  LOGGER.debug("URL: %s" % url)

  website = urllib2.urlopen(url)
  website_html = website.read()
  website.close()
  return website_html

# File operations
def ReadFile(file_name):
  result = ""
  if os.path.exists(file_name):
    rf = file(file_name, "r")
    result = rf.read()
    rf.close()
  return result

def WriteFile(file_name, contents):
  wf = file(file_name, "w")
  wf.write(contents)
  wf.close()

