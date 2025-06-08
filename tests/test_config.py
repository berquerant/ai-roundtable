import textwrap
from unittest import TestCase

import ai_roundtable.config as config


class TestRole(TestCase):
    def test_parse(self):
        testcases = [
            (
                "singles without thread",
                textwrap.dedent(
                    """\
                    speakers:
                    - desc: s1desc
                      name: s1
                    """,
                ),
                "",
                config.Config(
                    speakers=[config.Speaker(name="s1", desc="s1desc")],
                    main_thread=config.MainThread(messages=[]),
                ),
            ),
            (
                "singles",
                textwrap.dedent(
                    """\
                    speakers:
                    - desc: s1desc
                      name: s1
                    """,
                ),
                textwrap.dedent(
                    """\
                    - speaker: s1
                      content: |
                        content1
                    """,
                ),
                config.Config(
                    speakers=[config.Speaker(name="s1", desc="s1desc")],
                    main_thread=config.MainThread(
                        messages=[
                            config.Message(
                                speaker="s1",
                                content="content1\n",
                            ),
                        ]
                    ),
                ),
            ),
            (
                "multiples",
                textwrap.dedent(
                    """\
                    speakers:
                    - name: s1
                      desc: s1desc
                    - name: s2
                      desc: s2desc
                    """,
                ),
                textwrap.dedent(
                    """\
                    - speaker: s1
                      content: |
                        content1
                    - speaker: s2
                      content: |
                        content2
                        end
                    """,
                ),
                config.Config(
                    speakers=[
                        config.Speaker(name="s1", desc="s1desc"),
                        config.Speaker(name="s2", desc="s2desc"),
                    ],
                    main_thread=config.MainThread(
                        messages=[
                            config.Message(
                                speaker="s1",
                                content="content1\n",
                            ),
                            config.Message(
                                speaker="s2",
                                content="content2\nend\n",
                            ),
                        ]
                    ),
                ),
            ),
        ]
        for title, c, t, want in testcases:
            with self.subTest(title):
                want.validate()
                got = config.ConfigYaml(config=c, thread=t).into_config()
                self.assertEqual(want, got)
                rgot = config.ConfigYaml.from_config(want).into_config()
                self.assertEqual(want, rgot)
