from arena_bulanci.bots.manual_bot import ManualBot
from arena_bulanci.bots.position_keep_bot import PositionKeepBot
from arena_bulanci.bots.random_walk_bot import RandomWalkBot
from arena_bulanci.core.execution import run_local_game

bots = [
    RandomWalkBot(), RandomWalkBot(), RandomWalkBot(), RandomWalkBot(), RandomWalkBot(), RandomWalkBot(),
    RandomWalkBot(), RandomWalkBot(), RandomWalkBot(),
    # PositionKeepBot((35, 25)),
    ManualBot(6975),
    # ManualBot(6977),
]

run_local_game(bots)
