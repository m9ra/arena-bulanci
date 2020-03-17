import random
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Tuple, List

from arena_bulanci.bots.bot_base_low_level import BotBaseLowLevel
from arena_bulanci.bots.game_plan import GamePlan
from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.player_move_request import PlayerMoveRequest
from arena_bulanci.core.game_updates.player_rotation_request import PlayerRotationRequest
from arena_bulanci.core.game_updates.shoot_request import ShootRequest
from arena_bulanci.core.player import Player
from arena_bulanci.core.utils import distance, DIRECTION_DEFINITIONS, step_from

MAX_CACHED_PLANS = 100
PLAN_EXECUTOR = ThreadPoolExecutor(max_workers=1)


class BotBase(BotBaseLowLevel):
    """
    Base class intended for all custom bots.
    Only play method is mandatory to be implemented.

    The game is controlled through moves. At a single tick (fyi TICKS_PER_SECOND) a single move is allowed.
    There are 4 basic moves.
    1) Rotate - changes direction which the bot is facing, there are four directions (fyi DIRECTION_DEFINITIONS)
    2) Step forward - makes a single step in bot's direction
    3) Shoot - shoots a bullet in bot's direction (if allowed by ammo and cooldown time)
    4) Spawn - which is handled automatically by the BotBaseLowLevel

    Method for basic moves 1..3 exists and also for their handy compositions exits in this class. They are prefixed by MOVE_
    The MOVE_ methods are enqueuing requests that will be sent one by one to the game.
    The _play method is called to obtain some moves (if multiple moves are issued, the _play method is not called until all the moves were played).

    This means that if bot makes 10 moves in a single _play call, then the _play won't be called for next 10 ticks of the game.
    (which can hurt performance of e.g. quick bullet avoidance strategies).
    Therefore making smaller amount of moves at a single _play call is advised.

    In this class, there are useful callbacks available (e.g. handling when bot spawned, was killed, etc.).
    Also, this class contains many useful methods implemented which are handy for custom bot development.
    (e.g. sophisticated path planning algorithm which fallbacks to simple navigation strategies before full plan is calculated).

    The utility methods should be considered as a reference, how to use `Game` API.
    """

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
    def game(self) -> Game:
        """
        Game is the main API for accessing state of the game.
        """
        return self._game

    @property
    def my_player(self) -> Player:
        """
        Player which is controlled by this bot.
        """
        return self.game.get_player(self.player_id)

    @property
    def opponents(self) -> List[Player]:
        """
        Opponents of this bot.
        """
        return self.game.opponents_of(self.my_player)

    @property
    def position(self) -> Tuple[int, int]:
        """
        Actual position of this bot.
        """
        return self.my_player.position

    @property
    def direction(self) -> int:
        """
        Actual direction of this bot.
        """
        return self.my_player.direction

    @property
    def can_shoot(self):
        """
        Determine if this bot can shoot in this move.
        This considers both, ammo and cooldown time.
        """
        return self.game.can_player_shoot(self.player_id)

    def MOVE_shoot(self):
        """
        Enqueues a single move which will make the bot shoot if allowed.
        """
        self._add_update_request(ShootRequest(self.player_id))

    def MOVE_rotate(self, direction: int, skip_if_already_rotated: bool = True):
        """
        Enqueues rotation move (only if necessary by default) to the given direction.
        """

        if skip_if_already_rotated and self.direction == direction:
            return

        self._add_update_request(PlayerRotationRequest(self.player_id, direction % len(DIRECTION_DEFINITIONS)))

    def MOVE_step_forward(self):
        """
        Enqueues a single step forward move (in current direction).
        The move is rejected if obstacle is in the way (which results in loosing move. See self.has_free_steps_in for obstacle detection)
        """
        self._add_update_request(PlayerMoveRequest(self.player_id))

    def MOVE_go_towards(self, target: Tuple[int, int]):
        """
        Enqueues a composition of rotation and step moves in order to get to given position from current position.
        At most three moves are enqueued at a single time.
        Uses shortest path planning + simple fallback in order to be real time processing friendly.

        Getting stuck at temporary obstacles (i.e. other players) is solved by adding random steps and rotations.
        """
        if not self._try_move_towards_by_plan(target):
            self._simple_move_towards(target)

    def MOVE_rotate_randomly(self):
        """
        Enqueues a move which rotates to a random direction
        """
        self.MOVE_rotate(random.randint(0, len(DIRECTION_DEFINITIONS) - 1))

    def get_random_reachable_point(self) -> Tuple[int, int]:
        """
        Gets a random point where bot will be able to walk.
        Temporary obstacles (i.e. other players) are not considered.
        """
        # every spawn point has to be reachable
        return self.game.find_spawn_point()

    def has_free_steps_in(self, direction: int, step_count: int = 1) -> bool:
        """
        Determines if the bot can do step_count consecutive moves in given direction, from current position.
        Note, that movement of temporal obstacles cannot be considered. Only current obstacle positions are accounted.
        """
        next_position = self.position
        for _ in range(step_count):
            next_position = step_from(next_position, direction)
            if not self.game.can_player_step_on(next_position, disabled_objects=[self.my_player]):
                return False

        return True

    def try_rotate_towards_shootable_opponent(self) -> bool:
        """
        Tries to find a direction in which a clear view to an opponent exits (in terms of bullet path).
        If so, true is returned and rotation move is enqueued.
        Otherwise, no move is enqueued.
        """
        for opponent, shooting_direction in self.get_shootable_opponents():
            self.MOVE_rotate(shooting_direction)
            return True

        return False

    def get_shootable_opponents(self) -> List[Tuple[Player, int]]:
        """
        Gets a list of player, direction pairs.
        The players can be shot by a direct bullet when current bot is rotated by the direction.
        """
        result = []
        for opponent in self.game.opponents_of(self.my_player):
            shooting_direction = self.my_player.get_closest_direction_towards(opponent.position)
            if not self.game.has_clear_bullet_path(self.my_player.as_if_rotated_to(shooting_direction), opponent):
                continue  # can't hit the opponent

            result.append((opponent, shooting_direction))

        return result

    def _simple_move_towards(self, target: Tuple[int, int]):
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
                self.MOVE_rotate_randomly()
                for _ in range(2):
                    self.MOVE_step_forward()

            self._add_update_request(move_request)
        else:
            self.MOVE_rotate(walk_direction)

    def _try_move_towards_by_plan(self, target: Tuple[int, int]):
        if target not in self._position_plans:
            if len(self._position_plans) > MAX_CACHED_PLANS:
                # free up some memory, because there were too many plans created
                self._position_plans.clear()

            self._position_plans[target] = None  # allocate slot for the plan

            def _create_plan_async():
                plan = GamePlan.plan_route_to_targets([target], stop_position=self.position)
                self._position_plans[target] = plan

            PLAN_EXECUTOR.submit(_create_plan_async)
            return False

        plan = self._position_plans[target]
        if plan is None:
            # plan was requested but is not available yet
            return False

        if plan.board.get(self.position) is None:
            plan.calculate(stop_position=self.position)

        desired_direction = plan.board[self.position].move_direction
        if not self.has_free_steps_in(desired_direction):
            # plan does not count with temporary obstacles
            return False

        self.MOVE_rotate(desired_direction)
        self.MOVE_step_forward()
        return True

