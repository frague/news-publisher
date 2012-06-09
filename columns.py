class column:
  """ Base class for column parsing """
  matches = ()

  def is_match_for(self, name):
    """ Identifies if provided text corresponds to this class """
    return name in self.matches

  def parse(sel, text):
    """ Tries to parse provided text """
    self.content = text

  def update_event(self, event):
    """ Updates GCalendar event with the data gathered """
    pass


class title_column(column):
  matches = (u"Мероприятие", u"Название мероприятия", u"Мероприятия", 
    u"Название Мероприятия", u"Название мероприятие", 
    u"Наименование мероприятия")

class date_column(column):
  matches = (u"Открытие", u"Время открытия", u"Начало")

class time_column(column):
  matches = (u"Открытие", u"Время открытия", u"Начало")

class place_column(column):
  matches = (u"Место проведения", u"Место проведения>")


