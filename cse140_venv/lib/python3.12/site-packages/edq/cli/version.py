"""
Get the version of the EduLinq Python utils package.
"""

import argparse
import sys

import edq.core.argparser
import edq.core.version

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    print(f"v{edq.core.version.get_version()}")
    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """

    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    return edq.core.argparser.get_default_parser(__doc__.strip())

if (__name__ == '__main__'):
    sys.exit(main())
