import datetime
import re
import time
import typing

PRETTY_SHORT_FORMAT: str = '%Y-%m-%d %H:%M'
"""
The format string for a pretty timestamp.
See: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

DEFAULT_EMBEDDED_PATTERN: str = r'<timestamp:(-?\d+|nil)>'
""" A regex for matching an embedded timestamp. """

UTC: datetime.timezone = datetime.timezone.utc
""" A shortcut for the UTC timezone. """

UNIXTIME_THRESHOLD_SECS: int = int(1e10)
""" Epoch time guessing threshold for seconds. """

UNIXTIME_THRESHOLD_MSECS: int = int(1e13)
""" Epoch time guessing threshold for milliseconds. """

UNIXTIME_THRESHOLD_USECS: int = int(1e16)
""" Epoch time guessing threshold for nanoseconds. """

class Duration(int):
    """
    A Duration represents some length in time in milliseconds.
    """

    def to_secs(self) -> float:
        """ Convert the duration to float seconds. """

        return self / 1000.0

    def to_msecs(self) -> int:
        """ Convert the duration to integer milliseconds. """

        return self

class Timestamp(int):
    """
    A Timestamp represent a moment in time (sometimes called "datetimes").
    Timestamps are internally represented by the number of milliseconds since the
    (Unix Epoch)[https://en.wikipedia.org/wiki/Unix_time].
    This is sometimes referred to as "Unix Time".
    Since Unix Time is in UTC, timestamps do not need to carry timestamp information with them.

    Note that timestamps are just integers with some decoration,
    so they respond to all normal int functionality.
    """

    def sub(self, other: 'Timestamp') -> Duration:
        """ Return a new duration that is the difference of this and the given duration. """

        return Duration(self - other)

    def to_pytime(self, timezone: typing.Union[datetime.timezone, None] = None) -> datetime.datetime:
        """ Convert this timestamp to a Python datetime in the given timezone (local by default). """

        if (timezone is None):
            timezone = get_local_timezone()

        return datetime.datetime.fromtimestamp(self / 1000, timezone)

    def to_local_pytime(self) -> datetime.datetime:
        """ Convert this timestamp to a Python datetime in the system timezone. """

        return self.to_pytime(timezone = get_local_timezone())

    def pretty(self, short: bool = False, timezone: typing.Union[datetime.timezone, None] = None) -> str:
        """
        Get a "pretty" string representation of this timestamp.
        There is no guarantee that this representation can be parsed back to its original form.

        If no timezone is provided, the system's local timezone will be used.
        """

        if (timezone is None):
            timezone = get_local_timezone()

        pytime = self.to_pytime(timezone = timezone)

        if (short):
            return pytime.strftime(PRETTY_SHORT_FORMAT)

        return pytime.isoformat(timespec = 'milliseconds')

    @staticmethod
    def from_pytime(pytime: datetime.datetime) -> 'Timestamp':
        """ Convert a Python datetime to a timestamp. """

        return Timestamp(int(pytime.timestamp() * 1000))

    @staticmethod
    def now() -> 'Timestamp':
        """ Get a Timestamp that represents the current moment. """

        return Timestamp(time.time() * 1000)

    @staticmethod
    def convert_embedded(
            text: str,
            embedded_pattern: str = DEFAULT_EMBEDDED_PATTERN,
            pretty: bool = False,
            short: bool = True,
            timezone: typing.Union[datetime.timezone, None] = None,
            ) -> str:
        """
        Look for any timestamps embedded in the text and replace them.
        """

        while True:
            match = re.search(embedded_pattern, text)
            if (match is None):
                break

            initial_text = match.group(0)
            timestamp_text = match.group(1)

            timestamp = Timestamp()
            if (timestamp_text != 'nil'):
                timestamp = Timestamp(int(timestamp_text))

            replacement_text = str(timestamp)
            if (pretty):
                replacement_text = timestamp.pretty(short = short, timezone = timezone)

            text = text.replace(initial_text, replacement_text)

        return text

    @staticmethod
    def guess(value: typing.Any) -> 'Timestamp':
        """
        Try to parse a timestamp out of a value.
        Empty values will get zero timestamps.
        Purely digit strings will be converted to ints and treated as UNIX times.
        Floats will be considered UNIX epoch seconds and converted to milliseconds.
        Other strings will be attempted to be parsed with datetime.fromisoformat().
        """

        raw_value = value

        # Empty timestamp.
        if (value is None):
            return Timestamp(0)

        # Check for already parsed timestamps.
        if (isinstance(value, Timestamp)):
            return value

        # Floats are assumed to be epoch seconds.
        if (isinstance(value, float)):
            value = int(1000 * value)

        # At this point, we only want to be dealing with strings or ints.
        if (not isinstance(value, (int, str))):
            value = str(value)

        # Check for string specifics.
        if (isinstance(value, str)):
            # Check for empty strings.
            value = value.strip()
            if (len(value) == 0):
                return Timestamp(0)

            # Check for digit or float strings.
            if (re.match(r'^\d+\.\d+$', value) is not None):
                value = int(1000 * float(value))
            elif (re.match(r'^\d+$', value) is not None):
                value = int(value)

        if (isinstance(value, int)):
		    # Use reasonable thresholds to guess the units of the value (sec, msec, usec, nsec).
            if (value < UNIXTIME_THRESHOLD_SECS):
                # Time is in seconds.
                return Timestamp(value * 1000)
            elif (value < UNIXTIME_THRESHOLD_MSECS):
                # Time is in milliseconds.
                return Timestamp(value)
            elif (value < UNIXTIME_THRESHOLD_USECS):
                # Time is in microseconds.
                return Timestamp(value / 1000)
            else:
                # Time is in nanoseconds.
                return Timestamp(value / 1000 / 1000)

        # Try to convert from an ISO string.

        # Parse out some cases that Python <= 3.10 cannot deal with.
        # This will remove fractional seconds.
        value = re.sub(r'Z$', '+00:00', value)
        value = re.sub(r'(\d\d:\d\d)(\.\d+)', r'\1', value)

        try:
            value = datetime.datetime.fromisoformat(value)
        except Exception as ex:
            raise ValueError(f"Failed to parse timestamp string '{raw_value}'.") from ex

        return Timestamp.from_pytime(value)

def get_local_timezone() -> datetime.timezone:
    """ Get the local (system) timezone or raise an exception. """

    local_timezone = datetime.datetime.now().astimezone().tzinfo
    if ((local_timezone is None) or (not isinstance(local_timezone, datetime.timezone))):
        raise ValueError("Could not discover local timezone.")

    return local_timezone
