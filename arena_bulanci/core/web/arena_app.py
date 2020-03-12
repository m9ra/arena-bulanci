import json
import os
import sys
from threading import Thread
from time import sleep

from flask import Flask, render_template
from flask_bootstrap import Bootstrap

from arena_bulanci.core.config import REMOTE_ARENA_WEB_PORT, REMOTE_ARENA_GAME_UPDATES_PORT, TICKS_PER_SECOND
from arena_bulanci.core.game import Game
from arena_bulanci.core.utils import jsondumps, jsonloads
from arena_bulanci.core.web.game_update_server import GameUpdateServer
from arena_bulanci.core.web.user_stats import UserStats


class ArenaApp(object):
    def __init__(self, game: Game, host: str, web_port: int, game_updates_port: int, arena_name: str):
        self._game = game
        self._host = host
        self._web_port = web_port
        self._game_updates_port = game_updates_port
        self._arena_name = arena_name

        self._control_callback = None
        self._is_running = False
        self._user_statistics = {}

        self._arena_state_file = self._arena_name + ".state.json"
        if os.path.isfile(self._arena_state_file):
            with open(self._arena_state_file, "r") as f:
                self._user_statistics = jsonloads(f.read())

        Thread(target=self._persistency_worker, daemon=True).start()

    def run_blocking(self):
        self._start_game_updates()
        self._block_on_web_server()

    def run_async(self):
        self._start_game_updates()
        Thread(target=self._block_on_web_server, daemon=True).start()

    def register_control_callback(self, callback):
        if self._is_running:
            raise AssertionError("Can't register callback when server is running")

        self._control_callback = callback

    def _start_game_updates(self):
        self._is_running = True
        server = GameUpdateServer(self._game, self._host, self._game_updates_port)
        server.on_kill_registered = self._kill_handler
        server.on_shot_registered = self._shot_handler
        server.on_connection_stats_registered = self._connection_stats_handler
        if self._control_callback:
            server.register_control_callback(self._control_callback)

        server.start()

    def _kill_handler(self, killer, victim):
        def _expected_win_probability(rating1, rating2):
            return 1.0 / (1.0 + pow(10, ((rating2 - rating1) / 400)))

        stats1 = self._get_user_statistics(killer)
        stats2 = self._get_user_statistics(victim)

        stats1.kills += 1
        stats2.deaths += 1

        p1 = _expected_win_probability(stats1.rating, stats2.rating)
        p2 = _expected_win_probability(stats2.rating, stats1.rating)
        K = 20
        stats1.rating = stats1.rating + K * (1 - p1)
        stats2.rating = stats2.rating + K * (0 - p2)

    def _shot_handler(self, player):
        self._get_user_statistics(player).shots += 1

    def _connection_stats_handler(self, player, connection_time: float, ping_time: float):
        stats = self._get_user_statistics(player)
        if connection_time is None:
            stats.is_online = False
        else:
            stats.is_online = True
            stats.total_time += connection_time
            stats.ping = ping_time

    def _get_user_statistics(self, player) -> UserStats:
        if not player in self._user_statistics:
            self._user_statistics[player] = UserStats(player)

        return self._user_statistics[player]

    def _persistency_worker(self):
        while True:
            with open(self._arena_state_file, "w")as f:
                f.write(jsondumps(self._user_statistics))

            sleep(30)

    def _block_on_web_server(self):
        app = Flask(__name__)
        app.secret_key = b'afer234\n\xec]/'
        Bootstrap(app)

        arena = self

        @app.route("/game")
        def game():
            return render_template(
                "game.html",
                game_updates_port=arena._game_updates_port,
                add_controls=self._control_callback is not None
            )

        @app.route("/")
        def index():
            return render_template(
                "index.html",
                web_port=arena._web_port,
                game_updates_port=arena._game_updates_port,
                arena=arena._arena_name
            )

        @app.route("/results_table")
        def results_table():
            users = list(arena._user_statistics.values())
            users.sort(key=lambda s: s.rating, reverse=True)
            return render_template("results_table.html", users=users)

        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        print(f"ARENA WEB ON: http://{self._host}:{self._web_port}/")
        app.run(
            debug=True, use_reloader=False, host=self._host,
            port=self._web_port,
        )


def _game_worker(game: Game):
    while game.is_running:
        game.step(catch_exceptions=True)
        sleep(1.0 / TICKS_PER_SECOND)


if __name__ == "__main__":
    arena_game = Game()
    Thread(target=_game_worker, args=[arena_game], daemon=True).start()

    arena_app = ArenaApp(arena_game, '0.0.0.0', REMOTE_ARENA_WEB_PORT, REMOTE_ARENA_GAME_UPDATES_PORT, sys.argv[1])
    arena_app.run_blocking()
