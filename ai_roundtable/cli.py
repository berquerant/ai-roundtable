"""Entry point of CLI."""

import argparse
import os
import sys
import textwrap
import typing
from contextlib import contextmanager

from .bot import Evaluator, EvaluatorFeedback
from .config import ConfigYaml, Config, Message
from .io import file_or
from .log import debug, log, quiet
from .mtg import Meeting
from .rule import Rule
from .skeleton import Skeleton
from .yamlx import dumps as yaml_dumps


def main() -> int:
    """Entry point of CLI."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Discuss with multiple AIs",
        epilog=textwrap.dedent(
            """\
            Examples:
            # start discussion
            python -m ai_roundtable.cli --skeleton dual > dual.yml
            python -m ai_roundtable.cli -c dual.yml -a "Can AI be a friend to humans?"
            # continue discussion
            python -m ai_roundtable.cli -c dual.yml -a "Can AI be a friend to humans?" -o thread.yml
            python -m ai_roundtable.cli -c dual.yml -t thread.yml

            Environment variables:
              OPENAI_API_KEY
                required, API key from OpneAI project
        """
        ),
    )
    parser.add_argument(
        "-a",
        "--agenda",
        type=str,
        action="store",
        help=textwrap.dedent(
            """\
            first message to give to AI, agenda.
            @file_name to specify a file.
            @- to read from stdin.
            if not specified and thread file exists, the first statement should be agenda"""
        ),
    )
    parser.add_argument(
        "-m", "--model", type=str, action="store", default="gpt-4o-mini", help="AI model, default: gpt-4o-mini"
    )
    parser.add_argument(
        "-c", "--config", type=str, action="store", default="config.yml", help="config file, default: config.yml"
    )
    parser.add_argument("-t", "--thread", type=str, action="store", help="thread file, - means stdin")
    parser.add_argument("-o", "--out", type=str, action="store", help="thread output, default: stdout")
    parser.add_argument(
        "-n", "--max_turns", type=int, action="store", default=8, help="maximum number of statements, default: 8"
    )
    parser.add_argument(
        "--eval_messages",
        type=int,
        action="store",
        default=5,
        help="maximum number of statements to go back for evaluation, default: 5",
    )
    parser.add_argument("-e", "--eval_out", type=str, action="store", help="evaluation output, default: stdout")
    parser.add_argument(
        "-s",
        "--skip_eval",
        type=int,
        action="store",
        default=0,
        help="turns skip evaluation, negative value means never evaluate, default: 0",
    )
    parser.add_argument(
        "--user_input_end", type=str, action="store", default="END", help="signal end of user input, default: END"
    )
    parser.add_argument("--debug", action="store_true", help="enable debug log")
    parser.add_argument("--quiet", action="store_true", help="quiet log")
    parser.add_argument("--skeleton", choices=["minimal", "dual", "full"], help="display config skeleton")
    parser.add_argument(
        "--instructions",
        action="store",
        type=int,
        help="display instructions for n-th speaker (0 means the first speaker), needs config",
    )
    args = parser.parse_args()

    if args.debug:
        debug()
    if args.quiet:
        quiet()

    log().debug("start ai-roundtable")

    if args.skeleton:
        match args.skeleton:
            case "minimal":
                print(Skeleton.minimal())
            case "dual":
                print(Skeleton.dual())
            case "full":
                print(Skeleton.full())
        return 0

    def config() -> Config:
        with open(args.config) as f:
            config = f.read()
        thread = ""
        match args.thread:
            case "-":
                thread = sys.stdin.read()
            case None:
                thread = ""
            case v:
                if os.path.isfile(v):
                    with open(v) as f:
                        thread = f.read()
        return ConfigYaml(config=config, thread=thread).into_config()

    @contextmanager
    def out_stream(
        dest: str | None, default: typing.IO[str] = sys.stdout
    ) -> typing.Generator[typing.IO[str], None, None]:
        if dest is None:
            yield default
            return
        try:
            f = open(dest, "a")
            yield f
        finally:
            f.close()

    c = config()

    def read_agenda() -> str:
        if args.agenda:
            a: str = args.agenda
            return file_or(a)
        if args.instructions is not None:
            return "DUMMY AGENDA"
        if len(c.main_thread) == 0:
            raise Exception("no agenda!")
        return c.main_thread.messages[0].content

    agenda = read_agenda()

    with out_stream(args.out) as out, out_stream(args.eval_out) as eval_out:

        def message_append_hook(m: Message) -> None:
            log().info("message apppended id=%s", m.identity())
            obj = [m.into_dict()]
            s = yaml_dumps(obj)
            print(s, file=out, flush=True)

        def evaluator_hook(e: EvaluatorFeedback) -> None:
            log().info("evaluation appended decision=%s", e.decision)
            obj = [e.into_dict()]
            s = yaml_dumps(obj)
            print(s, file=eval_out, flush=True)

        c.main_thread.set_append_hook(message_append_hook)
        meeting = Meeting(
            rule=Rule(config=c),
            model=args.model,
            max_turns=args.max_turns,
            end=args.user_input_end,
            evaluator=Evaluator(
                main_thread=c.main_thread,
                agenda=agenda,
                latest_messages=args.eval_messages,
                hook=evaluator_hook,
            ),
            skip_eval_turns=args.skip_eval,
            agenda=agenda,
        )
        meeting.setup()
        if args.instructions is not None:
            print(Rule(config=c).print_rules(c.speakers[args.instructions].name).describe())
            return 0
        meeting.start()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
