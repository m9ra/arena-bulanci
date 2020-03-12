from typing import Tuple

from arena_bulanci.bots.bot_base import BotBase


class PositionKeepBot(BotBase):
    def __init__(self, target: Tuple[int, int]):
        super().__init__()

        self._target = target

    def _play(self):
        if self.position == self._target:
            # at position, shoot if needed
            if self.can_shoot and self.try_rotate_towards_shootable_opponent():
                # there is someone who could be shot
                self.shoot()
        else:
            # get closer to the target
            self.move_towards(self._target)
