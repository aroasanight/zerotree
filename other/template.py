# write the code inside a function underneath the comment near the bottom stating WRITE YOUR PROGRAM HERE INSIDE A FUNCTION (it's hard to miss)
# remember to change the function name to something descriptive!
# enter a name for your mode HERE (i'll transplant this into the code manually): 
# tips: 
#   1. call pixels.show() only when absolutely necessary - ie don't call it individually per pixel if updating the whole tree, it's very, VERY slow.
#   2. DO NOT use infinite loops - your function will be looped repeatedly anyway, so make the end of the function leaves it in a state where when started again it'll loop nicely.

# add any imports that aren't in the current imports section below this comment vvv
# import xyz
# import xyz
# import xyz


# current imports
import board
import colorsys
import json
import math
import neopixel
import os
import platform
import psutil
import subprocess
import threading
import time
from datetime import datetime




# neopixel setup - don't change these throughout your code (yes, including the brightness)
LED_PIN = board.D18
LED_COUNT = 50
LED_BRIGHTNESS = 0.2
pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, brightness=LED_BRIGHTNESS, auto_write=False, pixel_order=neopixel.RGB)

# coordinates
# index 0 in the array is the position of LED 0.
# coordinates in the format [x,y], where x is horizontal with 0 being the far left, and where y is vertical with 0 being the top.
coordinates = [[281, 712], [198, 713], [164, 716], [111, 705], [57, 718], [72, 622], [0, 593], [65, 534], [62, 568], [104, 580], [152, 575], [229, 604], [256, 607], [333, 572], [342, 539], [360, 497], [340, 453], [320, 505], [280, 519], [244, 489], [189, 448], [114, 516], [58, 513], [48, 457], [82, 398], [95, 399], [117, 380], [212, 381], [230, 393], [278, 403], [312, 419], [320, 369], [342, 311], [268, 294], [282, 244], [257, 231], [216, 249], [174, 261], [150, 279], [78, 301], [135, 244], [89, 170], [132, 147], [111, 142], [156, 155], [230, 174], [237, 166], [270, 112], [208, 91], [192, 0]]




# ------------------------------------------------- #
#  !! WRITE YOUR PROGRAM HERE INSIDE A FUNCTION !!  #
# ------------------------------------------------- #

def rainbow_up():
    for i in range(0, 720):
        for j in range(0,50):
            if coordinates[j][1] == 719-i:
                h = ((i / 720) * 360)
                s = 0.7
                l = 0.4
                c = (1 - abs(2*l - 1)) * s
                x = c * (1 - abs((h / 60) % 2 - 1))
                m = l - c / 2
                if 0 <= h < 60:
                    r, g, b = c, x, 0
                elif 60 <= h < 120:
                    r, g, b = x, c, 0
                elif 120 <= h < 180:
                    r, g, b = 0, c, x
                elif 180 <= h < 240:
                    r, g, b = 0, x, c
                elif 240 <= h < 300:
                    r, g, b = x, 0, c
                else:
                    r, g, b = c, 0, x
                r, g, b = (r + m) * 255, (g + m) * 255, (b + m) * 255
                pixels[j] = int(r), int(g), int(b)

    pixels.show()