import os

import edq.testing.unittest

import edq.util.dirent
import edq.util.gzip

THIS_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
DATA_DIR = os.path.join(THIS_DIR, 'testdata', 'gzip')

class TestGzip(edq.testing.unittest.BaseTest):
    """ Test gzipping functionality. """

    def test_file_base(self):
        """ Test file-based operations. """

        text_contents = 'abc123'
        base_path = edq.util.dirent.get_temp_path('edq-testing-gzip-bytes-base-')
        edq.util.dirent.write_file(base_path, text_contents, newline = False)

        data = edq.util.gzip.compress_path(base_path)
        output_string = edq.util.gzip.uncompress_to_string(data)

        self.assertEqual(text_contents, output_string, 'Decompressed data does not match raw file data.')

        direct_path = edq.util.dirent.get_temp_path('edq-testing-gzip-bytes-direct-')
        edq.util.gzip.uncompress_to_path(data, direct_path)

        self.assertFileHashEqual(base_path, direct_path)

    def test_file_base64(self):
        """ Test file-based operations using base64. """

        text_contents = 'abc123'
        base_path = edq.util.dirent.get_temp_path('edq-testing-gzip-base64-base')
        edq.util.dirent.write_file(base_path, text_contents, newline = False)

        data = edq.util.gzip.compress_path_as_base64(base_path)
        output = edq.util.gzip.uncompress_base64_to_string(data)

        self.assertEqual(text_contents, output, 'Decompressed data does not match raw file data.')

        direct_path = edq.util.dirent.get_temp_path('edq-testing-gzip-base64-direct-')
        edq.util.gzip.uncompress_base64_to_path(data, direct_path)

        self.assertFileHashEqual(base_path, direct_path)
