import os

import edq.testing.unittest
import edq.core.config
import edq.util.dirent
import edq.util.json

def creat_test_dir(temp_dir_prefix: str) -> str:
    """
    Creat a temp dir and populate it with dirents for testing.

    This test data directory is laid out as:
    .
    ├── custom-name
    │   └── custom-edq-config.json
    ├── dir-config
    │   └── edq-config.json
    ├── empty
    │   └── edq-config.json
    ├── empty-dir
    ├── empty-key
    │   └── edq-config.json
    ├── global
    │   └── edq-config.json
    ├── malformed
    │   └── edq-config.json
    ├── multiple-options
    │   └── edq-config.json
    ├── nested
    │   ├── config.json
    │   ├── edq-config.json
    │   └── nest1
    │       ├── nest2a
    │       └── nest2b
    │           └── edq-config.json
    ├── old-name
    │   ├── config.json
    │   └── nest1
    │       └── nest2
    └── simple
        └── edq-config.json
    """

    temp_dir = edq.util.dirent.get_temp_dir(prefix = temp_dir_prefix)

    empty_config_dir_path = os.path.join(temp_dir, "empty")
    edq.util.dirent.mkdir(empty_config_dir_path)
    edq.util.json.dump_path({}, os.path.join(empty_config_dir_path, edq.core.config.DEFAULT_CONFIG_FILENAME))

    multiple_option_config_dir_path = os.path.join(temp_dir, "multiple-options")
    edq.util.dirent.mkdir(multiple_option_config_dir_path)
    edq.util.json.dump_path(
        {"user": "user@test.edulinq.org", "pass": "password1234"},
        os.path.join(multiple_option_config_dir_path, edq.core.config.DEFAULT_CONFIG_FILENAME)
    )

    empty_key_config_dir_path = os.path.join(temp_dir, "empty-key")
    edq.util.dirent.mkdir(empty_key_config_dir_path)
    edq.util.json.dump_path({"": "user@test.edulinq.org"}, os.path.join(empty_key_config_dir_path, edq.core.config.DEFAULT_CONFIG_FILENAME))

    custom_name_config_dir_path = os.path.join(temp_dir, "custom-name")
    edq.util.dirent.mkdir(custom_name_config_dir_path)
    edq.util.json.dump_path({"user": "user@test.edulinq.org"}, os.path.join(custom_name_config_dir_path, "custom-edq-config.json"))

    edq.util.dirent.mkdir(os.path.join(temp_dir, "dir-config", "edq-config.json"))
    edq.util.dirent.mkdir(os.path.join(temp_dir, "empty-dir"))

    global_config_dir_path = os.path.join(temp_dir, "global")
    edq.util.dirent.mkdir(global_config_dir_path)
    edq.util.json.dump_path({"user": "user@test.edulinq.org"}, os.path.join(global_config_dir_path, edq.core.config.DEFAULT_CONFIG_FILENAME))

    old_name_config_dir_path = os.path.join(temp_dir, "old-name")
    edq.util.dirent.mkdir(os.path.join(old_name_config_dir_path, "nest1", "nest2"))
    edq.util.json.dump_path({"user": "user@test.edulinq.org"}, os.path.join(old_name_config_dir_path, "config.json"))

    nested_dir_path = os.path.join(temp_dir, "nested")
    edq.util.dirent.mkdir(os.path.join(nested_dir_path, "nest1", "nest2a"))
    edq.util.dirent.mkdir(os.path.join(nested_dir_path, "nest1", "nest2b"))

    edq.util.json.dump_path({"server": "http://test.edulinq.org"}, os.path.join(nested_dir_path, edq.core.config.DEFAULT_CONFIG_FILENAME))
    edq.util.json.dump_path({"user": "user@test.edulinq.org"}, os.path.join(nested_dir_path, "config.json"))
    edq.util.json.dump_path(
        {"user": "user@test.edulinq.org"},
        os.path.join(nested_dir_path, "nest1", "nest2b", edq.core.config.DEFAULT_CONFIG_FILENAME),
    )

    simple_config_dir_path = os.path.join(temp_dir, "simple")
    edq.util.dirent.mkdir(simple_config_dir_path)
    edq.util.dirent.write_file(
        os.path.join(simple_config_dir_path, edq.core.config.DEFAULT_CONFIG_FILENAME),
        '{"user": "user@test.edulinq.org",}',
    )

    malformed_config_dir_path = os.path.join(temp_dir, "malformed")
    edq.util.dirent.mkdir(malformed_config_dir_path)
    edq.util.dirent.write_file(
        os.path.join(malformed_config_dir_path, edq.core.config.DEFAULT_CONFIG_FILENAME),
        "{user: user@test.edulinq.org}",
    )

    return temp_dir

class TestConfig(edq.testing.unittest.BaseTest):
    """ Test basic operations on configs. """

    def test_get_tiered_config_base(self):
        """
        Test that configuration files are loaded correctly from the file system with the expected tier.
        """

        temp_dir = creat_test_dir(temp_dir_prefix = "edq-test-config-get-tiered-config-")

        # [(work directory, extra arguments, expected config, expected source, error substring), ...]
        test_cases = [
            # No Config
            (
                "empty-dir",
                {},
                {},
                {},
                None,
            ),

            # Global Config

            # Custom Global Config Path
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_GLOBAL,
                        path = os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Empty Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "empty", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {},
                {},
                None,
            ),

            # Empty Key Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "empty-key", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {},
                {},
                "Found an empty configuration option key associated with the value 'user@test.edulinq.org'.",
            ),

            # Directory Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "dir-config", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {},
                {},
                None,
            ),

            # Non-Existent Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "empty-dir", "non-existent-config.json"),
                    },
                },
                {},
                {},
                None,
            ),

            # Malformed Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "malformed", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {},
                {},
                "Failed to read JSON file",
            ),

            # Ignore Config Option
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "multiple-options", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        edq.core.config.IGNORE_CONFIGS_KEY: [
                            "pass",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_GLOBAL,
                        path = os.path.join(temp_dir, "multiple-options", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Ignore Non-Existing Config Option
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        edq.core.config.IGNORE_CONFIGS_KEY: [
                            "non-existing-option",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_GLOBAL,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Local Config

            # Default config file in current directory.
            (
                "simple",
                {},
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Custom config file in current directory.
            (
                "custom-name",
                {
                    "config_filename": "custom-edq-config.json",
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                    ),
                },
                None,
            ),

            # Legacy config file in current directory.
            (
                "old-name",
                {
                    "legacy_config_filename": "config.json",
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "old-name", "config.json"),
                    ),
                },
                None,
            ),

            # Default config file in an ancestor directory.
            (
                os.path.join("nested", "nest1", "nest2a"),
                {},
                {
                    "server": "http://test.edulinq.org",
                },
                {
                    "server": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "nested", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Legacy config file in an ancestor directory.
            (
                os.path.join("old-name", "nest1", "nest2"),
                {
                    "legacy_config_filename": "config.json",
                },
                {},
                {},
                None,
            ),

            # Empty Config JSON
            (
                "empty",
                {},
                {},
                {},
                None,
            ),

            # Empty Key Config JSON
            (
                "empty-key",
                {},
                {},
                {},
                "Found an empty configuration option key associated with the value 'user@test.edulinq.org'.",
            ),

            # Directory Config JSON
            (
                "dir-config",
                {},
                {},
                {},
                None,
            ),

            # Malformed Config JSON
            (
                "malformed",
                {},
                {},
                {},
                "Failed to read JSON file",
            ),

            # Ignore Config Option
            (
                "multiple-options",
                {
                    "cli_arguments":{
                        edq.core.config.IGNORE_CONFIGS_KEY: [
                            "pass",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "multiple-options", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Ignore Non-Existing Config Option
            (
                "simple",
                {
                    "cli_arguments":{
                        edq.core.config.IGNORE_CONFIGS_KEY: [
                            "non-existing-option",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),


            # All 3 local config locations present at the same time.
            (
                os.path.join("nested", "nest1", "nest2b"),
                {
                    "legacy_config_filename": "config.json",
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "nested", "nest1", "nest2b", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # CLI Provided Config

            # Distinct Keys
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                            os.path.join(temp_dir, "nested", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                    "server": "http://test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                    "server": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "nested", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Overwriting Keys
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                            os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Empty Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "empty", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                    },
                },
                {},
                {},
                None,
            ),

            # Empty Key Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "empty-key", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                    },
                },
                {},
                {},
                "Found an empty configuration option key associated with the value 'user@test.edulinq.org'.",
            ),

            # Directory Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "dir-config", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                    },
                },
                {},
                {},
                "IsADirectoryError",
            ),

            # Non-Existent Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "empty-dir", "non-existent-config.json"),
                        ],
                    },
                },
                {},
                {},
                "FileNotFoundError",
            ),

            # Malformed Config JSON
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "malformed", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                    },
                },
                {},
                {},
                "Failed to read JSON file",
            ),

            # Ignore Config Option
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "multiple-options", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                        edq.core.config.IGNORE_CONFIGS_KEY: [
                            "pass",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "multiple-options", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Ignore Non-Existing Config Option
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                        edq.core.config.IGNORE_CONFIGS_KEY: [
                            "non-existing-option",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),


            # CLI Options:

            # CLI arguments only (direct key: value).
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Empty Config Key
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "=user@test.edulinq.org",
                        ],
                    },
                },
                {},
                {},
                "Found an empty configuration option key associated with the value 'user@test.edulinq.org'.",
            ),

            # Empty Config Value
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=",
                        ],
                    },
                },
                {
                    "user": "",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Separator In Config Value
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "pass=password=1234",
                        ],
                    },
                },
                {
                    "pass": "password=1234",
                },
                {
                    "pass": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Invalid Config Option Format
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "useruser@test.edulinq.org",
                        ],
                    },
                },
                {},
                {},
                "Invalid configuration option 'useruser@test.edulinq.org'.",
            ),

            # Ignore Config Option
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                            "pass=password1234",
                        ],
                        edq.core.config.IGNORE_CONFIGS_KEY:[
                            "pass",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Ignore Non-Existing Config Option
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                        edq.core.config.IGNORE_CONFIGS_KEY:[
                            "non-existing-option",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Combinations

            # Global Config + Local Config
            (
                "simple",
                {
                    "cli_arguments": {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_LOCAL,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Global Config + CLI Provided Config
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    ),
                },
                None,
            ),

            # Global + CLI Bare Options
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Local Config + CLI Provided Config
            (
                "simple",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                    ),
                },
                None,
            ),

            # Local Config + CLI Bare Options
            (
                "simple",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            #  CLI Provided Config + CLI Bare Options
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Global Config + CLI Provided Config + CLI Bare Options
            (
                "empty-dir",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "simple", edq.core.config.DEFAULT_CONFIG_FILENAME),
                        ],
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Global Config + Local Config + CLI Bare Options
            (
                "simple",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Global Config + Local Config + CLI Provided Config
            (
                "simple",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                        ],
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                    ),
                },
                None,
            ),

            # Local Config + CLI Provided Config + CLI Bare Options
            (
                "simple",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIGS_KEY: [
                            "user=user@test.edulinq.org",
                        ],
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                        ],
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                },
                {
                    "user": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),

            # Global Config + Local Config + CLI Provided Config + CLI Bare Options
            (
                "simple",
                {
                    "cli_arguments": {
                        edq.core.config.CONFIG_PATHS_KEY: [
                            os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                        ],
                        edq.core.config.CONFIGS_KEY: [
                            "pass=password1234",
                        ],
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "global", edq.core.config.DEFAULT_CONFIG_FILENAME),
                    },
                },
                {
                    "user": "user@test.edulinq.org",
                    "pass": "password1234",
                },
                {
                    "user": edq.core.config.ConfigSource(
                        label = edq.core.config.CONFIG_SOURCE_CLI_FILE,
                        path = os.path.join(temp_dir, "custom-name", "custom-edq-config.json"),
                    ),
                    "pass": edq.core.config.ConfigSource(label = edq.core.config.CONFIG_SOURCE_CLI),
                },
                None,
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (test_work_dir, extra_args, expected_config, expected_source, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{test_work_dir}'):"):
                cli_args = extra_args.get("cli_arguments", None)
                if cli_args is None:
                    extra_args["cli_arguments"] = {
                        edq.core.config.GLOBAL_CONFIG_KEY: os.path.join(temp_dir, "empty", edq.core.config.DEFAULT_CONFIG_FILENAME)
                    }
                else:
                    cli_global_config_path = cli_args.get(edq.core.config.GLOBAL_CONFIG_KEY, None)
                    if cli_global_config_path is None:
                        extra_args["cli_arguments"][edq.core.config.GLOBAL_CONFIG_KEY] = os.path.join(
                            temp_dir, "empty", edq.core.config.DEFAULT_CONFIG_FILENAME
                        )

                cutoff = extra_args.get("local_config_root_cutoff", None)
                if (cutoff is None):
                    extra_args["local_config_root_cutoff"] = temp_dir

                previous_work_directory = os.getcwd()
                initial_work_directory = os.path.join(temp_dir, test_work_dir)
                os.chdir(initial_work_directory)

                try:
                    (actual_config, actual_sources) = edq.core.config.get_tiered_config(**extra_args)
                except Exception as ex:
                    error_string = self.format_error_string(ex)

                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                finally:
                    os.chdir(previous_work_directory)

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertJSONDictEqual(expected_config, actual_config)
                self.assertJSONDictEqual(expected_source, actual_sources)
