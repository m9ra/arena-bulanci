from typing import List

from arena_bulanci.core.collision_exception import CollisionException
from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.game_updates.player_state_change import PlayerStateChange
from arena_bulanci.core.game_updates.player_update_request import PlayerUpdateRequest
from arena_bulanci.core.utils import DIRECTION_DEFINITIONS


class PlayerMoveRequest(PlayerUpdateRequest):
    def create_updates(self, game: 'Game') -> List[GameUpdate]:
        player = game.get_player(self.player_id)

        move = DIRECTION_DEFINITIONS[player.direction]
        p = player.position
        next_position = (p[0] + move[0], p[1] + move[1])

        if not game.can_player_step_on(next_position, disabled_objects=[player]):
            raise CollisionException("Can't step on the position")

        return [PlayerStateChange(self.player_id, new_position=next_position)]

    def __repr__(self):
        return f"move: {self.player_id}"
