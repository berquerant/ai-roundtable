import typing
from dataclasses import dataclass

from agents import ModelProvider

from .bot import Bot, Human, BotProto, EndEvaluator, SummaryEvaluator, Evaluator, RawEvaluator
from .config import Config, Speaker
from .log import log
from .rule import Rule


@dataclass
class Meeting:
    model: str
    max_turns: int
    rule: Rule
    end: str
    end_evaluator_hook: typing.Callable[[bool], None]
    summary_evaluator_hook: typing.Callable[[str], None]
    raw_evaluator_hook: typing.Callable[[str, str], None]
    skip_eval_turns: int
    language: str
    agenda: str
    latest_messages: int
    base_url: str
    api_key_env: str

    @property
    def config(self) -> Config:
        return self.rule.config

    def setup(self) -> None:
        self.config.setup()

    def __provider(self, speaker: Speaker) -> ModelProvider:
        return speaker.provider(
            model=self.model,
            base_url=self.base_url,
            api_key_env=self.api_key_env,
        )

    def __evaluator_params(self, speaker: Speaker) -> dict[str, typing.Any]:
        log().info("evaluator[%s]: %s", speaker.name, speaker.model_or(self.model))
        return {
            "name": speaker.name,
            "main_thread": self.config.main_thread,
            "agenda": self.agenda,
            "latest_messages": self.latest_messages,
            "language": self.language,
            "model_provider": self.__provider(speaker),
        }

    @property
    def __end_evaluator(self) -> Evaluator[bool]:
        return EndEvaluator(hook=self.end_evaluator_hook, **self.__evaluator_params(self.config.end_evaluator))

    @property
    def __summary_evaluator(self) -> Evaluator[str]:
        return SummaryEvaluator(
            hook=self.summary_evaluator_hook, **self.__evaluator_params(self.config.summary_evaluator)
        )

    @property
    def __raw_evaluators(self) -> list[Evaluator[str]]:
        RawEvaluator
        return [
            RawEvaluator(
                hook=lambda v: self.raw_evaluator_hook(x.name, v),
                desc=x.desc,
                **self.__evaluator_params(x),
            )
            for x in self.config.raw_evaluators
        ]

    def new_bot(self, speaker: Speaker) -> BotProto:
        if speaker.human:
            log().info("speaker[human]: %s", speaker.name)
            return Human(
                main_thread=self.config.main_thread,
                speaker=speaker,
                end=self.end,
            )

        log().info("speaker[bot]: %s, %s", speaker.name, speaker.model_or(self.model))
        return Bot(
            main_thread=self.config.main_thread,
            speaker=speaker,
            instructions=self.rule.print_rules(
                speaker=speaker.name, language=self.language, agenda=self.agenda
            ).describe(),
            model_provider=self.__provider(speaker),
        )

    def __speaker(self, turn: int) -> Speaker:
        index = (turn - 1) % len(self.config.speakers)
        return self.config.speakers[index]

    def __skip(self, turn: int) -> bool:
        if self.skip_eval_turns < 0:
            log().debug("turn: %d, skip eval because skip_eval_turns is negative", turn)
            return True
        if turn <= self.skip_eval_turns:
            log().debug("turn: %d, skip eval because turn <= skip_eval_turns", turn)
            return True
        if turn / len(self.config.speakers) < 2:
            log().debug("turn: %d, skip eval because turn is too small", turn)
            return True
        if turn % len(self.config.speakers) != 0:
            log().debug("turn: %d, skip eval because not everyone has spoken yet", turn)
            return True
        return False

    async def __evaluate(self, turn: int) -> bool:
        if self.__skip(turn):
            return False
        log().info("turn: %d, evaluate", turn)
        if not await self.__end_evaluator.evaluate():
            return False
        log().info("meeting end due to end evaluation")
        await self.__summary_evaluator.evaluate()
        for e in self.__raw_evaluators:
            await e.evaluate()
        return True

    async def start(self) -> None:
        log().info("meeting start")
        for turn in range(1, self.max_turns + 1):
            s = self.__speaker(turn)
            log().info("turn: %d, speaker: %s", turn, s.name)
            await self.new_bot(s).reply()
            if await self.__evaluate(turn):
                return
        log().info("meeting end due to max_turns: %d", self.max_turns)
