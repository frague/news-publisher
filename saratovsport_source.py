#!/usr/local/bin/python
# coding: windows-1251


class Saratovsport:
	def __init__(self):
		self.baseURL = "http://www.saratovsport.ru"

		self.titleTemplate = "<a href=\"##url:\"##\">Основные ##title:<##</a>"
		self.newsTemplate = """<tr>##<##
<td##>##>##date:</td>##</td>##<##
<td##>##>##time:</td>##</td>##<##
<td##>##>##title:</td>##</td>##<##
<td##>##>##opening:</td>##</td>##<##
<td##>##>##responsible:</td>##</td>##<##
<td##>##>##where:</td>##</td>##<##
<td##>##>##participants:</td>##</td>##<##
</tr>"""

	def RetrieveEvents(self):
		# Retrieve events
		for t in GetTemplateMatches(GetWebPage(baseURL), titleTemplate):
			for e in GetTemplateMatches(GetWebPage("%s%s" % (baseURL, t["url"].replace("&amp;", "&"))), newsTemplate):
				dates = DatesRange(e["date"], e["time"])
				if dates:
					title = e["title"].decode("windows-1251")
					if not gcEventDoesExist(e["title"]):
						#gcCreateEvent(e)
						print "[+] '%s'" % title
					else:
						print "[-] '%s'" % title

