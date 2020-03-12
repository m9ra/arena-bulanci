import os

from arena_bulanci.bots.random_walk_bot import RandomWalkBot
from arena_bulanci.core.execution import run_remote_arena_game

ARENA_USERNAME = os.getenv("ARENA_USERNAME")
if not ARENA_USERNAME:
    raise AssertionError("Environment variable ARENA_USERNAME is missing")

run_remote_arena_game(RandomWalkBot(), ARENA_USERNAME)
