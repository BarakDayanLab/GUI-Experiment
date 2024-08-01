import os
import time
import glob
import json
from os import listdir
from os.path import isfile, join
import socket
from csv import reader
import time, threading
import struct
import socket
from threading import Thread, Event, Timer


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
        self.socket.settimeout(10.0)

    def reinitialize_socket(self):
        self.socket.close()
        self.initialize_socket()

    def connect_socket(self):
        if self.stop_thread.is_set():
            return

        while not self.connected:
            try:
                self.socket.connect((self.ip, self.port))
                self.connection_callback(True)
                self.connected = True
            except OSError as e:
                print(f'Attempted to connect. Error: {e}')
                time.sleep(1)
                self.reinitialize_socket()
        return

    def reconnect_socket(self):
        self.reinitialize_socket()
        self.connect_socket_thread = Thread(target=self.connect_socket)
        self.connect_socket_thread.start()

    def is_connected(self):
        return self.connected

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
        pass


class SNSPDsLogsSync:
    # Class constants
    LOGS_SOURCE_PATH = 'U:\\Personal Folders\\drorg\\Temp\\SNSPDs Logs'
    LOGS_TARGET_PATH = 'U:\\Lab_2023\\Experiment_results\\QRAM\\SNSPDs\\snspds.csv'

    SYNC_PERIOD = 30  # Every 30 seconds

    SERVER_IP = "132.77.54.212"  # Lab 112
    SERVER_PORT = 5051

    def __init__(self):
        self.last_sync = time.time()
        self.socket = SocketClient(self.SERVER_IP, self.SERVER_PORT, self._connection_status)
        self.socket.start()
        pass

    def _connection_status(self, is_connected):
        if is_connected:
            hostname, my_ip_address = self.socket.get_host_ip()
            print('Socket client running on host {}. IP: {}'.format(hostname, my_ip_address))
        else:
            print("connection to socket server lost. Trying to reconnect...")
        pass

    def read_csv_last_line(self, csv_file):
        with open(csv_file, "r") as f1:
            all_lines = f1.readlines()
        return all_lines[0], all_lines[-1]

    def read_csv(self, csv_file):

        # skip first line i.e. read header first and then iterate over each row of csv as a list
        with open(csv_file, 'r') as read_obj:
            csv_reader = reader(read_obj)
            header = next(csv_reader)
            # Check file as empty
            if header != None:
                # Iterate over each row after the header in the csv
                for row in csv_reader:
                    # row variable is a list that represents a row in csv
                    print(row)
        return 5

    def write_txt_file(self, str):
        with open(self.LOGS_TARGET_PATH, 'w') as f:
            f.write(str)

    def extract_data_and_send(self):

        # Get CSV files in folder
        all_csv_files = glob.glob(self.LOGS_SOURCE_PATH + '\\*.csv')

        # Get the most recent one - and parse its date from name
        latest_file = max(all_csv_files, key=os.path.getmtime)

        # Get header and last line from CSV file
        header_line, last_line = self.read_csv_last_line(latest_file)

        # Break into tokens and prepare json for sending over the wire
        keys = header_line.replace('\n', '').split(',')
        values = last_line.replace('\n', '').split(',')
        dict = {}
        for i in range(0, len(keys)):
            dict[keys[i]] = values[i]

        # Send data over the wire
        self.send_data(dict)
        pass

    def copy_files(self):

        # Get CSV files in folder
        all_csv_files = glob.glob(self.LOGS_SOURCE_PATH + '\\*.csv')

        # Get the most recent one - and parse its date from name
        latest_file = max(all_csv_files, key=os.path.getmtime)

        # Open the file as CSV and read last line written to it
        header_line, last_line = self.read_csv_last_line(latest_file)
        values = last_line.split(',')

        # Write it to the Mounted drive
        self.write_txt_file(last_line)

        pass

    def send_data(self, data_dict):
        """
        Send information to the server
        """

        try:
            self.socket.send_data(data_dict)
        except Exception as e:
            print(f'Unable to send data: {e}')
        finally:
            # close client socket (connection to the server)
            #self.client.close()
            #print("Connection to server closed")
            pass

        pass

    def mainloop(self):
        while True:
            time_str = time.strftime("%Y%m%d-%H%M%S")
            print(time_str + ': Running sync process...')
            self.extract_data_and_send()
            #self.copy_files()
            time.sleep(self.SYNC_PERIOD)


if __name__ == "__main__":
    sync = SNSPDsLogsSync()
    sync.mainloop()
    pass
