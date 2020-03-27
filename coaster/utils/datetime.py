# -*- coding: utf-8 -*-

"""
Date, time and timezone utilities
---------------------------------
"""

from __future__ import absolute_import
import six

from datetime import datetime

from aniso8601 import parse_datetime, parse_duration
from aniso8601.exceptions import ISOFormatError as ParseError
import isoweek
import pytz

__all__ = [
    'utcnow',
    'parse_isoformat',
    'parse_duration',
    'isoweek_datetime',
    'midnight_to_utc',
    'sorted_timezones',
    'ParseError',
]

# --- Thread safety fix -------------------------------------------------------

# Force import of strptime. This was previously used in :func:`parse_isoformat`,
# but we have left this in because it could break elsewhere.
# https://stackoverflow.com/q/16309650/78903
datetime.strptime('20160816', '%Y%m%d')


def utcnow():
    """
    Returns the current time at UTC with `tzinfo` set
    """
    return datetime.now(pytz.UTC)


def parse_isoformat(text, naive=True, delimiter='T'):
    """
    Attempts to parse an ISO 8601 timestamp as generated by
    `datetime.isoformat()`. Timestamps without a timezone are assumed to be at
    UTC. Raises :exc:`ParseError` if the timestamp cannot be parsed.

    :param bool naive: If `True`, strips timezone and returns datetime at UTC.
    """
    if naive:
        return parse_datetime(text, delimiter).astimezone(pytz.UTC).replace(tzinfo=None)
    else:
        return parse_datetime(text, delimiter)


def isoweek_datetime(year, week, timezone='UTC', naive=False):
    """
    Returns a datetime matching the starting point of a specified ISO week
    in the specified timezone (default UTC). Returns a naive datetime in
    UTC if requested (default False).

    >>> isoweek_datetime(2017, 1)
    datetime.datetime(2017, 1, 2, 0, 0, tzinfo=<UTC>)
    >>> isoweek_datetime(2017, 1, 'Asia/Kolkata')
    datetime.datetime(2017, 1, 1, 18, 30, tzinfo=<UTC>)
    >>> isoweek_datetime(2017, 1, 'Asia/Kolkata', naive=True)
    datetime.datetime(2017, 1, 1, 18, 30)
    >>> isoweek_datetime(2008, 1, 'Asia/Kolkata')
    datetime.datetime(2007, 12, 30, 18, 30, tzinfo=<UTC>)
    """
    naivedt = datetime.combine(isoweek.Week(year, week).day(0), datetime.min.time())
    if isinstance(timezone, six.string_types):
        tz = pytz.timezone(timezone)
    else:
        tz = timezone
    dt = tz.localize(naivedt).astimezone(pytz.UTC)
    if naive:
        return dt.replace(tzinfo=None)
    else:
        return dt


def midnight_to_utc(dt, timezone=None, naive=False):
    """
    Returns a UTC datetime matching the midnight for the given date or datetime.

    >>> from datetime import date
    >>> midnight_to_utc(datetime(2017, 1, 1))
    datetime.datetime(2017, 1, 1, 0, 0, tzinfo=<UTC>)
    >>> midnight_to_utc(pytz.timezone('Asia/Kolkata').localize(datetime(2017, 1, 1)))
    datetime.datetime(2016, 12, 31, 18, 30, tzinfo=<UTC>)
    >>> midnight_to_utc(datetime(2017, 1, 1), naive=True)
    datetime.datetime(2017, 1, 1, 0, 0)
    >>> midnight_to_utc(pytz.timezone('Asia/Kolkata').localize(datetime(2017, 1, 1)),
    ...   naive=True)
    datetime.datetime(2016, 12, 31, 18, 30)
    >>> midnight_to_utc(date(2017, 1, 1))
    datetime.datetime(2017, 1, 1, 0, 0, tzinfo=<UTC>)
    >>> midnight_to_utc(date(2017, 1, 1), naive=True)
    datetime.datetime(2017, 1, 1, 0, 0)
    >>> midnight_to_utc(date(2017, 1, 1), timezone='Asia/Kolkata')
    datetime.datetime(2016, 12, 31, 18, 30, tzinfo=<UTC>)
    >>> midnight_to_utc(datetime(2017, 1, 1), timezone='Asia/Kolkata')
    datetime.datetime(2016, 12, 31, 18, 30, tzinfo=<UTC>)
    >>> midnight_to_utc(pytz.timezone('Asia/Kolkata').localize(datetime(2017, 1, 1)),
    ...   timezone='UTC')
    datetime.datetime(2017, 1, 1, 0, 0, tzinfo=<UTC>)
    """
    if timezone:
        if isinstance(timezone, six.string_types):
            tz = pytz.timezone(timezone)
        else:
            tz = timezone
    elif isinstance(dt, datetime) and dt.tzinfo:
        tz = dt.tzinfo
    else:
        tz = pytz.UTC

    utc_dt = tz.localize(datetime.combine(dt, datetime.min.time())).astimezone(pytz.UTC)
    if naive:
        return utc_dt.replace(tzinfo=None)
    return utc_dt


def sorted_timezones():
    """
    Return a list of timezones sorted by offset from UTC.
    """

    def hourmin(delta):
        if delta.days < 0:
            hours, remaining = divmod(86400 - delta.seconds, 3600)
        else:
            hours, remaining = divmod(delta.seconds, 3600)
        minutes, remaining = divmod(remaining, 60)
        return hours, minutes

    now = datetime.utcnow()
    # Make a list of country code mappings
    timezone_country = {}
    for countrycode in pytz.country_timezones:
        for timezone in pytz.country_timezones[countrycode]:
            timezone_country[timezone] = countrycode

    # Make a list of timezones, discarding the US/* and Canada/* zones since they aren't
    # reliable for DST, and discarding UTC and GMT since timezones in that zone have
    # their own names
    timezones = [
        (pytz.timezone(tzname).utcoffset(now, is_dst=False), tzname)
        for tzname in pytz.common_timezones
        if not tzname.startswith('US/')
        and not tzname.startswith('Canada/')
        and tzname not in ('GMT', 'UTC')
    ]
    # Sort timezones by offset from UTC and their human-readable name
    presorted = [
        (
            delta,
            '%s%s - %s%s (%s)'
            % (
                (delta.days < 0 and '-')
                or (delta.days == 0 and delta.seconds == 0 and ' ')
                or '+',
                '%02d:%02d' % hourmin(delta),
                (pytz.country_names[timezone_country[name]] + ': ')
                if name in timezone_country
                else '',
                name.replace('_', ' '),
                pytz.timezone(name).tzname(now, is_dst=False),
            ),
            name,
        )
        for delta, name in timezones
    ]
    presorted.sort()
    # Return a list of (timezone, label) with the timezone offset included in the label.
    return [(name, label) for (delta, label, name) in presorted]
