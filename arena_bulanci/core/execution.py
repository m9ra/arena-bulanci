import datetime
import gc
from time import sleep
from typing import List

from arena_bulanci.bots.bot_base import BotBase
from arena_bulanci.core.config import LOCAL_ARENA_GAME_UPDATES_PORT, LOCAL_ARENA_WEB_PORT, TICKS_PER_SECOND, \
    REMOTE_ARENA_GAME_UPDATES_PORT, REMOTE_ARENA_HOSTNAME, LOCAL_ARENA_RAW_UPDATES_PORT
from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.error import ErrorUpdate
from arena_bulanci.core.networking.socket_client import SocketClient
from arena_bulanci.core.utils import jsondumps, jsonloads, validate_email
from arena_bulanci.core.web.arena_app import ArenaApp


def run_local_game(bots: List[BotBase], simulate_real_delay=True):
    game = Game(verbose=False)
    app = ArenaApp(game, '127.0.0.1', LOCAL_ARENA_WEB_PORT, LOCAL_ARENA_GAME_UPDATES_PORT, LOCAL_ARENA_RAW_UPDATES_PORT,
                   "Local Arena")
    app.run_async()

    # made up bot names
    for i, bot in enumerate(bots):
        bot.player_id = f"player{i}@mail.domain"
        bot._raw_game = game

    while game.is_running:
        iteration_start = datetime.datetime.now()
        bot_updates = []

        # collect  update requests from bots
        for bot in bots:
            game_copy = game.copy_without_internal_data()
            update_request = bot.pop_update_request(game_copy)
            if update_request:
                bot_updates.append(update_request)

        # run game steps
        game.accept(bot_updates)
        game.step(catch_exceptions=False)
        iteration_end = datetime.datetime.now()

        iteration_duration = (iteration_end - iteration_start).total_seconds()
        if simulate_real_delay:
            # optionally simulate iteration delay
            desired_iteration_time = 1 / TICKS_PER_SECOND
            sleep_time = max(0, desired_iteration_time - iteration_duration)
            sleep(sleep_time)


def run_remote_arena_game(bot: BotBase, username: str, print_skipped_tick_info: bool = True,
                          print_think_time: bool = False):
    _run_remote_arena_game(bot, username, print_skipped_tick_info=print_skipped_tick_info,
                           print_think_time=print_think_time)


def _run_remote_arena_game(bot: BotBase, username: str, reconnect=True, print_skipped_tick_info=True,
                           print_think_time=False):
    while True:
        try:
            _raw_play_remote_game(bot, username, print_skipped_tick_info=print_skipped_tick_info,
                                  print_think_time=print_think_time)
        except (ConnectionAbortedError, ConnectionRefusedError):
            if reconnect:
                print("Disconnected, trying to reconnect")
                sleep(5)
                continue

            else:
                print("Disconnected, ending.")
                break


def _raw_play_remote_game(bot: BotBase, username: str, print_skipped_tick_info=True, print_think_time=False):
    bot.player_id = username
    validate_email(username)

    client = SocketClient()
    client.connect(REMOTE_ARENA_HOSTNAME, REMOTE_ARENA_GAME_UPDATES_PORT + 1)
    client.send_string(jsondumps({"player_id": username, "version": "1.0.3"}))
    initial_data_str = client.read_string()
    print(f"Player {username} connected")
    data = jsonloads(initial_data_str)

    client.send_string(jsondumps(None))  # send first update empty

    game: Game = data["state"]
    game._tick_subscribers = []
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
        for update_group in update_groups:
            if not is_first and print_skipped_tick_info:
                print(f"INFO: Skipping tick: {game.tick}")
            is_first = False

            game.external_step(update_group["updates"])
            if game.tick != update_group["tick"]:
                raise AssertionError("FATAL ERROR: Tick update was missed")

        before_think_time = datetime.datetime.now()
        update_request = bot.pop_update_request(game)
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
