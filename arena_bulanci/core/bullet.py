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

    def get_current_trajectory(self, game: 'Game', trajectory_ticks=1) -> Optional[Segment]:
        total_ticks_travelled = game.tick - self.start_tick
        if total_ticks_travelled == 0:
            return None

        end = (
            self.start_position[0] + self.direction_coords[0] * total_ticks_travelled * BULLET_SPEED * trajectory_ticks,
            self.start_position[1] + self.direction_coords[1] * total_ticks_travelled * BULLET_SPEED * trajectory_ticks
        )
        total_ticks_travelled -= 1
        start = (
            self.start_position[0] + self.direction_coords[0] * total_ticks_travelled * BULLET_SPEED * trajectory_ticks,
            self.start_position[1] + self.direction_coords[1] * total_ticks_travelled * BULLET_SPEED * trajectory_ticks
        )
        return Segment(start, end, self.direction_coords)
