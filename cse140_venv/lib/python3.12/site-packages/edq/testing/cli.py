"""
Infrastructure for testing CLI tools using a JSON file which describes a test case,
which is essentially an invocation of a CLI tool and the expected output.

The test case file must be a `.txt` file that live in the test cases dir.
The file contains two parts (separated by a line with just TEST_CASE_SEP):
the first part which is a JSON object (see below for available keys),
and a second part which is the expected text output (stdout).
For the keys of the JSON section, see the defaulted arguments to CLITestInfo.
The options JSON will be splatted into CLITestInfo's constructor.

If a test class implements a method with the signature `modify_cli_test_info(self, test_info: CLITestInfo) -> None`,
then this method will be called with the test info right after the test info is read from disk.

If a test class implements a class method with the signature `get_test_basename(cls, path: str) -> str`,
then this method will be called to create the base name for the test case at the given path.

The expected output or any argument can reference the test's current temp or data dirs with `__TEMP_DIR__()` or `__DATA_DIR__()`, respectively.
An optional slash-separated path can be used as an argument to reference a path within those base directories.
For example, `__DATA_DIR__(foo/bar.txt)` references `bar.txt` inside the `foo` directory inside the data directory.
"""

import contextlib
import glob
import io
import os
import re
import sys
import typing

import edq.testing.asserts
import edq.testing.unittest
import edq.util.dirent
import edq.util.json
import edq.util.pyimport

TEST_CASE_SEP: str = '---'
OUTPUT_SEP: str = '+++'
DATA_DIR_ID: str = '__DATA_DIR__'
ABS_DATA_DIR_ID: str = '__ABS_DATA_DIR__'
TEMP_DIR_ID: str = '__TEMP_DIR__'
BASE_DIR_ID: str = '__BASE_DIR__'

REPLACE_LIMIT: int = 10000
""" The maximum number of replacements that will be made with a single test replacement. """

DEFAULT_ASSERTION_FUNC_NAME: str = 'edq.testing.asserts.content_equals_normalize'

BASE_TEMP_DIR_ATTR: str = '_edq_cli_base_test_dir'

class CLITestInfo:
    """ The required information to run a CLI test. """

    def __init__(self,
            test_name: str,
            base_dir: str,
            data_dir: str,
            temp_dir: str,
            cli: typing.Union[str, None] = None,
            arguments: typing.Union[typing.List[str], None] = None,
            error: bool = False,
            platform_skip: typing.Union[str, None] = None,
            stdout_assertion_func: typing.Union[str, None] = DEFAULT_ASSERTION_FUNC_NAME,
            stderr_assertion_func: typing.Union[str, None] = None,
            expected_stdout: str = '',
            expected_stderr: str = '',
            split_stdout_stderr: bool = False,
            strip_error_output: bool = True,
            extra_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
            **kwargs: typing.Any) -> None:
        self.skip_reasons: typing.List[str] = []
        """
        Reasons that this test will be skipped.
        Any entries in this list indicate that the test should be skipped.
        """

        self.platform_skip_pattern: typing.Union[str, None] = platform_skip
        """
        A pattern to check if the test should be skipped on the current platform.
        Will be used in `re.search()` against `sys.platform`.
        """

        if ((platform_skip is not None) and re.search(platform_skip, sys.platform)):
            self.skip_reasons.append(f"not available on platform: '{sys.platform}'")

        self.test_name: str = test_name
        """ The name of this test. """

        self.base_dir: str = base_dir
        """
        The base directory for this test (usually the dir the CLI test file lives.
        This is the expansion for `__BASE_DIR__` paths.
        """

        self.data_dir: str = data_dir
        """
        A directory that additional testing data lives in.
        This is the expansion for `__DATA_DIR__` paths.
        """

        self.temp_dir: str = temp_dir
        """
        A temp directory that this test has access to.
        This is the expansion for `__TEMP_DIR__` paths.
        """

        edq.util.dirent.mkdir(temp_dir)

        if (cli is None):
            raise ValueError("Missing CLI module.")

        self.module_name: str = cli
        """ The name of the module to invoke. """

        self.module: typing.Any = None
        """ The module to invoke. """

        if (not self.should_skip()):
            self.module = edq.util.pyimport.import_name(self.module_name)

        if (arguments is None):
            arguments = []

        self.arguments: typing.List[str] = arguments
        """ The CLI arguments. """

        self.error: bool = error
        """ Whether or not this test is expected to be an error (raise an exception). """

        self.stdout_assertion_func: typing.Union[edq.testing.asserts.StringComparisonAssertion, None] = None
        """ The assertion func to compare the expected and actual stdout of the CLI. """

        if ((stdout_assertion_func is not None) and (not self.should_skip())):
            self.stdout_assertion_func = edq.util.pyimport.fetch(stdout_assertion_func)

        self.stderr_assertion_func: typing.Union[edq.testing.asserts.StringComparisonAssertion, None] = None
        """ The assertion func to compare the expected and actual stderr of the CLI. """

        if ((stderr_assertion_func is not None) and (not self.should_skip())):
            self.stderr_assertion_func = edq.util.pyimport.fetch(stderr_assertion_func)

        self.expected_stdout: str = expected_stdout
        """ The expected stdout. """

        self.expected_stderr: str = expected_stderr
        """ The expected stderr. """

        if (error and strip_error_output):
            self.expected_stdout = self.expected_stdout.strip()
            self.expected_stderr = self.expected_stderr.strip()

        self.split_stdout_stderr: bool = split_stdout_stderr
        """
        Split stdout and stderr into different strings for testing.
        By default, these two will be combined.
        If both are non-empty, then they will be joined like: f"{stdout}\n{OUTPUT_SEP}\n{stderr}".
        Otherwise, only the non-empty one will be present with no separator.
        Any stdout assertions will be applied to the combined text.
        """

        # Make any path normalizations over the arguments and expected output.
        self.expected_stdout = self._expand_paths(self.expected_stdout)
        self.expected_stderr = self._expand_paths(self.expected_stderr)
        for (i, argument) in enumerate(self.arguments):
            self.arguments[i] = self._expand_paths(argument)

        if (extra_options is None):
            extra_options = {}

        self.extra_options: typing.Union[typing.Dict[str, typing.Any], None] = extra_options
        """
        A place to store additional options.
        Extra top-level options will cause tests to error.
        """

        if (len(kwargs) > 0):
            raise ValueError(f"Found unknown CLI test options: '{kwargs}'.")

    def _expand_paths(self, text: str) -> str:
        """
        Expand path replacements in testing text.
        This allows for consistent paths (even absolute paths) in the test text.
        """

        replacements = [
            (DATA_DIR_ID, self.data_dir, False),
            (TEMP_DIR_ID, self.temp_dir, False),
            (BASE_DIR_ID, self.base_dir, False),
            (ABS_DATA_DIR_ID, self.data_dir, True),
        ]

        for (key, target_dir, normalize) in replacements:
            text = replace_path_pattern(text, key, target_dir, normalize_path = normalize)

        return text

    def should_skip(self) -> bool:
        """ Check if this test should be skipped. """

        return (len(self.skip_reasons) > 0)

    def skip_message(self) -> str:
        """ Get a message displaying the reasons this test should be skipped. """

        return f"This test has been skipped because of the following: {self.skip_reasons}."

    @staticmethod
    def load_path(path: str, test_name: str, base_temp_dir: str, data_dir: str) -> 'CLITestInfo':
        """ Load a CLI test file and extract the test info. """

        options, expected_stdout = read_test_file(path)

        options['expected_stdout'] = expected_stdout

        base_dir = os.path.dirname(os.path.abspath(path))
        temp_dir = os.path.join(base_temp_dir, test_name)

        return CLITestInfo(test_name, base_dir, data_dir, temp_dir, **options)

@typing.runtime_checkable
class TestMethodWrapperFunction(typing.Protocol):
    """
    A function that can be used to wrap/modify a CLI test method before it is attached to the test class.
    """

    def __call__(self,
            test_method: typing.Callable,
            test_info_path: str,
            ) -> typing.Callable:
        """
        Wrap and/or modify the CLI test method before it is attached to the test class.
        See _get_test_method() for the input method.
        The returned method will be used in-place of the input one.
        """

def read_test_file(path: str) -> typing.Tuple[typing.Dict[str, typing.Any], str]:
    """ Read a test case file and split the output into JSON data and text. """

    json_lines: typing.List[str] = []
    output_lines: typing.List[str] = []

    text = edq.util.dirent.read_file(path, strip = False)

    accumulator = json_lines
    for line in text.split("\n"):
        if (line.strip() == TEST_CASE_SEP):
            accumulator = output_lines
            continue

        accumulator.append(line)

    options = edq.util.json.loads(''.join(json_lines))
    output = "\n".join(output_lines)

    return options, output

def replace_path_pattern(text: str, key: str, target_dir: str, normalize_path: bool = False) -> str:
    """ Make any test replacement inside the given string. """

    for _ in range(REPLACE_LIMIT):
        match = re.search(rf'{key}\(([^)]*)\)', text)
        if (match is None):
            break

        filename = match.group(1)

        # Normalize any path separators.
        filename = os.path.join(*filename.split('/'))

        if (filename == ''):
            path = target_dir
        else:
            path = os.path.join(target_dir, filename)

        if (normalize_path):
            path = os.path.abspath(path)

        text = text.replace(match.group(0), path)

    return text

def _get_test_method(test_name: str, path: str, data_dir: str) -> typing.Callable:
    """ Get a test method that represents the test case at the given path. """

    def __method(self: edq.testing.unittest.BaseTest,
            reraise_exception_types: typing.Union[typing.Tuple[typing.Type], None] = None,
            **kwargs: typing.Any) -> None:
        test_info = CLITestInfo.load_path(path, test_name, getattr(self, BASE_TEMP_DIR_ATTR), data_dir)

        # Allow the test class a chance to modify the test info before the test runs.
        if (hasattr(self, 'modify_cli_test_info')):
            self.modify_cli_test_info(test_info)

        if (test_info.should_skip()):
            self.skipTest(test_info.skip_message())

        old_args = sys.argv
        sys.argv = [test_info.module.__file__] + test_info.arguments

        try:
            with contextlib.redirect_stdout(io.StringIO()) as stdout_output:
                with contextlib.redirect_stderr(io.StringIO()) as stderr_output:
                    test_info.module.main()

            stdout_text = stdout_output.getvalue()
            stderr_text = stderr_output.getvalue()

            if (test_info.error):
                self.fail(f"No error was not raised when one was expected ('{str(test_info.expected_stdout)}').")
        except BaseException as ex:
            if ((reraise_exception_types is not None) and isinstance(ex, reraise_exception_types)):
                raise ex

            if (not test_info.error):
                raise ex

            stdout_text = self.format_error_string(ex)

            stderr_text = ''
            if (isinstance(ex, SystemExit) and (ex.__context__ is not None)):
                stderr_text = self.format_error_string(ex.__context__)
        finally:
            sys.argv = old_args

        if (not test_info.split_stdout_stderr):
            if ((len(stdout_text) > 0) and (len(stderr_text) > 0)):
                stdout_text = f"{stdout_text}\n{OUTPUT_SEP}\n{stderr_text}"
            elif (len(stderr_text) > 0):
                stdout_text = stderr_text

        if (test_info.stdout_assertion_func is not None):
            test_info.stdout_assertion_func(self, test_info.expected_stdout, stdout_text)

        if (test_info.stderr_assertion_func is not None):
            test_info.stderr_assertion_func(self, test_info.expected_stderr, stderr_text)

    return __method

def add_test_paths(target_class: type, data_dir: str, paths: typing.List[str],
        test_method_wrapper: typing.Union[TestMethodWrapperFunction, None] = None) -> None:
    """ Add tests from the given test files. """

    # Attach a temp directory to the testing class so all tests can share a common base temp dir.
    if (not hasattr(target_class, BASE_TEMP_DIR_ATTR)):
        setattr(target_class, BASE_TEMP_DIR_ATTR, edq.util.dirent.get_temp_path('edq_cli_test_'))

    for path in sorted(paths):
        basename = os.path.splitext(os.path.basename(path))[0]
        if (hasattr(target_class, 'get_test_basename')):
            basename = getattr(target_class, 'get_test_basename')(path)

        test_name = 'test_cli__' + basename

        try:
            test_method = _get_test_method(test_name, path, data_dir)
        except Exception as ex:
            raise ValueError(f"Failed to parse test case '{path}'.") from ex

        if (test_method_wrapper is not None):
            test_method = test_method_wrapper(test_method, path)

        setattr(target_class, test_name, test_method)

def discover_test_cases(target_class: type, test_cases_dir: str, data_dir: str,
        test_method_wrapper: typing.Union[TestMethodWrapperFunction, None] = None) -> None:
    """ Look in the text cases directory for any test cases and add them as test methods to the test class. """

    paths = list(sorted(glob.glob(os.path.join(test_cases_dir, "**", "*.txt"), recursive = True)))
    add_test_paths(target_class, data_dir, paths, test_method_wrapper = test_method_wrapper)
