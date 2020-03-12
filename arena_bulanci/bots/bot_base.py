import random
from queue import Queue
from threading import Thread
from time import sleep
from typing import Tuple, Optional, List

from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.game_update_request import GameUpdateRequest
from arena_bulanci.core.game_updates.player_move_request import PlayerMoveRequest, DIRECTION_DEFINITIONS, \
    DIRECTION_LOOKUP
from arena_bulanci.core.game_updates.player_rotation_request import PlayerRotationRequest
from arena_bulanci.core.game_updates.player_spawn_request import PlayerSpawnRequest
from arena_bulanci.core.game_updates.shoot_request import ShootRequest
from arena_bulanci.core.player import Player
from arena_bulanci.core.utils import distance, install_kill_on_exception_in_any_thread


class BotBase(object):
    def __init__(self):
        self.player_id: Optional[str] = None
        self.color: Optional[Tuple[int, int, int]] = (
            random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        )
        self._waits_for_spawn = True
        self._waits_for_kill = False
        self._update_requests: List[GameUpdateRequest] = []
        self._incoming_updates = Queue()
        self._game: Optional[Game] = None

        install_kill_on_exception_in_any_thread()
        self._worker = Thread(target=self._play_worker, daemon=True).start()
        self._update_request_callback = None

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

    @property
    def is_game_running(self):
        return self._game.is_running

    @property
    def game(self):
        return self._game

    @property
    def my_player(self) -> Player:
        return self.game.get_player(self.player_id)

    @property
    def position(self):
        return self.my_player.position

    @property
    def direction(self):
        return self.my_player.direction

    @property
    def can_shoot(self):
        return self.game.can_player_shoot(self.player_id)

    def shoot(self):
        self.add_update_request(ShootRequest(self.player_id))

    def move_towards(self, target: Tuple[int, int]):
        # todo add obstacle avoiding logic here (maybe real path planning?)
        d = DIRECTION_DEFINITIONS[self.direction]
        p = self.position
        new_pos = (p[0] + d[0], p[1] + d[1])
        if distance(new_pos, target) < distance(self.position, target):
            walk_direction = self.direction
        else:
            walk_direction = self.my_player.get_closest_direction_towards(target)

        if walk_direction == self.my_player.direction:
            move_request = PlayerMoveRequest(self.player_id)
            if not self.game.validate(move_request):
                # probably some obstacle, make random step to unstuck
                self.rotate_randomly()

            self.add_update_request(move_request)
        else:
            self.rotate(walk_direction)

    def move(self):
        self.add_update_request(PlayerMoveRequest(self.player_id))

    def rotate(self, direction):
        self.add_update_request(PlayerRotationRequest(self.player_id, direction))

    def rotate_randomly(self):
        self.add_update_request(PlayerRotationRequest(
            self.player_id, random.randint(0, len(DIRECTION_DEFINITIONS) - 1)
        ))

    def try_rotate_towards_shootable_opponent(self):
        for opponent in self.game.opponents_of(self.my_player):
            shooting_direction = self.my_player.get_closest_direction_towards(opponent.position)
            if not self.game.has_clear_bullet_path(self.my_player.as_if_rotated_to(shooting_direction), opponent):
                continue  # can't hit the opponent

            if shooting_direction != self.direction:
                self.add_update_request(PlayerRotationRequest(self.player_id, shooting_direction))

            return True

        return False

    def get_random_reachable_point(self):
        # every spawn point has to be reachable
        return self.game.find_spawn_point()

    def add_update_request(self, request: GameUpdateRequest):
        self._update_requests.append(request)

    def get_update_request_async(self, game: Game, callback):
        self._update_request_callback = callback
        self._incoming_updates.put(game.copy_without_internal_data())

    def pop_update_request(self, game: Game):
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
                self.add_update_request(PlayerSpawnRequest(self.player_id, self.color))

        if not self._update_requests:
            return None

        return self._update_requests.pop(0)

    def _play_worker(self):
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
