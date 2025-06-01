import sys
import typing
from dataclasses import dataclass


@dataclass
class Writer:
    """Output stream."""

    dest: str

    @classmethod
    def stdout(cls) -> typing.Self:
        return cls(dest="stdout")

    @classmethod
    def stderr(cls) -> typing.Self:
        return cls(dest="stderr")

    @classmethod
    def new(cls, dest: str) -> typing.Self:
        return cls(dest=dest)

    def write(self, msg: str) -> None:
        """Write msg to dest."""
        match self.dest:
            case "stdout":
                print(msg, file=sys.stdout, flush=True)
            case "stderr":
                print(msg, file=sys.stderr, flush=True)
            case dest:
                with open(dest, "a") as f:
                    print(msg, file=f, flush=True)


def read_user_input(end: str) -> list[str]:
    """Read user input line by line until reading end."""
    lines: list[str] = []
    while True:
        line = input()
        if line == end:
            return lines
        lines.append(line)


def file_or(v: str) -> str:
    """Read file if v starts with @ else v."""
    if not v.startswith("@"):
        return v
    if v.lstrip("@") == "-":
        return sys.stdin.read()
    with open(v.lstrip("@")) as f:
        return f.read()
