import textwrap
from dataclasses import dataclass

from .config import Config
from .desc import Section


@dataclass
class Rule:
    config: Config

    def print_rules(self, speaker: str, language: str, agenda: str) -> Section:
        return Section(
            heading="Rules of Meeting",
            content=textwrap.dedent(
                """\
                You are about to attend a meeting.
                Please read and understand the rules as they are explained to you.""",
            ),
            children=[
                self.language(language),
                self.messages(),
                self.role_of_speaker(speaker),
                self.introduction(speaker),
                self.agenda(agenda),
            ],
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
                        Speaker: The content of the Message
                        It can span multiple lines
                        ```

                        Here is an example of a Message:

                        ```
                        alice: To be, or not to be,
                        that is the question.
                        ```""",
                    ),
                ),
                Section(
                    heading="Write Messages",
                    content=textwrap.dedent(
                        """\
                        When writing a Message, ONLY write the content.
                        Participant names should be written in their original language
                        regardless of the language indicated in **Language** section.

                        Here is an example:

                        ```
                        There's always good weather
                        to be found somewhere.
                        ```"""
                    ),
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
        )

    def introduction(self, speaker: str) -> Section:
        return Section(
            heading="Introduction",
            content=textwrap.dedent(
                """\
                You are about to attend a meeting.
                There will be {number} participants including you, {participants}.
                Please read **Read and Write Messages**, **Language**, **Agenda** and **You are a Speaker** sections,
                read the conference messages you will be given, and write your own opinions.
                DO NOT respond to this instruction and write your own opinions immediately.""",
            ).format(
                number=len(self.config.speaker_dict),
                participants=", ".join(x for x in self.config.speaker_dict.elems.keys() if x != speaker),
            ),
        )

    def language(self, language: str) -> Section:
        return Section(
            heading="Language",
            content=textwrap.dedent(
                """\
                You must write your own opinions **in {language}**.""",
            ).format(language=language),
        )

    def agenda(self, agenda: str) -> Section:
        return Section(
            heading="Agenda",
            content=textwrap.dedent(
                """\
                **{agenda}**""",
            ).format(agenda=agenda),
        )
