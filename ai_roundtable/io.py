import sys


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
