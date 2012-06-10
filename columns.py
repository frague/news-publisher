#!/usr/local/bin/python
# coding: windows-1251

import yaml
from utils import *
from logger import get_logger

LOGGER = get_logger(__name__)

class column:
  """ Base class for column parsing """
  all_matches = None
  matches = None 

  @staticmethod
  def get_matches(self):
    """ Loads columns matches from the yaml config """
    if not self.all_matches:
      self.all_matches = yaml.load(ReadFile("columns.yaml"))

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

  def parse(sel, text):
    """ Tries to parse provided text """
    self.content = text

  def update_event(self, event):
    """ Updates GCalendar event with the data gathered """
    pass

  def __repr__(self):
    return self.__class__.__name__

class title_column(column):
  pass  

class date_column(column):
  pass

class time_column(column):
  pass

class place_column(column):
  pass


