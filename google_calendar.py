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
from logger import get_logger

LOGGER = get_logger(__name__)

class gcalendar():
  service = None
  events_cache = None
  event_length = datetime.timedelta(hours=4)

  def __init__(self, email, password, calendar):
    self.email = email
    self.password = password
    self.calendar = calendar
    LOGGER.debug("Google calendar initialization")

  def date(self, d):
    return d.strftime("%Y-%m-%dT%H:%M:%S")

  def recurrent_date(self, d):
    return d.strftime("%Y%m%dT%H%M%SZ")

  justDate = re.compile(u"[^\d\-\,а-я]")
  # Login
  def login(self):
    self.service = gdata.calendar.service.CalendarService()
    self.service.email = self.email
    self.service.password = self.password
    self.service.source = 'Calendar automated updater'
    self.service.ProgrammaticLogin()
    LOGGER.debug("Logging in to the calendar %s" % self.email)

  def create_event(self):
    ''' Creates empty event '''
    self.event = gdata.calendar.CalendarEventEntry()
    self.event.time = None
    self.event.start_date = None

  def adjust_event_time(self, year=None):
    if not self.event.start_date:
      return

    # If year is provided, replace existing years with it
    if year:
      self.event.start_date.replace(year)
      if self.event.end_date:
        self.event.end_date.replace(year)

    if self.event.time:
      self.event.start_date = datetime.datetime.combine(self.event.start_date.date(), self.event.time)

    LOGGER.debug("Adjusted start_date: %s" % self.event.start_date)

    if self.event.end_date:
      # Dates range
      recurrence_data = "DTSTART;TZID=Europe/Moscow:%s\r\nDURATION:PT4H\r\nRRULE:FREQ=DAILY;UNTIL=%s\r\n" % (
        self.recurrent_date(self.event.start_date), self.recurrent_date(self.event.end_date + self.event_length))
      self.event.recurrence = gdata.calendar.Recurrence(text=recurrence_data)
    else:
      # Single day event
      self.event.when.append(gdata.calendar.When(start_time=self.date(self.event.start_date), 
        end_time=self.date(self.event.start_date + self.event_length)))
    

  def save_event(self, attempts=5):
    ''' Inserts event to calendar '''
    if self.event:
      for i in range(0, attempts):
        LOGGER.debug("(%s) Saving event '%s'" % (i + 1, self.event.name))
        try:
          self.service.InsertEvent(self.event, 
            "/calendar/feeds/%s@group.calendar.google.com/private/full" % self.calendar)
          return True
        except Exception:
          time.sleep(5)
    return False


  def _decode(self, text):
    return text.decode("utf-8")

  @property
  def event_exists(self):
    if not self.event:
      return False

    if not self.events_cache:
      # Request last and upcoming events to check if one with title provided
      # already exists. Store results in cache
      LOGGER.debug("Building calendar events cache")
      self.events_cache = {}

      query = gdata.calendar.service.CalendarEventQuery("%s@group.calendar.google.com" % self.calendar, 
        "private", "full")
      today = datetime.date.today()
      query.start_min = self.date(today - datetime.timedelta(days=70))
      query.start_max = self.date(today + datetime.timedelta(days=70))
      query.max_results = 200
      feed = self.service.CalendarQuery(query)

      for i, an_event in enumerate(feed.entry):
        self.events_cache[self._decode(an_event.title.text)] = True
        LOGGER.debug("Event '%s'" % self._decode(an_event.title.text))

      if not len(self.events_cache):
        raise Exception("[x] Unable to read existing events cache!")

    result = self.events_cache.has_key(self.event.name)
    self.events_cache[self.event.name] = True
    return result

