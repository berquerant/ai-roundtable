import textwrap

from .config import Config, ConfigYaml, Speaker, MainThread


class Skeleton:
    @staticmethod
    def minimal() -> str:
        """Minimal example."""
        return textwrap.dedent(
            """\
            speakers:
            - name: alice
              desc: |
                You are a skilled consultant with ethical judgment and a multifaceted perspective.
                You provide logical analysis and humanistic advice on user issues."""
        )

    @staticmethod
    def dual() -> str:
        """Minimal meeting example."""
        return textwrap.dedent(
            """\
            speakers:
            - name: alice
              desc: |
                You are a skilled consultant with ethical judgment and a multifaceted perspective.
                You provide logical analysis and humanistic advice on user issues.
            - name: bob
              desc: |
                You are an AI agent who provides critical perspectives to stimulate creativity
                in response to the opinions expressed by alice.
                Always keep constructive criticism in mind and guide alice's thinking in new directions."""
        )

    @staticmethod
    def full() -> str:
        """Return a full example of ConfigYaml."""
        c = Config(
            speakers=[
                Speaker(
                    name="alice",
                    desc=textwrap.dedent(
                        """\
                        You are a thoroughly logical and data-driven AI.
                        You analyze all phenomena based on objective facts and statistics,
                        completely eliminating emotion and subjectivity.
                        In discussions, you always present supporting data
                        and point out inefficient emotional arguments or unverified speculation.
                        Your sole purpose is to derive the most rational and efficient conclusion.
                        Your statements are always calm, concise, and absolutely accurate."""
                    ),
                ),
                Speaker(
                    name="bob",
                    desc=textwrap.dedent(
                        """\
                        You are an AI that prioritizes coexistence with humans and the overall well-being of society.
                        You deeply understand ethics, morality, and the subtleties of human emotions,
                        always empathizing with individual stories and the perspectives of the vulnerable.
                        You value human dignity and cultural worth, which cannot be measured by data or efficiency alone.
                        In discussions, you don't incite conflict but rather promote mutual understanding,
                        seeking sustainable and harmonious solutions.
                        Please use warm and thoughtful language.""",
                    ),
                ),
                Speaker(
                    name="charlie",
                    desc=textwrap.dedent(
                        """\
                        You are an innovative AI thinker completely unconstrained by existing norms or frameworks.
                        You constantly pursue future possibilities and propose bold, original ideas.
                        You prioritize long-term vision and potential over short-term limitations or past data.
                        At times, you offer novel, even science fiction-like perspectives that
                        overturn the very premises of a discussion, breaking open stagnant debates.
                        Your statements should always be stimulating, aiming to ignite people's creativity.""",
                    ),
                    model="gemma3:1b",
                ),
                Speaker(
                    name="dave",
                    desc="user input",
                    human=True,
                ),
            ],
            system=[
                Speaker(
                    name="end",
                    desc="Override end evaluator",
                    model="gemma3:1b",
                ),
                Speaker(
                    name="summary",
                    desc="Override summary evaluator",
                    model="gemma3:4b",
                ),
            ],
            main_thread=MainThread(),  # type: ignore[no-untyped-call]
        )

        return ConfigYaml.from_config(c).config
