# arena-bulanci

This is a toolkit for writing realtime bots in a 2D shooting game.
Tested on Windows and Ubuntu with Python 3.7

Remote arena is available on http://packa1.cz:6969/

## How to start
0) `git clone https://github.com/m9ra/arena-bulanci`
1) `cd arena-bulanci`
2) `pip install -r requirements.txt`
3) Open arena-bulanci in PyCharm 
4) Create new configuration for `arena-bulanci/arena_bulanci/play_on_remote_arena.py` and set `ARENA_USERNAME` env variable to your email
5) Run the configuration

Out of the box, `RandomWalkBot` will start playing on remote arena.
You can write your own bots or find more pre-implemented bots in `arena-bulanci/arena_bulanci/bots`

### Manual play
If you want to control your bot manually, just uncomment ManualBot in `arena-bulanci/arena_bulanci/play_on_remote_arena.py`.
When you run the script, you will see link with arena, where you can control your bot by keyboard arrows and space bar (shooting).


## Writing your bots
- Good starting point is `arena-bulanci/arena_bulanci/bots/bot_base.py` which contains lot of referential implementations + game rules and available game moves.
- Get inspired by bots in `arena-bulanci/arena_bulanci/bots`.
- You may find useful definitions and utility methods in `arena-bulanci/arena_bulanci/core/utils.py`
- `arena-bulanci/arena_bulanci/core` should not be changed much (may be useful for very advanced stuff only)

