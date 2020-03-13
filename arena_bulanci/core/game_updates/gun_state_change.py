from typing import Optional

from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.utils import has


class GunStateChange(GameUpdate):
    def __init__(self, player_id: str, new_ammo_count: Optional[int] = None):
        self.player_id = player_id

        self._new_ammo_count = new_ammo_count

    def apply_on(self, game: 'Game'):
        if has(self._new_ammo_count):
            player = game.get_player(self.player_id)
            if player.gun.ammo_count > self._new_ammo_count:
                player.gun._cooldown_start = game.tick

            player.gun.ammo_count = self._new_ammo_count

    def __repr__(self):
        result = f"gun_change({self.player_id}):"

        if has(self._new_ammo_count):
            result += f" ammo count = {self._new_ammo_count}"

        return result
