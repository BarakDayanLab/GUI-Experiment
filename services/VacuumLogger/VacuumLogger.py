from functions.DLinkDCS932L.Webcam import Webcam
from services.GoogleSheet.GoogleSheet import GoogleSheet
from datetime import datetime
import time


class VacuumLogger:

    def __init__(self, minutes_interval):
        # Initialize webcam
        self.webcam = Webcam('132.77.54.139',
                             'admin',
                             '123456',
                             r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                             x=170, y=80, h=120, w=360)

        # Initialize connection to Google Sheet
        self.gs = GoogleSheet()

        self.interval = minutes_interval
        pass

    def _get_vacuum_value(self):
        text_rgb = self.webcam.get_text('rgb', False)
        text_grey = self.webcam.get_text('grey', False)

        torr_value = text_rgb
        if text_rgb != text_grey:
            torr_value = text_rgb

        if len(torr_value) < 6:
            return 'na'

        if torr_value.find('-') == -1:
            return 'na'

        torr_value = torr_value[0] + '.' + torr_value[1:-1].replace('-', 'E-0')  # Remove new line at the end and add the 'E'xponent symbol

        return torr_value

    def _write_line_to_sheet(self, torr_value):
        num_rows = self.gs.get_number_of_rows()

        current_time = datetime.now()
        str_date_time = current_time.strftime("%d/%m/%Y %H:%M:%S")

        # Write the date and value to the next row
        self.gs.write_value(num_rows + 1, 1, str_date_time)
        self.gs.write_value(num_rows + 1, 2, torr_value)

    def mainloop(self):

        while True:
            torr_value = self._get_vacuum_value()
            self._write_line_to_sheet(torr_value)
            print(f'Logged {torr_value}')
            time.sleep(60*self.interval)  # Sleep for <interval> minutes
            #time.sleep(5)  # Sleep for 5 seconds

        pass


if __name__ == "__main__":

    logger = VacuumLogger(minutes_interval=5)
    logger.mainloop()

    # Should never reach here...
    pass