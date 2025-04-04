import textwrap
from dataclasses import dataclass, make_dataclass, asdict
from typing import Literal, Protocol, Callable, cast

from agents import Agent, Runner, TResponseInputItem, ModelProvider, RunConfig

from .config import MainThread, Speaker, RoleDict, PermissionDict, Thread
from .data import Dict
from .desc import Section
from .io import read_user_input
from .log import log
from .yamlx import dumps as yaml_dumps


@dataclass
class Message:
    """Message to be sent to the Agent."""

    role: str
    content: str

    @staticmethod
    def user(content: str) -> "Message":
        """Return a new user message."""
        return Message(role="user", content=content)

    @staticmethod
    def assistant(content: str) -> "Message":
        """Return a new assistant message."""
        return Message(role="assistant", content=content)

    def into_item(self) -> TResponseInputItem:
        """Convert into Agent input."""
        return cast(TResponseInputItem, {"role": self.role, "content": self.content})


class BotProto(Protocol):
    """Chat bot protocol."""

    def reply(self) -> None: ...


@dataclass
class Bot:
    """Chat bot."""

    model: str
    instructions: str
    main_thread: MainThread
    speaker: Speaker
    role_dict: RoleDict
    permission_dict: PermissionDict
    model_provider: ModelProvider

    def __new_message(self, speaker: str, content: str) -> Message:
        if self.speaker.name == speaker:
            return Message.assistant(content)
        return Message.user(content)

    @property
    def __thread(self) -> Thread:
        return self.speaker.read_messages(self.main_thread, self.role_dict, self.permission_dict)

    @property
    def __messages(self) -> list[Message]:
        return [self.__new_message(x.speaker, yaml_dumps(x.into_dict())) for x in self.__thread.messages]

    @property
    def __output_type(self) -> type:
        s = self.speaker
        return make_dataclass(
            f"Feedback_{s.name}",
            [
                ("content", str),
                ("role", Literal[tuple(s.write_roles)]),
            ],
        )

    def reply(self) -> None:
        """Append a reply to the main thread."""
        log().info("%s: begin reply", self.speaker.name)
        output_type = self.__output_type
        agent = Agent(name="assistant", instructions=self.instructions, output_type=output_type)
        result = Runner.run_sync(
            starting_agent=agent,
            input=[x.into_item() for x in self.__messages],
            run_config=RunConfig(model_provider=self.model_provider),
        ).final_output
        result_role: str = result.role
        result_content: str = result.content
        permissions = self.role_dict.get_or_raise(result_role, Exception(f"role {result.role} not found")).permissions
        self.main_thread.append(self.speaker.name, permissions, result_content)
        log().info("%s: end reply", self.speaker.name)


@dataclass
class Human:
    """Human as a chat bot."""

    main_thread: MainThread
    speaker: Speaker
    role_dict: RoleDict
    permission_dict: PermissionDict
    end: str

    def reply(self) -> None:
        """Append a reply to the main thread."""
        log().info("%s: begin reply", self.speaker.name)
        choices = ", ".join(self.speaker.write_roles)
        while True:
            role = input(f"ROLE({choices})> ")
            if role not in self.speaker.write_roles:
                log().warn("%s: role %s is not allowed", self.speaker.name, role)
                continue
            break
        permissions = self.role_dict.get_or_raise(role, Exception(f"role {role} not found")).permissions
        log().info("%s: content(end=%s)> ", self.speaker.name, self.end)
        content = "\n".join(read_user_input(self.end))
        self.main_thread.append(self.speaker.name, permissions, content)
        log().info("%s: end reply", self.speaker.name)


@dataclass
class EvaluatorFeedback:
    """Result of Evaluation."""

    summary_of_discussion: str
    reason_for_decision: str
    decision: Literal["continue", "end"]

    def into_dict(self) -> Dict:
        """Convert into dict."""
        return asdict(self)


@dataclass
class Evaluator:
    """Evaluate the main thread."""

    main_thread: MainThread
    agenda: str
    latest_messages: int
    hook: Callable[[EvaluatorFeedback], None]
    model_provider: ModelProvider

    def evaluate(self) -> EvaluatorFeedback:
        """Decide whether to continue or end the discussion."""
        log().info("evaluator: begin")
        agent = Agent(
            name="evaluator",
            instructions=self.__description.describe(),
            output_type=EvaluatorFeedback,
        )
        result: EvaluatorFeedback = Runner.run_sync(
            starting_agent=agent,
            input=[x.into_item() for x in self.__messages],
            run_config=RunConfig(model_provider=self.model_provider),
        ).final_output
        self.hook(result)
        log().info("evaluator: end")
        return result

    @property
    def __messages(self) -> list[Message]:
        return [
            Message(
                role="user",
                content=textwrap.dedent(
                    """\
                    speaker: {speaker}
                    content:
                    {content}"""
                ).format(speaker=x.speaker, content=x.content),
            )
            for x in self.main_thread.messages[-self.latest_messages :]
        ]

    @property
    def __description(self) -> Section:
        return Section(
            heading="When to Stop Discussing",
            content=textwrap.dedent(
                """\
                You carefully evaluate the content of the discussion and
                decide whether you should continue or end the discussion.
                For example, you should end the discussion in the following situations:

                - The agenda item has been fully discussed and a conclusion has been reached
                - No conclusion can be reached by continuing the discussion.
                - Similar opinions are being repeated.

                When deciding whether to continue or end the discussion,
                please provide feedback on why you are making that decision and a summary of the discussion so far.
                The agenda item is {agenda}.""",
            ).format(agenda=self.agenda),
        )
