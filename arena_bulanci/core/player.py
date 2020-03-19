from copy import copy
from typing import Optional, Tuple

from arena_bulanci.core.config import TICKS_PER_SECOND, BULLET_RAY_LENGTH, PLAYER_BOX_RADIUS
from arena_bulanci.core.gun import Gun
from arena_bulanci.core.physics.segment import Segment
from arena_bulanci.core.utils import DIRECTION_DEFINITIONS, closest_direction_towards


def create_revolver():
    return Gun("revolver", full_ammo_count=5, cooldown_time=TICKS_PER_SECOND // 2, reload_time=5 * TICKS_PER_SECOND)


class Player(object):
    def __init__(self, id: str):
        self.id: str = id
        self.position: Optional[Tuple[int, int]] = None
        self._direction: Optional[int] = None

        self.gun: Gun = create_revolver()

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        if not isinstance(value, int):
            raise ValueError(f"direction has to be `int` but was {value}")

        self._direction = value

    def as_if_rotated_to(self, direction: int):
        """
        Creates shallow copy of this player, pointing to specified direction
        """
        if not isinstance(direction, int):
            raise ValueError(f"direction has to be `int` but was {direction}")

        player_copy = copy(self)
        player_copy.direction = direction

        return player_copy

    def get_closest_direction_towards(self, other_position: Tuple[int, int]) -> int:
        p = self.position
        o = other_position

        if p == o:
            # i.e. no rotation
            return self.direction

        return closest_direction_towards(p, o)

    def get_bullet_ray(self) -> Segment:
        p = self.position
        d = DIRECTION_DEFINITIONS[self.direction]

        bullet_start_position = self._add_gun_offset(self.position, d)

        end = (p[0] + BULLET_RAY_LENGTH * d[0], p[1] + BULLET_RAY_LENGTH * d[1])
        return Segment(bullet_start_position, end, d)

    def _add_gun_offset(self, p, d):
        r = PLAYER_BOX_RADIUS + 1 + 1e-5
        return p[0] + d[0] * r, p[1] + d[1] * r

    def __repr__(self):
        return f"{self.id}: pos = {self.position}, dir = {self.direction}"
