import random
from typing import List, Optional, Tuple

from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.game_updates.player_state_change import PlayerStateChange
from arena_bulanci.core.game_updates.player_update_request import PlayerUpdateRequest
from arena_bulanci.core.utils import DIRECTION_DEFINITIONS


class PlayerSpawnRequest(PlayerUpdateRequest):
    def __init__(self, player_id, color: Optional[Tuple[int, int, int]]):
        super().__init__(player_id)
        self.color = color

    def create_updates(self, game: 'Game') -> List[GameUpdate]:
        if game.player_is_spawned(self.player_id):
            raise ValueError("Can't spawn player which is in game already")

        if not game.can_spawn(self.player_id):
            raise ValueError("Can't spawn player so quickly")

        if self.color is not None:
            c = self.color
            if not isinstance(c, tuple) or len(c) != 3 or not all(isinstance(p, int) and 0 <= p <= 255 for p in c):
                raise ValueError(f"color: {c}")

        position = game.find_spawn_point()
        direction = random.choice(range(len(DIRECTION_DEFINITIONS)))
        return [PlayerStateChange(
            self.player_id,
            new_position=position,
            new_direction=direction,
            new_color=self.color,
            is_alive=True
        )]

    def __repr__(self):
        return f"spawn: {self.player_id}, color: {self.color}"
