import time
import datetime

import edq.testing.unittest
import edq.util.time

TIMEZONE_UTC: datetime.timezone = datetime.timezone.utc
TIMEZONE_PST: datetime.timezone = datetime.timezone(datetime.timedelta(hours = -7), name = 'PST')
TIMEZONE_CEST: datetime.timezone = datetime.timezone(datetime.timedelta(hours = 2), name = 'CEST')

class TestTime(edq.testing.unittest.BaseTest):
    """ Test time-based operations. """

    def test_timestamp_now(self):
        """ Test getting a timestamp for the current moment. """

        start = edq.util.time.Timestamp.now()
        time.sleep(0.01)
        middle = edq.util.time.Timestamp.now()
        time.sleep(0.01)
        end = edq.util.time.Timestamp.now()

        self.assertLessEqual(start, middle)
        self.assertLessEqual(middle, end)

    def test_timestamp_pytime_conversion(self):
        """ Test converting between timestamps and Python datetimes. """

        # [(timestamp, python time), ...]
        test_cases = [
            (edq.util.time.Timestamp(0), datetime.datetime(1970, 1, 1, 0, 0, 0, 0, TIMEZONE_UTC)),

            (edq.util.time.Timestamp(1755139534019), datetime.datetime(2025, 8, 14, 2,  45, 34, 19000, TIMEZONE_UTC)),
            (edq.util.time.Timestamp(1755139534019), datetime.datetime(2025, 8, 13, 19, 45, 34, 19000, TIMEZONE_PST)),
            (edq.util.time.Timestamp(1755139534019), datetime.datetime(2025, 8, 14, 4,  45, 34, 19000, TIMEZONE_CEST)),
        ]

        for (i, test_case) in enumerate(test_cases):
            (timestamp, pytime) = test_case

            with self.subTest(msg = f"Case {i} ('{timestamp}' == '{pytime}'):"):
                convert_pytime = timestamp.to_pytime(pytime.tzinfo)
                self.assertEqual(pytime, convert_pytime, 'pytime')

                convert_timestamp = edq.util.time.Timestamp.from_pytime(pytime)
                self.assertEqual(timestamp, convert_timestamp, 'timestamp')

                # Check other time zones.
                # Use string comparisons to ensure the timezone is compared (and not just the UTC time).
                timezones = [
                    TIMEZONE_UTC,
                    TIMEZONE_PST,
                    TIMEZONE_CEST,
                ]

                for timezone in timezones:
                    pytime_pst = pytime.astimezone(timezone).isoformat(timespec = 'milliseconds')
                    convert_pytime_pst = timestamp.to_pytime(timezone).isoformat(timespec = 'milliseconds')
                    self.assertEqual(pytime_pst, convert_pytime_pst, f"pytime {timezone}")

    def test_timestamp_pretty(self):
        """ Test the "pretty" representations of timestamps. """

        # [(timestamp, timezone, pretty short, pretty long), ...]
        test_cases = [
            (edq.util.time.Timestamp(0), TIMEZONE_UTC, "1970-01-01 00:00", "1970-01-01T00:00:00.000+00:00"),

            (edq.util.time.Timestamp(1755139534019), TIMEZONE_UTC,  "2025-08-14 02:45", "2025-08-14T02:45:34.019+00:00"),
            (edq.util.time.Timestamp(1755139534019), TIMEZONE_PST,  "2025-08-13 19:45", "2025-08-13T19:45:34.019-07:00"),
            (edq.util.time.Timestamp(1755139534019), TIMEZONE_CEST, "2025-08-14 04:45", "2025-08-14T04:45:34.019+02:00"),
        ]

        for (i, test_case) in enumerate(test_cases):
            (timestamp, timezone, expected_pretty_short, expected_pretty_long) = test_case

            with self.subTest(msg = f"Case {i} ('{timestamp}'):"):
                actual_pretty_short = timestamp.pretty(short = True, timezone = timezone)
                actual_pretty_long = timestamp.pretty(short = False, timezone = timezone)

                self.assertEqual(expected_pretty_short, actual_pretty_short, 'short')
                self.assertEqual(expected_pretty_long, actual_pretty_long, 'long')

    def test_timestamp_sub(self):
        """ Test subtracting timestamps. """

        # [(a, b, expected), ...]
        # All values in this structure will be in ints and converted later.
        test_cases = [
            (0, 0, 0),
            (0, 1, -1),
            (1, 0, 1),

            (100, 100, 0),
            (100, 101, -1),
            (101, 100, 1),
        ]

        for (i, test_case) in enumerate(test_cases):
            (raw_a, raw_b, raw_expected) = test_case

            with self.subTest(msg = f"Case {i} ({raw_a} - {raw_b}):"):
                a = edq.util.time.Timestamp(raw_a)
                b = edq.util.time.Timestamp(raw_b)
                expected = edq.util.time.Duration(raw_expected)

                actual = a - b
                self.assertEqual(expected, actual)

    def test_timestamp_embedded(self):
        """
        Test pulling timestamps out of messages.
        """

        # [(input, expected, timezone), ...]
        test_cases = [
            (
                "Some <timestamp:0> timestamp.",
                "Some 1970-01-01 00:00 timestamp.",
                edq.util.time.UTC,
            ),
            (
                "Some <timestamp:1695873620000> timestamp.",
                "Some 2023-09-28 04:00 timestamp.",
                edq.util.time.UTC,
            ),
            (
                "Some <timestamp:1695873620000> timestamp.",
                "Some 2023-09-28 03:00 timestamp.",
                datetime.timezone(datetime.timedelta(hours = -1)),
            ),
            (
                "No timestamp here.",
                "No timestamp here.",
                edq.util.time.UTC,
            ),
            (
                "Some <timestamp:nil> timestamp.",
                "Some 1970-01-01 00:00 timestamp.",
                edq.util.time.UTC,
            ),
            (
                "Some <timestamp:-60000> timestamp.",
                "Some 1969-12-31 23:59 timestamp.",
                edq.util.time.UTC,
            ),
            (
                "Some <timestamp:-60001> timestamp.",
                "Some 1969-12-31 23:58 timestamp.",
                edq.util.time.UTC,
            ),
            (
                "Timestamp one <timestamp:0> and two <timestamp:-60000>.",
                "Timestamp one 1970-01-01 00:00 and two 1969-12-31 23:59.",
                edq.util.time.UTC,
            ),
            (
                "Timestamp one <timestamp:0> and two <timestamp:0>.",
                "Timestamp one 1970-01-01 00:00 and two 1970-01-01 00:00.",
                edq.util.time.UTC,
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (text, expected, timezone) = test_case

            with self.subTest(msg = f"Case {i} ('text')"):
                actual = edq.util.time.Timestamp.convert_embedded(text, pretty = True, timezone = timezone)
                self.assertEqual(expected, actual)

    def test_timestamp_guess(self):
        """ Test guessing timestamps from values. """

        # [(value, expected), ...]
        test_cases = [
            # Empty
            (None, edq.util.time.Timestamp(0)),
            ('', edq.util.time.Timestamp(0)),

            # Self
            (edq.util.time.Timestamp(123), edq.util.time.Timestamp(123)),

            # Int
            (0, edq.util.time.Timestamp(0)),
            (123, edq.util.time.Timestamp(123000)),  # Secs
            (1230000000, edq.util.time.Timestamp(1230000000000)),  # Secs
            (1230000000000, edq.util.time.Timestamp(1230000000000)),  # MSecs
            (1230000000000000, edq.util.time.Timestamp(1230000000000)),  # USecs
            (1230000000000000000, edq.util.time.Timestamp(1230000000000)),  # NSecs
            ('1230000000', edq.util.time.Timestamp(1230000000000)),

            # Float
            (1230000000.0, edq.util.time.Timestamp(1230000000000)),
            ('1230000000.0', edq.util.time.Timestamp(1230000000000)),

            # String
            ('2023-09-28T04:00:20Z', edq.util.time.Timestamp(1695873620000)),
            ('2023-09-28T04:00:20+00:00', edq.util.time.Timestamp(1695873620000)),
            ('2023-09-28T13:10:44+00:00', edq.util.time.Timestamp(1695906644000)),
            ('2023-09-28T04:00:20.683684Z', edq.util.time.Timestamp(1695873620000)),
            ('2023-09-28T04:00:20.683684+00:00', edq.util.time.Timestamp(1695873620000)),
            ('2023-09-28T13:10:44.432050+00:00', edq.util.time.Timestamp(1695906644000)),
            ('2023-09-28T13:10:44.43205+00:00', edq.util.time.Timestamp(1695906644000)),
        ]

        for (i, test_case) in enumerate(test_cases):
            (value, expected) = test_case

            with self.subTest(msg = f"Case {i} ('{value}'):"):
                actual = edq.util.time.Timestamp.guess(value)
                self.assertEqual(expected, actual)
