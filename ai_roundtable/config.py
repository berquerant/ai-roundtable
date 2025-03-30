from dataclasses import dataclass
from datetime import datetime
from typing import Callable, cast

import yaml

from .data import meta, IntoDict, FromDict, IdentityDict, Validator, Desc
from .log import log
from .yamlx import dumps as yaml_dumps


@dataclass(frozen=True)
class Permission(Validator, IntoDict, FromDict, Desc):
    """Permission definition."""

    name: str = meta(desc="permission name", validator=Validator.length()).field(str)
    desc: str = meta(desc="permission description").field(str, default="")

    def identity(self) -> str:
        return self.name


PermissionDict = IdentityDict[Permission]


@dataclass
class Role(Validator, IntoDict, FromDict, Desc):
    """Named set of permissions."""

    name: str = meta(desc="role name", validator=Validator.length()).field(str)
    desc: str = meta(desc="role description", validator=Validator.length()).field(str)
    permissions: set[str] = meta(desc="permissions assinged to this role", validator=Validator.length()).field(
        set[str], default_factory=set
    )

    def identity(self) -> str:
        return self.name

    def permission_list(self, d: PermissionDict) -> list[Permission]:
        r = []
        for x in self.permissions:
            if x not in d:
                log().warn("permission %s not found in role %s", x, self.identity())
                continue
            r.append(d[x])
        return r

    def readable(self, message: "Message", d: PermissionDict) -> bool:
        return len(set(self.permission_list(d)) & set(message.permission_list(d))) > 0


RoleDict = IdentityDict[Role]


@dataclass
class Message(Validator, IntoDict, FromDict, Desc):
    """Message definition."""

    timestamp: int = meta(desc="message timestamp", validator=Validator.ge(0)).field(int)
    id: int = meta(desc="message id", validator=Validator.ge(0)).field(int)
    content: str = meta(desc="message content", validator=Validator.length()).field(str)
    speaker: str = meta(desc="message speaker", validator=Validator.length()).field(str)
    permissions: set[str] = meta(desc="required permissions to read this message", validator=Validator.length()).field(
        set[str], default_factory=set
    )

    def permission_list(self, d: PermissionDict) -> list[Permission]:
        r = []
        for x in self.permissions:
            if x not in d:
                log().warn("permission %s not found in message %s", x, self.identity())
                continue
            r.append(d[x])
        return r

    def identity(self) -> str:
        return str(self.id)


@dataclass
class Thread(Validator, IntoDict, FromDict):
    """Chat thread."""

    messages: list[Message] = meta(desc="list of messages").field(list[Message], default_factory=list)

    def select(self, pred: Callable[[Message], bool]) -> "Thread":
        return Thread(messages=[x for x in self.messages if pred(x)])

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

    @property
    def __max_id(self) -> int:
        if len(self.messages) > 0:
            return max(x.id for x in self.messages)
        return 0

    def append(self, speaker: str, permissions: set[str], content: str) -> None:
        m = Message(
            id=self.__max_id + 1,
            timestamp=int(datetime.now().timestamp()),
            speaker=speaker,
            permissions=permissions | {Builtin.dm_role_name(speaker)},
            content=content,
        )
        self.__append_hook(m)
        return self.messages.append(m)


@dataclass
class Speaker(Validator, IntoDict, FromDict):
    """Speaker definition."""

    name: str = meta(desc="speaker name", validator=Validator.length()).field(str)
    desc: str = meta(desc="speaker description", validator=Validator.length()).field(str)
    read_roles: set[str] = meta(desc="permissions to read messages").field(set[str], default_factory=set)
    write_roles: set[str] = meta(desc="permissions to write messages").field(set[str], default_factory=set)
    human: bool = meta(desc="if true, human").field(bool, default=False)

    def __roles(self, d: RoleDict, v: set[str]) -> list[Role]:
        return [d.get_or_raise(x, Exception(f"role {x} not found in speaker {self.identity()}")) for x in v]

    def rroles(self, d: RoleDict) -> list[Role]:
        return self.__roles(d, self.read_roles)

    def wroles(self, d: RoleDict) -> list[Role]:
        return self.__roles(d, self.write_roles)

    def __readable(self, message: Message, rd: RoleDict, pd: PermissionDict) -> bool:
        return any(r.readable(message, pd) for r in self.rroles(rd))

    def read_messages(self, main_thread: MainThread, rd: RoleDict, pd: PermissionDict) -> Thread:
        return main_thread.select(lambda m: self.__readable(m, rd, pd))

    def identity(self) -> str:
        return self.name


SpeakerDict = IdentityDict[Speaker]


class Builtin:
    """Provide builtin resources."""

    @staticmethod
    def prefix() -> str:
        return "rt_"

    @staticmethod
    def moderator_name() -> str:
        return "moderator"

    @classmethod
    def moderator_role_name(cls) -> str:
        return cls.prefix() + cls.moderator_name()

    @classmethod
    def moderator_role(cls, speakers: list[str]) -> Role:
        return Role(
            name=cls.moderator_role_name(), desc="meeting moderator", permissions=cls.admin_role(speakers).permissions
        )

    @classmethod
    def moderator_permission(cls) -> Permission:
        return Permission(name=cls.moderator_role_name(), desc="moderator permission")

    @classmethod
    def dm_role_name(cls, speaker: str) -> str:
        return cls.prefix() + speaker

    @classmethod
    def public_role_name(cls) -> str:
        return cls.prefix() + "public"

    @classmethod
    def dm_all_role_name(cls) -> str:
        return cls.prefix() + "dm_all"

    @classmethod
    def admin_role_name(cls) -> str:
        return cls.prefix() + "admin"

    @classmethod
    def public_permission(cls) -> Permission:
        return Permission(name=cls.public_role_name(), desc="allow public messages")

    @classmethod
    def public_role(cls) -> Role:
        return Role(
            name=cls.public_role_name(),
            desc="readable or writable public messages",
            permissions={cls.public_permission().name},
        )

    @classmethod
    def dm_permission(cls, speaker: str) -> Permission:
        return Permission(name=cls.dm_role_name(speaker), desc=f"allow direct messages for {speaker}")

    @classmethod
    def dm_role(cls, speaker: str) -> Role:
        return Role(
            name=cls.dm_role_name(speaker),
            desc=f"readable or writable direct messages for {speaker}",
            permissions={cls.dm_permission(speaker).name},
        )

    @classmethod
    def dm_all_role(cls, speakers: list[str]) -> Role:
        return Role(
            name=cls.dm_all_role_name(),
            desc="readable or writable all direct messages",
            permissions={cls.dm_role_name(x) for x in speakers},
        )

    @classmethod
    def admin_role(cls, speakers: list[str]) -> Role:
        return Role(
            name=cls.admin_role_name(),
            desc="readable or writable all messages",
            permissions=cls.dm_all_role(speakers).permissions | cls.public_role().permissions,
        )


@dataclass
class Config(IntoDict, FromDict):
    """Application config."""

    main_thread: MainThread = meta(desc="main thread").field(MainThread)
    permissions: list[Permission] = meta(desc="permission definitions").field(list[Permission], default_factory=list)
    roles: list[Role] = meta(desc="role definitions").field(list[Role], default_factory=list)
    speakers: list[Speaker] = meta(desc="speaker definitions").field(list[Speaker], default_factory=list)

    def setup(self) -> None:
        self.__generate_public_roles()
        self.__generate_dm_roles()
        self.__add_self_dm_roles()
        self.__generate_admin_role()
        self.__generate_moderator_role()
        self.validate()

    def __add_self_dm_roles(self) -> None:
        for s in self.speakers:
            s.read_roles.add(Builtin.dm_role_name(s.name))

    def __generate_moderator_role(self) -> None:
        self.permissions.append(Builtin.moderator_permission())
        self.roles.append(Builtin.moderator_role([x.name for x in self.speakers]))

    def __generate_public_roles(self) -> None:
        self.permissions.append(Builtin.public_permission())
        self.roles.append(Builtin.public_role())
        for s in self.speakers:
            # all speakers can read and write public messages
            s.read_roles.add(Builtin.public_role_name())
            s.write_roles.add(Builtin.public_role_name())

    def __generate_dm_roles(self) -> None:
        for s in self.speakers:
            n = s.name
            self.permissions.append(Builtin.dm_permission(n))
            self.roles.append(Builtin.dm_role(n))
        self.roles.append(Builtin.dm_all_role([x.name for x in self.speakers]))

    def __generate_admin_role(self) -> None:
        self.roles.append(Builtin.admin_role([x.name for x in self.speakers]))

    def validate(self) -> None:
        self.permission_dict
        self.role_dict
        self.speaker_dict
        self.__validate_main_thread()

    def __validate_main_thread(self) -> None:
        for x in self.main_thread.messages:
            self.__validate_message(x)

    def __validate_message(self, message: Message) -> None:
        pd = self.permission_dict
        sd = self.speaker_dict
        for x in message.permissions:
            if x not in pd.elems:
                raise Exception(f"permission {x} not found in message {message.identity()}")
        if message.speaker not in sd.elems:
            raise Exception(f"speaker {message.speaker} not found in message {message.identity()}")

    @property
    def speaker_dict(self) -> SpeakerDict:
        rd = self.role_dict
        d = SpeakerDict()
        for s in self.speakers:
            for r in s.read_roles:
                if r not in rd.elems:
                    raise Exception(f"read role {r} not found in speaker {s.name}")
            for r in s.write_roles:
                if r not in rd.elems:
                    raise Exception(f"write role {r} not found in speaker {s.name}")
            d.add(s)
        return d

    @property
    def role_dict(self) -> RoleDict:
        pd = self.permission_dict
        d = RoleDict()
        for r in self.roles:
            for x in r.permissions:
                if x not in pd.elems:
                    raise Exception(f"permission {x} not found in role {r.name}")
            d.add(r)
        return d

    @property
    def permission_dict(self) -> PermissionDict:
        d = PermissionDict()
        for x in self.permissions:
            d.add(x)
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
