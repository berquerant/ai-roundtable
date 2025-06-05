from dataclasses import dataclass

from agents import ModelProvider

from .bot import Bot, Human, BotProto, Evaluator
from .config import Config, Speaker, Builtin
from .log import log
from .rule import Rule


@dataclass
class Meeting:
    model: str
    max_turns: int
    rule: Rule
    end: str
    evaluator: Evaluator
    skip_eval_turns: int
    agenda: str
    model_provider: ModelProvider

    @property
    def config(self) -> Config:
        return self.rule.config

    def setup(self) -> None:
        self.config.setup()
        if len(self.config.main_thread) == 0:
            log().info("generate introduction messages")
            self.config.main_thread.append(Builtin.moderator_name(), Builtin.public_role().permissions, self.agenda)

    def new_bot(self, speaker: Speaker) -> BotProto:
        if speaker.human:
            return Human(
                main_thread=self.config.main_thread,
                speaker=speaker,
                role_dict=self.config.role_dict,
                permission_dict=self.config.permission_dict,
                end=self.end,
            )
        return Bot(
            main_thread=self.config.main_thread,
            speaker=speaker,
            role_dict=self.config.role_dict,
            permission_dict=self.config.permission_dict,
            model=self.model,
            instructions=self.rule.print_rules(speaker.name).describe(),
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
        r = await self.evaluator.evaluate()
        return r.decision == "end"

    async def start(self) -> None:
        log().info("meeting start")
        for turn in range(1, self.max_turns + 1):
            s = self.__speaker(turn)
            log().info("turn: %d, speaker: %s", turn, s.name)
            await self.new_bot(s).reply()
            if await self.__evaluate(turn):
                log().info("meeting end due to evaluation")
                return
        log().info("meeting end due to max_turns: %d", self.max_turns)
