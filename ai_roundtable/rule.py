import textwrap
from dataclasses import dataclass

from .config import Message, Config
from .desc import Section


@dataclass
class WriteMessage:
    role: str
    content: str


class MessageParser:
    @staticmethod
    def into_read(x: Message) -> str:
        return textwrap.dedent(
            """\
            timestamp: {timestamp}
            id: {id}
            speaker: {speaker}
            permissions: {permissions}
            content:
            {content}""",
        ).format(
            timestamp=x.timestamp,
            id=x.id,
            speaker=x.speaker,
            permissions=",".join(sorted(list(x.permissions))),
            content=x.content,
        )

    @staticmethod
    def read(v: str) -> Message:
        lines = v.split("\n")
        try:
            if len(lines) < 6:
                raise Exception("too few lines")
            if not lines[4].startswith("content:"):
                raise Exception("no content")
            content = "\n".join(lines[5:])
            d = {}
            for x in lines[:4]:
                k, v = x.split(":", 1)
                d[k] = v.strip()
            timestamp = int(d["timestamp"])
            id = int(d["id"])
            speaker = d["speaker"]
            permissions = set(p.strip() for p in d["permissions"].split(","))
            return Message(timestamp=timestamp, id=id, speaker=speaker, permissions=permissions, content=content)
        except Exception as e:
            e.add_note(f"failed to parse read message: {v}")
            raise

    @staticmethod
    def write(v: str) -> WriteMessage:
        lines = v.split("\n")
        try:
            if len(lines) < 3:
                raise Exception("too few lines")
            if not lines[0].startswith("role:"):
                raise Exception("no role")
            role = lines[0].split(":", 1)[1].strip()
            if not lines[1].startswith("content:"):
                raise Exception("no content")
            content = "\n".join(lines[2:])
            return WriteMessage(role=role, content=content)
        except Exception as e:
            e.add_note(f"failed to parse write message: {v}")
            raise


@dataclass
class Rule:
    config: Config

    def print_rules(self, speaker: str) -> Section:
        return Section(
            heading="Rules of Meeting",
            content=textwrap.dedent(
                """\
                You are about to attend a meeting.
                Please read and understand the rules as they are explained to you.""",
            ),
            children=[
                self.message_access_control(),
                self.messages(),
                self.role_of_speaker(speaker),
                self.intoduction(speaker),
            ],
        )

    @staticmethod
    def message_access_control() -> Section:
        return Section(
            heading="Message Access Control",
            content=textwrap.dedent(
                """\
                Permissions are granted to Messages or to Speakers via Roles.
                A Role is a collection of multiple Permissions grouped under a name.
                A Speaker can hold multiple Roles.
                When a Speaker makes a statement, they select one of their write_roles.
                The statement becomes a Message with the Permissions granted by the chosen Role.
                When a Speaker reads a Message, they compare all Permissions from all Roles
                in their read_roles with the Permissions of the Message.
                If there is an intersection between these Permissions, they can read the Message.

                For example, consider the following definitions:
                - Permissions p1 and p2 are defined.
                - Roles r1 and r2 each have Permissions p1 and p2, respectively.
                - Speakers s1 and s2 hold Roles r1 and r2, respectively, while Speaker s3 holds both Roles r1 and r2.
                - Messages m1 and m2 have Permissions p1 and p2, respectively,
                  and Message m3 has both Permissions p1 and p2.
                In this scenario:
                - s1 can read m1 and m3.
                - s2 can read m2 and m3.
                - s3 can read m1, m2, and m3.
                - s1 can create a Message using r1, thus creating a Message with Permission p1.
                - s2 can create a Message using r2, thus creating a Message with Permission p2.
                - s3 can create a Message using either r1 or r2,
                  thus creating a Message with either Permission p1 or p2."""
            ),
        )

    @staticmethod
    def messages() -> Section:
        return Section(
            heading="Read and Write Messages",
            children=[
                Section(
                    heading="Read Messages",
                    content=textwrap.dedent(
                        """\
                        The format of a Message is as follows:

                        ```
                        timestamp: The creation time of this Message (unix timestamp)
                        id: The id of this Message
                        speaker: The Speaker who created this Message
                        permissions: The Permissions required to read this Message, separated by commas
                        content:
                        The content of the Message
                        It can span multiple lines
                        ```

                        Here is an example of a Message:

                        ```
                        timestamp: 1742785200
                        id: 2
                        speaker: alice
                        permissions: p1, p2
                        content:
                        first
                        second
                        ```""",
                    ),
                ),
                Section(
                    heading="Write Messages",
                    content=textwrap.dedent(
                        """\
                        When writing a Message, please follow the instructions in the Message Access Control Section.
                        Choose one Role from `write_roles` and specify the content."""
                    ),
                    # content=textwrap.dedent(
                    #     """\
                    #     When writing a Message, please follow the instructions in the Message Access Control Section.
                    #     Choose one Role from `write_roles` and specify the content.
                    #     Here is an example of writing a Message:
                    #     ```
                    #     role: role1
                    #     content:
                    #     hello
                    #     world
                    #     ```
                    #     """
                    # ),
                ),
            ],
        )

    def role_of_speaker(self, speaker: str) -> Section:
        s = self.config.speaker_dict.get_or_raise(speaker, Exception(f"speaker {speaker} not found"))
        return Section(
            heading="You are a Speaker",
            content=textwrap.dedent(
                """\
            You are a Speaker named {speaker}.
            {desc}"""
            ).format(speaker=s.name, desc=s.desc),
            children=[
                Section(
                    heading="Your read_roles",
                    children=[Section(heading=x.name, content=x.desc) for x in s.rroles(self.config.role_dict)],
                ),
                Section(
                    heading="Your write_roles",
                    children=[Section(heading=x.name, content=x.desc) for x in s.wroles(self.config.role_dict)],
                ),
            ],
        )

    def intoduction(self, speaker: str) -> Section:
        return Section(
            heading="Introduction",
            content=textwrap.dedent(
                """\
                You are about to attend a meeting.
                There will be {number} participants including you, {participants}.
                Please read the Message Access Control, Read and Write Messages, and You are a Speaker sections,
                read the conference messages you will be given, and write your own opinions.""",
            ).format(
                number=len(self.config.speaker_dict),
                participants=", ".join(x for x in self.config.speaker_dict.elems.keys() if x != speaker),
            ),
        )
