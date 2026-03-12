"""
A place to handle common CLI arguments.
"parsers" in this file are always assumed to be argparse parsers.

The general idea is that callers can register callbacks to be called before and after parsing CLI arguments.
Pre-callbacks are generally intended to add arguments to the parser,
while post-callbacks are generally intended to act on the results of parsing.
"""

import argparse
import functools
import typing

import edq.core.config
import edq.core.log
import edq.util.net

@typing.runtime_checkable
class PreParseFunction(typing.Protocol):
    """
    A function that can be called before parsing arguments.
    """

    def __call__(self, parser: argparse.ArgumentParser, extra_state: typing.Dict[str, typing.Any]) -> None:
        """
        Prepare a parser for parsing.
        This is generally used for adding your module's arguments to the parser,
        for example a logging module may add arguments to set a logging level.

        The extra state is shared between all pre-parse functions
        and will be placed in the final parsed output under `_pre_extra_state_`.
        """

@typing.runtime_checkable
class PostParseFunction(typing.Protocol):
    """
    A function that can be called after parsing arguments.
    """

    def __call__(self,
            parser: argparse.ArgumentParser,
            args: argparse.Namespace,
            extra_state: typing.Dict[str, typing.Any]) -> None:
        """
        Take actions after arguments are parsed.
        This is generally used for initializing your module with options,
        for example a logging module may set a logging level.

        The extra state is shared between all post-parse functions
        and will be placed in the final parsed output under `_post_extra_state_`.
        """

class Parser(argparse.ArgumentParser):
    """
    Extend an argparse parser to call the pre and post functions.
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)

        self._pre_parse_callbacks: typing.Dict[str, PreParseFunction] = {}
        self._post_parse_callbacks: typing.Dict[str, PostParseFunction] = {}

    def register_callbacks(self,
            key: str,
            pre_parse_callback: typing.Union[PreParseFunction, None] = None,
            post_parse_callback: typing.Union[PostParseFunction, None] = None,
            ) -> None:
        """
        Register callback functions to run before/after argument parsing.
        Any existing callbacks under the specified key will be replaced.
        """

        if (pre_parse_callback is not None):
            self._pre_parse_callbacks[key] = pre_parse_callback

        if (post_parse_callback is not None):
            self._post_parse_callbacks[key] = post_parse_callback

    def parse_args(self,  # type: ignore[override]
            *args: typing.Any,
            skip_keys: typing.Union[typing.List[str], None] = None,
            **kwargs: typing.Any) -> argparse.Namespace:
        if (skip_keys is None):
            skip_keys = []

        # Call pre-parse callbacks.
        pre_extra_state: typing.Dict[str, typing.Any] = {}
        for (key, pre_parse_callback) in self._pre_parse_callbacks.items():
            if (key not in skip_keys):
                pre_parse_callback(self, pre_extra_state)

        # Parse the args.
        parsed_args = super().parse_args(*args, **kwargs)

        # Call post-parse callbacks.
        post_extra_state: typing.Dict[str, typing.Any] = {}
        for (key, post_parse_callback) in self._post_parse_callbacks.items():
            if (key not in skip_keys):
                post_parse_callback(self, parsed_args, post_extra_state)

        # Attach the additional state to the args.
        setattr(parsed_args, '_pre_extra_state_', pre_extra_state)
        setattr(parsed_args, '_post_extra_state_', post_extra_state)

        return parsed_args  # type: ignore[no-any-return]

def get_default_parser(description: str,
        version: typing.Union[str, None] = None,
        include_log: bool = True,
        include_config: bool = True,
        include_net: bool = False,
        config_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
        ) -> Parser:
    """ Get a parser with the requested default callbacks already attached. """

    if (config_options is None):
        config_options = {}

    parser = Parser(description = description)

    if (version is not None):
        parser.add_argument('--version',
                action = 'version', version = version)

    if (include_log):
        parser.register_callbacks('log', edq.core.log.set_cli_args, edq.core.log.init_from_args)

    if (include_config):
        config_pre_func = functools.partial(edq.core.config.set_cli_args, **config_options)
        config_post_func = functools.partial(edq.core.config.load_config_into_args, **config_options)
        parser.register_callbacks('config', config_pre_func, config_post_func)

    if (include_net):
        parser.register_callbacks('net', edq.util.net.set_cli_args, edq.util.net.init_from_args)

    return parser
