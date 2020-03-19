import math
import re
from typing import Tuple, Optional

import jsonpickle
import threading
import sys
import traceback
import os
import signal

DIRECTION_DEFINITIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
DIRECTION_LOOKUP = dict(zip(DIRECTION_DEFINITIONS, range(len(DIRECTION_DEFINITIONS))))

ROTATION_180 = [1, 0, 3, 2]

HORIZONTAL_DIRECTIONS = [2, 3]
VERTICAL_DIRECTIONS = [0, 1]

def has(value): return value is not None


def sign(v):
    if v > 0:
        return 1

    if v < 0:
        return -1

    return 0


def step_from(position: Tuple[int, int], direction: int):
    coords = DIRECTION_DEFINITIONS[direction]
    return position[0] + coords[0], position[1] + coords[1]


def rotate_180(direction: int) -> int:
    return ROTATION_180[direction]


def distance_sqr(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2


def distance(p1, p2):
    return math.sqrt(distance_sqr(p1, p2))


def grid_distance(p1: Tuple[int, int], p2: Tuple[int, int], initial_direction: Optional[int] = None) -> int:
    if p1 == p2:
        return 0

    extra_distance = 0
    if initial_direction:
        if closest_direction_towards(p1, p2) != initial_direction:
            extra_distance += 1

    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) + extra_distance


def closest_direction_towards(p: Tuple[int, int], o: Tuple[int, int]) -> int:
    xdiff = p[0] - o[0]
    ydiff = p[1] - o[1]

    if abs(xdiff) > abs(ydiff):
        direction_coords = (-sign(xdiff), 0)
    else:
        direction_coords = (0, -sign(ydiff))

    return DIRECTION_LOOKUP[direction_coords]

def is_orthogonal(dir1, dir2):
    return (dir1 in HORIZONTAL_DIRECTIONS) != (dir2 in HORIZONTAL_DIRECTIONS)



def jsonloads(json_str):
    # todo restrict classes
    return jsonpickle.loads(json_str)


def jsondumps(obj):
    return jsonpickle.dumps(obj)


def send_kill_signal(etype, value, tb):
    print('KILL ALL')
    traceback.print_exception(etype, value, tb)
    os.kill(os.getpid(), signal.SIGTERM)


original_init = threading.Thread.__init__


def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    original_run = self.run

    def patched_run(*args, **kw):
        try:
            original_run(*args, **kw)
        except:
            sys.excepthook(*sys.exc_info())

    self.run = patched_run


def install_kill_on_exception_in_any_thread():
    sys.excepthook = send_kill_signal
    threading.Thread.__init__ = patched_init


def format_elapsed_time(seconds):
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24

    if days > 2:
        days = math.floor(days)
        hours %= 24
        return f"{days:02.0f}d {hours:02.0f}h"

    if hours > 2:
        hours = math.floor(hours)
        minutes %= 60
        return f"{hours:02.0f}h {minutes:02.0f}m"

    minutes = math.floor(minutes)
    seconds %= 60
    return f"{minutes:02.0f}m {seconds:02.0f}s"


def validate_email(username):
    if not re.match("[^@]+@[^@]+\.[^@]+", username):
        raise ValueError(f"Username must be an email but `{username}` was given")
