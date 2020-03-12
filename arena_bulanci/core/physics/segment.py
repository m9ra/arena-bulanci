from typing import Tuple, List


class Segment(object):
    def __init__(self, start: Tuple[int, int], end: Tuple[int, int], direction_coords: Tuple[float,float]):
        self.start = start
        self.end = end
        self.direction_coords = direction_coords

    def intersects(self, boxes: List):
        for box in boxes:
            if box.intersects_with_segment(self.start, self.end):
                return True

        return False

    def get_intersection_points(self, box) -> List[Tuple[int, int]]:
        return box.intersection_points_with_segment(self.start, self.end)
