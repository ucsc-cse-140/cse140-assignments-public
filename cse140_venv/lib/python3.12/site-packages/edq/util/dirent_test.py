import os
import sys

import edq.testing.unittest
import edq.util.dirent

DIRENT_TYPE_DIR = 'dir'
DIRENT_TYPE_FILE = 'file'
DIRENT_TYPE_BROKEN_SYMLINK = 'broken_symlink'

def create_test_dir(temp_dir_prefix: str) -> str:
    """
    Create a temp dir and populate it with dirents for testing.

    This test data directory is laid out as:
    .
    ├── a.txt
    ├── dir_1
    │   ├── b.txt
    │   └── dir_2
    │       └── c.txt
    ├── dir_empty
    ├── file_empty
    ├── symlink_a.txt -> a.txt
    ├── symlink_dir_1 -> dir_1
    ├── symlink_dir_empty -> dir_empty
    └── symlink_file_empty -> file_empty

    Where non-empty files are filled with their filename (without the extension).
    """

    temp_dir = edq.util.dirent.get_temp_dir(prefix = temp_dir_prefix)

    # Dirs
    edq.util.dirent.mkdir(os.path.join(temp_dir, 'dir_1', 'dir_2'))
    edq.util.dirent.mkdir(os.path.join(temp_dir, 'dir_empty'))

    # Files
    edq.util.dirent.write_file(os.path.join(temp_dir, 'a.txt'), 'a')
    edq.util.dirent.write_file(os.path.join(temp_dir, 'file_empty'), '')
    edq.util.dirent.write_file(os.path.join(temp_dir, 'dir_1', 'b.txt'), 'b')
    edq.util.dirent.write_file(os.path.join(temp_dir, 'dir_1', 'dir_2', 'c.txt'), 'c')

    # Links
    os.symlink('a.txt', os.path.join(temp_dir, 'symlink_a.txt'))
    os.symlink('dir_1', os.path.join(temp_dir, 'symlink_dir_1'))
    os.symlink('dir_empty', os.path.join(temp_dir, 'symlink_dir_empty'))
    os.symlink('file_empty', os.path.join(temp_dir, 'symlink_file_empty'))

    return temp_dir

class TestDirent(edq.testing.unittest.BaseTest):
    """ Test basic operations on dirents. """

    def test_setup(self):
        """ Test that the base temp directory is properly setup. """

        temp_dir = self._prep_temp_dir()

        expected_paths = [
            ('a.txt', DIRENT_TYPE_FILE),
            ('dir_1', DIRENT_TYPE_DIR),
            (os.path.join('dir_1', 'b.txt'), DIRENT_TYPE_FILE),
            (os.path.join('dir_1', 'dir_2'), DIRENT_TYPE_DIR),
            (os.path.join('dir_1', 'dir_2', 'c.txt'), DIRENT_TYPE_FILE),
            ('dir_empty', DIRENT_TYPE_DIR),
            ('file_empty', DIRENT_TYPE_FILE),
            ('symlink_a.txt', DIRENT_TYPE_FILE, True),
            ('symlink_dir_1', DIRENT_TYPE_DIR, True),
            ('symlink_dir_empty', DIRENT_TYPE_DIR, True),
            ('symlink_file_empty', DIRENT_TYPE_FILE, True),
        ]

        self._check_existing_paths(temp_dir, expected_paths)

    def test_contains_path_base(self):
        """ Test checking path containment. """

        temp_dir = self._prep_temp_dir()

        # [(parent, child, contains?), ...]
        test_cases = [
            # Containment
            ('a', os.path.join('a', 'b', 'c'), True),
            (os.path.join('a', 'b'), os.path.join('a', 'b', 'c'), True),
            ('.', os.path.join('a', 'b', 'c'), True),
            ('..', '.', True),

            # Self No Containment
            ('a', 'a', False),
            (os.path.join('a', 'b', 'c'), os.path.join('a', 'b', 'c'), False),
            ('.', '.', False),

            # Trivial No Containment
            ('a', 'b', False),
            ('z', os.path.join('a', 'b', 'c'), False),
            ('aa', os.path.join('a', 'b', 'c'), False),
            ('a', os.path.join('aa', 'b', 'c'), False),

            # Child Contains Parent
            (os.path.join('a', 'b', 'c'), 'a', False),
            (os.path.join('a', 'b', 'c'), os.path.join('a', 'b'), False),
        ]

        for (i, test_case) in enumerate(test_cases):
            (parent, child, expected) = test_case

            with self.subTest(msg = f"Case {i} ('{parent}' ⊂ '{child}'):"):
                parent = os.path.join(temp_dir, parent)
                child = os.path.join(temp_dir, child)

                actual = edq.util.dirent.contains_path(parent, child)
                self.assertEqual(expected, actual)

    def test_read_write_file_bytes_base(self):
        """ Test reading and writing a file as bytes. """

        # [(path, write kwargs, read kwargs, write contents, expected contents, error substring), ...]
        # All conent should be strings that will be encoded.
        test_cases = [
            # Base
            (
                "test.txt",
                {},
                {},
                "test",
                "test",
                None,
            ),

            # Empty Write
            (
                "test.txt",
                {},
                {},
                "",
                "",
                None,
            ),

            # None Write
            (
                "test.txt",
                {},
                {},
                None,
                "",
                None,
            ),

            # Clobber
            (
                "a.txt",
                {},
                {},
                "test",
                "test",
                None,
            ),
            (
                "dir_1",
                {},
                {},
                "test",
                "test",
                None,
            ),
            (
                "symlink_a.txt",
                {},
                {},
                "test",
                "test",
                None,
            ),

            # No Clobber
            (
                "a.txt",
                {'no_clobber': True},
                {},
                "test",
                "test",
                'already exists',
            ),
            (
                "dir_1",
                {'no_clobber': True},
                {},
                "test",
                "test",
                'already exists',
            ),
            (
                "symlink_a.txt",
                {'no_clobber': True},
                {},
                "test",
                "test",
                'already exists',
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (path, write_options, read_options, write_contents, expected_contents, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{path}'):"):
                temp_dir = self._prep_temp_dir()
                path = os.path.join(temp_dir, path)

                if (write_contents is not None):
                    write_contents = bytes(write_contents, edq.util.dirent.DEFAULT_ENCODING)

                expected_contents = bytes(expected_contents, edq.util.dirent.DEFAULT_ENCODING)

                try:
                    edq.util.dirent.write_file_bytes(path, write_contents, **write_options)
                    actual_contents = edq.util.dirent.read_file_bytes(path, **read_options)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertEqual(expected_contents, actual_contents)

    def test_read_write_file_base(self):
        """ Test reading and writing a file. """

        # [(path, write kwargs, read kwargs, write contents, expected contents, error substring), ...]
        test_cases = [
            # Base
            (
                "test.txt",
                {},
                {},
                "test",
                "test",
                None,
            ),

            # Defaults
            (
                "test.txt",
                {},
                {},
                " test ",
                "test",
                None,
            ),

            # No Modifications
            (
                "test.txt",
                {'strip': False, 'newline': False},
                {'strip': False},
                " test ",
                " test ",
                None,
            ),

            # No Strip
            (
                "test.txt",
                {'strip': False, 'newline': True},
                {'strip': False},
                " test ",
                " test \n",
                None,
            ),

            # No Read Strip
            (
                "test.txt",
                {},
                {'strip': False},
                "test",
                "test\n",
                None,
            ),

            # Empty Write
            (
                "test.txt",
                {'newline': False},
                {},
                "",
                "",
                None,
            ),

            # None Write
            (
                "test.txt",
                {'newline': False},
                {},
                None,
                "",
                None,
            ),

            # Clobber
            (
                "a.txt",
                {},
                {},
                "test",
                "test",
                None,
            ),
            (
                "dir_1",
                {},
                {},
                "test",
                "test",
                None,
            ),
            (
                "symlink_a.txt",
                {},
                {},
                "test",
                "test",
                None,
            ),

            # No Clobber
            (
                "a.txt",
                {'no_clobber': True},
                {},
                "test",
                "test",
                'Destination of write already exists',
            ),
            (
                "dir_1",
                {'no_clobber': True},
                {},
                "test",
                "test",
                'Destination of write already exists',
            ),
            (
                "symlink_a.txt",
                {'no_clobber': True},
                {},
                "test",
                "test",
                'Destination of write already exists',
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (path, write_options, read_options, write_contents, expected_contents, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{path}'):"):
                temp_dir = self._prep_temp_dir()
                path = os.path.join(temp_dir, path)

                try:
                    edq.util.dirent.write_file(path, write_contents, **write_options)
                    actual_contents = edq.util.dirent.read_file(path, **read_options)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertEqual(expected_contents, actual_contents)

    def test_copy_contents_base(self):
        """ Test copying the contents of a dirent. """

        # [(source, dest, no clobber?, error substring), ...]
        test_cases = [
            ('a.txt', 'dir_1', False, None),
            ('a.txt', 'ZZZ', False, None),
            ('dir_empty', 'dir_1', False, None),

            ('dir_1', 'dir_1', False, 'Source and destination of contents copy cannot be the same'),
            ('dir_empty', 'symlink_dir_empty', False, 'Source and destination of contents copy cannot be the same'),

            ('a.txt', 'file_empty', False, 'Destination of contents copy exists and is not a dir'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (source, dest, no_clobber, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{source}' -> '{dest}'):"):
                temp_dir = self._prep_temp_dir()

                source = os.path.join(temp_dir, source)
                dest = os.path.join(temp_dir, dest)

                try:
                    edq.util.dirent.copy_contents(source, dest, no_clobber = no_clobber)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

    def test_copy_base(self):
        """ Test copying dirents. """

        # [(source, dest, no_clobber?, error substring), ...]
        test_cases = [
            # File
            ('a.txt', 'test.txt', False, None),
            ('a.txt', 'test.txt', True, None),
            ('a.txt', os.path.join('dir_1', 'test.txt'), False, None),
            ('a.txt', os.path.join('dir_1', 'test.txt'), True, None),

            # File - Clobber
            ('a.txt', 'file_empty', False, None),
            ('a.txt', os.path.join('dir_1', 'b.txt'), False, None),
            ('a.txt', 'dir_1', False, None),
            ('a.txt', os.path.join('dir_1', 'dir_2'), False, None),

            # File - No Clobber
            ('a.txt', 'file_empty', True, 'Destination of copy already exists'),
            ('a.txt', os.path.join('dir_1', 'b.txt'), True, 'Destination of copy already exists'),
            ('a.txt', 'dir_1', True, 'Destination of copy already exists'),
            ('a.txt', os.path.join('dir_1', 'dir_2'), True, 'Destination of copy already exists'),

            # Dir
            ('dir_empty', 'test', False, None),
            ('dir_empty', 'test', True, None),
            ('dir_empty', os.path.join('dir_1', 'test'), False, None),
            ('dir_empty', os.path.join('dir_1', 'test'), True, None),

            # Dir - Clobber
            ('dir_empty', 'file_empty', False, None),
            ('dir_empty', os.path.join('dir_1', 'b.txt'), False, None),
            ('dir_empty', 'dir_1', False, None),
            ('dir_empty', os.path.join('dir_1', 'dir_2'), False, None),

            # Dir - No Clobber
            ('dir_empty', 'file_empty', True, 'Destination of copy already exists'),
            ('dir_empty', os.path.join('dir_1', 'b.txt'), True, 'Destination of copy already exists'),
            ('dir_empty', 'dir_1', True, 'Destination of copy already exists'),
            ('dir_empty', os.path.join('dir_1', 'dir_2'), True, 'Destination of copy already exists'),

            # Link
            ('symlink_a.txt', 'test.txt', False, None),
            ('symlink_dir_1', 'test', False, None),
            ('symlink_dir_empty', 'test', False, None),
            ('symlink_file_empty', 'test.txt', False, None),

            # Link - Clobber
            ('symlink_a.txt', 'file_empty', False, None),
            ('symlink_a.txt', 'symlink_dir_1', False, None),

            # Link - No Clobber
            ('symlink_a.txt', 'file_empty', True, 'Destination of copy already exists'),
            ('symlink_a.txt', 'symlink_dir_1', True, 'Destination of copy already exists'),

            # Clobber Parent
            (os.path.join('dir_1', 'b.txt'), 'dir_1', False, 'Destination of copy cannot contain the source.'),

            # Same
            ('a.txt', 'a.txt', False, None),
            ('symlink_a.txt', 'a.txt', False, None),
            ('a.txt', 'a.txt', True, None),
            ('symlink_a.txt', 'a.txt', True, None),

            # Missing Source
            ('ZZZ', 'test.txt', False, 'Source of copy does not exist'),
            ('ZZZ', 'test.txt', True, 'Source of copy does not exist'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (source, dest, no_clobber, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{source}' -> '{dest}'):"):
                temp_dir = self._prep_temp_dir()

                source = os.path.join(temp_dir, source)
                dest = os.path.join(temp_dir, dest)

                try:
                    edq.util.dirent.copy(source, dest, no_clobber = no_clobber)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                dirent_type, is_link = self._get_dirent_type(source)

                checks = [
                    (source, dirent_type, is_link),
                ]

                if (not edq.util.dirent.same(source, dest)):
                    checks += [
                        (dest, dirent_type, is_link),
                    ]

                self._check_existing_paths(temp_dir, checks)

    def test_copy_special_matching_subdir_name(self):
        """ Test copying a special case of copying a files into themselves with matching names. """

        base_dir = edq.util.dirent.get_temp_dir()

        target_dir = os.path.join(base_dir, 'already_exists')
        target_file = os.path.join(target_dir, 'already_exists.txt')

        edq.util.dirent.mkdir(target_dir)
        edq.util.dirent.write_file(target_file, 'aaa')

        try:
            edq.util.dirent.copy(target_dir, target_file)
            self.fail("Did not get expected error.")
        except Exception as ex:
            error_string = self.format_error_string(ex)
            self.assertIn('Source of copy cannot contain the destination', error_string, 'Error is not as expected.')

        try:
            edq.util.dirent.copy(target_file, target_dir)
            self.fail("Did not get expected error.")
        except Exception as ex:
            error_string = self.format_error_string(ex)
            self.assertIn('Destination of copy cannot contain the source', error_string, 'Error is not as expected.')

    def test_same_base(self):
        """ Test checking for two paths pointing to the same dirent. """

        temp_dir = self._prep_temp_dir()

        # [(path, path, same?), ...]
        test_cases = [
            # Same
            ('a.txt', 'a.txt', True),
            ('dir_1', 'dir_1', True),
            (os.path.join('dir_1', 'b.txt'), os.path.join('dir_1', 'b.txt'), True),
            (os.path.join('dir_1', 'b.txt'), os.path.join('dir_1', '..', 'dir_1', 'b.txt'), True),

            # Not Same
            ('a.txt', 'dir_1', False),
            ('a.txt', os.path.join('dir_1', 'b.txt'), False),
            ('a.txt', 'file_empty', False),
            ('a.txt', 'dir_empty', False),

            # Not Exists
            ('a.txt', 'ZZZ', False),
            (os.path.join('dir_1', 'b.txt'), os.path.join('dir_1', 'ZZZ'), False),
            (os.path.join('dir_1', 'b.txt'), os.path.join('ZZZ', 'b.txt'), False),

            # Links
            ('a.txt', 'symlink_a.txt', True),
            ('a.txt', 'symlink_file_empty', False),
            ('dir_1', 'symlink_dir_1', True),
            ('dir_1', 'symlink_dir_empty', False),
        ]

        for (i, test_case) in enumerate(test_cases):
            (a, b, expected) = test_case

            with self.subTest(msg = f"Case {i} ('{a}' vs '{b}'):"):
                a = os.path.join(temp_dir, a)
                b = os.path.join(temp_dir, b)

                actual = edq.util.dirent.same(a, b)
                self.assertEqual(expected, actual)

    def test_mkdir_base(self):
        """ Test creating directories. """

        temp_dir = self._prep_temp_dir()

        # [(path, error substring), ...]
        test_cases = [
            # Base
            ('new_dir_1', None),
            (os.path.join('dir_1', 'new_dir_2'), None),

            # Missing Parents
            (os.path.join('ZZZ', 'new_dir_ZZZ'), None),
            (os.path.join('ZZZ', 'YYY', 'XXX', 'new_dir_XXX'), None),

            # Existing Dir
            ('dir_1', None),
            ('dir_empty', None),
            ('symlink_dir_1', None),

            # Existing Non-Dir
            ('a.txt', 'Target of mkdir already exists'),
            ('symlink_a.txt', 'Target of mkdir already exists'),

            # Existing Non-Dir Parent
            (os.path.join('dir_1', 'b.txt', 'BBB'), 'Target of mkdir contains parent'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (path, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{path}'):"):
                path = os.path.join(temp_dir, path)

                try:
                    edq.util.dirent.mkdir(path)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertTrue(edq.util.dirent.exists(path), 'Dir does not exist post mkdir.')

    def test_get_temp_path_base(self):
        """ Ensure that temp paths are not the same. """

        a = edq.util.dirent.get_temp_path()
        b = edq.util.dirent.get_temp_path()

        self.assertNotEqual(a, b)

    def test_get_temp_dir_base(self):
        """ Ensure that the temp dir exists. """

        path = edq.util.dirent.get_temp_dir()
        self.assertTrue(edq.util.dirent.exists(path))

    def test_exists_base(self):
        """
        Test checking for existence.

        ./dir_empty and ./file_empty will be removed to check for broken links.
        """

        temp_dir = self._prep_temp_dir()

        # Remove some dirents to break links.
        edq.util.dirent.remove(os.path.join(temp_dir, 'dir_empty'))
        edq.util.dirent.remove(os.path.join(temp_dir, 'file_empty'))

        # [(path, exists?), ...]
        test_cases = [
            # File
            ('a.txt', True),
            (os.path.join('dir_1', 'b.txt'), True),

            # Dir
            ('dir_1', True),
            (os.path.join('dir_1', 'dir_2'), True),

            # Links
            ('symlink_a.txt', True),
            ('symlink_dir_1', True),
            ('symlink_dir_empty', True),  # Broken Link
            ('symlink_file_empty', True),  # Broken Link

            # Not Exists
            ('dir_empty', False),
            ('file_empty', False),
            (os.path.join('dir_1', 'ZZZ'), False),
        ]

        for (i, test_case) in enumerate(test_cases):
            (path, expected) = test_case

            with self.subTest(msg = f"Case {i} ('{path}'):"):
                path = os.path.join(temp_dir, path)
                actual = edq.util.dirent.exists(path)
                self.assertEqual(expected, actual)

    def test_move_base(self):
        """
        Test moving dirents.

        This test will create some additional dirents:
        ├── dir_1
        │   └── dir_2
        │       ├── a.txt
        │       └── dir_empty
        """

        # [(source, dest, no_clobber?, error substring), ...]
        # The dest can be a single string, or a tuple of (operation input, expected output).
        test_cases = [
            # File
            ('a.txt', 'test.txt', False, None),

            # Move into Dir - Explicit
            ('a.txt', os.path.join('dir_1', 'a.txt'), False, None),

            # Move into Dir - Implicit
            ('a.txt', ('dir_1', os.path.join('dir_1', 'a.txt')), False, None),

            # Move out of Dir
            (os.path.join('dir_1', 'b.txt'), 'b.txt', False, None),

            # Missing Parents
            ('a.txt', os.path.join('dir_1', 'a', 'b', 'a.txt'), False, None),

            # Same File
            ('a.txt', 'a.txt', False, None),

            # Clobber File with File
            ('a.txt', os.path.join('dir_1', 'b.txt'), False, None),

            # No Clobber File with File
            ('a.txt', os.path.join('dir_1', 'b.txt'), True, 'Destination of move already exists'),

            # Clobber File with File - Implicit
            ('a.txt', (os.path.join('dir_1', 'dir_2'), os.path.join('dir_1', 'dir_2', 'a.txt')), False, None),

            # No Clobber File with File - Implicit
            ('a.txt', os.path.join('dir_1', 'dir_2'), True, 'Destination of move already exists'),

            # Clobber Dir with Dir
            ('dir_empty', 'dir_1', False, None),

            # Clobber Dir with Dir - Implicit
            ('dir_empty', (os.path.join('dir_1', 'dir_2'), os.path.join('dir_1', 'dir_2', 'dir_empty')), False, None),

            # No Clobber Dir with Dir - Implicit
            ('dir_empty', os.path.join('dir_1', 'dir_2'), True, 'Destination of move already exists'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (source, raw_dest, no_clobber, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{source}' -> '{raw_dest}'):"):
                temp_dir = self._prep_temp_dir()

                # Create the additional dirents for this test.
                edq.util.dirent.copy(os.path.join(temp_dir, 'a.txt'), os.path.join(temp_dir, 'dir_1', 'dir_2', 'a.txt'))
                edq.util.dirent.copy(os.path.join(temp_dir, 'dir_empty'), os.path.join(temp_dir, 'dir_1', 'dir_2', 'dir_empty'))

                if (isinstance(raw_dest, tuple)):
                    (input_dest, expected_dest) = raw_dest
                else:
                    input_dest = raw_dest
                    expected_dest = raw_dest

                source = os.path.join(temp_dir, source)
                input_dest = os.path.join(temp_dir, input_dest)
                expected_dest = os.path.join(temp_dir, expected_dest)

                try:
                    edq.util.dirent.move(source, input_dest, no_clobber = no_clobber)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self._check_existing_paths(temp_dir, [expected_dest])

                if (not edq.util.dirent.same(os.path.join(temp_dir, source), os.path.join(temp_dir, expected_dest))):
                    self._check_nonexisting_paths(temp_dir, [source])

    def test_move_rename(self):
        """ Test renaming dirents (via move()). """

        temp_dir = self._prep_temp_dir()

        # [(source, dest, expected error), ...]
        rename_relpaths = [
            # Symlink - File
            ('symlink_a.txt', 'rename_symlink_a.txt', None),

            # Symlink - Dir
            ('symlink_dir_1', 'rename_symlink_dir_1', None),

            # File in Directory
            (os.path.join('dir_1', 'dir_2', 'c.txt'), os.path.join('dir_1', 'dir_2', 'rename_c.txt'), None),

            # File
            ('a.txt', 'rename_a.txt', None),

            # Empty File
            ('file_empty', 'rename_file_empty', None),

            # Directory
            ('dir_1', 'rename_dir_1', None),

            # Empty Directory
            ('dir_empty', 'rename_dir_empty', None),

            # Non-Existent
            ('ZZZ', 'rename_ZZZ', 'Source of move does not exist'),
        ]

        expected_paths = [
            ('rename_a.txt', DIRENT_TYPE_FILE),
            ('rename_dir_1', DIRENT_TYPE_DIR),
            (os.path.join('rename_dir_1', 'b.txt'), DIRENT_TYPE_FILE),
            (os.path.join('rename_dir_1', 'dir_2'), DIRENT_TYPE_DIR),
            (os.path.join('rename_dir_1', 'dir_2', 'rename_c.txt'), DIRENT_TYPE_FILE),
            ('rename_dir_empty', DIRENT_TYPE_DIR),
            ('rename_file_empty', DIRENT_TYPE_FILE),
            ('rename_symlink_a.txt', DIRENT_TYPE_BROKEN_SYMLINK, True),
            ('rename_symlink_dir_1', DIRENT_TYPE_BROKEN_SYMLINK, True),
            ('symlink_dir_empty', DIRENT_TYPE_BROKEN_SYMLINK, True),
            ('symlink_file_empty', DIRENT_TYPE_BROKEN_SYMLINK, True),
        ]

        unexpected_paths = [
            'symlink_a.txt',
            'symlink_dir_1',
            os.path.join('dir_1', 'dir_2', 'c.txt'),
            'a.txt',
            'file_empty',
            'dir_1',
            'dir_empty',
            'ZZZ',
            'rename_ZZZ',
        ]

        for (i, test_case) in enumerate(rename_relpaths):
            (source, dest, error_substring) = test_case

            source = os.path.join(temp_dir, source)
            dest = os.path.join(temp_dir, dest)

            try:
                edq.util.dirent.move(source, dest)
            except Exception as ex:
                error_string = self.format_error_string(ex)
                if (error_substring is None):
                    self.fail(f"Case {i}: Unexpected error: '{error_string}'.")

                self.assertIn(error_substring, error_string, 'Error is not as expected.')

                continue

            if (error_substring is not None):
                self.fail(f"Case {i}: Did not get expected error: '{error_substring}'.")

        self._check_nonexisting_paths(temp_dir, unexpected_paths)
        self._check_existing_paths(temp_dir, expected_paths)

    def test_remove_base(self):
        """ Test removing dirents. """

        temp_dir = self._prep_temp_dir()

        # Remove these paths in this order.
        remove_relpaths = [
            # Symlink - File
            'symlink_a.txt',

            # Symlink - Dir
            'symlink_dir_1',

            # File in Directory
            os.path.join('dir_1', 'dir_2', 'c.txt'),

            # File
            'a.txt',

            # Empty File
            'file_empty'

            # Directory
            'dir_1',

            # Empty Directory
            'dir_empty',

            # Non-Existent
            'ZZZ',
        ]

        expected_paths = [
            (os.path.join('dir_1', 'dir_2'), DIRENT_TYPE_DIR),
            ('file_empty', DIRENT_TYPE_FILE),
            # Windows has some symlink issues, so we will not check for this file.
            # ('symlink_dir_empty', DIRENT_TYPE_DIR, True),
        ]

        for relpath in remove_relpaths:
            path = os.path.join(temp_dir, relpath)
            edq.util.dirent.remove(path)

        self._check_nonexisting_paths(temp_dir, remove_relpaths)
        self._check_existing_paths(temp_dir, expected_paths)

    def test_tree_base(self):
        """
        Test getting a recursive tree for a directory.
        """

        temp_dir = self._prep_temp_dir()

        expected = {
            "edq_test_dirent": {
                "a.txt": "87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7",
                "dir_1": {
                    "b.txt": "0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f",
                    "dir_2": {
                        "c.txt": "a3a5e715f0cc574a73c3f9bebb6bc24f32ffd5b67b387244c2c909da779a1478"
                    }
                },
                "dir_empty": {},
                "file_empty": "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
                "symlink_a.txt": "18b7cb099a9ea3f50ba899b5ba81e0d377a5f3b16f8f6eeb8b3e58cd4692b993",
                "symlink_dir_1": {
                    "b.txt": "0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f",
                    "dir_2": {
                        "c.txt": "a3a5e715f0cc574a73c3f9bebb6bc24f32ffd5b67b387244c2c909da779a1478"
                    }
                },
                "symlink_dir_empty": {},
                "symlink_file_empty": "d6c5062a84a73af45c634ede745be0d3bde0c3e676fe6a2732ca38e3e4fb5f37"
            }
        }

        # Windows will have different hashes.
        if (sys.platform == 'win32'):
            expected = {
                "edq_test_dirent": {
                    "a.txt": "8e4621379786ef42a4fec155cd525c291dd7db3c1fde3478522f4f61c03fd1bd",
                    "dir_1": {
                        "b.txt": "679e273f78fc8f8ba114db23c2dce80cc77c91083939825ca830152f2f080d08",
                        "dir_2": {
                            "c.txt": "ef1fac987a48a7c02176f7e1c2d0e5cbda826c9558290ba153c90ea16d5d5a96"
                        }
                    },
                    "dir_empty": {},
                    "file_empty": "7eb70257593da06f682a3ddda54a9d260d4fc514f645237f5ca74b08f8da61a6",
                    "symlink_a.txt": "abc123",
                    "symlink_dir_1": {
                        "b.txt": "679e273f78fc8f8ba114db23c2dce80cc77c91083939825ca830152f2f080d08",
                        "dir_2": {
                            "c.txt": "ef1fac987a48a7c02176f7e1c2d0e5cbda826c9558290ba153c90ea16d5d5a96"
                        }
                    },
                    "symlink_dir_empty": {},
                    "symlink_file_empty": "abc123"
                }
            }

        actual = edq.util.dirent.tree(temp_dir, hash_files = True)

        # Normalize the top-level key.
        key = list(actual.keys())[0]
        actual['edq_test_dirent'] = actual.pop(key)

        # Normalize symlinks.
        expected['edq_test_dirent']['symlink_a.txt'] = 'abc123'
        expected['edq_test_dirent']['symlink_file_empty'] = 'abc123'
        actual['edq_test_dirent']['symlink_a.txt'] = 'abc123'
        actual['edq_test_dirent']['symlink_file_empty'] = 'abc123'

        self.assertJSONEqual(expected, actual)

    def _prep_temp_dir(self):
        return create_test_dir('edq_test_dirent_')

    def _check_existing_paths(self, base_dir, raw_paths):
        """
        Ensure that specific paths exists, and fail the test if they do not.
        All paths should be relative to the base dir.
        Paths can be:
         - A string.
         - A two-item tuple (path, dirent type).
         - A three-item tuple (path, dirent type, is link?).
        Missing components are not defaulted, they are just not checked.
        """

        for raw_path in raw_paths:
            relpath = ''
            dirent_type = None
            is_link = False

            if (isinstance(raw_path, str)):
                relpath = raw_path
            elif (isinstance(raw_path, tuple)):
                if (len(raw_path) not in [2, 3]):
                    raise ValueError(f"Expected exactly two or three items for path check, found {len(raw_path)} items: '{raw_path}'.")

                relpath = raw_path[0]
                dirent_type = raw_path[1]

                if (len(raw_path) == 3):
                    is_link = raw_path[2]
            else:
                raise ValueError(f"Could not parse expected path ({type(raw_path)}): '{raw_path}'.")

            path = os.path.join(base_dir, relpath)

            # Check the path exists.
            if (not edq.util.dirent.exists(path)):
                self.fail(f"Expected path does not exist: '{relpath}'.")

            # Check the link status.
            if (is_link is not None):
                if (is_link != os.path.islink(path)):
                    self.fail(f"Expected path does not have a matching link status. Expected {is_link}, but is {not is_link}: '{relpath}'.")

            # Check the type of the dirent.
            if (dirent_type is not None):
                if (dirent_type == DIRENT_TYPE_DIR):
                    if (not os.path.isdir(path)):
                        self.fail(f"Expected path to be a directory, but it is not: '{relpath}'.")
                elif (dirent_type == DIRENT_TYPE_FILE):
                    if (not os.path.isfile(path)):
                        self.fail(f"Expected path to be a file, but it is not: '{relpath}'.")
                elif (dirent_type == DIRENT_TYPE_BROKEN_SYMLINK):
                    if ((not os.path.islink(path)) or os.path.isfile(path) or os.path.isdir(path)):
                        self.fail(f"Expected path to be a broken link, but it is not: '{relpath}'.")
                else:
                    raise ValueError(f"Unknown dirent type '{dirent_type}' for path: '{relpath}'.")

    def _check_nonexisting_paths(self, base_dir, raw_paths):
        """
        Ensure that specific paths do not exists, and fail the test if they do exist.
        All paths should be relative to the base dir.
        Unlike _check_existing_paths(), paths should only be strings.
        """

        for relpath in raw_paths:
            path = os.path.join(base_dir, relpath)

            if (edq.util.dirent.exists(path)):
                self.fail(f"Path exists when it should not: '{relpath}'.")

    def _get_dirent_type(self, path):
        is_link = os.path.islink(path)
        dirent_type = None

        if (os.path.isdir(path)):
            dirent_type = DIRENT_TYPE_DIR
        elif (os.path.isfile(path)):
            dirent_type = DIRENT_TYPE_FILE
        elif (os.path.islink(path)):
            dirent_type = DIRENT_TYPE_BROKEN_SYMLINK
        else:
            raise ValueError(f"Unknown dirent type: '{path}'.")

        return dirent_type, is_link
