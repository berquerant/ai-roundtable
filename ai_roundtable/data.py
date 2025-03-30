from abc import ABC
from dataclasses import dataclass, is_dataclass, fields, Field, field, MISSING
from types import GenericAlias
from typing import Callable, Any, Optional, TypeVar, Self, Protocol, cast, Type

from .desc import Section


class MetaException(Exception):
    """An Exception from Meta."""


ValidatorFunc = Callable[[Any], bool]
Dict = dict[str, Any]


class FromDict(ABC):
    """Conversion from Dict."""

    @classmethod
    def from_dict_default(cls, name: str, value: Any) -> Any:
        """Override from_dict partially like json's default."""
        return value

    @classmethod
    def from_dict(cls: type[Self], d: Dict) -> Self:
        """Convert from Dict."""
        if not is_dataclass(cls):
            raise MetaException("from_dict got not dataclass")

        def from_dict_or(t: type, x: Any) -> Any:
            if hasattr(t, "from_dict"):
                if not isinstance(x, dict):
                    raise Exception(f"want dict but got {x}")
                return t.from_dict(x)
            if t not in [int, float, str, bool]:
                raise Exception(f"unsupported type: {t}")
            if not isinstance(x, t):
                raise Exception(f"want {t} but got {x}")
            return x

        r = {}
        for f in fields(cls):
            name = f.name
            typ = f.type
            value = d.get(name)
            try:
                meta = Meta.from_field(f)
                if meta is None:
                    raise Exception("no Meta")
                if not meta.dict_conv:
                    continue
                if value is None:
                    # set default value if exist
                    if f.default != MISSING:
                        value = f.default
                    elif f.default_factory != MISSING:
                        value = f.default_factory()
                    else:
                        raise Exception("value is None")

                if hasattr(value, "from_dict_default"):
                    r[name] = value.from_dict_default(name, value)
                    continue

                match typ:
                    case GenericAlias():  # like list[str]
                        if len(typ.__args__) != 1:
                            raise Exception(f"no generic type arg for {typ}")
                        arg = typ.__args__[0]
                        origin = typ.__origin__
                        if not isinstance(value, (list, set, tuple)):
                            raise Exception(f"want origin type: {origin} but got {value}")
                        match origin.__name__:
                            case "list":
                                r[name] = [from_dict_or(arg, x) for x in value]
                            case "set":
                                r[name] = {from_dict_or(arg, x) for x in value}
                            case "tuple":
                                r[name] = tuple(from_dict_or(arg, x) for x in value)
                            case _:
                                raise Exception(f"unsupported generic type: {origin}")
                    case _:
                        r[name] = from_dict_or(typ, value)
            except Exception as e:
                e.add_note(f"from_dict: field {name} of {cls.__name__}")
                raise MetaException from e
        return cls(**r)


class IntoDict(ABC):
    """Conversion into Dict."""

    def into_dict(self) -> Dict:
        """Convert into Dict."""
        if not is_dataclass(self):
            raise MetaException("into_dict got not dataclass")

        def into_dict_or(v: Any) -> Any:
            return v.into_dict() if hasattr(v, "into_dict") else v

        r: dict[str, Any] = {}
        for f in fields(self):
            name = f.name
            try:
                meta = Meta.from_field(f)
                if meta is None:
                    raise Exception("no Meta")
                if not meta.dict_conv:
                    continue
                value = getattr(self, name)

                match value:
                    case list():
                        r[name] = [into_dict_or(v) for v in value]
                    case set():
                        r[name] = {into_dict_or(v) for v in value}
                    case tuple():
                        r[name] = tuple(into_dict_or(v) for v in value)
                    case _:
                        r[name] = into_dict_or(value)
            except Exception as e:
                e.add_note(f"from into_dict: field {name} of class {self.__class__.__name__}")
                raise MetaException from e
        return r


class Desc(ABC):
    """Extract descriptions."""

    @classmethod
    def describe(cls) -> Section:
        """Extract descriptions from fields."""
        if not is_dataclass(cls):
            raise MetaException("describe got not dataclass")

        c = []
        for f in fields(cls):
            name = f.name
            try:
                meta = Meta.from_field(f)
                if meta is None:
                    raise Exception("no Meta")
                if meta.ignore_desc:
                    continue
                c.append(Section(heading=name, content=meta.desc))
            except Exception as e:
                e.add_note(f"from describe: field {name} of class {cls.__name__}")
                raise MetaException from e
        return Section(heading=cls.__name__, content=cls.__doc__, children=c)


class IdentityProto(Protocol):
    """Define identitites."""

    def identity(self) -> str: ...


IdentityT = TypeVar("IdentityT", bound=IdentityProto)


@dataclass
class IdentityDict[IdentityT]:
    elems: dict[str, IdentityT] = field(default_factory=dict)

    def add(self, x: IdentityT) -> None:
        self.elems[x.identity()] = x  # type: ignore[attr-defined]

    def get(self, key: str) -> IdentityT | None:
        return self.elems.get(key)

    def get_or_raise(self, key: str, e: Exception) -> IdentityT:
        if key not in self.elems:
            raise e
        return self.elems[key]

    def __getitem__(self, key: str) -> IdentityT:
        """Index access."""
        return self.elems[key]

    def __contains__(self, key: str) -> bool:
        """Enable in statement."""
        return key in self.elems

    def __len__(self) -> int:
        """Length of the dict."""
        return len(self.elems)


@dataclass
class Meta:
    """Metadata of dataclass."""

    desc: str
    validator: ValidatorFunc | None = None
    dict_conv: bool = True  # requires default value, for IntoDict, FromDict
    ignore_desc: bool = False  # for Desc

    @staticmethod
    def new(
        desc: str, validator: ValidatorFunc | None = None, dict_conv: bool = True, ignore_desc: bool = False
    ) -> "Meta":
        if not desc:
            raise MetaException("Meta desc required")
        return Meta(desc=desc, validator=validator, dict_conv=dict_conv, ignore_desc=ignore_desc)

    def validate(self, x: Any) -> bool:
        return self.validator is None or self.validator(x)

    def field[T](self, t: Type[T], **kwargs) -> T:  # type: ignore[no-untyped-def]
        """Into dataclass's field."""
        kwargs["metadata"] = {"meta": self}
        return cast(T, field(**kwargs))

    @classmethod
    def from_field[T](cls, f: Field[T]) -> Optional["Meta"]:
        v = f.metadata.get("meta")
        return v if isinstance(v, Meta) else None


meta = Meta.new


class Validator:
    """Validator for dataclass fields."""

    def __post_init__(self) -> None:
        """Dataclass's __post_init__."""
        if not is_dataclass(self):
            raise MetaException("Validator got not dataclass")
        for f in fields(self):
            name = f.name
            try:
                meta = Meta.from_field(f)
                if meta is None:
                    raise Exception("no Meta")
                value = getattr(self, name)
                if not meta.validate(value):
                    raise Exception(f"invalid value: {value}")
            except Exception as e:
                e.add_note(f"from Validator: field {name} of class {f.__class__.__name__}")
                raise MetaException from e

    @staticmethod
    def length(min_len: int = 1, max_len: int | None = None) -> ValidatorFunc:
        return lambda x: len(x) >= min_len and (max_len is None or len(x) <= max_len)

    @staticmethod
    def ge(min_val: int) -> ValidatorFunc:
        return lambda x: x >= min_val
