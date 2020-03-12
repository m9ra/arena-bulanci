from typing import Optional, Tuple

from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.utils import has


class PlayerStateChange(GameUpdate):
    def __init__(self, player_id: str,
                 new_position: Optional[Tuple[int, int]] = None,
                 new_direction: Optional[int] = None,
                 is_alive: Optional[bool] = None,
                 new_color: Optional[Tuple[int, int, int]] = None
                 ):
        self.player_id = player_id

        self._new_position = new_position
        self._new_direction = new_direction
        self._new_color = new_color
        self._is_alive = is_alive

        if self._new_direction is not None and not isinstance(self._new_direction, int):
            raise ValueError(f"new_direction has to be `int` but was {self._new_direction}")

    def apply_on(self, game: 'Game'):
        if has(self._is_alive):
            if self._is_alive:
                game._spawn_player(self.player_id)
            else:
                game._kill_player(self.player_id)
                return  # kill is the last operation on the player

        player = game.get_player(self.player_id)
        if has(self._new_position):
            player.position = self._new_position

        if has(self._new_direction):
            player.direction = self._new_direction

        if has(self._new_color):
            player.color = self._new_color

    def __repr__(self):
        result = f"change({self.player_id}):"
        if has(self._is_alive):
            result += f" is_alive = {self._is_alive}"

        if has(self._new_position):
            result += f" position = {self._new_position}"

        if has(self._new_direction):
            result += f" dir = {self._new_direction}"

        return result
