import textwrap

from .config import Config, Role, Permission, ConfigYaml, Speaker, MainThread


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
            permissions=[
                Permission(name="dovish"),
            ],
            roles=[
                Role(name="dovish", desc="readable and writable dovish messages", permissions={"dovish"}),
            ],
            speakers=[
                Speaker(
                    name="alice",
                    desc="You are to be as discreet in your discussions as anyone else at this meeting.",
                    read_roles={"dovish"},
                    write_roles={"dovish"},
                ),
                Speaker(
                    name="bob",
                    desc="You are to remain neutral in the discussion at this meeting.",
                    read_roles={"dovish"},
                    write_roles={"dovish"},
                ),
                Speaker(
                    name="charlie",
                    desc="You are free to express your opinion without regard to your position in this meeting.",
                ),
                Speaker(
                    name="dave",
                    desc="user input",
                    human=True,
                ),
            ],
            main_thread=MainThread(),  # type: ignore[no-untyped-call]
        )

        return ConfigYaml.from_config(c).config
