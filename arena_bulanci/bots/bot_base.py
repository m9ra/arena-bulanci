import random
from concurrent.futures.thread import ThreadPoolExecutor
from queue import Queue
from threading import Thread
from typing import Tuple, Optional, List, Dict

from arena_bulanci.bots.game_plan import GamePlan
from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.game_update_request import GameUpdateRequest
from arena_bulanci.core.game_updates.player_move_request import PlayerMoveRequest
from arena_bulanci.core.game_updates.player_rotation_request import PlayerRotationRequest
from arena_bulanci.core.game_updates.player_spawn_request import PlayerSpawnRequest
from arena_bulanci.core.game_updates.shoot_request import ShootRequest
from arena_bulanci.core.player import Player
from arena_bulanci.core.utils import distance, install_kill_on_exception_in_any_thread, DIRECTION_DEFINITIONS, step_from

MAX_CACHED_PLANS = 1000
PLAN_EXECUTOR = ThreadPoolExecutor(max_workers=1)

class BotBase(object):
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
    def opponents(self):
        return self.game.opponents_of(self.my_player)

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
        if not self.try_move_towards_by_plan(target):
            self.simple_move_towards(target)

    def try_move_towards_by_plan(self, target: Tuple[int, int]):
        if target not in self._position_plans:
            if len(self._position_plans) > MAX_CACHED_PLANS:
                self._position_plans.clear()
            self._position_plans[target] = None  # allocate slot for the plan

            def _create_plan_async():
                plan = GamePlan.plan_route_to_targets([target], allow_shooting=True)
                self._position_plans[target] = plan

            PLAN_EXECUTOR.submit(_create_plan_async)
            return False

        plan = self._position_plans[target]
        if plan is None:
            # plan was requested but is not available yet
            return False

        desired_direction = plan.board[self.position].move_direction
        if not self.has_free_step_in(desired_direction):
            # plan does not count with temporary obstacles
            return False

        self.rotate(desired_direction)
        self.move()
        return True

    def has_free_step_in(self, direction: int, step_count: int = 1):
        next_position = self.position
        for _ in range(step_count):
            next_position = step_from(next_position, direction)
            if not self.game.can_player_step_on(next_position, disabled_objects=[self.my_player]):
                return False
        return True

    def simple_move_towards(self, target: Tuple[int, int]):
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
                for _ in range(2):
                    self.move()

            self.add_update_request(move_request)
        else:
            self.rotate(walk_direction)

    def move(self):
        self.add_update_request(PlayerMoveRequest(self.player_id))

    def rotate(self, direction, skip_if_already_rotated=True):
        if skip_if_already_rotated and self.direction == direction:
            return

        self.add_update_request(PlayerRotationRequest(self.player_id, direction % len(DIRECTION_DEFINITIONS)))

    def rotate_randomly(self):
        self.add_update_request(PlayerRotationRequest(
            self.player_id, random.randint(0, len(DIRECTION_DEFINITIONS) - 1)
        ))

    def try_rotate_towards_shootable_opponent(self):
        for opponent in self.game.opponents_of(self.my_player):
            shooting_direction = self.my_player.get_closest_direction_towards(opponent.position)
            if not self.game.has_clear_bullet_path(self.my_player.as_if_rotated_to(shooting_direction), opponent):
                continue  # can't hit the opponent

            self.rotate(shooting_direction)
            return True

        return False

    def get_shootable_opponents(self) -> List[Tuple[Player, int]]:
        result = []
        for opponent in self.game.opponents_of(self.my_player):
            shooting_direction = self.my_player.get_closest_direction_towards(opponent.position)
            if not self.game.has_clear_bullet_path(self.my_player.as_if_rotated_to(shooting_direction), opponent):
                continue  # can't hit the opponent

            result.append((opponent, shooting_direction))

        return result


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

        update = self._update_requests.pop(0)
        update.tick = game.tick
        return update

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
