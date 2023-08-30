from PIL import Image
import requests
from io import BytesIO
# import the necessary packages
import pytesseract
import argparse
import cv2
import numpy as np

# -----------------------------------------------------------
# Important Notes:
#
# 1) Tesseract MUST be installed on machine (ON TOP of installing the pytesseract package)
# See: https://github.com/UB-Mannheim/tesseract/wiki
#
# 2) After installation, the path should be passed in constructor - as it needs to be set
# -----------------------------------------------------------


class Webcam:

    def __init__(self, ip, username, password, tesseract_exe_path):
        self.url = f'http://{username}:{password}@{ip}/image/jpeg.cgi'

        # Set the Tesseract executable path
        pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
        pass

    def get_image(self):
        response = requests.get(self.url)
        img = Image.open(BytesIO(response.content))
        return img

    def show_image(self):
        img = self.get_image()
        img.show()
        pass

    def cv2_show_image(self):
        img = self.get_image()
        nimg = np.asarray(img)
        cv2.imshow("Image", nimg)
        cv2.waitKey(0)
        pass

    def get_text(self, mode):
        self.text = None
        if mode=='rgb':
            self.text = self._ocr_rgb()
        else:
            self.text = self._ocr_greyscale()
        return self.text

    def _ocr_rgb(self, psm=7):
        img = self.get_image()

        # Convert to numpy array
        nimg = np.asarray(img)
        (h, w) = nimg.shape[:2]

        rgb = np.asarray(img)
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_CUBIC)
        text = pytesseract.image_to_string(rgb, config=f'--psm {psm} tessedit_char_whitelist=0123456789-.')  # config="outputbase digits"
        return text

    def _ocr_greyscale(self, psm=7):
        img = self.get_image()

        # Convert to numpy array
        nimg = np.asarray(img)

        gry = cv2.cvtColor(nimg, cv2.COLOR_BGR2GRAY)
        gry = cv2.resize(gry, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        gry = cv2.bitwise_not(gry)
        text = pytesseract.image_to_string(gry, config=f'--psm {psm} tessedit_char_whitelist=0123456789-.')
        return text
