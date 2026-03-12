import os

import edq.testing.unittest
import edq.util.pyimport

THIS_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
PACKAGE_ROOT_DIR = os.path.join(THIS_DIR, '..')

class TestPyImport(edq.testing.unittest.BaseTest):
    """ Test Python importing operations. """

    def test_import_path_base(self):
        """ Test importing a module from a path. """

        # [(relative path, error substring), ...]
        # All paths are relative to the package root.
        test_cases = [
            # Standard Module
            (os.path.join('util', 'pyimport.py'), None),

            # Errors
            ('ZZZ', 'Module path does not exist'),
            ('util', 'Module path is not a file'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (relpath, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{relpath}'):"):
                path = os.path.join(PACKAGE_ROOT_DIR, relpath)

                try:
                    module = edq.util.pyimport.import_path(path)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertIsNotNone(module)

    def test_import_name_base(self):
        """ Test importing a module from a name. """

        # [(name, error substring), ...]
        test_cases = [
            # Standard Module
            ('edq.util.pyimport', None),

            # Package (__init__.py)
            ('edq.util', None),

            # Errors
            ('', 'Empty module name'),
            ('edq.util.ZZZ', 'Unable to locate module'),
            ('edq.util.pyimport.ZZZ', 'Unable to locate module'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (name, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{name}'):"):
                try:
                    module = edq.util.pyimport.import_name(name)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertIsNotNone(module)

    def test_fetch_base(self):
        """ Test fetching an attribute from a module. """

        # [(name, error substring), ...]
        test_cases = [
            # Standard Module
            ('edq.util.pyimport.fetch', None),

            # Errors
            ('', 'Target name of fetch must be fully qualified'),
            ('edq', 'Target name of fetch must be fully qualified'),
            ('ZZZ.aaa', 'Unable to locate module'),
            ('edq.ZZZ.aaa', 'Unable to locate module'),
            ('edq.util.pyimport.ZZZ', 'does not have attribute'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (name, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{name}'):"):
                try:
                    target = edq.util.pyimport.fetch(name)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertIsNotNone(target)
