#!/usr/local/bin/python
# coding: windows-1251

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

class calendar():
  service = None

  def __init__(self, email, password, calendar):
    self.email = email
    self.password = password
    self.calendar = calendar

  def gcDate(d):
    return d.strftime("%Y-%m-%dT%H:%M:%S")

  def gcRecurrentDate(d):
    return d.strftime("%Y%m%dT%H%M%SZ")

  justDate = re.compile(u"[^\d\-\,а-я]")
  def DatesRange(date_string, time):
    global year

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
        month = get_match_group(date_string, re.compile("\d+-\d+\s([^\d]+)$"), 1)
        if month:
          # Same month
          fr = DetectDate("%s %s" % (dates[0], month), time)
          to = DetectDate(dates[1], time)
        else:
          # Different months
          fr = DetectDate(dates[0].strip(), time)
          to = DetectDate(dates[1].strip(), time)

        return [fr, to]
      return []

  # Login
  def gcLogin():
    self.service = gdata.calendar.service.CalendarService()
    self.service.email = self.email
    self.service.password = self.password
    self.service.source = 'Calendar automated updater'
    self.service.ProgrammaticLogin()

  # Create Quick Event
  def gcCreateEvent(e, start_date, end_date=None):
    result = True

    title = ReplaceSpecials(e[u"Мероприятие"])
    place = ReplaceSpecials(e[u"Место проведения"])

    if not title:
      return False

    event = gdata.calendar.CalendarEventEntry()
    event.title = atom.Title(text = title)

    content = u"%s\nМесто проведения: %s" % (title, place)
    event.content = atom.Content(text = content)
    event.where.append(gdata.calendar.Where(value_string = place))

    try:
      if end_date:
        recurrence_data = "DTSTART;TZID=Europe/Moscow:%s\r\nDURATION:PT4H\r\nRRULE:FREQ=DAILY;UNTIL=%s\r\n" % (gcRecurrentDate(start_date), gcRecurrentDate(end_date + eventLength))
        #print recurrence_data
        event.recurrence = gdata.calendar.Recurrence(text=recurrence_data)
      else:
        event.when.append(gdata.calendar.When(start_time=gcDate(start_date), end_time=gcDate(start_date + eventLength)))

      new_event = self.service.InsertEvent(event, '/calendar/feeds/%s@group.calendar.google.com/private/full' % self.calendar)
      return True
    except:
      return False

  def gcEventDoesExist(title):
    global event_titles, requested

    if not requested:
      requested = True

      query = gdata.calendar.service.CalendarEventQuery('%s@group.calendar.google.com' % calendar, 'private', 'full')
      today = datetime.date.today()
      query.start_min = gcDate(today - datetime.timedelta(days=70))
      query.start_max = gcDate(today + datetime.timedelta(days=70))
      query.max_results = 200
      feed = self.service.CalendarQuery(query)

      for i, an_event in enumerate(feed.entry):
        event_titles[an_event.title.text.decode("utf-8")] = 1

        LOGGER.debug("Event '%s'" % an_event.title.text.decode("utf-8"))

      if len(event_titles) == 0:
        raise Exception("[x] Unable to read existing events cache!")

    result = event_titles.has_key(title)
    event_titles[title] = 1
    return result

