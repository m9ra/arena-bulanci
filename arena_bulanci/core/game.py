import datetime
import random
import sys
import traceback
from copy import deepcopy
from typing import Dict, List, Tuple, Iterable, Callable, Optional

from arena_bulanci.core.bullet import Bullet
from arena_bulanci.core.collision_exception import CollisionException
from arena_bulanci.core.config import MAP_WIDTH, MAP_HEIGHT, PLAYER_BOX_RADIUS, MIN_RESPAWN_TICK_COUNT, MAX_BULLET_AGE
from arena_bulanci.core.game_updates.error import ErrorUpdate
from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.game_updates.game_update_request import GameUpdateRequest
from arena_bulanci.core.game_updates.gun_state_change import GunStateChange
from arena_bulanci.core.game_updates.player_state_change import PlayerStateChange
from arena_bulanci.core.game_updates.remove_bullet import RemoveBullet
from arena_bulanci.core.maps.na_dobrou_noc import get_obstacle_boxes
from arena_bulanci.core.physics.circle_box import CircleBox
from arena_bulanci.core.physics.segment import Segment
from arena_bulanci.core.player import Player
from arena_bulanci.core.utils import distance_sqr

OBSTACLE_BOXES = list(get_obstacle_boxes())
_UNREACHABLE_POSITIONS: List[Tuple[int, int]] = []


class Game(object):
    def __init__(self, verbose=False):
        self._tick = 0
        self._players: Dict[str, Player] = {}
        self._dead_players: Dict[str, Tuple[Player, int]] = {}
        self._bullets: List[Bullet] = []
        self._update_requests: List[GameUpdateRequest] = []

        self._verbose = verbose
        self._tick_subscribers = []
        self._pretick_subscribers = []

    @property
    def tick(self):
        return self._tick

    @property
    def is_running(self):
        return True

    @property
    def bullets(self) -> List[Bullet]:
        return list(self._bullets)

    def subscribe_ticks(self, subscriber: Callable[[List[GameUpdate]], None]):
        self._tick_subscribers.append(subscriber)

    def subscribe_preticks(self, subscriber: Callable):
        self._pretick_subscribers.append(subscriber)

    def accept(self, update_requests: List[GameUpdateRequest]):
        self._update_requests.extend(update_requests)

    def step(self, catch_exceptions=True) -> List[GameUpdate]:
        for pretick_subscriber in self._pretick_subscribers:
            pretick_subscriber()

        tick_start = datetime.datetime.now()
        verified_updates = []
        requests = self._update_requests
        self._update_requests = []

        already_requesting_players = set()
        for update_request in requests:
            player_id = None
            try:
                player_id = update_request.player_id
                if player_id in already_requesting_players:
                    raise ValueError(f"User {player_id} tried more than one request")
                already_requesting_players.add(player_id)

                updates = update_request.create_updates(self)
            except CollisionException:
                if self._verbose:
                    print(f"Collision on `{update_request}`")

                continue  # collisions are expected
            except Exception as e:
                try:
                    msg = f"Exception on `{update_request}` {repr(e)}"
                    verified_updates.append(ErrorUpdate(player_id, msg))
                    if not catch_exceptions:
                        raise e

                    print(msg)
                except:
                    print(f"ERROR: {player_id} {repr(e)}")
                    traceback.print_exc()

                continue  # this update request was not approved

            for update in updates:
                update.apply_on(self)
                verified_updates.append(update)

        for update in self._get_cron_updates():
            update.apply_on(self)
            verified_updates.append(update)

        self._tick += 1
        tick_end = datetime.datetime.now()
        if self._verbose:
            tick_duration = (tick_end - tick_start).total_seconds() * 1000
            print(f"TICK {self.tick} {tick_duration:.2f}ms ")
            for update in verified_updates:
                print(update)

        for subscriber in self._tick_subscribers:
            subscriber(verified_updates)

        return verified_updates

    def external_step(self, updates: List[GameUpdate]):
        for update in updates:
            update.apply_on(self)

        self._tick += 1

        for subscriber in self._tick_subscribers:
            subscriber(updates)

    def validate(self, request: GameUpdateRequest):
        try:
            request.create_updates(self)
        except:
            return False

        return True

    def copy_without_internal_data(self):
        tick_subscribers = self._tick_subscribers
        pretick_subscribers = self._pretick_subscribers
        self._tick_subscribers = None
        self._pretick_subscribers = None
        try:
            game_copy = deepcopy(self)
        finally:
            self._tick_subscribers = tick_subscribers
            self._pretick_subscribers = pretick_subscribers

        game_copy._tick_subscribers = None
        game_copy._pretick_subscribers = None
        game_copy._verbose = None
        game_copy._update_requests = []

        return game_copy

    def get_player(self, state_id: str) -> Player:
        return self._players[state_id]

    def opponents_of(self, player: Player) -> List[Player]:
        result = []
        for opponent in self._players.values():
            if opponent.id == player.id:
                continue

            result.append(opponent)

        return result

    def can_player_shoot(self, player_id: str):
        player = self._players[player_id]
        return player.gun.can_shoot(self)

    def player_is_spawned(self, player_id: str) -> bool:
        return player_id in self._players

    def can_spawn(self, player_id: str) -> bool:
        return self.ticks_from_death(player_id) >= MIN_RESPAWN_TICK_COUNT

    def has_clear_bullet_path(self, player1: Player, player2: Player):
        # determine if player1 can hit player2
        # i.e. it detects if the bullet path is clear of obstacles and would end up in the player2
        ray = player1.get_bullet_ray()
        hit_obj = self.get_nearest_hit(ray)
        return hit_obj == player2

    def can_player_step_on(self, position: Tuple[int, int], disabled_objects=None):
        if position[0] < PLAYER_BOX_RADIUS or position[1] < PLAYER_BOX_RADIUS:
            return False

        if position[0] + PLAYER_BOX_RADIUS > MAP_WIDTH or position[1] + PLAYER_BOX_RADIUS > MAP_HEIGHT:
            return False

        if disabled_objects is None:
            disabled_objects = set()

        spawn_box = self.get_player_bounding_boxes(position)
        disabled_objects = set(disabled_objects)
        for box, obj in self.get_all_bounding_boxes():
            if obj in disabled_objects:
                continue

            if box.intersects(spawn_box):
                return False

        return True

    def ticks_from_death(self, player_id):
        if player_id not in self._dead_players:
            return sys.maxsize

        return self.tick - self._dead_players[player_id][1]

    def find_spawn_point(self) -> Tuple[int, int]:
        while True:
            point = (random.randint(0, MAP_WIDTH), random.randint(0, MAP_HEIGHT))
            if self.can_player_step_on(point):
                return point

    @classmethod
    def get_player_bounding_boxes(cls, position: Tuple[int, int]) -> List:
        return [CircleBox(position, PLAYER_BOX_RADIUS)]

    def _spawn_player(self, player_id: str):
        if player_id in self._dead_players:
            player, _ = self._dead_players.pop(player_id)
            if player.gun.ammo_count == 0:
                player.gun._cooldown_start = self.tick
        else:
            player = Player(player_id)

        self._players[player.id] = player

    def _kill_player(self, player_id: str):
        killed_player = self._players.pop(player_id, None)
        if killed_player:
            self._dead_players[player_id] = killed_player, self.tick

    def _get_cron_updates(self) -> List[GameUpdate]:
        result = []
        for player in self._players.values():
            gun = player.gun
            if gun.can_reload(self):
                result.append(GunStateChange(player.id, new_ammo_count=gun.full_ammo_count))

        for bullet in self._bullets:
            bullet_age = self.tick - bullet.start_tick
            trajectory = bullet.get_current_trajectory(self)
            hit = self.get_nearest_hit(trajectory)

            hit_player_id = None
            if isinstance(hit, Player):
                hit_player_id = hit.id
                result.append(PlayerStateChange(hit_player_id, is_alive=False))

            if hit is not None or bullet_age > MAX_BULLET_AGE:
                result.append(RemoveBullet(bullet.id, hit_player_id, bullet.reward_receiver_id))

        return result

    def get_nearest_hit(self, segment: Segment, extra_obstacles: Optional[List[Tuple]] = None):
        if segment is None:
            return None

        intersections = []
        for box, obj in self.get_all_bounding_boxes():
            for intersection in segment.get_intersection_points(box):
                intersections.append((intersection, obj))

        if extra_obstacles:
            for box, obj in extra_obstacles:
                for intersection in segment.get_intersection_points(box):
                    intersections.append((intersection, obj))


        if not intersections:
            return None

        return min(intersections, key=lambda p: distance_sqr(segment.start, p[0]))[1]

    def get_all_bounding_boxes(self) -> Iterable[Tuple]:
        for player in self._players.values():
            for box in self.get_player_bounding_boxes(player.position):
                yield box, player

        for box in OBSTACLE_BOXES:
            yield box, box

    @classmethod
    def get_positions_unreachable_for_players(cls):
        global _UNREACHABLE_POSITIONS

        return list(_UNREACHABLE_POSITIONS)

    @classmethod
    def would_player_hit_obstacle_on(cls, position: Tuple[int, int]):
        if position[0] < PLAYER_BOX_RADIUS or position[1] < PLAYER_BOX_RADIUS:
            return True

        if position[0] + PLAYER_BOX_RADIUS > MAP_WIDTH or position[1] + PLAYER_BOX_RADIUS > MAP_HEIGHT:
            return True

        bounding_boxes = cls.get_player_bounding_boxes(position)

        for box in OBSTACLE_BOXES:
            if box.intersects(bounding_boxes):
                return True

        return False


for x in range(MAP_WIDTH):
    for y in range(MAP_HEIGHT):
        position = (x, y)
        if Game.would_player_hit_obstacle_on(position):
            _UNREACHABLE_POSITIONS.append(position)
