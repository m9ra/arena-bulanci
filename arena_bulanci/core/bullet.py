from typing import Tuple, Optional

from arena_bulanci.core.config import BULLET_SPEED
from arena_bulanci.core.physics.segment import Segment
from arena_bulanci.core.utils import DIRECTION_LOOKUP


class Bullet(object):
    def __init__(self, id: str, start_tick: int, start_position: Tuple[int, int], direction_coords: Tuple[float, float],
                 reward_receiver_id: str):
        self.id: str = id
        self.start_tick = start_tick
        self.start_position = start_position
        self.direction_coords = direction_coords
        self.reward_receiver_id = reward_receiver_id

    @property
    def direction(self):
        return DIRECTION_LOOKUP[self.direction_coords]

    def get_current_trajectory(self, game: 'Game', trajectory_ticks=1, tick_offset=0) -> Optional[Segment]:
        trajectory_start_tick = max(self.start_tick, game.tick - 1 + tick_offset)
        trajectory_end_tick = trajectory_start_tick + trajectory_ticks

        if trajectory_start_tick == trajectory_end_tick:
            return None

        ticks_from_start = trajectory_start_tick - self.start_tick

        start = (
            self.start_position[0] + self.direction_coords[0] * ticks_from_start * BULLET_SPEED,
            self.start_position[1] + self.direction_coords[1] * ticks_from_start * BULLET_SPEED
        )

        end = (
            start[0] + self.direction_coords[0] * trajectory_ticks * BULLET_SPEED,
            start[1] + self.direction_coords[1] * trajectory_ticks * BULLET_SPEED,
        )
        return Segment(start, end, self.direction_coords)
