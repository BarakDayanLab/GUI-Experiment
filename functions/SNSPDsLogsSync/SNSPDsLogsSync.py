import os
import time
import glob
from os import listdir
from os.path import isfile, join
from csv import reader
import numpy as np



class SNSPDsLogsSync:
    # Class constants
    #LOGS_SOURCE_PATH = 'C:\\Users\\drorg\\Downloads\\SNSPDS Log file\\Source'
    #LOGS_TARGET_PATH = 'C:\\Users\\drorg\\Downloads\\SNSPDS Log file\\Target\\snspds.npy'
    LOGS_SOURCE_PATH = 'C:\\Users\\labbd\\Desktop\PhotonSpot\\freezecontrol2.1.8.weizmann\log'
    #LOGS_TARGET_PATH = 'U:\\Lab_2023\\Experiment_results\\QRAM\\SNSPDs\\snspds.npy'
    LOGS_TARGET_PATH = 'U:\\Lab_2023\\Experiment_results\\QRAM\\SNSPDs\\snspds.csv'
    #SYNC_PERIOD = 2 * 60  # Every 2 minutes
    SYNC_PERIOD = 30  # Every 10 seconds


    def __init__(self):
        self.last_sync = time.time()
        pass

    def read_csv_last_line(self, csv_file):
        with open(csv_file, "r") as f1:
            last_line = f1.readlines()[-1]
        return last_line

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

    def write_np_file(self, values):
        try:
            np.save(self.LOGS_TARGET_PATH, np.array(values))
        except Exception as e:
            print(e)

    def write_txt_file(self, str):
        with open(self.LOGS_TARGET_PATH, 'w') as f:
            f.write(str)

    def copy_files(self):

        # Get CSV files in folder
        all_csv_files = glob.glob(self.LOGS_SOURCE_PATH + '\\*.csv')

        # Get the most recent one - and parse its date from name
        latest_file = max(all_csv_files, key=os.path.getmtime)

        # Open the file as CSV and read last line written to it
        #rows = self.read_csv(latest_file)
        last_line = self.read_csv_last_line(latest_file)
        values = last_line.split(',')

        # Write it to the Mounted drive
        #self.write_np_file(values)
        self.write_txt_file(last_line)

        pass

    def start_sync(self):
        # Is it time to sync?
        time_passed = time.time() - self.last_sync
        self.last_sync = time.time()
        if time_passed < self.SYNC_PERIOD:
            return

        # Start sync
        self.copy_files()

        pass


    def mainloop(self):
        while True:
            time_str = time.strftime("%Y%m%d-%H%M%S")
            print(time_str + ': Running sync process...')
            self.copy_files()
            time.sleep(self.SYNC_PERIOD)

if __name__ == "__main__":
    sync = SNSPDsLogsSync()
    sync.mainloop()
    pass
