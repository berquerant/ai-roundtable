from dataclasses import dataclass

from agents import ModelProvider

from .bot import Bot, Human, BotProto, Evaluator
from .config import Config, Speaker
from .log import log
from .rule import Rule


@dataclass
class Meeting:
    model: str
    max_turns: int
    rule: Rule
    end: str
    end_evaluator: Evaluator[bool]
    summary_evaluator: Evaluator[str]
    skip_eval_turns: int
    model_provider: ModelProvider
    language: str
    agenda: str

    @property
    def config(self) -> Config:
        return self.rule.config

    def setup(self) -> None:
        self.config.setup()

    def new_bot(self, speaker: Speaker) -> BotProto:
        if speaker.human:
            return Human(
                main_thread=self.config.main_thread,
                speaker=speaker,
                end=self.end,
            )
        return Bot(
            main_thread=self.config.main_thread,
            speaker=speaker,
            model=self.model,
            instructions=self.rule.print_rules(
                speaker=speaker.name, language=self.language, agenda=self.agenda
            ).describe(),
            model_provider=self.model_provider,
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
        return await self.end_evaluator.evaluate()

    async def start(self) -> None:
        log().info("meeting start")
        for turn in range(1, self.max_turns + 1):
            s = self.__speaker(turn)
            log().info("turn: %d, speaker: %s", turn, s.name)
            await self.new_bot(s).reply()
            if await self.__evaluate(turn):
                log().info("meeting end due to end evaluation")
                await self.summary_evaluator.evaluate()
                return
        log().info("meeting end due to max_turns: %d", self.max_turns)
