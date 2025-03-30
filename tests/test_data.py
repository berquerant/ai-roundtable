from dataclasses import dataclass
from unittest import TestCase

import ai_roundtable.data as data
import ai_roundtable.desc as desc


class TestData(TestCase):
    def test_validator(self):
        @dataclass
        class TestValidator(data.Validator):
            num: int = data.meta(desc="number").field(int)
            positive: int = data.meta(desc="positive number", validator=lambda x: x > 0).field(int)

        with self.subTest("success"):
            got = TestValidator(num=100, positive=10)
            self.assertEqual(100, got.num)
            self.assertEqual(10, got.positive)
        with self.subTest("validated"):
            with self.assertRaises(data.MetaException):
                TestValidator(num=100, positive=-10)

    def test_into_dict(self):
        @dataclass
        class TestIntoDictInternal(data.IntoDict):
            val: int = data.meta(desc="intval").field(int)
            iset: set[int] = data.meta(desc="isetval").field(set[int], default_factory=set)

        @dataclass
        class TestIntoDict(data.IntoDict):
            num: int = data.meta(desc="numval").field(int)
            string: str = data.meta(desc="strval").field(str)
            ignore: bool = data.meta(desc="ignore", dict_conv=False).field(bool)
            internal: TestIntoDictInternal = data.meta(desc="internalval").field(TestIntoDictInternal)
            internal_list: list[TestIntoDictInternal] = data.meta(desc="ilistval").field(
                list[TestIntoDictInternal], default_factory=list
            )

        got = TestIntoDict(
            num=1,
            string="s",
            ignore=True,
            internal=TestIntoDictInternal(val=100),
            internal_list=[TestIntoDictInternal(val=110, iset={3})],
        ).into_dict()
        want = {
            "num": 1,
            "string": "s",
            "internal": {
                "val": 100,
                "iset": set(),
            },
            "internal_list": [{"val": 110, "iset": {3}}],
        }
        self.assertEqual(want, got)

    def test_from_dict_default(self):
        @dataclass
        class TestFromDictDefault(data.FromDict):
            string: str = data.meta(desc="string").field(str, default="dstring")
            int_list: list[int] = data.meta(desc="ints").field(list[int], default_factory=list)

        got = TestFromDictDefault.from_dict({})
        want = TestFromDictDefault(string="dstring", int_list=[])
        self.assertEqual(want, got)

    def test_from_dict(self):
        @dataclass
        class TestFromDictInternal(data.FromDict):
            val: int = data.meta(desc="intval").field(int)
            iset: set[int] = data.meta(desc="isetval").field(set[int], default_factory=set)

        @dataclass
        class TestFromDict(data.FromDict):
            num: int = data.meta(desc="numval").field(int)
            string: str = data.meta(desc="strval").field(str)
            internal: TestFromDictInternal = data.meta(desc="internalval").field(TestFromDictInternal)
            ignore: bool = data.meta(desc="ignore", dict_conv=False).field(bool, default=False)
            internal_list: list[TestFromDictInternal] = data.meta(desc="ilistval").field(
                list[TestFromDictInternal], default_factory=list
            )

        d = {
            "num": 1,
            "string": "s",
            "internal": {
                "val": 100,
                "iset": [1, 2],
            },
            "ignore": False,
            "internal_list": [{"val": 110, "iset": {3}}],
        }
        got = TestFromDict.from_dict(d)
        want = TestFromDict(
            num=1,
            string="s",
            internal=TestFromDictInternal(val=100, iset={1, 2}),
            internal_list=[TestFromDictInternal(val=110, iset={3})],
        )
        self.assertEqual(want, got)

    def test_desc(self):
        @dataclass
        class TestDesc(data.Desc):
            """testdesc doc"""

            number: int = data.meta(desc="number desc").field(int)
            string: str = data.meta(desc="string desc").field(str)
            ignore: str = data.meta(desc="ignore desc", ignore_desc=True).field(str)

        got = TestDesc.describe()
        want = desc.Section(
            heading="TestDesc",
            content="testdesc doc",
            children=[
                desc.Section(heading="number", content="number desc"),
                desc.Section(heading="string", content="string desc"),
            ],
        )
        self.assertEqual(want, got)
