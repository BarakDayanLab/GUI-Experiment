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

    def __init__(self, ip, username, password, tesseract_exe_path, x=None, y=None, h=None, w=None):
        self.url = f'http://{username}:{password}@{ip}/image/jpeg.cgi'

        self.x = x
        self.y = y
        self.h = h
        self.w = w

        # Set the Tesseract executable path
        pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
        pass

    def get_image(self):
        response = requests.get(self.url)
        img = Image.open(BytesIO(response.content))
        nimg = np.asarray(img)

        # Need cropping?
        if self.x is not None:
            nimg = nimg[self.y:self.y + self.h, self.x:self.x + self.w]

        return nimg

    def show_image(self):
        nimg = self.get_image()
        cv2.imshow("Image", nimg)
        cv2.waitKey(0)
        pass

    def get_text(self, mode, debug=False):
        self.text = None
        if mode == 'rgb':
            self.text = self._ocr_rgb(debug=debug)
        else:
            self.text = self._ocr_greyscale(debug=debug)
        return self.text

    def _ocr_rgb(self, psm=7, debug=False):
        rgb = self.get_image()
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_CUBIC)
        text = pytesseract.image_to_string(rgb, config=f'--psm {psm} vacuum')  # config="outputbase digits"

        if debug:
            cv2.imshow("Image", rgb)
            cv2.waitKey(0)

        return text

    def _ocr_greyscale(self, psm=7, debug=False):
        gry = self.get_image()
        gry = cv2.cvtColor(gry, cv2.COLOR_BGR2GRAY)
        gry = cv2.resize(gry, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        gry = cv2.bitwise_not(gry)
        text = pytesseract.image_to_string(gry, config=f'--psm {psm} vacuum')

        if debug:
            cv2.imshow("Image", gry)
            cv2.waitKey(0)

        return text
