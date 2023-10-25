from functions.DLinkDCS932L.Webcam import Webcam
from services.GoogleSheet.GoogleSheet import GoogleSheet
from datetime import datetime
import time
import re


class VacuumLogger:

    def __init__(self, seconds_interval, debug=False):
        # Initialize webcam
        self.webcam = Webcam('132.77.54.139',
                             'admin',
                             '123456',
                             r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                             x=100, y=50, h=120, w=380)

        # Initialize connection to Google Sheet
        self.gs = GoogleSheet()
        self.debug = debug

        self.interval = seconds_interval
        pass

    def _get_vacuum_values(self):
        text_rgb = self.webcam.get_text('rgb', self.debug)
        text_grey = self.webcam.get_text('grey', self.debug)

        text_rgb = text_rgb[:-1]
        text_grey = text_grey[:-1]

        torr_value = text_rgb
        if torr_value.find('-') == -1:
            torr_value = 'na'
        else:
            torr_value = torr_value[0] + '.' + torr_value[1:].replace('-', 'E-0')  # Remove new line at the end and add the 'E'xponent symbol

        # if torr_value[0] == '1':
        #     torr_value = '7' + torr_value[1:]

        return torr_value, text_rgb, text_grey

    def _write_line_to_sheet(self, torr_value):
        num_rows = self.gs.get_number_of_rows()

        current_time = datetime.now()
        str_date_time = current_time.strftime("%d/%m/%Y %H:%M:%S")

        # Write the date and value to the next row
        self.gs.write_value(num_rows + 1, 1, str_date_time)
        self.gs.write_value(num_rows + 1, 2, torr_value)

    def _write_values_to_sheet(self, torr_value, text_rgb, text_grey):
        num_rows = self.gs.get_number_of_rows()

        current_time = datetime.now()
        str_date_time = current_time.strftime("%d/%m/%Y %H:%M:%S")

        # Write the date and value to the next row
        self.gs.write_value(num_rows + 1, 1, str_date_time)
        self.gs.write_value(num_rows + 1, 2, torr_value)
        self.gs.write_value(num_rows + 1, 3, text_rgb)
        self.gs.write_value(num_rows + 1, 4, text_grey)

    def mainloop(self):

        while True:
            torr_value, text_rgb, text_grey = self._get_vacuum_values()
            self._write_values_to_sheet(torr_value, text_rgb, text_grey)

            #torr_value = self._get_vacuum_value()

            # Using regex()

            # if re.match('^[0-9E.-]*$', torr_value):
            #     self._write_line_to_sheet(torr_value)
            #     print(f'Logged {torr_value}')
            # else:
            #     print(f'Got invalid readout: {torr_value}. Skipping.')

            time.sleep(self.interval)  # Sleep for <interval> seconds
        pass


if __name__ == "__main__":

    logger = VacuumLogger(seconds_interval=2 * 60, debug=True)  # Every 60 seconds

    #logger.webcam.calibrate()

    logger.mainloop()

    # Should never reach here...
    pass