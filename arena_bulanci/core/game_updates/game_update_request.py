from typing import List

from arena_bulanci.core.game_updates.game_update import GameUpdate


class GameUpdateRequest(object):
    def create_updates(self, game: 'Game') -> List[GameUpdate]:
        """
        Creates update from the request.
        If update can't be applied (e.g. due to rules), exception is raised.
        """
        raise NotImplementedError("must be overridden")
