from utils import *
from columns import *
from logger import get_logger

LOGGER = get_logger(__name__)

# Expressions
cell_expr = re.compile("(<t[rdh])[^>]*>", re.IGNORECASE)
td_expr = re.compile("(<td>)(%s+)(</td>)" % not_equal_expr("</td>"))
th_expr = re.compile("(<th>)(%s+)(</th>)" % not_equal_expr("</th>"))
clean_expr = re.compile("[<>]")
de_whitespace = re.compile("\s+")

column_types = (title_column, date_column, time_column, place_column)
 
# Clean up HTML table markup
def clean_table(markup):
  markup = re.sub("</{0,1}tbody>", "", markup).strip()
  return cell_expr.sub("\\1>", markup)

# Clean up table cells contents
def clean_cells(markup):
  markup = th_expr.sub(strip_tags, markup)
  return td_expr.sub(strip_tags, markup)

# Parses table with header into a set of dectionaries, one per each row
def parse_headed_table(markup):
  headers = []
  contents = []
  header_match = False

  for row in markup.strip().split("<tr>"):
    if not row:
      continue
 
    values = []
    for v in re.split("<t[dh]>", re.sub("</(tr|td|th)>", "", row).strip()):
      values.append(to_unicode(v).strip())
 
    if not len(headers):
      # Table columns names are not defined
      for col in values:
        col = clean_expr.sub("", de_whitespace.sub(" ", col.strip()))
        LOGGER.debug("Column '%s' found" % col)

        col_classes = []
        for c in column_types:
          if c.is_match_for(c, col):
            col_classes.append(c)
            header_match = True
        headers.append(col_classes if len(col_classes) else None)
      header_defined = True
    else:
      if len(headers) != len(values):
        # Amount of cells isn't equal to columns'
        continue

      contents.append(values)

  LOGGER.debug("Headers: %s" % headers)
  return headers if header_match else None, contents

