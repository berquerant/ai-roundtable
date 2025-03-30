def read_user_input(end: str) -> list[str]:
    """Read user input line by line until reading end."""
    lines: list[str] = []
    while True:
        line = input()
        if line == end:
            return lines
        lines.append(line)
