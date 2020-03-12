from typing import Optional

from arena_bulanci.core.game_updates.game_update import GameUpdate


class RemoveBullet(GameUpdate):
    def __init__(self, bullet_id: str, hit_player_id: Optional[str], reward_receiver_id: Optional[str]):
        self._bullet_id = bullet_id
        self.hit_player_id = hit_player_id
        self.reward_receiver_id = reward_receiver_id

    def apply_on(self, game: 'Game'):
        for i in range(len(game._bullets)):
            if game._bullets[i].id == self._bullet_id:
                del game._bullets[i]
                return

    def __repr__(self):
        return f"remove_bulet: {self._bullet_id}"
