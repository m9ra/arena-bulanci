import os

TICKS_PER_SECOND = 15
MIN_RESPAWN_TICK_COUNT = TICKS_PER_SECOND * 5.0
MAP_WIDTH = 160
MAP_HEIGHT = 90
PLAYER_BOX_RADIUS = 2.01

BULLET_RAY_LENGTH = MAP_HEIGHT + MAP_WIDTH
BULLET_SPEED = 5
MAX_BULLET_AGE = BULLET_RAY_LENGTH / BULLET_SPEED

REMOTE_ARENA_HOSTNAME = "packa1.cz"
REMOTE_ARENA_WEB_PORT = 6969
REMOTE_ARENA_GAME_UPDATES_PORT = 6970

LOCAL_ARENA_WEB_PORT = 6971
LOCAL_ARENA_GAME_UPDATES_PORT = 6972

REMOTE_ARENA_HOSTNAME = os.getenv("REMOTE_HOSTNAME_OVERRIDE", REMOTE_ARENA_HOSTNAME)
