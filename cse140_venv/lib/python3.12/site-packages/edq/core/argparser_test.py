import functools

import edq.core.argparser
import edq.testing.unittest

class TestArgParser(edq.testing.unittest.BaseTest):
    """ Test argument parsing. """

    def test_callbacks_base(self):
        """ Test the argument parsing callbacks. """

        # [(parse text, [(key, pre, post), ...], skip keys, expected (as dict)), ...]
        test_cases = [
            # Empty
            (
                "",
                [],
                [],
                {
                    '_pre_extra_state_': {},
                    '_post_extra_state_': {},
                },
            ),

            # Single Callbacks
            (
                "",
                [
                    ('test', functools.partial(_pre_callback_append, value = 1), functools.partial(_post_callback_append, value = 2)),
                ],
                [],
                {
                    '_pre_extra_state_': {
                        'append': [1],
                    },
                    '_post_extra_state_': {
                        'append': [2],
                    },
                },
            ),

            # Double Callbacks
            (
                "",
                [
                    ('test1', functools.partial(_pre_callback_append, value = 1), functools.partial(_post_callback_append, value = 2)),
                    ('test2', functools.partial(_pre_callback_append, value = 3), functools.partial(_post_callback_append, value = 4)),
                ],
                [],
                {
                    '_pre_extra_state_': {
                        'append': [1, 3],
                    },
                    '_post_extra_state_': {
                        'append': [2, 4],
                    },
                },
            ),

            # Split Callbacks
            (
                "",
                [
                    ('test1', functools.partial(_pre_callback_append, value = 1), None),
                    ('test2', None, functools.partial(_post_callback_append, value = 4)),
                ],
                [],
                {
                    '_pre_extra_state_': {
                        'append': [1],
                    },
                    '_post_extra_state_': {
                        'append': [4],
                    },
                },
            ),

            # Override Callbacks
            (
                "",
                [
                    ('test', functools.partial(_pre_callback_append, value = 1), functools.partial(_post_callback_append, value = 2)),
                    ('test', functools.partial(_pre_callback_append, value = 3), functools.partial(_post_callback_append, value = 4)),
                ],
                [],
                {
                    '_pre_extra_state_': {
                        'append': [3],
                    },
                    '_post_extra_state_': {
                        'append': [4],
                    },
                },
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (text, registrations, skip_keys, expected) = test_case

            with self.subTest(msg = f"Case {i} ('{text}'):"):
                parser = edq.core.argparser.Parser(f"Case {i}")
                for (key, pre, post) in registrations:
                    parser.register_callbacks(key, pre, post)

                args = parser.parse_args(text.split(), skip_keys = skip_keys)

                actual = vars(args)
                self.assertJSONDictEqual(expected, actual)

def _pre_callback_append(parser, extra_state, key = 'append', value = None) -> None:
    """ Append the given value into the extra state. """

    if (key not in extra_state):
        extra_state[key] = []

    extra_state[key].append(value)

def _post_callback_append(parser, args, extra_state, key = 'append', value = None) -> None:
    """ Append the given value into the extra state. """

    if (key not in extra_state):
        extra_state[key] = []

    extra_state[key].append(value)
