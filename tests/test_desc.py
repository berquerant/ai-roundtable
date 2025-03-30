import textwrap
from unittest import TestCase

import ai_roundtable.desc as desc


class TestSection(TestCase):
    def test_describe(self):
        s = desc.Section(
            heading="h1",
            content="h1c",
            children=[
                desc.Section(heading="h2_1", content="h2_1c"),
                desc.Section(heading="h2_2", content="h2_2c", children=[desc.Section(heading="h3_1", content="h3_1c")]),
            ],
        )
        want = textwrap.dedent(
            """\
            # h1
            h1c
            ## h2_1
            h2_1c
            ## h2_2
            h2_2c
            ### h3_1
            h3_1c"""
        )
        got = s.describe()
        self.assertEqual(want, got)
