from arena_bulanci.core.game_updates.game_update import GameUpdate


class ErrorUpdate(GameUpdate):
    def __init__(self, player_id, error):
        self._player_id = player_id
        self.error = error

    def apply_on(self, game: 'Game'):
        pass  # nothing to do here
