import datetime
import gc
from collections import defaultdict
from time import sleep
from typing import List, Optional

from arena_bulanci.bots.bot_base import BotBase
from arena_bulanci.bots.jupyter_bot import JupyterBot
from arena_bulanci.core.config import LOCAL_ARENA_GAME_UPDATES_PORT, LOCAL_ARENA_WEB_PORT, TICKS_PER_SECOND, \
    REMOTE_ARENA_GAME_UPDATES_PORT, REMOTE_ARENA_HOSTNAME, REMOTE_ARENA_WEB_PORT, LOCAL_ARENA_RAW_UPDATES_PORT
from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.error import ErrorUpdate
from arena_bulanci.core.networking.socket_client import SocketClient
from arena_bulanci.core.utils import jsondumps, jsonloads, validate_email
from arena_bulanci.core.web.arena_app import ArenaApp

JUPYTER_BOT: Optional[BotBase] = JupyterBot()

def run_local_game(bots: List[BotBase], simulate_real_delay=True):
    game = Game(verbose=False)
    app = ArenaApp(game, '127.0.0.1', LOCAL_ARENA_WEB_PORT, LOCAL_ARENA_GAME_UPDATES_PORT, LOCAL_ARENA_RAW_UPDATES_PORT,
                   "Local Arena")
    app.run_async()

    # made up bot names
    for i, bot in enumerate(bots):
        bot.player_id = f"player{i}@mail.domain"
        bot._raw_game = game

    last_updates = None
    last_whole_iteration_duration = None
    while game.is_running:
        iteration_start = datetime.datetime.now()
        bot_updates = []

        # collect  update requests from bots
        for bot in bots:
            app._connection_stats_handler(bot.player_id, last_whole_iteration_duration, 0)
            game_copy = game.copy_without_internal_data()
            update_request = bot.pop_update_request(game_copy, last_updates)
            if update_request:
                bot_updates.append(update_request)

        # run game steps
        game.accept(bot_updates)
        last_updates = game.step(catch_exceptions=False)
        iteration_end = datetime.datetime.now()

        iteration_duration = (iteration_end - iteration_start).total_seconds()
        if simulate_real_delay:
            # optionally simulate iteration delay
            desired_iteration_time = 1 / TICKS_PER_SECOND
            sleep_time = max(0, desired_iteration_time - iteration_duration)
            sleep(sleep_time)

        last_whole_iteration_duration = (datetime.datetime.now() - iteration_start).total_seconds()


def run_remote_arena_game(bot: BotBase, username: str, print_skipped_tick_info: bool = True,
                          print_think_time: bool = False, arena_hostname_override: str = None):
    _run_remote_arena_game(bot, username, print_skipped_tick_info=print_skipped_tick_info,
                           print_think_time=print_think_time, arena_hostname_override=arena_hostname_override)


def run_remote_arena_game_for_jupyter(arena_hostname, username, screen_size_factor=0.5):
    validate_email(username)

    JUPYTER_BOT.run(arena_hostname, username)

    url = f"http://{arena_hostname}:{REMOTE_ARENA_WEB_PORT}/game"
    from IPython.display import IFrame
    return IFrame(url, width=int(1920 * screen_size_factor), height=int(1080 * screen_size_factor))



def _run_remote_arena_game(bot: BotBase, username: str, reconnect=True, print_skipped_tick_info=True,
                           print_think_time=False, arena_hostname_override: str = None):
    statistics = defaultdict(int)

    while True:
        try:
            statistics["connection_count"] += 1
            _raw_play_remote_game(bot, username, statistics, print_skipped_tick_info=print_skipped_tick_info,
                                  print_think_time=print_think_time, arena_hostname_override=arena_hostname_override)
        except SystemExit:
            print("Exiting.")
            break
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError, ConnectionError):
            if reconnect:
                print("Disconnected, trying to reconnect")
                sleep(5)
                continue

            else:
                print("Disconnected, ending.")
                break


def _raw_play_remote_game(bot: BotBase, username: str, statistics: defaultdict, print_skipped_tick_info=True,
                          print_think_time=False, arena_hostname_override: str = None):

    bot.player_id = username
    validate_email(username)

    client = SocketClient()

    hostname = REMOTE_ARENA_HOSTNAME
    if arena_hostname_override:
        hostname = arena_hostname_override

    client.connect(hostname, REMOTE_ARENA_GAME_UPDATES_PORT + 1)
    client.send_string(jsondumps({
        "player_id": username, "version": "1.0.5", "bot": (bot.__class__.__module__ + "." + bot.__class__.__qualname__), "root": __file__
    }))
    initial_data_str = client.read_string()
    print(f"Player {username} connected")
    data = jsonloads(initial_data_str)

    client.send_string(jsondumps(None))  # send first update empty

    _future_requests = []
    game: Game = data["state"]
    game._tick_subscribers = []
    game._pretick_subscribers = []
    bot._raw_game = game
    while game.is_running:
        update_data_str = client.read_string()
        start = datetime.datetime.now()
        if update_data_str is None:
            raise ConnectionAbortedError("Connection was closed")

        if update_data_str == "disconnected":
            raise AssertionError("Connection was ended because of other connection with the same id.")

        update_groups = jsonloads(update_data_str)

        for update_group in update_groups:
            updates = update_group["updates"]
            for update in updates:
                if isinstance(update, ErrorUpdate) and update._player_id == bot.player_id:
                    print("ERROR: ", update.error)

        is_first = True
        last_updates = []
        for update_group in update_groups:
            if is_first:
                statistics["ticks"] += 1
                is_first = False
            else:
                if _future_requests:
                    statistics["future_requests_used"] += 1
                    future_request = _future_requests.pop(0)
                    if bot.try_pop_by_future_request(future_request):
                        statistics["correct_future_requests"] += 1
                    else:
                        statistics["incorrect_future_requests"] += 1
                else:
                    statistics["skipped_ticks"] += 1
                    if print_skipped_tick_info:
                        print(f"INFO: Skipping tick: {game.tick}")

            last_updates.extend(update_group["updates"])
            game.external_step(update_group["updates"])
            if game.tick != update_group["tick"]:
                raise AssertionError("FATAL ERROR: Tick update was missed")

        before_think_time = datetime.datetime.now()
        current_update_request = bot.pop_update_request(game, last_updates)
        _future_requests = bot.get_future_requests(current_update_request)

        update_request = [current_update_request] + _future_requests
        update_request_str = jsondumps(update_request)

        before_send_time = datetime.datetime.now()
        client.send_string(update_request_str)
        before_gc_time = datetime.datetime.now()
        gc.collect(generation=0)
        end = datetime.datetime.now()
        duration = (end - start).total_seconds()
        if (1.0 / TICKS_PER_SECOND) - duration < 0.02:
            print(
                f"WARN: Think time: {duration * 1000:.2f}ms at tick: {game.tick}. Before think: {duration_format(start, before_think_time)}, before send: {duration_format(start, before_send_time)}, before gc: {duration_format(start, before_gc_time)}. ")

        if print_think_time:
            print(f"Think time: {duration * 1000:.2f}ms")


def duration_format(start, end):
    return f"{(end - start).total_seconds() * 1000:.2f}ms"
