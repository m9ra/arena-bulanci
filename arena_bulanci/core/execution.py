import asyncio
import datetime
from time import sleep
from typing import List

import websockets

from arena_bulanci.bots.bot_base import BotBase
from arena_bulanci.core.config import LOCAL_ARENA_GAME_UPDATES_PORT, LOCAL_ARENA_WEB_PORT, TICKS_PER_SECOND, \
    REMOTE_ARENA_GAME_UPDATES_PORT, REMOTE_ARENA_HOSTNAME
from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.error import ErrorUpdate
from arena_bulanci.core.utils import jsondumps, jsonloads
from arena_bulanci.core.web.arena_app import ArenaApp


def run_local_game(bots: List[BotBase], simulate_real_delay=True):
    game = Game(verbose=False)
    app = ArenaApp(game, '127.0.0.1', LOCAL_ARENA_WEB_PORT, LOCAL_ARENA_GAME_UPDATES_PORT, "Local Arena")
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


def run_remote_arena_game(bot: BotBase, username: str, print_think_time: bool = False):
    # connect to arena
    asyncio.get_event_loop().run_until_complete(
        _run_remote_arena_game(bot, username, print_think_time=print_think_time)
    )


async def _run_remote_arena_game(bot: BotBase, username: str, reconnect=True, print_think_time=False):
    while True:
        try:
            await _play_remote_game(bot, username, print_think_time=print_think_time)
        except (ConnectionRefusedError, websockets.ConnectionClosedError):
            if reconnect:
                print("Disconnected, trying to reconnect")
                await asyncio.sleep(5)
                continue

            else:
                print("Disconnected, ending.")
                break


async def _play_remote_game(bot: BotBase, username: str, print_think_time: bool = False):
    bot.player_id = username
    # todo validate username
    uri = f"ws://{REMOTE_ARENA_HOSTNAME}:{REMOTE_ARENA_GAME_UPDATES_PORT}/game"
    loop = asyncio.get_event_loop()
    async with websockets.connect(uri) as websocket:
        await websocket.send(jsondumps({"player_id": username}))
        initial_data_str = await websocket.recv()
        print(f"Player {username} connected")
        data = jsonloads(initial_data_str)

        game: Game = data["state"]
        game._subscribers = []
        bot._raw_game = game
        while game.is_running:
            update_data_str = await websocket.recv()
            if update_data_str == "disconnected":
                raise AssertionError("Connection was ended because of other connection with the same id.")

            data = jsonloads(update_data_str)
            updates = data["updates"]

            for update in updates:
                if isinstance(update, ErrorUpdate) and update._player_id == bot.player_id:
                    print("ERROR: ", update.error)

            game.external_step(updates)
            if game.tick != data["tick"]:
                raise AssertionError("Ticks were lost")

            def _on_update_available(update_request):
                if update_request is None:
                    return

                start = datetime.datetime.now()
                update_request_str = jsondumps(update_request)
                end = datetime.datetime.now()
                if print_think_time:
                    print(f"{(end - start).total_seconds() * 1000:.2f}")

                asyncio.run_coroutine_threadsafe(websocket.send(update_request_str), loop)

            bot.get_update_request_async(game, _on_update_available)
