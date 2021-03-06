import math
import random
from concurrent.futures.thread import ThreadPoolExecutor
from threading import Event
from typing import Tuple, List, Optional

from arena_bulanci.bots.game_plan import GamePlan
from arena_bulanci.core.bot_base_low_level import BotBaseLowLevel
from arena_bulanci.core.config import MAX_FUTURE_UPDATE_REQUESTS, MAX_BULLET_AGE, BULLET_SPEED
from arena_bulanci.core.game import Game, OBSTACLE_BOXES
from arena_bulanci.core.game_updates.game_update_request import GameUpdateRequest
from arena_bulanci.core.game_updates.player_move_request import PlayerMoveRequest
from arena_bulanci.core.game_updates.player_rotation_request import PlayerRotationRequest
from arena_bulanci.core.game_updates.shoot_request import ShootRequest
from arena_bulanci.core.physics.segment import Segment
from arena_bulanci.core.player import Player
from arena_bulanci.core.utils import distance, DIRECTION_DEFINITIONS, step_from, UP_DIRECTION, DOWN_DIRECTION, \
    LEFT_DIRECTION, RIGHT_DIRECTION, grid_distance

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

    def _on_kill_registered(self, killing_player_id: str, killed_player_id: str, bullet_id: str):
        """
        Callback called when a killing player kills another player with the bullet
        """
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

    def MOVE_go_towards(self, target: Tuple[int, int], wait_time_ms: int = 0):
        """
        Enqueues a composition of rotation and step moves in order to get to given position from current position.
        At most three moves are enqueued at a single time.
        Uses shortest path planning + simple fallback in order to be real time processing friendly.

        Allows specifying wait time (in which the plan can be calculated before fallback)

        Getting stuck at temporary obstacles (i.e. other players) is solved by adding random steps and rotations.
        """
        if self.position == target:
            return

        if not self._try_move_towards_by_plan(target, wait_time_ms=wait_time_ms):
            self._simple_move_towards(target)

    def MOVE_step_UP(self):
        """
        Enqueues rotation move (if needed) and a step forward in up direction.
        """
        self.MOVE_rotate(UP_DIRECTION)
        self.MOVE_step_forward()

    def MOVE_step_DOWN(self):
        """
        Enqueues rotation move (if needed) and a step forward in down direction.
        """
        self.MOVE_rotate(DOWN_DIRECTION)
        self.MOVE_step_forward()

    def MOVE_step_LEFT(self):
        """
        Enqueues rotation move (if needed) and a step forward in left direction.
        """
        self.MOVE_rotate(LEFT_DIRECTION)
        self.MOVE_step_forward()

    def MOVE_step_RIGHT(self):
        """
        Enqueues rotation move (if needed) and a step forward in right direction.
        """
        self.MOVE_rotate(RIGHT_DIRECTION)
        self.MOVE_step_forward()

    def MOVE_rotate_randomly(self):
        """
        Enqueues a move which rotates to a random direction
        """
        self.MOVE_rotate(random.randint(0, len(DIRECTION_DEFINITIONS) - 1))

    def will_be_bullet_hit(self, position: Tuple[int, int], from_tick: Optional[int] = None,
                           to_tick: Optional[int] = None):
        """
        Determine if player standing on given position will be hit by an already existing bullet.
        If not specified otherwise, only hit in the following game tick is tested.

        (Permanent obstacles are accounted for, other players are not)
        :param position: Position where the player is standing
        :param from_tick: If specified, determine start of time period in which hit will be tested. Defaults to game.tick
        :param to_tick: If specified, determine end of time period in which hit will be tested. Defaults to from_tick+1
        :return: True if player standing on position will be hit, False otherwise
        """

        if from_tick is None:
            from_tick = self.game.tick

        if to_tick is None:
            to_tick = from_tick + 1

        tick_offset = from_tick - self.game.tick
        trajectory_ticks = to_tick - from_tick

        boxes = self.game.get_player_bounding_boxes(position)
        for bullet in self.game.bullets:
            bullet_trajectory = bullet.get_current_trajectory(
                self.game, trajectory_ticks=trajectory_ticks,
                tick_offset=tick_offset
            )

            if bullet_trajectory.intersects(boxes):
                return True

        return False

    def ticks_before_bullet_hit(self, position: Tuple[int, int]) -> Optional[int]:
        """
        Determine after how many ticks bullet will hit a player if he was standing at given position.
        Number of ticks before first hit is returned, None if no hit is expected.

        NOTE: Permanent obstacles are accounted for only (players, which can block the path are not taken into account)
        """

        boxes = self.game.get_player_bounding_boxes(position)
        if len(boxes) != 1:
            raise AssertionError("Method is implemented for a single player bounding box only")

        ticks_to_hit = []
        player_box = boxes[0]
        for bullet in self.game.bullets:
            trajectory = bullet.get_current_trajectory(
                self.game, trajectory_ticks=MAX_BULLET_AGE,
            )

            hit_points = list(trajectory.get_intersection_points(player_box))
            if not hit_points:
                # bullet is not hitting the player
                continue

            pre_trajectory = Segment(bullet.start_position, trajectory.start, trajectory.direction_coords)
            pre_trajectory_hits = self.get_permanent_obstacle_hit_points(pre_trajectory)
            if pre_trajectory_hits:
                # bullet would hit some obstacle before getting to the player
                continue

            obstacle_hit_points = self.get_permanent_obstacle_hit_points(trajectory)
            bullet_end_point = min(
                hit_points + obstacle_hit_points,
                key=lambda p: grid_distance(bullet.start_position, p)
            )

            if bullet_end_point in hit_points:
                # hit is on player
                bullet_travel_distance = distance(trajectory.start, bullet_end_point)
                ticks_to_hit.append(math.ceil(bullet_travel_distance / BULLET_SPEED))

        if not ticks_to_hit:
            return None

        return min(ticks_to_hit)

    def get_permanent_obstacle_hit_points(self, trajectory: Segment) -> List[Tuple[int, int]]:
        """
        Gets intersection points of the trajectory and permanent obstacles.
        """
        intersections = []
        for box in OBSTACLE_BOXES:
            intersections.extend(trajectory.get_intersection_points(box))

        return intersections

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

    def get_future_requests(self, current_request: GameUpdateRequest) -> List[GameUpdateRequest]:
        """
        Every move request can be sent together with potential followup requests.
        This will prevent game tick drops due to network lag etc.

        The default strategy is implemented here.
        Feel free to include your own.
        """

        future_requests = []
        if self._update_requests:
            future_requests.extend(self._update_requests[0:MAX_FUTURE_UPDATE_REQUESTS])

        last_request = current_request if not future_requests else future_requests[-1]
        if len(future_requests) < 5 and isinstance(last_request, PlayerMoveRequest):
            # keep moving in case of temporary tick drops
            future_requests.extend(
                [current_request, current_request, current_request, current_request, current_request]
            )

        if current_request is None:
            # keep standing still
            future_requests.extend(
                [None, None, None, None, None]
            )

        return future_requests

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

    def _try_move_towards_by_plan(self, target: Tuple[int, int], wait_time_ms: int = 0):
        if target not in self._position_plans:
            if len(self._position_plans) > MAX_CACHED_PLANS:
                # free up some memory, because there were too many plans created
                self._position_plans.clear()
                print("INFO: Clearing position plan cache")

            self._position_plans[target] = None  # allocate slot for the plan

            if wait_time_ms:
                wait_event = Event()
            else:
                wait_event = None

            def _create_plan_async():
                plan = GamePlan.plan_route_to_targets([target], stop_position=self.position)
                self._position_plans[target] = plan
                if wait_event:
                    wait_event.set()

            PLAN_EXECUTOR.submit(_create_plan_async)
            if wait_time_ms:
                wait_event.wait(timeout=wait_time_ms / 1000.0)

            if target not in self._position_plans:
                # waiting was not helpful
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

