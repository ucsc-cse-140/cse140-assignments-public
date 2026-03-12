"""
Discover and run unit tests (via Python's unittest package)
that live in this project's base package
(the parent of this package).
"""

import argparse
import os
import re
import sys
import typing
import unittest

DEFAULT_TEST_FILENAME_PATTERN: str = '*_test.py'
""" The default pattern for test files. """

CLEANUP_FUNC_NAME: str = 'suite_cleanup'
"""
If a test class has a function with this name,
then the function will be run after the test suite finishes.
"""

def _collect_tests(suite: typing.Union[unittest.TestCase, unittest.suite.TestSuite]) -> typing.List[unittest.TestCase]:
    """
    Collect and return tests (unittest.TestCase) from the target directory.
    """

    if (isinstance(suite, unittest.TestCase)):
        return [suite]

    if (not isinstance(suite, unittest.suite.TestSuite)):
        raise ValueError(f"Unknown test type: '{str(type(suite))}'.")

    test_cases = []
    for test_object in suite:
        test_cases += _collect_tests(test_object)

    return test_cases

def run(args: typing.Union[argparse.Namespace, typing.Dict[str, typing.Any], None] = None) -> int:
    """
    Discover and run unit tests.
    This function may change your working directory.
    Will raise if tests fail to load (e.g. syntax errors) and a suggested exit code otherwise.
    """

    if (args is None):
        args = {}

    if (not isinstance(args, dict)):
        args = vars(args)

    if (args.get('work_dir', None) is not None):
        os.chdir(args['work_dir'])

    if (args.get('path_additions', None) is not None):
        for path in args['path_additions']:
            sys.path.append(path)

    test_dirs = args.get('test_dirs', None)
    if (test_dirs is None):
        test_dirs = []

    if (len(test_dirs) == 0):
        test_dirs.append('.')

    runner = unittest.TextTestRunner(verbosity = 3, failfast = args.get('fail_fast', False))
    test_cases = []

    for test_dir in test_dirs:
        discovered_suite = unittest.TestLoader().discover(test_dir, pattern = args.get('filename_pattern', DEFAULT_TEST_FILENAME_PATTERN))
        test_cases += _collect_tests(discovered_suite)

    # Cleanup class functions from test classes.
    # {class: function, ...}
    cleanup_funcs = {}

    tests = unittest.suite.TestSuite()

    for test_case in test_cases:
        if (isinstance(test_case, unittest.loader._FailedTest)):  # type: ignore[attr-defined]
            raise ValueError(f"Failed to load test: '{test_case.id()}'.") from test_case._exception

        pattern = args.get('pattern', None)
        if ((pattern is None) or re.search(pattern, test_case.id())):
            tests.addTest(test_case)

            # Check for a cleanup function.
            if (hasattr(test_case.__class__, CLEANUP_FUNC_NAME)):
                cleanup_funcs[test_case.__class__] = getattr(test_case.__class__, CLEANUP_FUNC_NAME)
        else:
            print(f"Skipping {test_case.id()} because of match pattern.")

    result = runner.run(tests)
    faults = len(result.errors) + len(result.failures)

    # Perform any cleanup.
    for cleanup_func in cleanup_funcs.values():
        cleanup_func()

    if (not result.wasSuccessful()):
        # This value will be used as an exit status, so it should not be larger than a byte.
        # (Some higher values are used specially, so just keep it at a round number.)
        return max(1, min(faults, 100))

    return 0

def main() -> int:
    """ Parse the CLI arguments and run tests. """

    args = _get_parser().parse_args()
    return run(args)

def _get_parser() -> argparse.ArgumentParser:
    """ Build a parser for CLI arguments. """

    parser = argparse.ArgumentParser(description = 'Run unit tests discovered in this project.')

    parser.add_argument('--work-dir', dest = 'work_dir',
        action = 'store', type = str, default = os.getcwd(),
        help = 'Set the working directory when running tests, defaults to the current working directory (%(default)s).')

    parser.add_argument('--tests-dir', dest = 'test_dirs',
        action = 'append',
        help = 'Discover tests from these directories. Defaults to the current directory.')

    parser.add_argument('--add-path', dest = 'path_additions',
        action = 'append',
        help = 'If supplied, add this path the sys.path before running tests.')

    parser.add_argument('--filename-pattern', dest = 'filename_pattern',
        action = 'store', type = str, default = DEFAULT_TEST_FILENAME_PATTERN,
        help = 'The pattern to use to find test files (default: %(default)s).')

    parser.add_argument('pattern',
        action = 'store', type = str, default = None, nargs = '?',
        help = 'If supplied, only tests with names matching this pattern will be run. This pattern is used directly in re.search().')

    return parser

if __name__ == '__main__':
    sys.exit(main())
