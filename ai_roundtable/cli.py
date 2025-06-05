"""Entry point of CLI."""

import argparse
import os
import sys
import textwrap

from .bot import Evaluator, EvaluatorFeedback
from .config import ConfigYaml, Config, Message
from .io import file_or, Writer
from .log import debug, log, quiet, stream
from .mtg import Meeting
from .provider import Setting
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

            Environment variables:
              OPENAI_API_KEY
                required, API key from OpenAI project
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
        "-u",
        "--base_url",
        type=str,
        action="store",
        help="base url of API",
    )
    parser.add_argument(
        "-c", "--config", type=str, action="store", default="config.yml", help="config file, default: config.yml"
    )
    parser.add_argument("-t", "--thread", type=str, action="store", help="thread file, - means stdin")
    parser.add_argument("-o", "--out", type=str, action="store", help="thread output, default: stdout")
    parser.add_argument("--disable_stream", action="store_true", help="disable message streaming to stdout")
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

    provider_setting = Setting(model_name=args.model, base_url=args.base_url, api_key=os.getenv("OPENAI_API_KEY") or "")

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
            return Writer.stdout()
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
        obj = [m.into_dict()]
        s = yaml_dumps(obj)
        out.write(s)

    def evaluator_hook(e: EvaluatorFeedback) -> None:
        log().info("evaluation appended decision=%s", e.decision)
        obj = [e.into_dict()]
        s = yaml_dumps(obj)
        eval_out.write(s)

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
            model_provider=provider_setting.provider,
        ),
        skip_eval_turns=args.skip_eval,
        agenda=agenda,
        model_provider=provider_setting.provider,
    )
    meeting.setup()
    if args.instructions is not None:
        print(Rule(config=c).print_rules(c.speakers[args.instructions].name).describe())
        return 0
    await meeting.start()

    return 0


if __name__ == "__main__":
    import sys
    import asyncio

    sys.exit(asyncio.run(main()))
