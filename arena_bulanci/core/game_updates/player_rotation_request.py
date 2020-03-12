from typing import List

from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.game_updates.player_state_change import PlayerStateChange
from arena_bulanci.core.game_updates.player_update_request import PlayerUpdateRequest


class PlayerRotationRequest(PlayerUpdateRequest):
    def __init__(self, player_id: str, desired_direction: int):
        super().__init__(player_id)

        if not isinstance(desired_direction, int):
            raise ValueError(f"direction has be passed as `int` but was {desired_direction}")

        self.desired_direction = desired_direction

    def create_updates(self, game: 'Game') -> List[GameUpdate]:
        player = game.get_player(self.player_id)

        return [PlayerStateChange(player.id, new_direction=self.desired_direction)]

    def __repr__(self):
        return f"rotate({self.desired_direction}): {self.player_id}"
