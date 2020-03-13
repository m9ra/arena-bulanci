from arena_bulanci.bots.bot_base import BotBase
from arena_bulanci.core.utils import distance


class RandomWalkBot(BotBase):
    def _on_bot_spawned(self):
        # choose a random target to which bot will be heading
        self._next_walk_target = self.get_random_reachable_point()

    def _play(self):
        if self.can_shoot and self.try_rotate_towards_shootable_opponent():
            # there is someone who could be shot
            self.shoot()
        if distance(self.position, self._next_walk_target) < 5:
            # target reached
            self._next_walk_target = self.get_random_reachable_point()  # choose a different target
        else:
            # get closer to the target
            self.move_towards(self._next_walk_target)
