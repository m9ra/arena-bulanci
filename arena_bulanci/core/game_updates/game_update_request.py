from typing import List, Optional

from arena_bulanci.core.game_updates.game_update import GameUpdate


class GameUpdateRequest(object):
    def __init__(self):
        self.tick: Optional[int] = None  # tick when this update was created

    def create_updates(self, game: 'Game') -> List[GameUpdate]:
        """
        Creates update from the request.
        If update can't be applied (e.g. due to rules), exception is raised.
        """
        raise NotImplementedError("must be overridden")
