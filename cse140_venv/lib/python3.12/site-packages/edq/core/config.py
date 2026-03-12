import argparse
import os
import typing

import platformdirs

import edq.util.dirent
import edq.util.json

CONFIG_SOURCE_GLOBAL: str = "<global config file>"
CONFIG_SOURCE_LOCAL: str = "<local config file>"
CONFIG_SOURCE_CLI_FILE: str = "<cli config file>"
CONFIG_SOURCE_CLI: str = "<cli argument>"

CONFIG_PATHS_KEY: str = 'config_paths'
CONFIGS_KEY: str = 'configs'
GLOBAL_CONFIG_KEY: str = 'global_config_path'
IGNORE_CONFIGS_KEY: str = 'ignore_configs'
DEFAULT_CONFIG_FILENAME: str = "edq-config.json"

class ConfigSource:
    """ A class for storing config source information. """

    def __init__(self, label: str, path: typing.Union[str, None] = None) -> None:
        self.label = label
        """ The label identifying the config (see CONFIG_SOURCE_* constants). """

        self.path = path
        """ The path of where the config was sourced from. """

    def __eq__(self, other: object) -> bool:
        if (not isinstance(other, ConfigSource)):
            return False

        return ((self.label == other.label) and (self.path == other.path))

    def __str__(self) -> str:
        return f"({self.label}, {self.path})"

def get_global_config_path(config_filename: str) -> str:
    """ Get the path for the global config file. """

    return platformdirs.user_config_dir(config_filename)

def get_tiered_config(
        config_filename: str = DEFAULT_CONFIG_FILENAME,
        legacy_config_filename: typing.Union[str, None] = None,
        cli_arguments: typing.Union[dict, argparse.Namespace, None] = None,
        local_config_root_cutoff: typing.Union[str, None] = None,
    ) -> typing.Tuple[typing.Dict[str, str], typing.Dict[str, ConfigSource]]:
    """
    Load all configuration options from files and command-line arguments.
    Returns a configuration dictionary with the values based on tiering rules and a source dictionary mapping each key to its origin.
    """

    if (cli_arguments is None):
        cli_arguments = {}

    config: typing.Dict[str, str] = {}
    sources: typing.Dict[str, ConfigSource] = {}

    # Ensure CLI arguments are always a dict, even if provided as argparse.Namespace.
    if (isinstance(cli_arguments, argparse.Namespace)):
        cli_arguments = vars(cli_arguments)

    global_config_path = cli_arguments.get(GLOBAL_CONFIG_KEY, get_global_config_path(config_filename))

    # Check the global user config file.
    if (os.path.isfile(global_config_path)):
        _load_config_file(global_config_path, config, sources, CONFIG_SOURCE_GLOBAL)

    # Check the local user config file.
    local_config_path = _get_local_config_path(
        config_filename = config_filename,
        legacy_config_filename = legacy_config_filename,
        local_config_root_cutoff = local_config_root_cutoff,
    )

    if (local_config_path is not None):
        _load_config_file(local_config_path, config, sources, CONFIG_SOURCE_LOCAL)

    # Check the config file specified on the command-line.
    config_paths = cli_arguments.get(CONFIG_PATHS_KEY, [])
    for path in config_paths:
        _load_config_file(path, config, sources, CONFIG_SOURCE_CLI_FILE)

    # Check the command-line config options.
    cli_configs = cli_arguments.get(CONFIGS_KEY, [])
    for cli_config in cli_configs:
        if ("=" not in cli_config):
            raise ValueError(
                f"Invalid configuration option '{cli_config}'."
                + " Configuration options must be provided in the format `<key>=<value>` when passed via the CLI."
            )

        (key, value) = cli_config.split("=", maxsplit = 1)

        key = key.strip()
        if (key == ""):
            raise ValueError(f"Found an empty configuration option key associated with the value '{value}'.")

        config[key] = value
        sources[key] = ConfigSource(label = CONFIG_SOURCE_CLI)

    # Finally, ignore any configs that is specified from CLI command.
    cli_ignore_configs = cli_arguments.get(IGNORE_CONFIGS_KEY, [])
    for ignore_config in cli_ignore_configs:
        config.pop(ignore_config, None)
        sources.pop(ignore_config, None)

    return config, sources

def _load_config_file(
        config_path: str,
        config: typing.Dict[str, str],
        sources: typing.Dict[str, ConfigSource],
        source_label: str,
    ) -> None:
    """ Loads config variables and the source from the given config JSON file. """

    config_path = os.path.abspath(config_path)
    for (key, value) in edq.util.json.load_path(config_path).items():
        key = key.strip()
        if (key == ""):
            raise ValueError(f"Found an empty configuration option key associated with the value '{value}'.")

        config[key] = value
        sources[key] = ConfigSource(label = source_label, path = config_path)

def _get_local_config_path(
        config_filename: str,
        legacy_config_filename: typing.Union[str, None] = None,
        local_config_root_cutoff: typing.Union[str, None] = None,
    ) -> typing.Union[str, None]:
    """
    Search for a config file in hierarchical order.
    Begins with the provided config file name,
    optionally checks the legacy config file name if specified,
    then continues up the directory tree looking for the provided config file name.
    Returns the path to the first config file found.

    If no config file is found, returns None.

    The cutoff parameter limits the search depth, preventing detection of config file in higher-level directories during testing.
    """

    # Provided config file is in current directory.
    if (os.path.isfile(config_filename)):
        return os.path.abspath(config_filename)

    # Provided legacy config file is in current directory.
    if (legacy_config_filename is not None):
        if (os.path.isfile(legacy_config_filename)):
            return os.path.abspath(legacy_config_filename)

    # Provided config file is found in an ancestor directory up to the root or cutoff limit.
    parent_dir = os.path.dirname(os.getcwd())
    return _get_ancestor_config_file_path(
        parent_dir,
        config_filename = config_filename,
        local_config_root_cutoff = local_config_root_cutoff,
    )

def _get_ancestor_config_file_path(
        current_directory: str,
        config_filename: str,
        local_config_root_cutoff: typing.Union[str, None] = None,
    ) -> typing.Union[str, None]:
    """
    Search through the parent directories (until root or a given cutoff directory(inclusive)) for a config file.
    Stops at the first occurrence of the specified config file along the path to root.
    Returns the path if a config file is found.
    Otherwise, returns None.
    """

    if (local_config_root_cutoff is not None):
        local_config_root_cutoff = os.path.abspath(local_config_root_cutoff)

    current_directory = os.path.abspath(current_directory)
    for _ in range(edq.util.dirent.DEPTH_LIMIT):
        config_file_path = os.path.join(current_directory, config_filename)
        if (os.path.isfile(config_file_path)):
            return config_file_path

        # Check if current directory is root.
        parent_dir = os.path.dirname(current_directory)
        if (parent_dir == current_directory):
            break

        if (local_config_root_cutoff == current_directory):
            break

        current_directory = parent_dir

    return None

def set_cli_args(parser: argparse.ArgumentParser, extra_state: typing.Dict[str, typing.Any],
        config_filename: str = DEFAULT_CONFIG_FILENAME,
        **kwargs: typing.Any,
    ) -> None:
    """
    Set common CLI arguments for configuration.
    """

    parser.add_argument('--config-global', dest = GLOBAL_CONFIG_KEY,
        action = 'store', type = str, default = get_global_config_path(config_filename),
        help = 'Set the default global config file path (default: %(default)s).',
    )

    parser.add_argument('--config-file', dest = CONFIG_PATHS_KEY,
        action = 'append', type = str, default = [],
        help = ('Load config options from a JSON file.'
            + ' This flag can be specified multiple times.'
            + ' Files are applied in the order provided and later files override earlier ones.'
            + ' Will override options form both global and local config files.')
    )

    parser.add_argument('--config', dest = CONFIGS_KEY,
        action = 'append', type = str, default = [],
        help = ('Set a configuration option from the command-line.'
            + ' Specify options as <key>=<value> pairs.'
            + ' This flag can be specified multiple times.'
            + ' The options are applied in the order provided and later options override earlier ones.'
            + ' Will override options form all config files.')
    )

    parser.add_argument('--ignore-config-option', dest = IGNORE_CONFIGS_KEY,
        action = 'append', type = str, default = [],
        help = ('Ignore any config option with the specified key.'
            + ' The system-provided default value will be used for that option if one exists.'
            + ' This flag can be specified multiple times.'
            + ' Ignored options are processed last.')
    )

def load_config_into_args(
        parser: argparse.ArgumentParser,
        args: argparse.Namespace,
        extra_state: typing.Dict[str, typing.Any],
        config_filename: str = DEFAULT_CONFIG_FILENAME,
        cli_arg_config_map: typing.Union[typing.Dict[str, str], None] = None,
        **kwargs: typing.Any,
    ) -> None:
    """
    Take in args from a parser that was passed to set_cli_args(),
    and get the tired configuration with the appropriate parameters, and attache it to args.

    Arguments that appear on the CLI as flags (e.g. `--foo bar`) can be copied over to the config options via `cli_arg_config_map`.
    The keys of `cli_arg_config_map` represent attributes in the CLI arguments (`args`),
    while the values represent the desired config name this argument should be set as.
    For example, a `cli_arg_config_map` of `{'foo': 'baz'}` will make the CLI argument `--foo bar`
    be equivalent to `--config baz=bar`.
    """

    if (cli_arg_config_map is None):
        cli_arg_config_map = {}

    for (cli_key, config_key) in cli_arg_config_map.items():
        value = getattr(args, cli_key, None)
        if (value is not None):
            getattr(args, CONFIGS_KEY).append(f"{config_key}={value}")

    (config_dict, sources_dict) = get_tiered_config(
        cli_arguments = args,
        config_filename = config_filename,
    )

    setattr(args, "_config", config_dict)
    setattr(args, "_config_sources", sources_dict)
