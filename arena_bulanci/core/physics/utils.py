import math
from typing import Tuple, List


def intersection_point_with_segment(p, a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dr2 = float(dx ** 2 + dy ** 2)

    lerp = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / dr2
    if lerp < 0:
        lerp = 0
    elif lerp > 1:
        lerp = 1

    x = lerp * dx + a[0]
    y = lerp * dy + a[1]

    return (x, y)


def point_to_segment_distance(p, a, b):
    return math.sqrt(point_to_segment_distance_sqr(p, a, b))


def point_to_segment_distance_sqr(p, a, b):
    x, y = intersection_point_with_segment(p, a, b)

    _dx = x - p[0]
    _dy = y - p[1]
    square_dist = _dx ** 2 + _dy ** 2
    return square_dist


def shortest_dist_to_point(self, other_point):
    return math.sqrt(self.sq_shortest_dist_to_point(other_point))


def segment_with_circle_intersection(start: Tuple[float, float], end: Tuple[float, float], center: Tuple[float, float], r: float
                                     ) -> List[Tuple[float, float]]:
    x1, y1 = start
    x2, y2 = end
    xc, yc = center

    dx = x1 - x2
    dy = y1 - y2
    rx = xc - x1
    ry = yc - y1
    a = dx * dx + dy * dy
    b = dx * rx + dy * ry
    c = rx * rx + ry * ry - r * r
    # Now solve a*t^2 + 2*b*t + c = 0
    d = b * b - a * c
    if d < 0.:
        # no real intersection
        return
    s = math.sqrt(d)
    t1 = (- b - s) / a
    t2 = (- b + s) / a
    if 0. <= t1 <= 1.:
        yield ((1 - t1) * x1 + t1 * x2, (1 - t1) * y1 + t1 * y2)
    if 0. <= t2 <= 1.:
        yield ((1 - t2) * x1 + t2 * x2, (1 - t2) * y1 + t2 * y2)
