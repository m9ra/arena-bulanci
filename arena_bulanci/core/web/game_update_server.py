import asyncio
import socket
import threading
from datetime import datetime
from threading import Thread, Lock
from typing import List, Set, Dict, Any, Optional

import websockets

from arena_bulanci.core.config import MAX_FUTURE_UPDATE_REQUESTS
from arena_bulanci.core.game import Game
from arena_bulanci.core.game_updates.add_bullet import AddBullet
from arena_bulanci.core.game_updates.error import ErrorUpdate
from arena_bulanci.core.game_updates.game_update import GameUpdate
from arena_bulanci.core.game_updates.game_update_request import GameUpdateRequest
from arena_bulanci.core.game_updates.remove_bullet import RemoveBullet
from arena_bulanci.core.networking.socket_client import SocketClient
from arena_bulanci.core.utils import jsondumps, jsonloads, validate_email


def log(message: str):
    now = datetime.now()
    print(f"[{now.strftime('%m/%d/%Y, %H:%M:%S')}] {message}")


class GameUpdateServer(object):
    def __init__(self, game: Game, host: str, port: int, raw_updates_port: int):
        self._game = game  # game which is played in the arena
        self._host = host
        self._port = port
        self._raw_updates_port = raw_updates_port
        self._update_roundtrip_start = None
        self.roundtrip_update_time = 0

        self._full_state_subscribers: Set[websockets] = set()
        self._player_to_client: Dict[str, SocketClient] = {}
        self._update_ready_clients: List[SocketClient] = []
        self._current_tick_update_ready_clients: List[SocketClient] = []
        self._pings: Dict[str, float] = {}

        self._loop = asyncio.new_event_loop()
        self._control_callback = None

        self.on_kill_registered = None
        self.on_shot_registered = None
        self.on_connection_stats_registered = None

        self._L_game = Lock()
        self._raw_game_pulse_event = threading.Event()
        self._player_requests: Dict[str, Optional[List[GameUpdateRequest]]] = {}
        self._is_future_request: Dict[str, bool] = {}
        self._player_updates: Dict[str, List[Dict[str, Any]]] = {}

    def start(self):
        self._game.subscribe_ticks(self._tick_handler)
        self._game.subscribe_preticks(self._pretick_handler)
        Thread(target=self._run_server, daemon=True).start()
        Thread(target=self._raw_accept_clients, daemon=True).start()

    def register_control_callback(self, control_callback):
        self._control_callback = control_callback

    def _run_server(self):
        asyncio.set_event_loop(self._loop)
        self._loop.create_task(self._connection_statistic_worker())
        self._loop.run_until_complete(websockets.serve(self._client_handler, self._host, self._port, compression=None))
        self._loop.run_forever()

    def _pretick_handler(self):
        self._update_roundtrip_start = datetime.now()
        collected_requests = []
        with self._L_game:
            self._current_tick_update_ready_clients = list(self._update_ready_clients)
            self._update_ready_clients.clear()

            for player_id, requests in self._player_requests.items():
                if not requests:
                    continue

                request = requests.pop(0)
                if not request:
                    continue

                request.player_id = player_id
                if not self._is_future_request[player_id]:
                    self._is_future_request[player_id] = True  # next request will be a future request if not replaced
                    collected_requests.append(request)

        self._game.accept(collected_requests)

    def _tick_handler(self, game_updates: List[GameUpdate]):
        for update in game_updates:
            if isinstance(update, AddBullet):
                if self.on_shot_registered:
                    self.on_shot_registered(update._reward_receiver)

            if isinstance(update, RemoveBullet):
                if self.on_kill_registered:
                    if update.hit_player_id is not None:
                        self.on_kill_registered(update.reward_receiver_id, update.hit_player_id)

        update_group = {
            "updates": game_updates,
            "tick": self._game.tick
        }

        # report updates
        for player_id, updates_group in list(self._player_updates.items()):
            updates_group.append(update_group)
            if len(updates_group) > 100:
                log(f"Player {player_id} was not responding for too long. Disconnecting.")
                self._player_updates.pop(player_id)
                client = self._player_to_client.get(player_id)
                if client:
                    client.disconnect()


        for client in self._current_tick_update_ready_clients:
            player_id = client.player_id
            try:
                update_groups_str = jsondumps(self._player_updates[player_id])
                client.send_string(update_groups_str)
                self._player_updates[player_id].clear()

            except Exception as e:
                log(f"sending updates to player_id: {player_id} failed: {repr(e)}")

        if self._update_roundtrip_start:
            self.roundtrip_update_time = (datetime.now() - self._update_roundtrip_start).total_seconds()
            if self.roundtrip_update_time > 0.035:
                log(f"WARN: Update roundtrip: {self.roundtrip_update_time * 1000:.2f}ms")

        with self._L_game:
            # make the pulse locked - this way, no update requests can be lost
            self._raw_game_pulse_event.set()
            self._raw_game_pulse_event.clear()

        if self._full_state_subscribers:
            full_state_data = self._get_full_state_data()
            asyncio.run_coroutine_threadsafe(
                asyncio.wait([self._send_full_state_data(subscriber, full_state_data) for subscriber in
                              self._full_state_subscribers]),
                self._loop
            )

        self._last_tick_time = datetime.now()

    async def _send_full_state_data(self, subscriber, full_state_data):
        try:
            await subscriber.send(full_state_data)
        except Exception as e:
            log(f"_send_full_state_data {subscriber} {repr(e)}")
            self._full_state_subscribers.discard(subscriber)

    async def _client_handler(self, websocket, path):
        log(f"_client_handler({websocket}, {path})")
        if path == "/game":
            await websocket.send("disconnected; Updates are now served through raw TCP only")
        elif path == "/observer":
            await self._observer_handler(websocket)

    async def _observer_handler(self, websocket):
        try:
            log(f"_observer_handler({websocket.local_address})")
            self._full_state_subscribers.add(websocket)
            full_state_data = self._get_full_state_data()
            await websocket.send(full_state_data)

            async for control_data in websocket:
                if self._control_callback:
                    self._control_callback(control_data)

        except Exception as e:
            log(f"_observer_handler: {repr(e)}")
        finally:
            self._full_state_subscribers.discard(websocket)

    def _get_full_state_data(self):
        # make a copy, so "uncommitted" updates are not leaking
        game_copy = self._game.copy_without_internal_data()
        full_state_data = jsondumps({
            "tick": self._game.tick,
            "state": game_copy
        })
        return full_state_data

    async def _connection_statistic_worker(self):
        while True:
            await asyncio.sleep(1)
            if not self.on_connection_stats_registered:
                continue

            for player_id, client in self._player_to_client.items():
                if client is None:
                    # player not connected
                    self.on_connection_stats_registered(player_id, None, None)
                else:
                    self.on_connection_stats_registered(player_id, 1.0, self._pings.get(player_id, 0))

    def _raw_accept_clients(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', self._port + 1))
        s.listen()
        log(f"ACCEPTING RAW CLIENTS ON PORT={self._raw_updates_port}")

        while True:
            client_socket, addr = s.accept()
            Thread(target=self._raw_game_play_handler, args=[client_socket, addr], daemon=True).start()

    def _raw_handle_player_connection(self, player_id: str, version: str, client: SocketClient):
        log(f"PLAYER CONNECTED: {player_id}, version: {version}")

        if player_id in self._player_to_client and self._player_to_client[player_id]:
            self._player_to_client[player_id].send_string("disconnected")
            self._player_to_client[player_id].disconnect()

        self._player_to_client[player_id] = client

    def _raw_handle_player_disconnection(self, player_id: str, client: SocketClient):
        log(f"PLAYER DISCONNECTED {player_id}")

        with self._L_game:
            self._player_requests[player_id] = None
            self._player_updates.pop(player_id, None)
            self._is_future_request.pop(player_id, None)

        if self._player_to_client.get(player_id) == client:
            self._player_to_client[player_id] = None

    def _raw_game_play_handler(self, socket, addr):
        player_id = None
        client = SocketClient(socket)

        try:
            initial_message_str = client.read_string()
            initial_message = jsonloads(initial_message_str)
            try:
                player_id = initial_message["player_id"]
                validate_email(player_id)
                version = initial_message.get("version")
                log(f"Connection attempt {player_id}> {initial_message}")

                if version is None:
                    raise ValueError("Version is not set. Please update your bot to current protocol.")

            except Exception as e:
                log(f"player validation {repr(e)}")
                client.send_string(
                    jsondumps({"updates": [ErrorUpdate(player_id, repr(e))], "tick": self._game.tick + 1})
                )
                client.send_string("disconnected")
                return

            client.player_id = player_id

            with self._L_game:
                self._is_future_request[player_id] = False
                self._player_requests[player_id] = None
                self._player_updates[player_id] = []

            client.send_string(self._get_full_state_data())
            self._raw_handle_player_connection(player_id, version, client)

            ping_start = datetime.now()
            while client.is_connected:
                message = client.read_string()
                if message is None:
                    break  # client disconnected

                update_request = jsonloads(message)

                if isinstance(update_request, list):
                    if len(update_request) > MAX_FUTURE_UPDATE_REQUESTS + 1:
                        raise ValueError(f"Too long update request sent, with length {len(update_request)}")
                else:
                    update_request = [update_request]

                with self._L_game:
                    self._is_future_request[player_id] = False
                    self._player_requests[player_id] = update_request
                    self._update_ready_clients.append(client)

                ping_end = datetime.now()
                ping_time = (ping_end - ping_start).total_seconds()
                if player_id not in self._pings:
                    self._pings[player_id] = ping_time

                self._pings[player_id] = self._pings[player_id] * 0.95 + 0.05 * ping_time
                self._raw_game_pulse_event.wait()  # wait for pulse - meaning, updates were sent
                ping_start = datetime.now()


        except Exception as e:
            log(f"_raw_game_play_handler: {repr(e)}")

        finally:
            if player_id:
                self._raw_handle_player_disconnection(player_id, client)
