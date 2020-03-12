from typing import Tuple, List

from arena_bulanci.core.physics.utils import point_to_segment_distance, segment_with_circle_intersection
from arena_bulanci.core.utils import distance


class CircleBox(object):
    def __init__(self, center: Tuple[float, float], radius: float):
        self._center = center
        self._radius = radius

    def intersects_with_segment(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        return point_to_segment_distance(self._center, start, end) < self._radius

    def intersection_points_with_segment(self, start: Tuple[float, float], end: Tuple[float, float]) \
            -> List[Tuple[float, float]]:
        return segment_with_circle_intersection(start, end, self._center, self._radius)

    def intersects_with_circle(self, center, radius):
        return distance(self._center, center) < self._radius + radius

    def intersects(self, boxes: List):
        for box in boxes:
            if box.intersects_with_circle(self._center, self._radius):
                return True

        return False
