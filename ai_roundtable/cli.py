"""Entry point of CLI."""

import argparse
import os
import sys
import textwrap

from .config import ConfigYaml, Config, Message
from .io import file_or, Writer
from .log import debug, log, quiet, stream
from .mtg import Meeting
from .rule import Rule
from .skeleton import Skeleton
from .yamlx import dumps as yaml_dumps


async def main() -> int:
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
            # custom model provider
            python -m ai_roundtable.cli -c dual.yml -a "Can AI be a friend to humans?" \\
              -u "http://localhost:11434/v1" -m "gemma3"

            A speaker that system.name is "end" overrides the end evaluator that \\
            dicides whther to continue the discussion.
            A speaker that system.name is "summary" override the summary evaluator that \\
            provides the summary of the discussion.
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
    parser.add_argument("-m", "--model", type=str, action="store", default="gemma3", help="AI model, default: gemma3")
    parser.add_argument(
        "-u",
        "--base_url",
        type=str,
        action="store",
        default="",
        help="base url of API",
    )
    parser.add_argument(
        "-c", "--config", type=str, action="store", default="config.yml", help="config file, default: config.yml"
    )
    parser.add_argument("-t", "--thread", type=str, action="store", help="thread file, - means stdin")
    parser.add_argument("-o", "--out", type=str, action="store", help="thread output, default: null")
    parser.add_argument("--disable_stream", action="store_true", help="disable message streaming to stdout")
    parser.add_argument(
        "-n", "--max_turns", type=int, action="store", default=16, help="maximum number of statements, default: 16"
    )
    parser.add_argument(
        "-p",
        "--eval_messages",
        type=int,
        action="store",
        default=5,
        help="maximum number of statements to go back for evaluation, default: 5",
    )
    parser.add_argument("-e", "--eval_out", type=str, action="store", help="evaluation output, default: null")
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
    parser.add_argument("-l", "--language", action="store", default="English", help="preferred language")
    parser.add_argument(
        "--api_key_env", action="store", type=str, default="", help="Name of environment variable of API key"
    )
    args = parser.parse_args()

    if args.debug:
        debug()
    if args.quiet:
        quiet()
    if not args.disable_stream:
        stream()

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

    def out_stream(dest: str | None) -> Writer:
        if dest is None:
            return Writer.null()
        return Writer.new(dest)

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
    out = out_stream(args.out)
    eval_out = out_stream(args.eval_out)

    def message_append_hook(m: Message) -> None:
        log().info("message apppended id=%s", m.identity())
        out.write(yaml_dumps([m.into_dict()]))

    def end_evaluator_hook(v: bool) -> None:
        log().info("end evaluation appended: %s", v)

    def summary_evaluator_hook(v: str) -> None:
        log().info("summary evaluation appended")
        eval_out.write(yaml_dumps([{"summary": v}]))

    def raw_evaluator_hook(name: str, v: str) -> None:
        log().info("%s evaluation appended", name)
        eval_out.write(yaml_dumps([{name: v}]))

    c.main_thread.set_append_hook(message_append_hook)
    meeting = Meeting(
        rule=Rule(config=c),
        model=args.model,
        max_turns=args.max_turns,
        end=args.user_input_end,
        end_evaluator_hook=end_evaluator_hook,
        summary_evaluator_hook=summary_evaluator_hook,
        raw_evaluator_hook=raw_evaluator_hook,
        skip_eval_turns=args.skip_eval,
        language=args.language,
        agenda=agenda,
        latest_messages=args.eval_messages,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
    )
    meeting.setup()
    if args.instructions is not None:
        print(
            Rule(config=c)
            .print_rules(speaker=c.speakers[args.instructions].name, language=args.language, agenda=agenda)
            .describe()
        )
        return 0
    await meeting.start()

    return 0


if __name__ == "__main__":
    import sys
    import asyncio

    sys.exit(asyncio.run(main()))
