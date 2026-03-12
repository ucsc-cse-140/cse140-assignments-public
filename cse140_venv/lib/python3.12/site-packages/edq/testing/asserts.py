"""
More complex testing assertions.
Often used as output checks in CLI tests.
"""

import re
import typing

import edq.testing.unittest

TRACEBACK_LINE_REGEX: str = r'^\s*File "[^"]+", line \d+,.*$\n.*$(\n\s*[\^~]+\s*$)?'
TRACEBACK_LINE_REPLACEMENT: str = '<TRACEBACK_LINE>'

TEXT_NORMALIZATIONS: typing.List[typing.Tuple[str, str]] = [
    (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ \[\S+ *\] - .*\.py:\d+ -- ', '<LOG_PREFIX> -- '),
    (r'\d+\.\d+ seconds', '<DURATION_SECONDS>'),
    (r'\bv\d+\.\d+\.\d+\b', '<VERSION>'),
    (r'^\s*File "[^"]+", line \d+,.*$\n.*$(\n\s*[\^~]+\s*$)?', '<TRACEBACK_LINE>'),
    (rf'{TRACEBACK_LINE_REPLACEMENT}(\n{TRACEBACK_LINE_REPLACEMENT})*', '<TRACEBACK>'),
]
"""
Normalization to make to the CLI output.
Formatted as: [(regex, replacement), ...]
"""

@typing.runtime_checkable
class StringComparisonAssertion(typing.Protocol):
    """
    A function that can be used as a comparison assertion for a test.
    """

    def __call__(self,
            test: edq.testing.unittest.BaseTest,
            expected: str, actual: str,
            **kwargs: typing.Any) -> None:
        """
        Perform an assertion between expected and actual data.
        """

def content_equals_raw(test: edq.testing.unittest.BaseTest, expected: str, actual: str, **kwargs: typing.Any) -> None:
    """ Check for equality using a simple string comparison. """

    test.assertEqual(expected, actual)

def content_equals_normalize(test: edq.testing.unittest.BaseTest, expected: str, actual: str, **kwargs: typing.Any) -> None:
    """
    Perform some standard text normalizations (see TEXT_NORMALIZATIONS) before using simple string comparison.
    """

    for (regex, replacement) in TEXT_NORMALIZATIONS:
        expected = re.sub(regex, replacement, expected, flags = re.MULTILINE)
        actual = re.sub(regex, replacement, actual, flags = re.MULTILINE)

    content_equals_raw(test, expected, actual)

def has_content_100(test: edq.testing.unittest.BaseTest, expected: str, actual: str, **kwargs: typing.Any) -> None:
    """ Check the that output has at least 100 characters. """

    return has_content(test, expected, actual, min_length = 100)

def has_content(test: edq.testing.unittest.BaseTest, expected: str, actual: str, min_length: int = 100) -> None:
    """ Ensure that the output has content of at least some length. """

    message = f"Output does not meet minimum length of {min_length}, it is only {len(actual)}."
    test.assertTrue((len(actual) >= min_length), msg = message)
