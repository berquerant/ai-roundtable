import textwrap
from unittest import TestCase

import ai_roundtable.rule as rule


class TestMessageParser(TestCase):
    def test_read(self):
        testcases = [
            (
                "single",
                textwrap.dedent(
                    """\
            timestamp: 1742785200
            id: 2
            speaker: s1
            permissions: p1
            content:
            body1"""
                ),
                rule.Message(
                    timestamp=1742785200,
                    id=2,
                    speaker="s1",
                    permissions={"p1"},
                    content=textwrap.dedent(
                        """\
                body1"""
                    ),
                ),
            ),
            (
                "multipermissions",
                textwrap.dedent(
                    """\
            timestamp: 1742785200
            id: 2
            speaker: s1
            permissions: p1,p2
            content:
            body1"""
                ),
                rule.Message(
                    timestamp=1742785200,
                    id=2,
                    speaker="s1",
                    permissions={"p1", "p2"},
                    content=textwrap.dedent(
                        """\
                body1"""
                    ),
                ),
            ),
            (
                "multilines multipermissions",
                textwrap.dedent(
                    """\
            timestamp: 1742785200
            id: 2
            speaker: s1
            permissions: p1,p2
            content:
            body1
            body2"""
                ),
                rule.Message(
                    timestamp=1742785200,
                    id=2,
                    speaker="s1",
                    permissions={"p1", "p2"},
                    content=textwrap.dedent(
                        """\
                body1
                body2"""
                    ),
                ),
            ),
        ]
        for title, v, want in testcases:
            with self.subTest(title):
                got = rule.MessageParser.read(v)
                self.assertEqual(want, got)
                rv = rule.MessageParser.into_read(got)
                self.assertEqual(v, rv)

    def test_write(self):
        testcases = [
            (
                "multilines",
                textwrap.dedent(
                    """\
        role: r1
        content:
        body1
        body2"""
                ),
                rule.WriteMessage(
                    role="r1",
                    content=textwrap.dedent(
                        """\
        body1
        body2"""
                    ),
                ),
            ),
            (
                "singleline",
                textwrap.dedent(
                    """\
        role: r1
        content:
        body1"""
                ),
                rule.WriteMessage(
                    role="r1",
                    content=textwrap.dedent(
                        """\
        body1"""
                    ),
                ),
            ),
        ]
        for title, v, want in testcases:
            with self.subTest(title):
                got = rule.MessageParser.write(v)
                self.assertEqual(want, got)
