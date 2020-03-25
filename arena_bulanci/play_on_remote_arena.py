import os

from arena_bulanci.bots.manual_bot import ManualBot
from arena_bulanci.bots.random_walk_bot import RandomWalkBot
from arena_bulanci.core.execution import run_remote_arena_game

ARENA_USERNAME = os.getenv("ARENA_USERNAME")
if not ARENA_USERNAME:
    raise AssertionError("Environment variable ARENA_USERNAME is missing")

my_bot_color = (50, 50, 0)

my_bot = RandomWalkBot(color=my_bot_color)
# my_bot = ManualBot(6975, color=my_bot_color) # if you want to control your bot manually uncomment this

run_remote_arena_game(my_bot, ARENA_USERNAME, print_skipped_tick_info=True, print_think_time=False)
