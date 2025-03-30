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
                    permissions:
                    - name: p1
                    roles:
                    - desc: r1desc
                      name: r1
                      permissions:
                      - p1
                    speakers:
                    - desc: s1desc
                      name: s1
                      read_roles:
                      - r1
                      write_roles:
                      - r1
                    """,
                ),
                "",
                config.Config(
                    permissions=[config.Permission(name="p1")],
                    roles=[config.Role(name="r1", desc="r1desc", permissions={"p1"})],
                    speakers=[config.Speaker(name="s1", desc="s1desc", read_roles={"r1"}, write_roles={"r1"})],
                    main_thread=config.MainThread(messages=[]),
                ),
            ),
            (
                "singles",
                textwrap.dedent(
                    """\
                    permissions:
                    - name: p1
                    roles:
                    - desc: r1desc
                      name: r1
                      permissions:
                      - p1
                    speakers:
                    - desc: s1desc
                      name: s1
                      read_roles:
                      - r1
                      write_roles:
                      - r1
                    """,
                ),
                textwrap.dedent(
                    """\
                    - timestamp: 1001
                      id: 1
                      speaker: s1
                      permissions:
                        - p1
                      content: |
                        content1
                    """,
                ),
                config.Config(
                    permissions=[config.Permission(name="p1")],
                    roles=[config.Role(name="r1", desc="r1desc", permissions={"p1"})],
                    speakers=[config.Speaker(name="s1", desc="s1desc", read_roles={"r1"}, write_roles={"r1"})],
                    main_thread=config.MainThread(
                        messages=[
                            config.Message(
                                timestamp=1001,
                                id=1,
                                speaker="s1",
                                permissions={"p1"},
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
                    permissions:
                    - name: p1
                      desc: ''
                    - name: p2
                      desc: ''
                    roles:
                    - name: r1
                      desc: r1desc
                      permissions:
                      - p1
                    - name: r2
                      desc: r2desc
                      permissions:
                      - p1
                      - p2
                    speakers:
                    - name: s1
                      desc: s1desc
                      read_roles:
                      - r1
                      write_roles:
                      - r1
                    - name: s2
                      desc: s2desc
                      read_roles:
                      - r1
                      write_roles:
                      - r1
                      - r2
                    """,
                ),
                textwrap.dedent(
                    """\
                    - timestamp: 1001
                      id: 1
                      speaker: s1
                      permissions:
                      - p1
                      content: |
                        content1
                    - timestamp: 1002
                      id: 2
                      speaker: s2
                      permissions:
                      - p1
                      - p2
                      content: |
                        content2
                        end
                    """,
                ),
                config.Config(
                    permissions=[config.Permission(name="p1"), config.Permission(name="p2")],
                    roles=[
                        config.Role(name="r1", desc="r1desc", permissions={"p1"}),
                        config.Role(name="r2", desc="r2desc", permissions={"p1", "p2"}),
                    ],
                    speakers=[
                        config.Speaker(name="s1", desc="s1desc", read_roles={"r1"}, write_roles={"r1"}),
                        config.Speaker(name="s2", desc="s2desc", read_roles={"r1"}, write_roles={"r1", "r2"}),
                    ],
                    main_thread=config.MainThread(
                        messages=[
                            config.Message(
                                timestamp=1001,
                                id=1,
                                speaker="s1",
                                permissions={"p1"},
                                content="content1\n",
                            ),
                            config.Message(
                                timestamp=1002,
                                id=2,
                                speaker="s2",
                                permissions={"p1", "p2"},
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

    def test_readable(self):
        pd = config.PermissionDict()
        pd.add(config.Permission(name="speaker_a", desc="permission:a"))
        pd.add(config.Permission(name="speaker_b", desc="permission:b"))
        pd.add(config.Permission(name="speaker_c", desc="permission:c"))

        role_a = config.Role(
            name="role_a",
            desc="role:a",
            permissions={"speaker_a"},
        )
        role_ab = config.Role(
            name="role_ab",
            desc="role:ab",
            permissions={"speaker_a", "speaker_b"},
        )

        message_a = config.Message(
            timestamp=1742308502,
            id=0,
            content="message a content",
            permissions={"speaker_a"},
            speaker="speaker_a",
        )
        message_b = config.Message(
            timestamp=1742308502,
            id=0,
            content="message b content",
            permissions={"speaker_b"},
            speaker="speaker_b",
        )
        message_bc = config.Message(
            timestamp=1742308502,
            id=0,
            content="message c content",
            permissions={"speaker_b", "speaker_c"},
            speaker="speaker_c",
        )

        testcases = [
            (role_a, message_a, True),
            (role_a, message_b, False),
            (role_a, message_bc, False),
            (role_ab, message_a, True),
            (role_ab, message_b, True),
            (role_ab, message_bc, True),
        ]
        for r, m, want in testcases:
            got = r.readable(m, pd)
            self.assertEqual(want, got)
