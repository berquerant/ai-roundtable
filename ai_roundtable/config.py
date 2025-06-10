import hashlib
import os
from dataclasses import dataclass
from typing import Callable, cast

import yaml
from agents import ModelProvider

from .data import meta, IntoDict, FromDict, IdentityDict, Validator, Desc
from .provider import Setting as ProviderSetting
from .slice import find
from .yamlx import dumps as yaml_dumps


@dataclass
class Message(Validator, IntoDict, FromDict, Desc):
    """Message definition."""

    content: str = meta(desc="message content", validator=Validator.length()).field(str)
    speaker: str = meta(desc="message speaker", validator=Validator.length()).field(str)

    def identity(self) -> str:
        return hashlib.sha256(f"{self.speaker}:{self.content}".encode()).hexdigest()

    def into_str(self) -> str:
        return f"{self.speaker}: {self.content}"


@dataclass
class Thread(Validator, IntoDict, FromDict):
    """Chat thread."""

    messages: list[Message] = meta(desc="list of messages").field(list[Message], default_factory=list)

    def select(self, pred: Callable[[Message], bool]) -> "Thread":
        return Thread(messages=[x for x in self.messages if pred(x)])

    def latest(self, n: int) -> "Thread":
        return Thread(messages=self.messages[-n:])

    def __len__(self) -> int:
        """Length of thread."""
        return len(self.messages)


class MainThread(Thread):
    """Chat main thread."""

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)

        def f(_: Message) -> None:
            return

        self.__append_hook = cast(Callable[[Message], None], f)

    def set_append_hook(self, f: Callable[[Message], None]) -> None:
        self.__append_hook = f

    def append(self, speaker: str, content: str) -> None:
        m = Message(
            speaker=speaker,
            content=content,
        )
        self.__append_hook(m)
        return self.messages.append(m)


@dataclass
class Speaker(Validator, IntoDict, FromDict):
    """Speaker definition."""

    name: str = meta(desc="speaker name", validator=Validator.length()).field(str)
    desc: str = meta(desc="speaker description").field(str, default="")
    human: bool = meta(desc="if true, human").field(bool, default=False)
    model: str = meta(desc="speaker model").field(str, default="")
    base_url: str = meta(desc="base url of API").field(str, default="")
    api_key_env: str = meta(desc="name of envvar of API key").field(str, default="")

    def identity(self) -> str:
        return self.name

    def model_or(self, model: str) -> str:
        if self.model != "":
            return self.model
        return model

    def provider(self, model: str = "", base_url: str = "", api_key_env: str = "") -> ModelProvider:
        return ProviderSetting(
            model_name=self.model_or(model),
            base_url=self.base_url or base_url,
            api_key=os.getenv(self.api_key_env or api_key_env) or "",
        ).provider


SpeakerDict = IdentityDict[Speaker]


class Builtin:
    """Provide builtin resources."""

    @staticmethod
    def prefix() -> str:
        return "rt_"

    @staticmethod
    def moderator_name() -> str:
        return "moderator"


@dataclass
class Config(IntoDict, FromDict):
    """Application config."""

    main_thread: MainThread = meta(desc="main thread").field(MainThread)
    speakers: list[Speaker] = meta(desc="speaker definitions").field(list[Speaker], default_factory=list)
    system: list[Speaker] = meta(desc="system definitions").field(list[Speaker], default_factory=list)

    @property
    def end_evaluator(self) -> Speaker:
        return find(
            self.system,
            lambda x: x.name == "end",
        ) or Speaker(name="end")

    @property
    def summary_evaluator(self) -> Speaker:
        return find(
            self.system,
            lambda x: x.name == "summary",
        ) or Speaker(name="summary")

    def setup(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.speaker_dict
        self.__validate_main_thread()

    def __validate_main_thread(self) -> None:
        for x in self.main_thread.messages:
            self.__validate_message(x)

    def __validate_message(self, message: Message) -> None:
        if message.speaker == Builtin.moderator_name():
            # skip moderator
            return
        sd = self.speaker_dict
        if message.speaker not in sd.elems:
            raise Exception(f"speaker {message.speaker} not found in message {message.identity()}")

    @property
    def speaker_dict(self) -> SpeakerDict:
        d = SpeakerDict()
        for s in self.speakers:
            d.add(s)
        return d


@dataclass
class ConfigYaml:
    """Config as yaml."""

    config: str
    thread: str

    def into_config(self) -> Config:
        c = yaml.safe_load(self.config)
        t = yaml.safe_load(self.thread)
        c["main_thread"] = {"messages": [] if t is None else t}
        return Config.from_dict(c)

    @staticmethod
    def from_config(c: Config) -> "ConfigYaml":
        d = c.into_dict()
        t = d["main_thread"]["messages"]
        del d["main_thread"]
        return ConfigYaml(
            config=yaml_dumps(d),
            thread=yaml_dumps(t),
        )
