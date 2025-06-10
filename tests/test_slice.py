from unittest import TestCase

import ai_roundtable.slice as slice


class TestSlice(TestCase):
    def test_find(self):
        testcases = [
            (
                "found",
                [1, 2, 3],
                lambda x: x > 2,
                3,
            ),
            (
                "not found",
                [1, 2, 3],
                lambda _: False,
                None,
            ),
        ]
        for title, items, pred, want in testcases:
            with self.subTest(title):
                got = slice.find(items, pred)
                self.assertEqual(want, got)
