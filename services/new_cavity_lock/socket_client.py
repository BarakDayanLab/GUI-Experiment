import json
import time
import struct
import socket
from threading import Thread, Event


class SocketClient:
    def __init__(self, ip, port, connection_callback=None):
        self.ip = ip
        self.port = port
        self.connection_callback = connection_callback

        self.socket = None
        self.initialize_socket()

        self.connect_socket_thread = Thread(target=self.connect_socket)
        self.stop_thread = Event()

        self.connected = False

    def start(self):
        self.connect_socket_thread.start()

    def close(self):
        self.stop_thread.set()

    def join(self):
        self.connect_socket_thread.join()
        self.socket.close()

    @staticmethod
    def get_host_ip():
        hostname = socket.gethostname()
        return hostname, socket.gethostbyname(hostname)

    def initialize_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(3)

    def reinitialize_socket(self):
        self.socket.close()
        self.initialize_socket()

    def connect_socket(self):
        if self.stop_thread.is_set():
            return

        try:
            self.socket.connect((self.ip, self.port))
            self.connection_callback(True)
            self.connected = True
        except OSError as e:
            time.sleep(1)
            self.reinitialize_socket()
            self.connect_socket()

    def reconnect_socket(self):
        self.reinitialize_socket()
        self.connect_socket_thread = Thread(target=self.connect_socket)
        self.connect_socket_thread.start()

    def send_data(self, message):
        if not self.connected:
            return
        message = json.dumps(message)
        message = message.encode()
        data_size = len(message)
        struct_data = struct.pack('!I', data_size) + message

        try:
            res = self.socket.send(struct_data)
            return res
        except OSError as e:
            self.connection_callback(False)
            self.connected = False
            self.reconnect_socket()
