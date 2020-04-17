import ctypes
from threading import Thread
from typing import Callable, Optional

from arena_bulanci.bots.bot_base import BotBase


class JupyterBot(BotBase):
    def __init__(self):
        super().__init__()
        self.handler: Optional[Callable] = None

        self._thread: Optional[Thread] = None
        self._arena: Optional[str] = None
        self._username: Optional[str] = None

    def _spawn_bot(self):
        if not self.handler:
            # prevent spawning if no handler is set
            return

        super()._spawn_bot()

    def _play(self):
        handler = self.handler

        if handler:
            try:
                handler(self)
            except Exception as e:
                print(f"JUPYTERBOT HANDLER RAISED ERROR: {repr(e)}")

    def stop(self):
        if self._thread:
            thread_id = self._thread.ident
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                print('Exception raise failure')

            self._thread.join()

    def run(self, arena_host: str, username: str):
        """
        This is a special runner intended for use from Jupyter notebook only
        :return:
        """

        if self._thread:
            self.stop()

        self._arena_host = arena_host
        self._username = username
        self._thread = Thread(target=self._run_worker)
        self._thread.start()

    def _run_worker(self):

        from arena_bulanci.core.execution import run_remote_arena_game

        run_remote_arena_game(self, self._username, arena_hostname_override=self._arena_host)
