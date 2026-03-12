import edq.testing.unittest
import edq.util.hash

class TestHash(edq.testing.unittest.BaseTest):
    """ Test hash-based operations. """

    def test_sha256_hex_base(self):
        """ Test the base sha256 hash. """

        # [(input, expected), ...]
        test_cases = [
            ('foo', '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae'),
            ('abcdefghijklmnopqrstuvwxyz1234567890', '77d721c817f9d216c1fb783bcad9cdc20aaa2427402683f1f75dd6dfbe657470'),
            ('', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
        ]

        for (i, test_case) in enumerate(test_cases):
            (text, expected) = test_case

            with self.subTest(msg = f"Case {i} ('{text}'):"):
                actual = edq.util.hash.sha256_hex(text)
                self.assertEqual(expected, actual)

    def test_clip_text_base(self):
        """ Test the base functionality of clip_text(). """

        # [(text, max length, kwargs, expected), ...]
        test_cases = [
            # No Clip
            (
                'abcdefghijklmnopqrstuvwxyz1234567890',
                100,
                {},
                'abcdefghijklmnopqrstuvwxyz1234567890',
            ),

            # Base Clip
            (
                'abcdefghijklmnopqrstuvwxyz1234567890',
                30,
                {},
                'abcdefg[text clipped 77d721c8]',
            ),

            # Full Clip
            (
                'abcdefghijklmnopqrstuvwxyz1234567890',
                23,
                {},
                '[text clipped 77d721c8]',
            ),

            # Over Clip
            (
                'abcdefghijklmnopqrstuvwxyz1234567890',
                10,
                {},
                '[text clipped 77d721c8]',
            ),

            # Different Hash Length
            (
                'abcdefghijklmnopqrstuvwxyz1234567890',
                30,
                {'hash_length': 10},
                'abcde[text clipped 77d721c817]',
            ),

            # Notification Longer Than Text
            (
                'abc',
                1,
                {},
                'abc',
            ),
            (
                'abcdefghijklmnopqrstuvwxyz1234567890',
                10,
                {'hash_length': 64},
                'abcdefghijklmnopqrstuvwxyz1234567890',
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (text, max_length, kwargs, expected) = test_case

            with self.subTest(msg = f"Case {i} ('{text}'):"):
                actual = edq.util.hash.clip_text(text, max_length, **kwargs)
                self.assertEqual(expected, actual)
