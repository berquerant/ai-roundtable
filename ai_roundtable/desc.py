from dataclasses import dataclass, field


@dataclass
class Section:
    """Markdown section."""

    heading: str
    content: str = ""
    children: list["Section"] = field(default_factory=list)

    def describe(self, heading_level: int = 1) -> str:
        r = [
            self.__heading(heading_level) + " " + self.heading,
            self.content,
        ]
        r.extend(x.describe(heading_level + 1) for x in self.children)
        return "\n".join(r)

    @staticmethod
    def __heading(level: int = 1) -> str:
        return "#" * level
