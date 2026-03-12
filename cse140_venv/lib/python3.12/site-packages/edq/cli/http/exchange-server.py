# pylint: disable=invalid-name

"""
Start an HTTP test server that serves the specified HTTP exchanges.
"""

import argparse
import os
import sys

import edq.core.argparser
import edq.testing.httpserver

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    match_options = {
        'params_to_skip': args.ignore_params,
        'headers_to_skip': args.ignore_headers,
    }

    server = edq.testing.httpserver.HTTPTestServer(
            port = args.port,
            match_options = match_options,
            verbose = True,
            raise_on_404 = False,
    )

    for path in args.paths:
        path = os.path.abspath(path)

        if (os.path.isfile(path)):
            server.load_exchange(path)
        else:
            server.load_exchanges_dir(path)

    server.start_and_wait()

    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """
    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip(),
            include_net = True,
    )

    parser.add_argument('paths', metavar = 'PATH',
        type = str, nargs = '+',
        help = 'Path to exchange files or dirs (which will be recursively searched for all exchange files).')

    parser.add_argument('--port', dest = 'port',
        action = 'store', type = int, default = None,
        help = 'The port to run this test server on. If not set, a random open port will be chosen.')

    parser.add_argument('--ignore-param', dest = 'ignore_params',
        action = 'append', type = str, default = [],
        help = 'Ignore this parameter during exchange matching.')

    parser.add_argument('--ignore-header', dest = 'ignore_headers',
        action = 'append', type = str, default = [],
        help = 'Ignore this header during exchange matching.')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
