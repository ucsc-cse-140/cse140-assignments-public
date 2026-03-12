"""
List the current configuration options.
"""

import argparse
import sys

import edq.core.argparser

CONFIG_FIELD_SEPARATOR: str = "\t"

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    rows = []

    for (key, value) in args._config.items():
        row = [key, str(value)]
        if (args.show_origin):
            config_source_obj = args._config_sources.get(key)

            origin = config_source_obj.path
            if (origin is None):
                origin = config_source_obj.label

            row.append(origin)

        rows.append(CONFIG_FIELD_SEPARATOR.join(row))

    rows.sort()

    if (not args.skip_header):
        header = ["Key", "Value"]
        if (args.show_origin):
            header.append("Origin")

        rows.insert(0, (CONFIG_FIELD_SEPARATOR.join(header)))

    print("\n".join(rows))
    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """

    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get a parser and add addition flags. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())
    modify_parser(parser)

    return parser

def modify_parser(parser: argparse.ArgumentParser) -> None:
    """ Add this CLI's flags to the given parser. """

    parser.add_argument("--show-origin", dest = 'show_origin',
        action = 'store_true',
        help = "Display where each configuration's value was obtained from.",
    )

    parser.add_argument("--skip-header", dest = 'skip_header',
        action = 'store_true',
        help = 'Skip headers when displaying configs.',
    )

if (__name__ == '__main__'):
    sys.exit(main())
