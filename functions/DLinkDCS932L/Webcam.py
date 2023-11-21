from PIL import Image
import requests
from io import BytesIO
# import the necessary packages
import pytesseract
import argparse
import cv2
import numpy as np
import keyboard
import time
from matplotlib import pyplot as plt
#from matplotlib import image as mpimg
import sys

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

    def get_image(self, crop=True):
        response = requests.get(self.url)
        img = Image.open(BytesIO(response.content))
        nimg = np.asarray(img)

        # Need cropping?
        if self.x is not None and crop:
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
        elif mode == 'grey':
            self.text = self._ocr_greyscale(debug=debug)
        else:
            self.text = self._ocr_experimental(debug=debug)
        return self.text

    def _ocr_experimental(self, debug=False):

        image = self.get_image()
        gry = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Look at a given row
        row = image[0]
        #img_array = np.array(image, dtype=np.uint8)



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

    def on_press(self, event):
        #print('press', event.key)
        sys.stdout.flush()
        should_update = True
        weight = 1

        if event.key.startswith('shift+'):
            weight = 10
            event.key = event.key.replace('shift+', '')

        if event.key == 'x':
            self.frame = cv2.bitwise_not(self.frame)
            self.im.set_data(self.frame)
            self.fig.canvas.draw()
            should_update = False
        elif event.key == 'left':
            self.x = self.x - weight
        elif event.key == 'right':
            self.x = self.x + weight
        elif event.key == 'up':
            self.y = self.y - weight
        elif event.key == 'down':
            self.y = self.y + weight
        elif event.key == '[':
            self.w = self.w + weight
        elif event.key == ']':
            self.w = self.w - weight
        elif event.key == 'a':
            self.h = self.h + 1
        elif event.key == 'A':
            self.h = self.h + 10
        elif event.key == 'z':
            self.h = self.h - 1
        elif event.key == 'Z':
            self.h = self.h - 10
        else:
            should_update = False

        if should_update:
            self.frame = self.org_frame[self.y:self.y + self.h, self.x:self.x + self.w]
            self.im.set_data(self.frame)
            self.fig.canvas.draw()
            print(f'x={self.x}, y={self.y}, h={self.h}, w={self.w}')

    def calibrate(self):
        """
        This method brings the camera image and allows to move it left/right (use arrows) or change the width
        (with '[' ot ']') or change the height (with 'a' or 'z')
        """

        self.org_frame = self.get_image(crop=False)

        self.frame = self.org_frame[self.y:self.y + self.h, self.x:self.x + self.w]

        plt.title("Position: Up-arrow Down-arrow  Width: [ ]  Height: a z")
        #plt.xlabel("X pixel scaling")
        #plt.ylabel("Y pixels scaling")

        self.fig, ax = plt.subplots()
        self.fig.canvas.mpl_connect('key_press_event', self.on_press)

        self.im = plt.imshow(self.frame)
        plt.show()

        pass

    @staticmethod
    def test():
        import cv2
        webcam = cv2.VideoCapture(2)  # Number which capture webcam in my machine
        # try either VideoCapture(0) or (1) based on your camera availability
        # in my desktop it works with (1)
        check, frame = webcam.read()

        cv2.imshow("Image", frame)
        cv2.waitKey(0)

        #cv2.imwrite(filename=r'<Your Directory>\saved_img.jpg', img=frame)

        webcam.release()
        pass

if __name__ == "__main__":

    Webcam.test()
    pass