import typing
import unittest

import edq.util.dirent
import edq.util.json
import edq.util.reflection

FORMAT_STR: str = "\n--- Expected ---\n%s\n--- Actual ---\n%s\n---\n"

class BaseTest(unittest.TestCase):
    """
    A base class for unit tests.
    """

    maxDiff = None
    """ Don't limit the size of diffs. """

    def assertJSONEqual(self, a: typing.Any, b: typing.Any, message: typing.Union[str, None] = None) -> None:  # pylint: disable=invalid-name
        """
        Like unittest.TestCase.assertEqual(),
        but uses a default assertion message containing the full JSON representation of the arguments.
        """

        a_json = edq.util.json.dumps(a, indent = 4)
        b_json = edq.util.json.dumps(b, indent = 4)

        if (message is None):
            message = FORMAT_STR % (a_json, b_json)

        super().assertEqual(a, b, msg = message)

    def assertJSONDictEqual(self, a: typing.Any, b: typing.Any, message: typing.Union[str, None] = None) -> None:  # pylint: disable=invalid-name
        """
        Like unittest.TestCase.assertDictEqual(),
        but will try to convert each comparison argument to a dict if it is not already,
        and uses a default assertion message containing the full JSON representation of the arguments.
        """

        if (not isinstance(a, dict)):
            if (isinstance(a, edq.util.json.DictConverter)):
                a = a.to_dict()
            else:
                a = vars(a)

        if (not isinstance(b, dict)):
            if (isinstance(b, edq.util.json.DictConverter)):
                b = b.to_dict()
            else:
                b = vars(b)

        a_json = edq.util.json.dumps(a, indent = 4)
        b_json = edq.util.json.dumps(b, indent = 4)

        if (message is None):
            message = FORMAT_STR % (a_json, b_json)

        super().assertDictEqual(a, b, msg = message)

    def assertJSONListEqual(self, a: typing.List[typing.Any], b: typing.List[typing.Any], message: typing.Union[str, None] = None) -> None:  # pylint: disable=invalid-name
        """
        Call assertDictEqual(), but supply a default message containing the full JSON representation of the arguments.
        """

        a_json = edq.util.json.dumps(a, indent = 4)
        b_json = edq.util.json.dumps(b, indent = 4)

        if (message is None):
            message = FORMAT_STR % (a_json, b_json)

        super().assertListEqual(a, b, msg = message)

    def assertFileHashEqual(self, a: str, b: str) -> None:  # pylint: disable=invalid-name
        """
        Assert that the hash of two files matches.
        Will fail if either path does not exist.
        """

        if (not edq.util.dirent.exists(a)):
            self.fail(f"File does not exist: '{a}'.")

        if (not edq.util.dirent.exists(b)):
            self.fail(f"File does not exist: '{b}'.")

        a_hash = edq.util.dirent.hash_file(a)
        b_hash = edq.util.dirent.hash_file(b)

        self.assertEqual(a_hash, b_hash, msg = f"Hash mismatch: '{a}' ({a_hash}) vs '{b}' ({b_hash}).")

    def format_error_string(self, ex: typing.Union[BaseException, None]) -> str:
        """
        Format an error string from an exception so it can be checked for testing.
        The type of the error will be included,
        and any nested errors will be joined together.
        """

        parts = []

        while (ex is not None):
            type_name = edq.util.reflection.get_qualified_name(ex)
            message = str(ex)

            parts.append(f"{type_name}: {message}")

            ex = ex.__cause__

        return "; ".join(parts)
