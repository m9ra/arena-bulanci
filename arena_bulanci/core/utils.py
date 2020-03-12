import math

import jsonpickle
import threading
import sys
import traceback
import os
import signal


def has(value): return value is not None


def sign(v):
    if v > 0:
        return 1

    if v < 0:
        return -1

    return 0


def distance_sqr(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2


def distance(p1, p2):
    return math.sqrt(distance_sqr(p1, p2))


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
