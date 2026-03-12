# pylint: disable=invalid-name

"""
Run specified CLI test files.
"""

import argparse
import sys
import unittest

import edq.core.argparser
import edq.testing.cli
import edq.testing.unittest

class CLITest(edq.testing.unittest.BaseTest):
    """ Test CLI invocations. """

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    edq.testing.cli.add_test_paths(CLITest, args.data_dir, args.paths)

    runner = unittest.TextTestRunner(verbosity = 2)
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(CLITest)
    results = runner.run(tests)

    return len(results.errors) + len(results.failures)

def main() -> int:
    """ Get a parser, parse the args, and call run. """
    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    parser.add_argument('paths', metavar = 'PATH',
        type = str, nargs = '+',
        help = 'Path to CLI test case files.')

    parser.add_argument('--data-dir', dest = 'data_dir',
        action = 'store', type = str, default = '.',
        help = 'The additional data directory (expansion of __DATA_DIR__) used for tests (default: %(default)s).')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
