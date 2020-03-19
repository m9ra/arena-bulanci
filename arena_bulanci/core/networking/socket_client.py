import json
import socket
import traceback
from threading import Lock
from typing import Optional

class SocketClient(object):
    def __init__(self, socket=None):
        self._L_send = Lock()
        self._L_read = Lock()
        self._socket = socket
        if self._socket is not None:
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self._is_connected = socket is not None

    @property
    def is_connected(self):
        return self._is_connected

    def connect(self, host, port):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._socket.connect((host, port))
        self._is_connected = True

    def disconnect(self):
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            print("shutdown not clean")

        self._is_connected = False

    def send_json(self, data):
        json_data = json.dumps(data)
        self.send_string(json_data)

    def read_json(self, timeout=None):
        json_data = self.read_string(timeout)
        if json_data is None or json_data == "":
            return None

        result = json.loads(json_data)
        return result

    def send_string(self, raw_data):
        raw_data_bytes = raw_data.encode('utf-8')
        self.send_bytes(raw_data_bytes)

    def read_string(self, timeout=None) -> Optional[str]:
        bytes = self.read_bytes(timeout)
        if bytes is None:
            return None

        return bytes.decode("utf-8")

    def send_bytes(self, raw_data_bytes):
        raw_data_bytes_len = len(raw_data_bytes)
        raw_data_bytes_len_bytes = int.to_bytes(raw_data_bytes_len, byteorder="big", length=4)
        if len(raw_data_bytes_len_bytes) != 4:
            AssertionError("Protocol expects 4 byte length specification")
        try:
            with self._L_send:
                self._atomic_send(raw_data_bytes_len_bytes)
                self._atomic_send(raw_data_bytes)

        except BrokenPipeError:
            # expected behaviour - end silently
            self._is_connected = False
        except Exception:
            self._is_connected = False
            # traceback.print_exc()

    def read_bytes(self, timeout=None) -> Optional[bytes]:
        try:
            self._socket.settimeout(timeout)
            with self._L_read:
                length_bytes = self._atomic_recv(4)
                length = int.from_bytes(length_bytes, byteorder="big")
                byte_buffer = self._atomic_recv(length)

            raw_data = bytearray(byte_buffer)
            return raw_data

        except (ConnectionResetError, BrokenPipeError):
            self._is_connected = False
            return None

        except Exception:
            # todo detect timeout
            self._is_connected = False
            # traceback.print_exc()
            return None

        finally:
            self._socket.settimeout(None)

    def _atomic_send(self, data_bytes):
        data_len = len(data_bytes)
        data_sent_so_far = 0
        while data_sent_so_far < data_len:
            data_sent_so_far += self._socket.send(data_bytes[data_sent_so_far:])

    def _atomic_recv(self, length):
        byte_buffer = []
        missing_bytes = length
        while missing_bytes > 0:
            data = self._socket.recv(missing_bytes)
            received_len = len(data)

            if received_len == 0:
                raise BrokenPipeError("Socket is not connected.")

            missing_bytes -= received_len
            byte_buffer.extend(data)
        return byte_buffer