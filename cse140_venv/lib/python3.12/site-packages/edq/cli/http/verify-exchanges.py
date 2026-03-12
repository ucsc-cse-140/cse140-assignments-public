# pylint: disable=invalid-name

"""
Verify that exchanges sent to a given server have the same response.
"""

import argparse
import sys

import edq.core.argparser
import edq.procedure.verify_exchanges

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    return edq.procedure.verify_exchanges.run(args.paths, args.server)

def main() -> int:
    """ Get a parser, parse the args, and call run. """
    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    parser.add_argument('server', metavar = 'SERVER',
        action = 'store', type = str, default = None,
        help = 'Address of the server to send exchanges to.')

    parser.add_argument('paths', metavar = 'PATH',
        type = str, nargs = '+',
        help = 'Path to exchange files or dirs (which will be recursively searched for all exchange files).')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
