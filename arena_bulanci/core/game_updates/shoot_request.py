from typing import List

from arena_bulanci.core.game_updates.add_bullet import AddBullet
from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.game_updates.gun_state_change import GunStateChange
from arena_bulanci.core.game_updates.player_update_request import PlayerUpdateRequest


class ShootRequest(PlayerUpdateRequest):
    def create_updates(self, game: 'Game') -> List[GameUpdate]:
        player = game.get_player(self.player_id)

        if not player.gun.can_shoot(game):
            raise ValueError("Can't shoot in this state")

        ray = player.get_bullet_ray()
        return [
            GunStateChange(self.player_id, new_ammo_count=player.gun.ammo_count - 1),
            AddBullet(f"bullet{game.tick}-{player.id}", ray.start, ray.direction_coords, self.player_id)
        ]

    def __repr__(self):
        return f"shoot: {self.player_id}"
