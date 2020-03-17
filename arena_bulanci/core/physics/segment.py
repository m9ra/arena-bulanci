import math
from typing import Tuple, List


class Segment(object):
    def __init__(self, start: Tuple[float, float], end: Tuple[float, float], direction_coords: Tuple[float, float]):
        self.start = start
        self.end = end
        self.direction_coords = direction_coords

    def intersects(self, boxes: List):
        for box in boxes:
            if box.intersects_with_segment(self.start, self.end):
                return True

        return False

    def get_discrete_positions(self) -> List[Tuple[int, int]]:
        result = []
        steps = max(abs(self.end[0] - self.start[0]), abs(self.end[1] - self.start[1]))
        steps = math.ceil(steps)
        for i in range(steps):
            xd = int(round(self.start[0] + self.direction_coords[0] * i))
            yd = int(round(self.start[1] + self.direction_coords[1] * i))
            result.append((xd, yd))

        return result



    def get_intersection_points(self, box) -> List[Tuple[int, int]]:
        return box.intersection_points_with_segment(self.start, self.end)
