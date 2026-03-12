# pylint: disable=invalid-name

"""
Send an HTTP exchange to the target server.
"""

import argparse
import sys

import edq.core.argparser
import edq.util.net

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    exchange = edq.util.net.HTTPExchange.from_path(args.path)
    _, body = exchange.make_request(args.server)

    print(body)

    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """
    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip(),
            include_net = True,
    )

    parser.add_argument('server', metavar = 'SERVER',
        action = 'store', type = str,
        help = 'Server to send the exahnge to.')

    parser.add_argument('path', metavar = 'PATH',
        action = 'store', type = str,
        help = 'Path to the exchange file.')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
