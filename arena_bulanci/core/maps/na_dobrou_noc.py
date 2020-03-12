from typing import List

from arena_bulanci.core.physics.circle_box import CircleBox


def get_obstacle_boxes() -> List[CircleBox]:
    for x, y, radius in [
        [120.5, 12.3, 3.5],
        [91, 40, 7],
        [83.5, 41.5, 4],
        [89, 76, 4.5],
        [135, 59, 4.5],
        [40, 53, 3.7],
        [36, 55.5, 3.7],
        [31.5, 59, 3.7],
        [21, 41, 4],
        [15, 15, 4.5],
        [57, 22, 13]
    ]:
        yield CircleBox((x, y), radius)
