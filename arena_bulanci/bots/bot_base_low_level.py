import random
from queue import Queue
from threading import Thread
from typing import Tuple, Optional, List, Dict

from arena_bulanci.bots.game_plan import GamePlan
from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.game_update_request import GameUpdateRequest
from arena_bulanci.core.game_updates.player_spawn_request import PlayerSpawnRequest
from arena_bulanci.core.utils import install_kill_on_exception_in_any_thread


class BotBaseLowLevel(object):
    """
    Low level implementation of Bot <--> Arena integration.
    There should not be any need to reed and modify this when writing custom bot.
    """

    def __init__(self, color: Tuple[int, int, int] = None):
        self.player_id: Optional[str] = None
        self.color: Optional[Tuple[int, int, int]] = color
        if self.color is None:
            self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        self._waits_for_spawn = True
        self._waits_for_kill = False
        self._update_requests: List[GameUpdateRequest] = []
        self._incoming_updates = Queue()
        self._game: Optional[Game] = None

        install_kill_on_exception_in_any_thread()
        self._worker = Thread(target=self._play_worker, daemon=True).start()
        self._update_request_callback = None
        self._position_plans: Dict[Tuple[int, int], GamePlan] = {}

    def _play(self):
        """
        The playing logic has to be implemented here
        """
        raise NotImplementedError("has to be overridden")

    def _on_bot_spawned(self):
        """Callback called when bot gets spawned"""
        pass  # nothing to do by default

    def _on_bot_killed(self):
        """Callback called when bot gets killed"""
        pass  # nothing to do by default

    def get_update_request_async(self, game: Game, callback):
        """
        Should be called only by the core package.
        Requests asynchronously an update request.
        """
        self._update_request_callback = callback
        self._incoming_updates.put(game.copy_without_internal_data())

    def pop_update_request(self, game: Game) -> GameUpdateRequest:
        """
        Should be called only by the core package.
        Pops a single update request.
        """
        self._game = game

        if game.player_is_spawned(self.player_id):
            if self._waits_for_spawn:
                self._waits_for_spawn = False
                self._waits_for_kill = True
                self._on_bot_spawned()

            if not self._update_requests:
                self._play()
        else:
            if self._waits_for_kill:
                self._waits_for_kill = False
                self._waits_for_spawn = True
                self._on_bot_killed()

            self._update_requests.clear()

            if game.can_spawn(self.player_id):
                self._add_update_request(PlayerSpawnRequest(self.player_id, self.color))

        if not self._update_requests:
            return None

        update = self._update_requests.pop(0)
        update.tick = game.tick
        return update

    def _add_update_request(self, request: GameUpdateRequest):
        """
        Adds update request to a queue which will be sent (one request at a time) to the arena.
        """
        self._update_requests.append(request)

    def _play_worker(self):
        """
        Worker dispatching update requests.
        """
        while True:
            game = self._incoming_updates.get()
            while not self._incoming_updates.empty():
                print(f"INFO: Skipping tick {game.tick}")
                game = self._incoming_updates.get_nowait()

            update = self.pop_update_request(game)

            callback = self._update_request_callback
            if callback:
                self._update_request_callback = None
                callback(update)
