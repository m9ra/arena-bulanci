from typing import Tuple, Optional

from arena_bulanci.core.config import BULLET_SPEED
from arena_bulanci.core.physics.segment import Segment


class Bullet(object):
    def __init__(self, id: str, start_tick: int, start_position: Tuple[int, int], direction_coords: Tuple[float, float],
                 reward_receiver_id: str):
        self.id: str = id
        self.start_tick = start_tick
        self.start_position = start_position
        self.direction_coords = direction_coords
        self.reward_receiver_id = reward_receiver_id

    def get_current_trajectory(self, game: 'Game') -> Optional[Segment]:
        total_ticks_travelled = game.tick - self.start_tick
        if total_ticks_travelled == 0:
            return None

        end = (
            self.start_position[0] + self.direction_coords[0] * total_ticks_travelled * BULLET_SPEED,
            self.start_position[1] + self.direction_coords[1] * total_ticks_travelled * BULLET_SPEED
        )
        start = (end[0] - self.direction_coords[0] * BULLET_SPEED, end[1] - self.direction_coords[1] * BULLET_SPEED)
        return Segment(start, end, self.direction_coords)
