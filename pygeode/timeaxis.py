# Time axis

# contains a relative time 'startdate', 'units', and 'values' (units since xxx)
# also contains an absolute time, defined by certain auxiliary arrays
# (usually 'year', 'month', 'day', 'hour', 'minute', 'second')
#    NOTE: not all auxiliary fields are necessarily included, depending on the context of the time axis

#TODO: add 'weights' array in 'uniquify', so the values for things such as monthly means
#      will be properly represented.  I.e.,if we then do an annual mean, we'll get the
#      same values as if we went directly from the instantaneous to annual mean.


# helper C extension (for things that numpy can't do easily)
from pygeode import timeaxiscore as lib

months = ['Smarch', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
months_full = ['Smarch', 'January', 'February', 'March', 'April', 'May', 'June',
             'July', 'August', 'September', 'October', 'November', 'December']



# Given a list of fields,
# return the order of indices that will sort the fields chronologically.
# Assume the fields are ordered from slowest varying to fastest varying.
def _argsort (fields):
  '''return a list of indices that would sort the axis'''
  import numpy as np
  assert len(fields) > 0, 'nothing to sort!'
  for f in fields: assert isinstance(f, np.ndarray), "bad field"
  # (lexsort uses the *last* column as the slowest varying key?)
  fields = fields[::-1]
  S = np.lexsort(fields)
  return S


# Take a list of fields (year, month, day, etc.) and return the fields with duplicates removed.
# NOTE: the fields are assumed to be pre-sorted
def _uniquify (fields):
  from pygeode import timeutils
  from warnings import warn
  warn ("Deprecated.  Use timeutils module.")
  return timeutils._uniquify(fields)



# time axis
#
# Optional properties:
#   year, month, day, hour, minute, second, ms  (numpy arrays)
#     (note: any of these can be ommitted, if they're not applicable)
#     (i.e., a monthly mean time axis would not have day, hour, etc.)
#
# 
# (superclass; use one of the subclasses defined below)
from pygeode.axis import TAxis
class Time (TAxis):
# {{{
  name = 'time'
  plotatts = TAxis.plotatts.copy()
  plotatts['plottitle'] = ''
  plotatts['plotfmt'] = '$v'
  plotatts['plotofsfmt'] = ''

  # List of valid *possible* field names for this class.
  # Override in subclasses.
  # Note: not necessarily *all* of these fields may be defined in a given instance.
  allowed_fields=()

  # Allow alternate construction(s) of the model time axis
  # Normal construction takes the explicit list of associated arrays
  # Alternatively, take a start date, list of offset values, and units
  def __init__ (self, values=None, startdate=None, units=None, **kwargs):
  # {{{
    from pygeode.axis import TAxis
    import numpy as np
    from warnings import warn
    if type(self) == Time:
      raise NotImplementedError("Can't instantiate Time class directly.  Please use StandardTime or ModelTime365, or some other calendar-specific subclass")

    assert units is not None, "child constructor did not provide units"

    # For the ultra-lazy:
    if isinstance(values,int): values = np.arange(values)

    # Extract any auxiliary fields passed to us (i.e. year, month, etc.)
    auxarrays = dict([k,np.asarray(v)] for k,v in kwargs.iteritems() if k in self.allowed_fields)

    # Generate absolute times from relative times?
    if auxarrays == {}:
      assert values is not None, "not enough information to construct a time axis"

      # Get the associated arrays (year, month, day, etc. fields)
      assert startdate is not None, "startdate required to generate the dates"
      auxarrays = self.val_as_date(np.asarray(values), startdate=startdate, units=units)

    # Determine the start date
    # (Keep the initial start date if one was given)
    if startdate is None:
      startdate = {}
      for aux,arr in auxarrays.iteritems():
        startdate[aux] = arr[0]

    # Generate relative times from absolute times?
    # (redo the 'values' array to be consistent with the absolute date/times)
    # (useful for example when concatenating vars along the time axis, when
    #  each var has a different start date (so the 'values' being concatenated
    #  together are meaningless)
    values = self.date_as_val(auxarrays, units=units, startdate=startdate)
#    if values is None:
#      values = self.date_as_val(auxarrays, units=units, startdate=startdate)


    # Put the auxiliary fields back into the keyword args, to pass them to the parent constructor
    for k,v in auxarrays.iteritems(): kwargs[k] = v
    del auxarrays

    # Call more general init to finalize things, and register the auxiliary fields with Axis
    # Also, pass the 'units' through this interface so it's a known auxiliary attribute
    # (so it's automatically handled in the Axis class for things like subsetting, merging, etc.)
    TAxis.__init__(self, values, units=units, startdate=startdate, **kwargs)
#    TAxis.__init__(self, values, units=units, **kwargs)

    # Add these as direct references in the time axis (not just in auxatts)
    self.units = units
    self.startdate = startdate
  # }}}


  def formatter(self, fmt=None):
  # {{{
    ''' formatter()
        Returns a matplotlib axis Formatter object; by default a FuncFormatter which calls formatvalue(). '''
    from timeticker import TimeFormatter
    return TimeFormatter(self, fmt)
  # }}}

  def locator(self):
  # {{{
    ''' locator() - Returns an AutoCalendarLocator object '''
    from timeticker import AutoCalendarLocator
    return AutoCalendarLocator(self)
  # }}}

  # Comparison
  def __eq__ (self, other):
  # {{{
    import numpy as np
    if self is other: return True
    if type(self) != type(other): return False
    # Different fields?
    if set(self.auxarrays.keys()) != set(other.auxarrays.keys()): return False
    # Different lengths?
    if len(self) != len(other): return False
    assert len(self.auxarrays) > 0, "how is date formed?"
    # Different field values?
    for k,f in self.auxarrays.iteritems():
      if not np.allclose(f,other.auxarrays[k]): return False

    return True
  # }}}

  #TODO: remove this once Axis.map_to is set up to wrap self.common_map??
  def map_to (self, other):
  # {{{
    ''' Define a mapping between this time axis and another one '''
    import numpy as np

    if not type(self) is type(other): return None
    #isinstance(other,Time): return None

    # "self" attributes must be a subset of "other" attributes
    if not set(self.auxarrays.keys()) <= set(other.auxarrays.keys()):
      return None


    # generate search arrays
    self_f, other_f = self.common_fields(other)
    if len(self_f) == 0:
      from warnings import warn
      warn ("Time axis is poorly constructed (no actual time information is available); comparing the 'values' array instead.", stacklevel=3)
      myvalues = self.values
      othervalues = other.values
      nfields = 1
    else:
      myvalues = np.vstack(self_f).transpose()
      othervalues = np.vstack(other_f).transpose()
      nfields = len(self_f)

    indices = np.empty(len(other), 'int32')
    myvalues = np.ascontiguousarray(myvalues, dtype='int32')
    othervalues = np.ascontiguousarray(othervalues, dtype='int32')
    ret = lib.get_indices (nfields, myvalues, len(myvalues),
                           othervalues, len(othervalues),
                           indices)

#    print othervalues, "map_to", myvalues, "=>", indices
    assert ret == 0
    # filter out mismatched values
    indices = indices[indices>=0]
#    # We should have found a match, or something is wrong?
#    assert len(indices) > 0, "failed to map %s to %s"%(self,other)
    # It's ok to not have a match
    return indices
  # }}}


  def common_map (self, other):
# {{{
    '''return the indices that map common elements from one time axis to another'''
    import numpy as np

#    print 'common_map:'
#    print self
#    print other
    assert self.isparentof(other) or other.isparentof(self)

    self_f, other_f = self.common_fields(other)

    assert len(self_f) > 0
    na = len(self)
    nb = len(other)
    # Create the input arrays
    a = np.vstack(self_f).transpose()
    b = np.vstack(other_f).transpose()
    # Get the sort order, with the common fields
    a_ind = _argsort(self_f)
    b_ind = _argsort(other_f)
    # Sort the arrays
    a = np.ascontiguousarray(a[a_ind,:],dtype='int32')
    b = np.ascontiguousarray(b[b_ind,:],dtype='int32')
    # Outputs
    nmap = max(na,nb)
    a_map = np.empty(nmap, 'int32')
    b_map = np.empty(nmap, 'int32')

    # Call the C routine
    nmap = lib.common_map(len(self_f), na, a, nb, b, a_map, b_map)

    # filter out unmapped indices
    a_map = a_map[:nmap]
    b_map = b_map[:nmap]
    # convert the indices from being relative to sort order to the original order
    a_map = a_ind[a_map]
    b_map = b_ind[b_map]
    return a_map, b_map
# }}}

  # Find common fields between two time axes.
  # Returns two lists - a list of arrays for the first axis, and a similar list for the second axis.
  # Only the fields that are common between the two axes are returned.
  # NOTE: does not compare the *values* of the fields, just the field names
  # (use 'common_map' to compare the values)
  def common_fields (self, other):
# {{{
    assert type(self) == type(other), "axes are incompatible: %s %s"%(type(self),type(other))
    assert self.allowed_fields == other.allowed_fields  # should be true if the above is true
    fnames = [f for f in self.allowed_fields if f in self.auxarrays and f in other.auxarrays]
    return [self.auxarrays[f] for f in fnames], [other.auxarrays[f] for f in fnames]
# }}}

  # Mask out certain fields from a time axis
  # resolution: maximum resolution of the output 'day', 'hour', 'year', etc.)
  # exclude: list of fields to remove (i.e. mask out 'year' when making a climatology axis)
  # include: explicit list of fields to include (everything else is excluded)
  def modify (self, resolution=None, exclude=[], include=[], uniquify=False):
    from pygeode import timeutils
    from warnings import warn
    warn ("Deprecated.  Use timeutils module.")
    return timeutils.modify(self, resolution, exclude, include, uniquify)


  # Get a relative time array with the given parameters
  def reltime (self, startdate=None, units=None):
    from pygeode import timeutils
    from warnings import warn
    warn ("Deprecated.  Use timeutils module.")
    return timeutils.reltime(self, startdate, units)

  # Get time increment
  # Units: day, hour, minute, second
  def delta (self, units=None):
    from pygeode import timeutils
    from warnings import warn
    warn ("Deprecated.  Use timeutils module.")
    return timeutils.delta(self, units)

  # Helper function; normalizes date object so that all fields are within the standard range
  def wrapdate(self, dt, allfields=False):
    from pygeode import timeutils
    from warnings import warn
    warn ("Deprecated.  Use timeutils module.")
    return timeutils.wrapdate(self, dt, allfields)

  # Helper function; returns time between two dates in specified units
  def date_diff(self, dt1, dt2, units = None):
    from pygeode import timeutils
    from warnings import warn
    warn ("Deprecated.  Use timeutils module.")
    return timeutils.date_diff(self, dt1, dt2, units)
  
# }}}
del TAxis


# A subclass of time axis which is calendar-aware
# (i.e., has a notion of years, months, days, etc.)
# Any time axis that references years, seconds, etc. is a subclass of this.
class CalendarTime(Time):
# {{{

  # Format of time axis used for str/repr functions
  plotatts = Time.plotatts.copy()
  plotatts['formatstr'] = '$b $d, $Y $H:$M:$S'

  # Regular expression used to parse times
  parse_pattern = '((?P<hour>\d{1,2}):(?P<minute>\d{2})(\s|:(?P<second>\d{2}))|^)(?P<day>\d{1,2}) (?P<month>[a-zA-Z]+) (?P<year>\d+)'

  allowed_fields = ('year', 'month', 'day', 'hour', 'minute', 'second')

  # Conversion factor for going from one unit to another
  unitfactor = {'seconds':1., 'minutes':60., 'hours':3600., 'days':86400.}

  # Overrides init to allow some special construction methods
  def __init__(self, values=None, datefmt=None, units=None, startdate=None, **kwargs):
# {{{
    import timeticker as tt
    import numpy as np
    from warnings import warn

    tg = []
    if 'year' in self.allowed_fields:
      tg.append(tt.YearTickGen(self, [500, 300, 200, 100, 50, 30, 20, 10, 5, 3, 2, 1]))
    if 'year' in self.allowed_fields and 'month' in self.allowed_fields:
      tg.append(tt.MonthTickGen(self, [6, 3, 2, 1]))
    if 'year' in self.allowed_fields and 'month' in self.allowed_fields and 'day' in self.allowed_fields:
      tg.append(tt.DayOfMonthTickGen(self, [15, 10, 5, 3, 2, 1]))
    tg.append(tt.HourTickGen(self, [12, 6, 3, 2, 1]))
    tg.append(tt.MinuteTickGen(self, [30, 15, 10, 5, 3, 2, 1]))
    tg.append(tt.SecondTickGen(self, [30, 15, 10, 5, 3, 2, 1]))
    self.tick_generators = tg

    # Fill in default values for start date
    if startdate is not None:
      default = dict(year=1, month=1, day=1, hour=0, minute=0, second=0)
      # Only use the allowed fields for this (sub)class
      default = dict([k,v] for k,v in default.iteritems() if k in self.allowed_fields)
      startdate = dict(default, **startdate)
      #for k in startdate.iterkeys():
        #assert k in self.allowed_fields, "%s is not an allowed field for %s"%(k,type(self))
      # If any auxiliary arrays are provided, then use only those fields
      if any (a in kwargs for a in self.allowed_fields):
        startdate = dict([k,v] for k,v in startdate.iteritems() if k in kwargs and k in self.allowed_fields)

    # Construct date from encoded values?
    #TODO: more cases, like yyyymmdd.hh?
    if values is not None and datefmt is not None:
      datefmt = datefmt.lower()
      date = np.asarray(values, 'int64')
      # Defaults
      N = len(date)
      one = np.ones(N)
      zero = np.zeros(N)
      default = dict(year=zero,month=one,day=one,hour=zero,minute=zero,second=zero)
      kwargs = dict(default, **kwargs)
      if datefmt == 'yyyymmddhh':
        kwargs['year'], date = divmod(date, 1000000)
        kwargs['month'], date = divmod(date, 10000)
        kwargs['day'], date = divmod(date, 100)
        kwargs['hour'] = date
      elif datefmt == 'yyyymmdd':
        kwargs['year'], date = divmod(date, 10000)
        kwargs['month'], date = divmod(date, 100)
        kwargs['day'] = date
      else: raise Exception ("unrecognized date format '%s'"%datefmt)

    elif values is not None and units is None:
#      raise Exception ("Don't know what units to use for the given values")
      # This can happen during concatenation - mismatched units may be dropped in concat(), so as a workaround, we ignore the values array and hope we have good auxarrays
      warn ("No units available for the given relative values.  Ignoring values array and relying on absolute date fields for initialization.", stacklevel=2)
      values = None

    if units is None:
      warn ("No units given, using default of 'days'", stacklevel=2)
      units = 'days'

    return Time.__init__(self, values=values, units=units, startdate=startdate, **kwargs)
# }}}

  # Day-of-year calculator
  # (for formatvalue)
  def _getdoy (self, date):
# {{{
    startdate = {'month':1,'day':0,'hour':0,'minute':0,'second':0}
    date.pop('year', 0)
    return self.date_as_val (dates=date, startdate=startdate, units='days')
# }}}

  # Number of days in a month
  # Required by timeticker
  def days_in_month(self, yr, mn):
  # {{{
    return self.date_as_val(startdate={'year':yr,'month':mn},
                            dates={'year':yr,'month':mn+1}, units='days')
  # }}}


  def formatvalue (self, val, fmt = None, units=True):
  # {{{
    ''' Returns formatted value where fmt is a strftime-like formatting string. The 
        following codes ($$ will yield the character $):
          $b - short month name
          $B - full month name
          $d - day of the month
          $D - 2-digit day of the month, zero-padded
          $H - hour (24 hr clock)
          $I - hour (12 hr clock)
          $j - day of the year
          $m - month number (Jan=1, ..., Dec=12)
          $M - minute
          $p - am/pm
          $P - AM/PM
          $S - second
          $y - 2 digit year
          $a - 4 digit year
          $Y - full year; if less than 100, preceeded by 'y'
          $v - value formatted with %d
          $V - value formatted with str()
     '''
    import numpy as np
    from string import Template

    dt = self.val_as_date(val)

    subs = {}

    # Build substitution dictionary
    if dt.has_key('year'):
      y = dt['year']
      subs['y'] = '%02d' % (y % 100)
      subs['a'] = '%d' % y
      if abs(y) < 100:
        subs['Y'] = 'y%d' % y
      else:
        subs['Y'] = '%d' % y
    else:
      subs['y'], subs['Y'] = '', ''

    if dt.has_key('month'):
      mi = dt['month']
      subs['b'] = months[mi]
      subs['B'] = months_full[mi]
      subs['m'] = mi
    else:
      mi = 0
      subs['b'], subs['B'], subs['m'] = '', '', ''
    
    if dt.has_key('day'):
      d = dt['day']
      subs['d'] = '%d' % d
      subs['D'] = '%02d' % d
      if dt.has_key('year') and 'year' in self.allowed_fields: subs['j'] = self._getdoy(dt)
    else:
      subs['d'], subs['D'], subs['j'] = '', '', ''

    if dt.has_key('hour'):
      h = dt['hour']
      subs['H'] = '%02d' % h
      subs['I'] = '%02d' % ((h - 1) % 12 + 1)
      subs['p'] = ['am', 'pm'][h / 12]
      subs['P'] = ['AM', 'PM'][h / 12]
    else:
      subs['H'], subs['I'], subs['p'], subs['P'] = '', '', '', ''

    if dt.has_key('minute'):
      M = dt['minute']
      subs['M'] = '%02d' % M
    else:
      subs['M'] = ''

    if dt.has_key('second'):
      s = dt['second']
      subs['S'] = '%02d' % s
    else:
      subs['S'] = ''

    subs['v'] = '%d' % val
    subs['V'] = str(val)

    if fmt is None:
      fmt = self.plotatts['formatstr']

    #print Template(fmt).substitute(subs)
    return Template(fmt).substitute(subs)
  # }}}

  # Simple little text output.
  # Should *not* depend on plot attributes (i.e. plotatts['formatstr'])
  def _val2str (self, val):
    s = ''
    dt = self.val_as_date (val)
    if 'month' in dt:
      s += months_full[dt['month']]
    if 'day' in dt:
      if len(s) == 0: s = 'day'
      s += ' '
      s += str(dt['day'])
    if 'year' in dt:
      if len(s) > 0: s += ', '
      s += str(dt['year'])
    if 'hour' in dt:
      hour = dt['hour']
      minute = dt.get('minute',0)
      second = dt.get('second',0)
      if len(s) > 0: s += ' '
      s += '%02d:%02d:%02d'%(hour,minute,second)
    return s

  def str_as_val(self, key, s):
# {{{
    ''' str_as_val() - interprets string s as a date and converts it to a value appropriate
            to this time axis. For now assumes a string in the form 
                '12 Dec 2008' or 
                '06:00:00 1 Jan 1979'.'''
    import re
    res = re.search(self.parse_pattern, s)
    if res is None:
      raise Exception('String "%s" not recognized as a time')

    d = {}
    for k, v in res.groupdict().iteritems():
      if k in ['hour', 'minute', 'second', 'day', 'year']:
        if v is not None: d[k] = int(v) 
      elif k == 'month':
        lmonths = [m.lower() for m in months]
        d[k] = lmonths.index(v.lower())

    return self.date_as_val(d)
# }}}

  # Convert a date dictionary to a tuple - fill in missing fields with defaults
  @staticmethod
  def _get_dates (dates, use_arrays = None):
# {{{
    import numpy as np

    if use_arrays is None: use_arrays = any(hasattr(d,'__len__') for d in dates.itervalues())

    if use_arrays:
      assert all(hasattr(d,'__len__') for d in dates.itervalues())
      n = set(len(d) for d in dates.itervalues())
      assert len(n) == 1, 'inconsistent array lengths'
      n = n.pop()
      zeros = np.zeros(n, 'int32') if use_arrays else 0
      ones = np.ones(n, 'int32') if use_arrays else 1
    else:
      assert all([(hasattr(d,'__len__') and len(d) == 1) or \
        not hasattr(d, '__len__') for d in dates.itervalues()])
      zeros = 0
      ones = 1

    year = dates.get('year', zeros)
    month = dates.get('month', ones)
    day = dates.get('day', ones)
    hour = dates.get('hour', zeros)
    minute = dates.get('minute', zeros)
    second = dates.get('second', zeros)

    if not use_arrays:
      # Fuck you, numpy scalars!
      year, month, day = int(year), int(month), int(day)
      hour, minute, second = int(hour), int(minute), int(second)

    return year, month, day, hour, minute, second
# }}}


  # Convert a relative time array to an absolute time
  # Dictionary of years, months, etc. from a relative time axis
  def val_as_date (self, vals = None, startdate = None, units = None, allfields=False):
  # {{{
    import numpy as np

    if vals is None: vals = self.values
    if startdate is None: startdate = self.startdate
    if units is None: units = self.units

    iyear, imonth, iday, ihour, iminute, isecond = self._get_dates(startdate)

    values = np.ascontiguousarray(np.round(vals * self.unitfactor[units]), dtype='int64')
    n = len(values)
    year   = np.empty(n, dtype='i')
    month  = np.empty(n, dtype='i')
    day    = np.empty(n, dtype='i')
    hour   = np.empty(n, dtype='i')
    minute = np.empty(n, dtype='i')
    second = np.empty(n, dtype='i')

    self._val_as_date (n, iyear, imonth, iday, ihour, iminute, isecond,
                        values,
                        year, month, day,
                        hour, minute, second)

    date = {'year':year, 'month':month, 'day':day, 'hour':hour, 'minute':minute, 'second':second}
    if not allfields:
      # Remove fields that weren't explicitly provided?
      date = dict([k,v] for k,v in date.iteritems() if k in startdate)
    if not hasattr(vals, '__len__'):
      date = dict([k,v[0]] for k,v in date.iteritems())
    return date
  # }}}

  # Convert an absolute time to a relative time
  def date_as_val (self, dates = None, startdate = None, units = None):
  # {{{
    import numpy as np

    if dates is None: dates = self.auxarrays
    if startdate is None: startdate = self.startdate
    if units is None: units = self.units

    iyear, imonth, iday, ihour, iminute, isecond = self._get_dates(startdate, use_arrays = False)
    year, month, day, hour, minute, second = self._get_dates(dates)
    year   = np.ascontiguousarray(year,   dtype='int32')
    month  = np.ascontiguousarray(month,  dtype='int32')
    day    = np.ascontiguousarray(day,    dtype='int32')
    hour   = np.ascontiguousarray(hour,   dtype='int32')
    minute = np.ascontiguousarray(minute, dtype='int32')
    second = np.ascontiguousarray(second, dtype='int32')

    n = len(year)
    vals = np.empty(n, dtype='int64')

    ret = self._date_as_val (n, iyear, imonth, iday, ihour, iminute, isecond,
                        year, month, day,
                        hour, minute, second,
                        vals)

    assert ret == 0

    # Were we passed a single date?  If so, return a scalar
    if not hasattr(dates.values()[0], '__len__'): vals = vals[0]
    return vals / self.unitfactor[units]
  # }}}

# }}}




# Specific calendars follow:

#NOTE: majority of calendar manipulation has been moved to a C interface (timeaxis.c)

# Standard time (with leap years)
class StandardTime(CalendarTime):
# {{{ 

  _val_as_date = lib.val_as_date_std
  _date_as_val = lib.date_as_val_std

# }}}

# Model time (365-day calendar)
class ModelTime365(CalendarTime):
# {{{

  _date_as_val = lib.date_as_val_365
  _val_as_date = lib.val_as_date_365

# }}} 

# Model time (360-day calendar)
class ModelTime360(CalendarTime):
# {{{

  _date_as_val = lib.date_as_val_360
  _val_as_date = lib.val_as_date_360

# }}} 

# Seasonal time axis
# (only has 'syear' and 'season' auxiliary arrays)
#TODO: add this to cfmeta package, so seasonal data can be saved/loaded
def makeSeasonalAxis(Base):
# {{{
  class SeasonalTime(Base):
    import numpy as np
    allowed_fields = ('year','season')

    # For now seasonal definitions are hard coded
    nseasons = 4
    seasons = ['DJF', 'MAM', 'JJA', 'SON']
    season_boundaries = [(-30,60),(60,152),(152,244),(244,335)]
    cdates = {'dyear':np.array([0, 0, 0, 0]), 
              'month':np.array([1,4,7,10]), 
              'day':np.array([16, 15, 16, 16])}
    plotatts = Base.plotatts.copy()
    plotatts['formatstr'] = '$s $y'

    # Generate year and season array
    # Note: year gets fudged for Decembers, to keep the seasons together
    # Convention: December 2006 -> DJF 2007
    def _get_seasons (self, dates):
  # {{{
      import numpy as np
      year, month, day, hour, minute, second = Base._get_dates(dates)
      doy = Base._getdoy(self, dates)         # Base season on day of the year (no support for leap years(!))

      if hasattr(year, '__len__'):
        season = np.zeros(len(year), 'i')
        for i, s in enumerate(self.season_boundaries):
          mplus = (s[0] <= doy - 365) & (doy - 365 < s[1])
          m = (s[0] <= doy) & (doy < s[1])
          mminus = (s[0] <= doy + 365) & (doy + 365 < s[1])
          year[mplus] += 1
          year[mminus] -= 1
          season[mplus | m | mminus] = i + 1
      else:
        for i, s in enumerate(self.season_boundaries):
          if s[0] <= doy - 365 < s[1]: year += 1; season = i + 1
          elif s[0] <= doy < s[1]: season = i + 1
          elif s[0] <= doy + 365 < s[1]: year -= 1; season = i + 1

      return {'year':year, 'season':season}
  # }}}

    def _get_cdates(self, dates):
  # {{{
      ''' _get_cdates(self, dates): returns central calendar dates of the seasonal dates given in the 
          dictionary of dates.'''
      import numpy as np

      use_arrays = any(hasattr(d,'__len__') for d in dates.itervalues())
      if use_arrays:
        assert all(hasattr(d,'__len__') for d in dates.itervalues())
        n = set(len(d) for d in dates.itervalues())
        assert len(n) == 1, 'inconsistent array lengths'
        n = n.pop()
        zeros = np.zeros(n, 'int32') 
        ones = np.ones(n, 'int32')
      else:
        zeros = 0
        ones = 1

      year = dates.get('year', zeros)
      season = dates.get('season', ones)
      year += (season - 1) / self.nseasons
      season = (season - 1) % self.nseasons

      year += self.cdates['dyear'][season]
      month = self.cdates['month'][season]
      day = self.cdates['day'][season]

      return {'year':year, 'month':month, 'day':day, 'hour':zeros, 'minute':zeros, 'second':zeros}
  # }}}

    def __init__ (self, values=None, units=None, startdate=None, **kwargs):
    # {{{
      import timeticker as tt
      tg=[]
      if 'year' in self.allowed_fields:
        tg.append(tt.YearTickGen(self, [500, 300, 200, 100, 50, 30, 20, 10, 5, 3, 2, 1]))
      tg.append(tt.SeasonTickGen(self, [2, 1]))
      self.tick_generators = tg

      # Fill in default values for start date; this works slightly differently than for CalendarTime
      if startdate is not None:
        default = dict(year=1, month=1, day=1, hour=0, minute=0, second=0)
        startdate = dict(default, **startdate)
        if 'season' in kwargs and 'year' not in kwargs: startdate.pop('year', 0)

      # Use days as default units
      if units is None: units = 'days'

      Time.__init__(self, values=values, startdate=startdate, units=units, **kwargs)

      # Check for the presence of auxarrays that aren't in allowed fields
      for k in self.auxarrays.iterkeys():
        assert k in self.allowed_fields, "%s is not an allowed field for %s"%(k,type(self))
    # }}}

    def formatvalue (self, val, fmt = None, units=True):
    # {{{
      ''' Returns formatted value where fmt is a strftime-like formatting string. The 
          following codes ($$ will yield the character $):
            $s - season name
            $y - 2 digit year
            $Y - 4 digit year
            $v - value formatted with %d
            $V - value formatted with str()
       '''
      import numpy as np
      from string import Template

      dt = self.val_as_date(val)

      subs = {}

      # Build substitution dictionary
      if dt.has_key('year'):
        y = dt['year']
        subs['y'] = '%02d' % (y % 100)
        subs['Y'] = '%d' % y
      else:
        subs['y'], subs['Y'] = '', ''

      if dt.has_key('season'):
        s = dt['season']
        subs['s'] = self.seasons[s-1]
      else:
        s = 0
        subs['s'] = ''

      subs['v'] = '%d' % val
      subs['V'] = str(val)

      if fmt is None:
        fmt = self.plotatts['formatstr']

      #print Template(fmt).substitute(subs)
      return Template(fmt).substitute(subs)
    # }}}

    def val_as_date (self, vals = None, startdate = None, units = None, allfields=False):
    # {{{
      if vals is None: vals = self.values
      if startdate is None: startdate = self.startdate
      date = Base.val_as_date(self, vals, startdate, units, allfields)
      date = self._get_seasons(date)
      # Remove year field if not explicitly provided
      if not allfields and 'year' not in startdate: date.pop('year', 0)
      return date
    # }}}

    def date_as_val (self, dates = None, startdate = None, units = None):
    # {{{
      if dates is None: dates = self.auxarrays
      if startdate is None: startdate = self.startdate
      
      if 'season' in dates.keys(): dates = self._get_cdates(dates)

      return Base.date_as_val(self, dates, startdate, units)
    # }}}

  SeasonalTime.__name__ = 'Seasonal'+Base.__name__
  return SeasonalTime
  # }}}

SeasonalStandardTime = makeSeasonalAxis(StandardTime)
SeasonalModelTime365 = makeSeasonalAxis(ModelTime365)

SeasonalTAxes = {StandardTime:SeasonalStandardTime,
                  ModelTime365:SeasonalModelTime365}

# Yearless calendar
# Kludges the CalendarTime axis so it has no years or months, just a running count of days
class Yearless(CalendarTime):
# {{{

  # Format of time axis used for str/repr functions
  plotatts = CalendarTime.plotatts.copy()
  plotatts['plotfmt'] = '$d'
  plotatts['formatstr'] = 'day $d, $H:$M:$S' 

  allowed_fields = ('day', 'hour', 'minute', 'second')

  _date_as_val = lib.date_as_val_yearless
  _val_as_date = lib.val_as_date_yearless

  # Day-of-year calculator
  # (for formatvalue)
  def _getdoy (self, date):
# {{{
    raise Exception("ain't got no years!")
#    return "<doy??>"
# }}}

  # Number of days in a month
  # Required by timeticker
  def days_in_month(self, yr, mn):
  # {{{
    raise Exception("ain't got no months!")
#    return "<days_in_month??>"
  # }}}

  def __init__ (self, *args, **kwargs):
    import timeticker as tt
    CalendarTime.__init__(self, *args, **kwargs)
    tg = []
    tg.append(tt.DayTickGen(self, [10000, 5000, 3000, 2000, 1000, 500, 300, 200, 100, 50, 30, 10, 5, 3, 2, 1]))
    tg.append(tt.HourTickGen(self, [12, 6, 3, 2, 1]))
    tg.append(tt.MinuteTickGen(self, [30, 15, 10, 5, 3, 2, 1]))
    tg.append(tt.SecondTickGen(self, [30, 15, 10, 5, 3, 2, 1]))
    self.tick_generators = tg

