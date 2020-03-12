import asyncio
from datetime import datetime
from threading import Thread

from typing import List, Set, Dict
import websockets

from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.add_bullet import AddBullet
from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.game_updates.remove_bullet import RemoveBullet
from arena_bulanci.core.utils import jsondumps, jsonloads


class GameUpdateServer(object):
    def __init__(self, game: Game, host: str, port: int):
        self._game = game  # game which is played in the arena
        self._host = host
        self._port = port

        self._update_subscribers: Set['websocket'] = set()
        self._full_state_subscribers: Set['websockets'] = set()
        self._player_to_ws: Dict[str, 'websockets'] = {}
        self._pings: Dict[str, float] = {}

        self._last_player_tick_time: Dict[str, datetime] = {}

        self._loop = asyncio.new_event_loop()
        self._control_callback = None

        self.on_kill_registered = None
        self.on_shot_registered = None
        self.on_connection_stats_registered = None

    def start(self):
        self._game.subscribe_ticks(self._tick_handler)
        Thread(target=self._run_server, daemon=True).start()

    def register_control_callback(self, control_callback):
        self._control_callback = control_callback

    def _run_server(self):
        asyncio.set_event_loop(self._loop)
        self._loop.create_task(self._connection_statistic_worker())
        self._loop.run_until_complete(websockets.serve(self._client_handler, self._host, self._port))
        self._loop.run_forever()

    def _tick_handler(self, game_updates: List[GameUpdate]):
        for update in game_updates:
            if isinstance(update, AddBullet):
                if self.on_shot_registered:
                    self.on_shot_registered(update._reward_receiver)

            if isinstance(update, RemoveBullet):
                if self.on_kill_registered:
                    if update.hit_player_id is not None:
                        self.on_kill_registered(update.reward_receiver_id, update.hit_player_id)

        if self._update_subscribers:
            tick_data = jsondumps({
                "tick": self._game.tick,
                "updates": game_updates
            })

            asyncio.run_coroutine_threadsafe(
                asyncio.wait([subscriber.send(tick_data) for subscriber in self._update_subscribers]),
                self._loop
            )

        if self._full_state_subscribers:
            full_state_data = self._get_full_state_data()
            asyncio.run_coroutine_threadsafe(
                asyncio.wait([subscriber.send(full_state_data) for subscriber in self._full_state_subscribers]),
                self._loop
            )

        self._last_tick_time = datetime.now()

    async def _client_handler(self, websocket, path):
        print(f"_client_handler({websocket}, {path})")
        if path == "/game":
            await self._game_play_handler(websocket)
        elif path == "/observer":
            await self._observer_handler(websocket)

    async def _game_play_handler(self, websocket):
        player_id = None
        try:
            await self._subscribe_game_updates(websocket, full_state=False)
            initial_message_str = await websocket.recv()
            initial_message = jsonloads(initial_message_str)
            player_id = initial_message["player_id"]
            await self._handle_player_connection(player_id, websocket)

            async for message in websocket:
                ping_time = (datetime.now() - self._last_tick_time).total_seconds()
                if player_id not in self._pings:
                    self._pings[player_id] = ping_time

                self._pings[player_id] = self._pings[player_id] * 0.95 + 0.05 * ping_time

                update_request = jsonloads(message)
                update_request.player_id = player_id
                self._game.accept([update_request])
        except Exception as e:
            print(f"_game_play_handler: {repr(e)}")
        finally:
            if player_id:
                self._handle_player_disconnection(player_id, websocket)
            await self._unsubscribe_game_updates(websocket)

    async def _observer_handler(self, websocket):
        try:
            await self._subscribe_game_updates(websocket, full_state=True)
            async for control_data in websocket:
                if self._control_callback:
                    self._control_callback(control_data)

        except Exception as e:
            print(f"_observer_handler: {repr(e)}")
        finally:
            await self._unsubscribe_game_updates(websocket)

    async def _subscribe_game_updates(self, websocket, full_state=False):
        if full_state:
            self._full_state_subscribers.add(websocket)
        else:
            self._update_subscribers.add(websocket)

        full_state_data = self._get_full_state_data()
        await websocket.send(full_state_data)

    def _get_full_state_data(self):
        # make a copy, so "uncommitted" updates are not leaking
        game_copy = self._game.copy_without_internal_data()
        full_state_data = jsondumps({
            "tick": self._game.tick,
            "state": game_copy
        })
        return full_state_data

    async def _unsubscribe_game_updates(self, websocket):
        self._update_subscribers.discard(websocket)
        self._full_state_subscribers.discard(websocket)

    async def _handle_player_connection(self, player_id: str, websocket):
        print(f"PLAYER CONNECTED: {player_id}")

        if player_id in self._player_to_ws and self._player_to_ws[player_id]:
            await self._player_to_ws[player_id].send("disconnected")
            await self._player_to_ws[player_id].close()

        self._player_to_ws[player_id] = websocket

    def _handle_player_disconnection(self, player_id: str, websocket):
        print(f"PLAYER DISCONNECTED {player_id}")

        if self._player_to_ws[player_id] == websocket:
            self._player_to_ws[player_id] = None

    async def _connection_statistic_worker(self):
        while True:
            await asyncio.sleep(1)
            if not self.on_connection_stats_registered:
                continue

            for player_id, ws in self._player_to_ws.items():
                if ws is None:
                    # player not connected
                    self.on_connection_stats_registered(player_id, None, None)
                else:
                    self.on_connection_stats_registered(player_id, 1.0, self._pings.get(player_id, 0))
