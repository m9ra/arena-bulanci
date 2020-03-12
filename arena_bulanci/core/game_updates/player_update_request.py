from arena_bulanci.core.game_updates.game_update_request import GameUpdateRequest


class PlayerUpdateRequest(GameUpdateRequest):
    def __init__(self, player_id: str):
        self.player_id = player_id

