from typing import Optional, Tuple

from arena_bulanci.bots.bot_base import BotBase
from arena_bulanci.core.web.arena_app import ArenaApp


class ManualBot(BotBase):
    def __init__(self, port: int, color: Optional[Tuple[int, int, int]] = None, ws_port: Optional[int] = None,
                 raw_updates_port: Optional[int] = None):
        super().__init__(color=color)

        if not ws_port:
            ws_port = port + 1

        if not raw_updates_port:
            raw_updates_port = ws_port + 1

        self._port = port
        self._ws_port = ws_port
        self._raw_updates_port = raw_updates_port

        self._initialized = False

    def _on_bot_spawned(self):
        self._desired_direction = 0
        self._move = False
        self._shoot = False

    def _play(self):
        if not self._initialized:
            self._initialized = True
            app = ArenaApp(self._raw_game, "127.0.0.1", self._port, self._ws_port, self._raw_updates_port,
                           "Manual Bot Control Web")
            app.register_control_callback(self._controll_callback)
            app.run_async()
            print(f"MANUAL CONTROL WEB FOR `{self.player_id}` RUNNING ON: http://127.0.0.1:{self._port}/game\n")

        if self.direction != self._desired_direction:
            self.MOVE_rotate(self._desired_direction)
            return

        if self._shoot:
            self._shoot = False
            if self.can_shoot:
                self.MOVE_shoot()

            return

        if self._move:
            self.MOVE_step_forward()
            return

    def _controll_callback(self, data):
        if data == "shoot":
            self._shoot = True

        if data.startswith("dir:"):
            self._desired_direction = int(data[4:])
            self._move = True

        if data == "stop":
            self._move = False
