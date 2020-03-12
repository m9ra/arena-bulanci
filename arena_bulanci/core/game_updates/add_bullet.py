from typing import Tuple

from arena_bulanci.core.bullet import Bullet
from arena_bulanci.core.game_updates.game_update import GameUpdate


class AddBullet(GameUpdate):
    def __init__(self, bullet_id: str,
                 position: Tuple[int, int], direction_coords: Tuple[float, float], reward_receiver: str):
        self._bullet_id = bullet_id
        self._position = position
        self._direction_coords = direction_coords
        self._reward_receiver = reward_receiver

    def apply_on(self, game: 'Game'):
        game._bullets.append(Bullet(
            self._bullet_id, game.tick, self._position, self._direction_coords, reward_receiver_id=self._reward_receiver
        ))

    def __repr__(self):
        return f"add_bullet({self._bullet_id}): pos = {self._position}, dir = {self._direction_coords}, rcv = {self._reward_receiver}"
