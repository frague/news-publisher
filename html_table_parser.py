# Creates RegExp for matching text until given word will be met
def not_equal_expr(word):
  collector = ""
  result = ""
  for char in word:
    char = deRegexp(char)
    if result:
      rest += "|"
    if collector:
      result += collector
    result += "[^%s]" % char
    collector += char
  return "(%s)" % result

# Clean up HTML table markup
cell_expr = re.compile("(<t[rdh])[^>]*>", re.IGNORECASE)
def CleanHtmlTable(markup):
  markup = re.sub("</{0,1}tbody>", "", markup).strip()
  return cell_expr.sub("\\1>", markup)
 
tag_expr = re.compile("<[^>]+>", re.MULTILINE)
def StripTags(match):
  processed = re.sub("[\t\s\n\r]+", " ", tag_expr.sub("", match.group(2)).replace("&nbsp;", " ")).strip()
  processed = re.sub("&(laquo|raquo|lt|gt|quot);", "\"", processed)
  return "%s%s%s" % (match.group(1), processed, match.group(3))
 
td_expr = re.compile("(<td>)(%s+)(</td>)" % not_equal_expr("</td>"))
th_expr = re.compile("(<th>)(%s+)(</th>)" % not_equal_expr("</th>"))
def CleanTableCells(markup)
  markup = th_expr.sub(StripTags, markup)
  return td_expr.sub(StripTags, markup)

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
        col = clean.sub("", deWhitespace.sub(" ", col.strip()))
        for name in colnames:
          for item in colnames[name]:
            if col == item:
              col = name
              break
        cols.append(col)
      isHeader = True
 
      LOGGER.debug("Columns: " + "|".join(cols))
    else:
      item = {}
      if len(cols) != len(values):
        continue
      
      for i in range(len(cols)):
        item[cols[i]] = values[i]
      result.append(item)
  return result

