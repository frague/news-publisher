#!/usr/local/bin/python
# coding: windows-1251

import yaml
import atom
import gdata
import datetime
from utils import *
from logger import get_logger
from google_calendar import gcalendar

LOGGER = get_logger(__name__)

class column:
  """ Base class for column parsing """
  all_matches = None
  matches = None 

  @staticmethod
  def get_matches(self):
    """ Loads columns matches from the yaml config """
    if not self.all_matches:
      self.all_matches = yaml.load(read_file("columns.yaml"))

    try:
      self.matches = self.all_matches["columns"][str(self)]
    except:
      raise Exception("Unable to load columns for %s" % self)

  @staticmethod
  def is_match_for(self, name):
    """ Identifies if provided text corresponds to this class """
    self.get_matches(self)
    LOGGER.debug("Match for '%s' as %s is %s" % (name, self, name in self.matches))
    return name in self.matches

  @staticmethod
  def update_event(cal, text):
    """ Updates GCalendar event with the data gathered """
    pass

  def __repr__(self):
    return self.__class__.__name__

class title_column(column):
  @staticmethod
  def update_event(cal, text):
    LOGGER.debug("Event's title: '%s'" % text)
    cal.event.title = atom.Title(text = text)
    cal.event.name = text

class date_column(column):
  @staticmethod
  def update_event(cal, text):
    if cal.event.start_date:
      # If value already set - skip
      return

    LOGGER.debug("Parsing event date from '%s'" % text)
    start_date, end_date = dates_range(text, datetime.datetime.now().year)
    if start_date:
      cal.event.start_date = start_date
      cal.event.end_date = end_date
      LOGGER.debug("Event lasts from %s till %s" % (printable_date(start_date), 
        printable_date(end_date)))
    elif not cal.event.start_date:
      raise Exception("Unable to parse event date '%s'" % text)
    
class time_column(column):
  @staticmethod
  def update_event(cal, text):
    if cal.event.time:
      # If value already set - skip
      return

    LOGGER.debug("Parsing time: %s" % text)
    time = get_match_group(text, re.compile("(([0-1]{0,1}[0-9]|2[0-3])[-:.][0-5][0-9])"), 1)
    if time:
      (hours, minutes) = re.split("[^\d]", time)
      cal.event.time = datetime.time(int(hours), int(minutes))
      LOGGER.debug("Event start time: %s" % cal.event.time)
    elif not cal.event.time:
      raise Exception("Unable to parse event time '%s'" % text)

class place_column(column):
  @staticmethod
  def update_event(cal, text):
    LOGGER.debug("Event's place: '%s'" % text)
    content = u"Место проведения: %s" % text
    cal.event.content = atom.Content(text = text)
    cal.event.where.append(gdata.calendar.Where(value_string = text))

# Service methods
event_length = datetime.timedelta(hours=4)

def update_event_dates(event):
    try:
      if event.end_date:
        recurrence_data = "DTSTART;TZID=Europe/Moscow:%s\r\nDURATION:PT4H\r\nRRULE:FREQ=DAILY;UNTIL=%s\r\n" % (
          self.recurrent_date(event.start_date), 
          self.recurrent_date(event.end_date + event_length))
        event.recurrence = gdata.calendar.Recurrence(text=recurrence_data)
      else:
        event.when.append(gdata.calendar.When(start_time=self.date(start_date), 
          end_time=self.date(start_date + eventLength)))
      return True
    except:
      return False

