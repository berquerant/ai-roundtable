import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Callable, cast, TypeVar, Generic, override

from agents import Agent, Runner, TResponseInputItem, ModelProvider, RunConfig, RunResultStreaming
from openai.types.responses import ResponseTextDeltaEvent

from .config import MainThread, Speaker, Thread
from .desc import Section
from .io import read_user_input
from .log import log, stream_log


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

    async def reply(self) -> None: ...


async def streaming(result: RunResultStreaming) -> None:
    """Print stream_log."""
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            msg = event.data.delta
            stream_log(msg)
    stream_log("\n")


@dataclass
class Bot:
    """Chat bot."""

    instructions: str
    main_thread: MainThread
    speaker: Speaker
    model_provider: ModelProvider

    def __new_message(self, speaker: str, content: str) -> Message:
        if self.speaker.name == speaker:
            return Message.assistant(content)
        return Message.user(content)

    @property
    def __thread(self) -> Thread:
        return self.main_thread

    @property
    def __messages(self) -> list[Message]:
        return [self.__new_message(x.speaker, x.into_str()) for x in self.__thread.messages]

    async def reply(self) -> None:
        """Append a reply to the main thread."""
        log().info("%s: begin reply", self.speaker.name)
        agent = Agent(name="assistant", instructions=self.instructions)
        messages = self.__messages
        for i, x in enumerate(messages):
            log().debug("input[%s][%d][%s]: %s", self.speaker.name, i, x.role, x.content)
        result = Runner.run_streamed(
            starting_agent=agent,
            input=[x.into_item() for x in messages],
            run_config=RunConfig(model_provider=self.model_provider),
        )
        await streaming(result)
        final_output: str = result.final_output
        self.main_thread.append(self.speaker.name, final_output)
        log().info("%s: end reply", self.speaker.name)


@dataclass
class Human:
    """Human as a chat bot."""

    main_thread: MainThread
    speaker: Speaker
    end: str

    async def reply(self) -> None:
        """Append a reply to the main thread."""
        log().info("%s: begin reply (human)", self.speaker.name)
        log().info("%s: content(end=%s)> ", self.speaker.name, self.end)
        content = "\n".join(read_user_input(self.end))
        self.main_thread.append(self.speaker.name, content)
        log().info("%s: end reply (human)", self.speaker.name)


ET = TypeVar("ET")


@dataclass
class Evaluator(ABC, Generic[ET]):
    """Evaluate the main thread."""

    name: str
    main_thread: MainThread
    latest_messages: int
    model_provider: ModelProvider
    hook: Callable[[ET], None]
    agenda: str
    language: str

    @abstractmethod
    def parse_output(self, output: str) -> ET: ...

    @abstractmethod
    def description(self) -> Section: ...

    @property
    def __messages(self) -> list[Message]:
        return [Message.user(x.into_str()) for x in self.main_thread.latest(self.latest_messages).messages]

    async def evaluate(self) -> ET:
        log().info("evaluator[%s]: begin", self.name)
        agent = Agent(
            name=f"evaluator[{self.name}]",
            instructions=self.description().describe(),
        )
        messages = self.__messages
        for i, x in enumerate(messages):
            log().debug("input[%s][%d][%s]: %s", self.name, i, x.role, x.content)
        result = Runner.run_streamed(
            starting_agent=agent,
            input=[x.into_item() for x in messages],
            run_config=RunConfig(model_provider=self.model_provider),
        )
        await streaming(result)
        final_output: str = result.final_output
        ret = self.parse_output(final_output)
        self.hook(ret)
        log().info("evaluator[%s]: end", self.name)
        return ret


class SummaryEvaluator(Evaluator[str]):
    """Summarize the main thread."""

    @override
    def parse_output(self, output: str) -> str:
        return output

    @override
    def description(self) -> Section:
        return Section(
            heading="Summary",
            content=textwrap.dedent(
                """\
                Provide summary of input text concisely and comprehensively in {language}.""",
            ).format(language=self.language),
        )


class EndEvaluator(Evaluator[bool]):
    """Evaluate the main thread."""

    @override
    def parse_output(self, output: str) -> bool:
        return "yes" in output

    @override
    def description(self) -> Section:
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
                only reply "yes" to end the discussion, or "no" if not.
                The agenda item is {agenda}.""",
            ).format(agenda=self.agenda),
        )
