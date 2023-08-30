#-----------------------------------------------------
# NOTE:
#
# It is a bit of a tricky process to create authentication to a Google Sheet.
# This requires creating a service and a key in Development Console.
# You can get some instructions as how to do it here:
#
# https://www.makeuseof.com/tag/read-write-google-sheets-python/
#
#-----------------------------------------------------
import inspect
import gspread
from oauth2client.service_account import ServiceAccountCredentials


class GoogleSheet:

    def __init__(self):
        self.key_file = 'vacuum-pressure-logging-fec930aae86a.json'
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Get the path of this class so we can prefix the key file
        # (to ensure it doesn't matter what project uses this class and what is the location it runs from)
        self.key_file = inspect.getfile(GoogleSheet).replace('GoogleSheet.py', self.key_file)

        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.key_file, scopes)
        file = gspread.authorize(credentials)  # authenticate the JSON key with gspread
        sheet = file.open("Vacuum Pressure Log")  # open sheet
        self.worksheet = sheet.sheet1  # replace sheet_name with the name that corresponds to yours, e.g, it can be sheet1
        pass

    def get_all_values(self):
        return self.worksheet.get_all_values()

    def get_number_of_rows(self):
        # this is a list of all data and the length is equal to the number of rows including header row if it exists in data set
        max_rows = len(self.worksheet.get_all_values())
        return max_rows

    def get_number_of_cols(self):
        # this will count the items in the first row, and assumes the first row is either header or has no empty cells        num_rows = len(self.worksheet.row_values(1))
        max_cols = len(self.worksheet.get_all_values()[0])
        return max_cols

    def get_value(self, row, col):
        return self.worksheet.cell(row, col).value

    def write_value(self, row, col, value):
        self.worksheet.update_cell(row, col, value)

    def read_range(self, range):
        # Range: E.g. 'A1:B4'
        return self.worksheet.range(range)


if __name__ == "__main__":

    from functions.DLinkDCS932L.Webcam import Webcam
    from datetime import datetime

    wc = Webcam('132.77.54.139', 'admin', '123456', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    text = wc.get_text('rgb')

    gs = GoogleSheet()
    num_rows = gs.get_number_of_rows()

    current_time = datetime.now()
    str_date_time = current_time.strftime("%d/%m/%Y %H:%M:%S")

    torr_value = text
    torr_value = torr_value[0]+'.'+torr_value[1:-1].replace('-', 'E-')  # Remove new line at the end and add the 'E'xponent symbol

    gs.write_value(num_rows+1, 1, str_date_time)
    gs.write_value(num_rows+1, 2, torr_value)

    pass