import os
import typing

import edq.testing.unittest
import edq.util.dirent
import edq.util.json
import edq.util.reflection

class TestJSON(edq.testing.unittest.BaseTest):
    """ Test JSON utils. """

    def test_loading_dumping_base(self):
        """
        Test the family of JSON loading and dumping functions.
        """

        # [(string, dict, strict?, error_substring), ...]
        test_cases = [
            # Base
            (
                '{"a": 1}',
                {"a": 1},
                False,
                None,
            ),

            # Trivial - Strict
            (
                '{"a": 1}',
                {"a": 1},
                True,
                None,
            ),

            # JSON5
            (
                '{"a": 1,}',
                {"a": 1},
                False,
                None,
            ),

            # JSON5 - Strict
            (
                '{"a": 1,}',
                {"a": 1},
                True,
                'JSONDecodeError',
            ),
        ]

        # [(function, name), ...]
        test_methods = [
            (self._subtest_loads_dumps, 'subtest_loads_dumps'),
            (self._subtest_load_dump, 'subtest_load_dump'),
            (self._subtest_load_dump_path, 'subtest_load_dump_path'),
        ]

        for (test_method, test_method_name) in test_methods:
            for (i, test_case) in enumerate(test_cases):
                (text_content, dict_content, strict, error_substring) = test_case

                with self.subTest(msg = f"Subtest {test_method_name}, Case {i} ('{text_content}'):"):
                    try:
                        test_method(text_content, dict_content, strict)
                    except AssertionError:
                        # The subttest failed an assertion.
                        raise
                    except Exception as ex:
                        error_string = self.format_error_string(ex)
                        if (error_substring is None):
                            self.fail(f"Unexpected error: '{error_string}'.")

                        self.assertIn(error_substring, error_string, 'Error is not as expected.')

                        continue

                    if (error_substring is not None):
                        self.fail(f"Did not get expected error: '{error_substring}'.")

    def _subtest_loads_dumps(self, text_content, dict_content, strict):
        actual_dict = edq.util.json.loads(text_content, strict = strict)
        actual_text = edq.util.json.dumps(dict_content)
        double_conversion_text = edq.util.json.dumps(actual_dict)

        self.assertDictEqual(dict_content, actual_dict)
        self.assertEqual(actual_text, double_conversion_text)

    def _subtest_load_dump(self, text_content, dict_content, strict):
        temp_dir = edq.util.dirent.get_temp_dir(prefix = 'edq_test_json_')

        path_text = os.path.join(temp_dir, 'test-text.json')
        path_dict = os.path.join(temp_dir, 'test-dict.json')

        edq.util.dirent.write_file(path_text, text_content)

        with open(path_text, 'r', encoding = edq.util.dirent.DEFAULT_ENCODING) as file:
            text_load = edq.util.json.load(file, strict = strict)

        with open(path_dict, 'w', encoding = edq.util.dirent.DEFAULT_ENCODING) as file:
            edq.util.json.dump(dict_content, file)

        with open(path_dict, 'r', encoding = edq.util.dirent.DEFAULT_ENCODING) as file:
            dict_load = edq.util.json.load(file, strict = strict)

        self.assertDictEqual(dict_content, text_load)
        self.assertDictEqual(dict_load, text_load)

    def _subtest_load_dump_path(self, text_content, dict_content, strict):
        temp_dir = edq.util.dirent.get_temp_dir(prefix = 'edq_test_json_path_')

        path_text = os.path.join(temp_dir, 'test-text.json')
        path_dict = os.path.join(temp_dir, 'test-dict.json')

        edq.util.dirent.write_file(path_text, text_content)
        text_load = edq.util.json.load_path(path_text, strict = strict)

        edq.util.json.dump_path(dict_content, path_dict)
        dict_load = edq.util.json.load_path(path_dict, strict = strict)

        self.assertDictEqual(dict_content, text_load)
        self.assertDictEqual(dict_load, text_load)

    def test_object_base(self):
        """
        Test loading and dumping JSON objects
        """

        # [(string, object, error_substring), ...]
        test_cases = [
            # Base
            (
                '{"a": 1, "b": "b"}',
                _TestConverter(1, "b"),
                None,
            ),

            # Missing Key
            (
                '{"a": 1}',
                _TestConverter(1, None),
                None,
            ),

            # Empty
            (
                '{}',
                _TestConverter(None, None),
                None,
            ),

            # Extra Key
            (
                '{"a": 1, "b": "b", "c": 0}',
                _TestConverter(1, "b"),
                None,
            ),

            # List
            (
                '[{"a": 1, "b": "b"}]',
                _TestConverter(1, "b"),
                'not a dict',
            ),
        ]

        # [(function, name), ...]
        test_methods = [
            (self._subtest_loads_object, 'subtest_loads_object'),
            (self._subtest_load_object_path, 'subtest_load_object_path'),
        ]

        for (test_method, test_method_name) in test_methods:
            for (i, test_case) in enumerate(test_cases):
                (text_content, object_content, error_substring) = test_case

                with self.subTest(msg = f"Subtest {test_method_name}, Case {i} ('{text_content}'):"):
                    try:
                        test_method(text_content, object_content)
                    except AssertionError:
                        # The subttest failed an assertion.
                        raise
                    except Exception as ex:
                        error_string = self.format_error_string(ex)
                        if (error_substring is None):
                            self.fail(f"Unexpected error: '{error_string}'.")

                        self.assertIn(error_substring, error_string, 'Error is not as expected.')

                        continue

                    if (error_substring is not None):
                        self.fail(f"Did not get expected error: '{error_substring}'.")

    def _subtest_loads_object(self, text_content, object_content):
        actual_object = edq.util.json.loads_object(text_content, _TestConverter)
        actual_text = edq.util.json.dumps(object_content)
        double_conversion_text = edq.util.json.dumps(actual_object)

        self.assertEqual(object_content, actual_object)
        self.assertEqual(actual_text, double_conversion_text)

    def _subtest_load_object_path(self, text_content, object_content):
        temp_dir = edq.util.dirent.get_temp_dir(prefix = 'edq_test_json_object_path_')

        path_text = os.path.join(temp_dir, 'test-text.json')
        path_object = os.path.join(temp_dir, 'test-object.json')

        edq.util.dirent.write_file(path_text, text_content)
        text_load = edq.util.json.load_object_path(path_text, _TestConverter)

        edq.util.json.dump_path(object_content, path_object)
        object_load = edq.util.json.load_object_path(path_object, _TestConverter)

        self.assertEqual(object_content, text_load)
        self.assertEqual(object_load, text_load)

class _TestConverter(edq.util.json.DictConverter):
    def __init__(self, a: typing.Union[int, None] = None, b: typing.Union[str, None] = None, **kwargs) -> None:
        self.a: typing.Union[int, None] = a
        self.b: typing.Union[str, None] = b

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return vars(self)

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> typing.Any:
        return _TestConverter(**data)
