#region SETUP
import board
import colorsys
import json
import math
import neopixel
import os
import platform
import psutil
import random
import RPi.GPIO as GPIO
import subprocess
import threading
import time
from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify


pixelsPin = board.D18
pixelsCount = 50
pixelsBrightness = 0.2                                                                      # neopixel.RGB otherwise they're in GRB format
pixels = neopixel.NeoPixel(pixelsPin, pixelsCount, brightness=pixelsBrightness, auto_write=False, pixel_order=neopixel.RGB)

powerButtonPin = 17
modeButtonPin = 27
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setup(powerButtonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(modeButtonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

app = Flask(__name__)


power = True
tempBrightness = pixelsBrightness
sleepTimes = {"weekdays": {"startTime": "00:00", "endTime": "00:00"}, "weekends": {"startTime": "00:00", "endTime": "00:00"}}
selectedMode = 0
interruptMode = 0
booCoords = [170, 400]
booHue = 0.005
coordinates = [[281, 712], [198, 713], [164, 716], [111, 705], [57, 718], [72, 622], [0, 593], [65, 534], [62, 568], [104, 580], [152, 575], [229, 604], [256, 607], [333, 572], [342, 539], [360, 497], [340, 453], [320, 505], [280, 519], [244, 489], [189, 448], [114, 516], [58, 513], [48, 457], [82, 398], [95, 399], [117, 380], [212, 381], [230, 393], [278, 403], [312, 419], [320, 369], [342, 311], [268, 294], [282, 244], [257, 231], [216, 249], [174, 261], [150, 279], [78, 301], [135, 244], [89, 170], [132, 147], [111, 142], [156, 155], [230, 174], [237, 166], [270, 112], [208, 91], [192, 0]]
# 11 - [152, 575]
# 21 - [189, 448]
# avg - 170, 500

customColor = {"r": 255, "g": 0, "b": 0}  # Default to red

lastSleepState = False

#endregion
#region FUNCTIONS

# sleep mode times are persistant
def saveSleepTimes():
    with open('settings/sleep_times.json', 'w') as file:
        json.dump(sleepTimes, file, indent=4)

def loadSleepTimes():
    global sleepTimes
    try:
        with open('settings/sleep_times.json', 'r') as file:
            sleepTimes = json.load(file)
    except FileNotFoundError:
        sleepTimes = {
            "weekdays": {"startTime": "00:00", "endTime": "00:00"},
            "weekends": {"startTime": "00:00", "endTime": "00:00"}
        }
        saveSleepTimes()

def sleepTimeCheck():
    now = datetime.now()
    currentTime = now.strftime("%H:%M")
    dayOfWeek = now.weekday()  # 0 = monday, 6 = sunday
    
    if dayOfWeek < 4:  # monday through tuesday (morning time AND evening time follow weekdays)
        startTime = datetime.strptime(sleepTimes["weekdays"]["startTime"], "%H:%M").time()
        endTime = datetime.strptime(sleepTimes["weekdays"]["endTime"], "%H:%M").time()
    elif dayOfWeek == 5:  # friday (morning time follows weekdays, evening time follows weekends)
        startTime = datetime.strptime(sleepTimes["weekdays"]["startTime"], "%H:%M").time()
        endTime = datetime.strptime(sleepTimes["weekends"]["endTime"], "%H:%M").time()
    elif dayOfWeek == 6:  # saturday (morning time AND evening time follow weekends)
        startTime = datetime.strptime(sleepTimes["weekends"]["startTime"], "%H:%M").time()
        endTime = datetime.strptime(sleepTimes["weekends"]["endTime"], "%H:%M").time()
    else:  # sunday (morning time follows weekends, evening time follows weekdays)
        startTime = datetime.strptime(sleepTimes["weekends"]["startTime"], "%H:%M").time()
        endTime = datetime.strptime(sleepTimes["weekdays"]["endTime"], "%H:%M").time()

    currentTimeObject = datetime.strptime(currentTime, "%H:%M").time()

    if startTime <= endTime: # both times are on the same day
        if startTime <= currentTimeObject and currentTimeObject <= endTime: return True
        else: return False
    else: # times go overnight
        if currentTimeObject >= startTime or currentTimeObject <= endTime: return True
        else: return False


# ...and so is the last used mode
def saveSelectedMode():
    """Save the selected mode to a JSON file."""
    with open('settings/selected_mode.json', 'w') as file:
        json.dump({"selected": selectedMode}, file)

def loadSelectedMode():
    """Load the selected mode from a JSON file."""
    global selectedMode
    try:
        with open('settings/selected_mode.json', 'r') as file:
            selectedData = json.load(file)
            selectedMode = selectedData.get("selected", 0)
    except FileNotFoundError:
        saveSelectedMode()

def saveCustomColor():
    with open('settings/custom_color.json', 'w') as file:
        json.dump(customColor, file)

def loadCustomColor():
    global customColor
    try:
        with open('settings/custom_color.json', 'r') as file:
            customColor = json.load(file)
    except FileNotFoundError:
        saveCustomColor()

#endregion
#region MODES FUNCS

class LEDMode:
    def __init__(self, mode_function):
        self.mode_function = mode_function
        self._running = False
        self._paused = False
        self._thread = None

    def start(self):
        if not self._running:
            self._running = True
            self._paused = False
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()

    def run(self):
        while self._running:
            if (self._paused) or (not power):
                time.sleep(0.1)
                pixels.fill((0,0,0))
                pixels.show()
                continue
            self.mode_function()

    def stop(self):
        self._running = False
        if self._thread: self._thread.join()

    def pause(self): self._paused = True
    def resume(self): self._paused = False

def modeBreakCheck():
    global interruptMode
    if selectedMode != interruptMode:
        interruptMode = selectedMode
        return(True)
    elif not power: return(True)
    elif sleepTimeCheck(): return(True)
    else: return(False)

# Helper function to get custom color tuple
def getCustomColor():
    return (customColor["r"], customColor["g"], customColor["b"])

# --------------------------------- #
# [        !!   MODES   !!        ] #
# --------------------------------- #

#endregion
#region MGRP solid colours
def solidRed():
    pixels.fill((255, 0, 0))
    pixels.show()
    time.sleep(0.1)

def solidOrange():
    pixels.fill((255, 75, 0))
    pixels.show()
    time.sleep(0.1)

def solidYellow():
    pixels.fill((255, 200, 0))
    pixels.show()
    time.sleep(0.1)

def solidGreen():
    pixels.fill((0, 255, 0))
    pixels.show()
    time.sleep(0.1)

def solidCyan():
    pixels.fill((0, 255, 105))
    pixels.show()
    time.sleep(0.1)

def solidLightBlue():
    pixels.fill((0, 170, 255))
    pixels.show()
    time.sleep(0.1)

def solidBlue():
    pixels.fill((0, 0, 255))
    pixels.show()
    time.sleep(0.1)

def solidPurple():
    pixels.fill((140, 0, 255))
    pixels.show()
    time.sleep(0.1)

def solidMagenta():
    pixels.fill((255, 0, 255))
    pixels.show()
    time.sleep(0.1)

def solidPink():
    pixels.fill((255, 0, 140))
    pixels.show()
    time.sleep(0.1)

def solidPink2():
    pixels.fill((255, 0, 140))
    pixels.show()
    time.sleep(1)
    pixels.fill((5, 0, 140))
    pixels.show()
    time.sleep(1)
    pixels.fill((255, 0, 10))
    pixels.show()
    time.sleep(1)


#endregion
#region MGRP test modes
def cycleColours():
    colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    for colour in colours:
        if modeBreakCheck(): break
        pixels.fill(colour)
        pixels.show()
        time.sleep(0.5)

def rgbChase():
    for i in range(0,50):
        if modeBreakCheck(): break
        pixels.fill((0,0,0))
        pixels[i] = ((255,0,0))
        pixels.show()
        time.sleep(0.2)
        pixels[i] = ((0,255,0))
        pixels.show()
        time.sleep(0.2)
        pixels[i] = ((0,0,255))
        pixels.show()
        time.sleep(0.2)


#endregion
#region MGRP stand up maths
def standUpRotate():
    center_x = sum(x[0] for x in coordinates) / len(coordinates)
    center_y = sum(x[1] for x in coordinates) / len(coordinates)

    hue = 0.0
    for i in range(0,2):
        for angle in range(0, 3600, 36):
            if modeBreakCheck(): break
            for i in range(pixelsCount):
                x, y = coordinates[i]

                dx = x - center_x
                dy = y - center_y
                
                new_x = center_x + dx * math.cos(math.radians(angle/10)) - dy * math.sin(math.radians(angle/10))

                if new_x < center_x:
                    colour = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                else:
                    complementary_hue = (hue + 0.5) % 1.0 
                    colour = colorsys.hsv_to_rgb(complementary_hue, 1.0, 1.0)

                pixels[i] = tuple(int(c * 255) for c in colour)

            pixels.show()
            hue += 0.005
            if hue > 1.0:
                hue = 0.0 
            time.sleep(0.05)


#endregion
#region MGRP SUM Insp
def booCircle():
    global booHue

    for radius in range(0,500,3):
        if booHue > 1.0:
            booHue = 0.0
        booHue += 0.005
        pixels.fill((0,0,0))
        for j in range(0,50):
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < (radius**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > ((radius-80)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
        if modeBreakCheck(): break
        pixels.show()
    for radius in range(500,0,-3):
        if booHue > 1.0:
            booHue = 0.0
        booHue += 0.005
        pixels.fill((0,0,0))
        for j in range(0,50):
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < (radius**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > ((radius-80)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
        if modeBreakCheck(): break
        pixels.show()
    for i in range(0,2):
        for radius in range(0,500,8):
            if booHue > 1.0:
                booHue = 0.0
            booHue += 0.005
            pixels.fill((0,0,0))
            for j in range(0,50):
                if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < (radius**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > ((radius-120)**2):
                    pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if modeBreakCheck(): break
            pixels.show()
        for radius in range(500,0,-8):
            if booHue > 1.0:
                booHue = 0.0
            booHue += 0.005
            pixels.fill((0,0,0))
            for j in range(0,50):
                if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < (radius**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > ((radius-120)**2):
                    pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if modeBreakCheck(): break
            pixels.show()

def booRadioOut():
    global booHue

    for radius in range(0,600,2):
        if booHue > 1.0:
            booHue = 0.0
        booHue += 0.005
        pixels.fill((0,0,0))
        for j in range(0,50):
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius+600)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)+600)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius+300)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)+300)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius+000)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)+000)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius-300)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)-300)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius-600)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)-600)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
        if modeBreakCheck(): break
        pixels.show()

def booRadioIn():
    global booHue

    for radius in range(600,0,-2):
        if booHue > 1.0:
            booHue = 0.0
        booHue += 0.005
        pixels.fill((0,0,0))
        for j in range(0,50):
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius+600)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)+600)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius+300)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)+300)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius+000)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)+000)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius-300)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)-300)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((radius-600)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((radius-80)-600)**2):
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
        if modeBreakCheck(): break
        pixels.show()

def booSinBounce():
    global booHue

    for sinIn in range(0,360):
        if booHue > 1.0:
            booHue = 0.0
        booHue += 0.01
        if modeBreakCheck(): break
        r = math.sin(sinIn)
        if r<0:r=0-math.sqrt(abs(r*225))/225
        r = ((r+0.15)/1.15)
        pixels.fill((0,0,0))
        for j in range(0,50):
            if ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) < ((r*300)**2) and ((coordinates[j][0]-booCoords[0])**2) + ((coordinates[j][1]-booCoords[1])**2) > (((r*300)-100)**2):
                # pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue,1.0,1.0)))
                pixels[j] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue+(j*0.004),0.9,1.0)))
        pixels.show()
        time.sleep(0.05)

        

def gameOfLife():
    global booHue
    pixelsOn = []
    for i in range(0,50):
        pixelsOn.append(random.randint(0,1))

    newPixelsOn = pixelsOn
    
    while True:
        pixelsOn = newPixelsOn
        for i in range(0,400):
            if booHue > 1.0:
                booHue = 0.0
            booHue += 0.01
            if modeBreakCheck(): break
            pixels.fill((0,0,0))
            for i in range(0,50):
                nextIndex = i+1
                lastIndex = i-1
                if nextIndex >= 50:
                    nextIndex = 0
                if lastIndex < 0:
                    lastIndex = 49
                if pixelsOn[i] == 1:
                    pixels[i] = tuple(int(c * 255) for c in (colorsys.hsv_to_rgb(booHue+(i*0.004),0.9,1.0)))
                    # pixels[i] = ((255,0,200))
                    if pixelsOn[lastIndex] == pixelsOn[nextIndex]:
                        newPixelsOn[i] = 0
                    else:
                        newPixelsOn[i] = 1
                else:
                    if pixelsOn[lastIndex] == pixelsOn[nextIndex]:
                    # if pixelsOn[lastIndex] == 1 and pixelsOn[nextIndex] == 1:
                        newPixelsOn[i] = 1
                    else:
                        newPixelsOn[i] = 0
            pixels.show()
            time.sleep(0.4)
                
                

#endregion
#region MGRP static
def spectrumHorizontal():
    for i in range(0, 365):
        for j in range(0,50):
            if coordinates[j][0] == 364-i:
                h = ((i / 365) * 360)
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

def spectrumVertical():
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


#endregion
#region MGRP christmas ROGB

def christmasTypical():
    for i in range(0,50):
        if i%4 == 0:
            pixels[i] = ((255,0,0))
        if i%4 == 1:
            pixels[i] = ((255,100,0))
        if i%4 == 2:
            pixels[i] = ((0,255,0))
        if i%4 == 3:
            pixels[i] = ((0,90,255))
    pixels.show()
    time.sleep(0.1)

def christmasInWaves():
    for j in range(0,100):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((round((255/100)*j),round((100/100)*j),0))
            if i%4 == 1:
                pixels[i] = ((round(255-((255/100)*j)),0,0))
            if i%4 == 2:
                pixels[i] = ((0,round((90/100)*j),round((255/100)*j)))
            if i%4 == 3:
                pixels[i] = ((0,round(255-((255/100)*j)),0))
        pixels.show()
    for j in range(100,0,-1):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((round((255/100)*j),round((100/100)*j),0))
            if i%4 == 1:
                pixels[i] = ((round(255-((255/100)*j)),0,0))
            if i%4 == 2:
                pixels[i] = ((0,round((90/100)*j),round((255/100)*j)))
            if i%4 == 3:
                pixels[i] = ((0,round(255-((255/100)*j)),0))
        pixels.show()

def christmasSequential():
    for i in range(0,50):
        if i%4 == 0:
            pixels[i] = ((255,0,0))
        if i%4 == 1:
            pixels[i] = ((0,0,0))
        if i%4 == 2:
            pixels[i] = ((0,255,0))
        if i%4 == 3:
            pixels[i] = ((0,0,0))
    pixels.show()
    time.sleep(0.5)
    for i in range(0,50):
        if i%4 == 0:
            pixels[i] = ((0,0,0))
        if i%4 == 1:
            pixels[i] = ((255,100,0))
        if i%4 == 2:
            pixels[i] = ((0,0,0))
        if i%4 == 3:
            pixels[i] = ((0,90,255))
    pixels.show()
    time.sleep(0.5)

def christmasSloGo():
    for j in range(0,100):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((round((255/100)*j),round((100/100)*j),0))
            if i%4 == 1:
                pixels[i] = ((round(255-((255/100)*j)),0,0))
            if i%4 == 2:
                pixels[i] = ((0,round((90/100)*j),round((255/100)*j)))
            if i%4 == 3:
                pixels[i] = ((0,round(255-((255/100)*j)),0))
        pixels.show()
        time.sleep(0.1)
    for j in range(100,0,-1):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((round((255/100)*j),round((100/100)*j),0))
            if i%4 == 1:
                pixels[i] = ((round(255-((255/100)*j)),0,0))
            if i%4 == 2:
                pixels[i] = ((0,round((90/100)*j),round((255/100)*j)))
            if i%4 == 3:
                pixels[i] = ((0,round(255-((255/100)*j)),0))
        pixels.show()
        time.sleep(0.1)

def christmasChasing():
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((0,0,0))
            if i%4 == 1:
                pixels[i] = ((255,0,0))
            if i%4 == 2:
                pixels[i] = ((0,0,0))
            if i%4 == 3:
                pixels[i] = ((0,255,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((255,100,0))
            if i%4 == 1:
                pixels[i] = ((0,0,0))
            if i%4 == 2:
                pixels[i] = ((0,90,255))
            if i%4 == 3:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range(0,2):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((0,0,0))
            if i%4 == 1:
                pixels[i] = ((255,0,0))
            if i%4 == 2:
                pixels[i] = ((0,0,0))
            if i%4 == 3:
                pixels[i] = ((0,255,0))
        pixels.show()
        time.sleep(0.3)
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((255,100,0))
            if i%4 == 1:
                pixels[i] = ((0,0,0))
            if i%4 == 2:
                pixels[i] = ((0,90,255))
            if i%4 == 3:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.3)

def christmasSlowFade():
    for j in range(0,100):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((round((255/100)*j),round((100/100)*j),0))
            if i%4 == 1:
                pixels[i] = ((round((255/100)*j),0,0))
            if i%4 == 2:
                pixels[i] = ((0,round((90/100)*j),round((255/100)*j)))
            if i%4 == 3:
                pixels[i] = ((0,round((255/100)*j),0))
        pixels.show()
        time.sleep(0.1)
    for j in range(100,0,-1):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((round((255/100)*j),round((100/100)*j),0))
            if i%4 == 1:
                pixels[i] = ((round((255/100)*j),0,0))
            if i%4 == 2:
                pixels[i] = ((0,round((90/100)*j),round((255/100)*j)))
            if i%4 == 3:
                pixels[i] = ((0,round((255/100)*j),0))
        pixels.show()
        time.sleep(0.1)

def christmasTwinkle():
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((0,0,0))
            if i%4 == 1:
                pixels[i] = ((255,0,0))
            if i%4 == 2:
                pixels[i] = ((0,0,0))
            if i%4 == 3:
                pixels[i] = ((0,255,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%4 == 0:
                pixels[i] = ((255,100,0))
            if i%4 == 1:
                pixels[i] = ((0,0,0))
            if i%4 == 2:
                pixels[i] = ((0,90,255))
            if i%4 == 3:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)

#endregion
#region MGRP christmas White
warmWhite = [255,160,40]

def christmasWhiteTypical():
    pixels.fill((warmWhite[0],warmWhite[1],warmWhite[2]))
    pixels.show()
    time.sleep(0.1)

def christmasWhiteInWaves():
    for j in range(0,100):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((warmWhite[0]/150)*j),round((warmWhite[1]/150)*j),round((warmWhite[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(warmWhite[0]-((warmWhite[0]/150)*j)),round(warmWhite[1]-((warmWhite[1]/150)*j)),round(warmWhite[2]-((warmWhite[2]/150)*j))))
        pixels.show()
    for j in range(100,0,-1):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((warmWhite[0]/150)*j),round((warmWhite[1]/150)*j),round((warmWhite[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(warmWhite[0]-((warmWhite[0]/150)*j)),round(warmWhite[1]-((warmWhite[1]/150)*j)),round(warmWhite[2]-((warmWhite[2]/150)*j))))
        pixels.show()

def christmasWhiteSequential():
    for i in range(0,50):
        if i%2 == 0:
            pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
        if i%2 == 1:
            pixels[i] = ((0,0,0))
    pixels.show()
    time.sleep(0.5)
    for i in range(0,50):
        if i%2 == 0:
            pixels[i] = ((0,0,0))
        if i%2 == 1:
            pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
    pixels.show()
    time.sleep(0.5)

def christmasWhiteSloGo():
    for j in range(0,100):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((warmWhite[0]/150)*j),round((warmWhite[1]/150)*j),round((warmWhite[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(warmWhite[0]-((warmWhite[0]/150)*j)),round(warmWhite[1]-((warmWhite[1]/150)*j)),round(warmWhite[2]-((warmWhite[2]/150)*j))))
        pixels.show()
        time.sleep(0.1)
    for j in range(100,0,-1):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((warmWhite[0]/150)*j),round((warmWhite[1]/150)*j),round((warmWhite[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(warmWhite[0]-((warmWhite[0]/150)*j)),round(warmWhite[1]-((warmWhite[1]/150)*j)),round(warmWhite[2]-((warmWhite[2]/150)*j))))
        pixels.show()
        time.sleep(0.1)

def christmasWhiteChasing():
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
            if i%2 == 1:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((0,0,0))
            if i%2 == 1:
                pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range(0,2):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
            if i%2 == 1:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.3)
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((0,0,0))
            if i%2 == 1:
                pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
        pixels.show()
        time.sleep(0.3)

def christmasWhiteSlowFade():
    for j in range(0,100):
        if modeBreakCheck(): break
        pixels.fill((round((warmWhite[0]/150)*j),round((warmWhite[1]/150)*j),round((warmWhite[2]/150)*j)))
        pixels.show()
        time.sleep(0.1)
    for j in range(100,0,-1):
        if modeBreakCheck(): break
        pixels.fill((round((warmWhite[0]/150)*j),round((warmWhite[1]/150)*j),round((warmWhite[2]/150)*j)))
        pixels.show()
        time.sleep(0.1)

def christmasWhiteTwinkle():
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
            if i%2 == 1:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range (0,3):
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((0,0,0))
            if i%2 == 1:
                pixels[i] = ((warmWhite[0],warmWhite[1],warmWhite[2]))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)


#endregion
#region MGRP christmas White

def customChristmasTypical():
    custom_colour = getCustomColor()
    pixels.fill((custom_colour[0],custom_colour[1],custom_colour[2]))
    pixels.show()
    time.sleep(0.1)

def customChristmasInWaves():
    for j in range(0,100):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((custom_colour[0]/150)*j),round((custom_colour[1]/150)*j),round((custom_colour[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(custom_colour[0]-((custom_colour[0]/150)*j)),round(custom_colour[1]-((custom_colour[1]/150)*j)),round(custom_colour[2]-((custom_colour[2]/150)*j))))
        pixels.show()
    for j in range(100,0,-1):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((custom_colour[0]/150)*j),round((custom_colour[1]/150)*j),round((custom_colour[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(custom_colour[0]-((custom_colour[0]/150)*j)),round(custom_colour[1]-((custom_colour[1]/150)*j)),round(custom_colour[2]-((custom_colour[2]/150)*j))))
        pixels.show()

def customChristmasSequential():
    custom_colour = getCustomColor()
    for i in range(0,50):
        if i%2 == 0:
            pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
        if i%2 == 1:
            pixels[i] = ((0,0,0))
    pixels.show()
    time.sleep(0.5)
    for i in range(0,50):
        if i%2 == 0:
            pixels[i] = ((0,0,0))
        if i%2 == 1:
            pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
    pixels.show()
    time.sleep(0.5)

def customChristmasSloGo():
    for j in range(0,100):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((custom_colour[0]/150)*j),round((custom_colour[1]/150)*j),round((custom_colour[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(custom_colour[0]-((custom_colour[0]/150)*j)),round(custom_colour[1]-((custom_colour[1]/150)*j)),round(custom_colour[2]-((custom_colour[2]/150)*j))))
        pixels.show()
        time.sleep(0.1)
    for j in range(100,0,-1):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((round((custom_colour[0]/150)*j),round((custom_colour[1]/150)*j),round((custom_colour[2]/150)*j)))
            if i%2 == 1:
                pixels[i] = ((round(custom_colour[0]-((custom_colour[0]/150)*j)),round(custom_colour[1]-((custom_colour[1]/150)*j)),round(custom_colour[2]-((custom_colour[2]/150)*j))))
        pixels.show()
        time.sleep(0.1)

def customChristmasChasing():
    for j in range (0,3):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
            if i%2 == 1:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range (0,3):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((0,0,0))
            if i%2 == 1:
                pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range(0,2):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
            if i%2 == 1:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.3)
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((0,0,0))
            if i%2 == 1:
                pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
        pixels.show()
        time.sleep(0.3)

def customChristmasSlowFade():
    for j in range(0,100):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        pixels.fill((round((custom_colour[0]/150)*j),round((custom_colour[1]/150)*j),round((custom_colour[2]/150)*j)))
        pixels.show()
        time.sleep(0.1)
    for j in range(100,0,-1):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        pixels.fill((round((custom_colour[0]/150)*j),round((custom_colour[1]/150)*j),round((custom_colour[2]/150)*j)))
        pixels.show()
        time.sleep(0.1)

def customChristmasTwinkle():
    for j in range (0,3):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
            if i%2 == 1:
                pixels[i] = ((0,0,0))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)
    for j in range (0,3):
        custom_colour = getCustomColor()
        if modeBreakCheck(): break
        for i in range(0,50):
            if i%2 == 0:
                pixels[i] = ((0,0,0))
            if i%2 == 1:
                pixels[i] = ((custom_colour[0],custom_colour[1],custom_colour[2]))
        pixels.show()
        time.sleep(0.1)
        pixels.fill((0,0,0))
        pixels.show()
        time.sleep(0.1)


#endregion
#region MODES LIST

# Mode structure: [Group, Name, LEDMode, ShowInPhysicalButton, ShowInHA, IsCustomColorMode]
modes = [
    ["Solid Colours", "Red", LEDMode(solidRed), False, False, False],
    ["Solid Colours", "Orange", LEDMode(solidOrange), False, False, False],
    ["Solid Colours", "Yellow", LEDMode(solidYellow), False, False, False],
    ["Solid Colours", "Green", LEDMode(solidGreen), False, False, False],
    ["Solid Colours", "Cyan", LEDMode(solidCyan), False, False, False],
    ["Solid Colours", "Light blue", LEDMode(solidLightBlue), False, False, False],
    ["Solid Colours", "Blue", LEDMode(solidBlue), False, False, False],
    ["Solid Colours", "Purple", LEDMode(solidPurple), False, False, False],
    ["Solid Colours", "Magenta", LEDMode(solidMagenta), False, False, False],
    ["Solid Colours", "Pink", LEDMode(solidPink), False, False, False],
    ["Solid Colours", "Pink3", LEDMode(solidPink2), False, False, False],
    ["Test Modes", "Chase", LEDMode(rgbChase), False, False, False],
    ["Test Modes", "RGB cycle", LEDMode(cycleColours), False, False, False],
    ["SUM", "Rotate", LEDMode(standUpRotate), False, True, False],
    ["SUM Insp", "BCircle", LEDMode(booCircle), False, True, False],
    ["SUM Insp", "BRadio Out", LEDMode(booRadioOut), False, True, False],
    ["SUM Insp", "BRadio In", LEDMode(booRadioIn), False, True, False],
    ["SUM Insp", "BSinBounce", LEDMode(booSinBounce), False, True, False],
    ["SUM Insp", "CGoL", LEDMode(gameOfLife), False, True, False],
    ["Static", "Rainbow across", LEDMode(spectrumHorizontal), False, True, False],
    ["Static", "Rainbow up", LEDMode(spectrumVertical), False, True, False],
    ["Christmas Typical (ROGB)", "Steady on", LEDMode(christmasTypical), True, True, False],
    ["Christmas Typical (ROGB)", "In waves", LEDMode(christmasInWaves), True, True, False],
    ["Christmas Typical (ROGB)", "Sequential", LEDMode(christmasSequential), True, True, False],
    ["Christmas Typical (ROGB)", "Slo go", LEDMode(christmasSloGo), True, True, False],
    ["Christmas Typical (ROGB)", "Chasing/flash", LEDMode(christmasChasing), True, True, False],
    ["Christmas Typical (ROGB)", "Slow fade", LEDMode(christmasSlowFade), True, True, False],
    ["Christmas Typical (ROGB)", "Twinkle/flash", LEDMode(christmasTwinkle), True, True, False],
    ["Christmas Typical (White)", "Steady on", LEDMode(christmasWhiteTypical), False, False, False],
    ["Christmas Typical (White)", "In waves", LEDMode(christmasWhiteInWaves), False, False, False],
    ["Christmas Typical (White)", "Sequential", LEDMode(christmasWhiteSequential), False, False, False],
    ["Christmas Typical (White)", "Slo go", LEDMode(christmasWhiteSloGo), False, False, False],
    ["Christmas Typical (White)", "Chasing/flash", LEDMode(christmasWhiteChasing), False, False, False],
    ["Christmas Typical (White)", "Slow fade", LEDMode(christmasWhiteSlowFade), False, False, False],
    ["Christmas Typical (White)", "Twinkle/flash", LEDMode(christmasWhiteTwinkle), False, False, False],
    # NEW: Custom color modes for HA
    ["Christmas Custom", "HASteady on", LEDMode(customChristmasTypical), False, True, True],
    ["Christmas Custom", "HAIn waves", LEDMode(customChristmasInWaves), False, True, True],
    ["Christmas Custom", "HASequential", LEDMode(customChristmasSequential), False, True, True],
    ["Christmas Custom", "HASlo go", LEDMode(customChristmasSloGo), False, True, True],
    ["Christmas Custom", "HAChasing/flash", LEDMode(customChristmasChasing), False, True, True],
    ["Christmas Custom", "HASlow fade", LEDMode(customChristmasSlowFade), False, True, True],
    ["Christmas Custom", "HATwinkle/flash", LEDMode(customChristmasTwinkle), False, True, True],
]

#endregion
#region ROUTES files
@app.route('/')
def serveHTML():
    return send_from_directory('.', 'controlpanel/index.html')

@app.route('/style.css')
def serveCSS():
    return send_from_directory('.', 'controlpanel/style.css')

@app.route('/script.js')
def serveJS():
    return send_from_directory('.', 'controlpanel/script.js')

@app.route('/favicon.ico')
def serveFavicon():
    return send_from_directory('.', 'controlpanel/favicon.ico')


#endregion
#region ROUTES home assistant
@app.route('/api/ha/post/toggle-power', methods=['POST'])
def postHATogglePower():
    global power
    power = not power
    if not power:
        pixels.fill((0, 0, 0))
        pixels.show()
    return jsonify({"power": power})

# home assistant 0-255 range instead of 0-100
@app.route('/api/ha/post/new-brightness', methods=['POST'])
def postHASetBrightness():
    global tempBrightness
    brightnessValue = max(0, min(100, round(int(request.json.get("brightness", 100))/2.55)))
    tempBrightness = brightnessValue / 100
    pixels.brightness = tempBrightness
    pixels.show()
    return jsonify({"brightness": tempBrightness})

@app.route('/api/ha/post/new-color', methods=['POST'])
def postHASetColor():
    global customColor
    r = max(0, min(255, int(request.json.get("r", 255))))
    g = max(0, min(255, int(request.json.get("g", 0))))
    b = max(0, min(255, int(request.json.get("b", 0))))
    
    customColor = {"r": r, "g": g, "b": b}
    saveCustomColor()
    
    return jsonify(customColor)

# NEW: Set mode from HA (using mode index or effect name)
@app.route('/api/ha/post/new-mode', methods=['POST'])
def postHASetMode():
    global selectedMode
    global power
    
    try:
        # Support both index and effect name
        modeValue = request.json.get("mode")
        
        if isinstance(modeValue, int):
            selectedValue = modeValue
        else:
            # Find mode by name
            selectedValue = None
            for index, mode in enumerate(modes):
                if mode[4] and mode[1] == modeValue:  # mode[4] is ShowInHA
                    selectedValue = index
                    break
            
            if selectedValue is None:
                return jsonify({"error": "Mode not found"}), 400
        
        if 0 <= selectedValue < len(modes) and modes[selectedValue][4]:
            toggleNow = power
            if toggleNow: power = False
            for mode in modes: mode[2].stop()
            selectedMode = selectedValue
            modes[selectedMode][2].start()
            if toggleNow: power = True
            saveSelectedMode()
            return jsonify({
                "selected": selectedMode,
                "mode": modes[selectedMode][1],
                "isCustomColor": modes[selectedMode][5]
            })
        else:
            return jsonify({"error": "Invalid mode"}), 400
            
    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/ha/get/modes', methods=['GET'])
def getHAModes():
    # Return only modes that should show in HA (mode[4] == True)
    haModes = []
    for index, mode in enumerate(modes):
        if mode[4]:  # ShowInHA
            haModes.append({
                "index": index,
                "group": mode[0],
                "name": mode[1],
                "isCustomColor": mode[5]
            })
    
    # Also return as pipe-separated string for backwards compatibility
    modesString = "|".join([f"{m['index']} - {m['name']}" for m in haModes])
    
    return jsonify({
        "modes": haModes,
        "modesString": modesString,
        "effectList": [m['name'] for m in haModes]
    })

# settings for home assistant since it doesn't need sleep times, and needs brightness in 0-255 instead of 0-100 like a normal person
@app.route('/api/ha/get/settings', methods=['GET'])
def getHASettings():
    currentModeDescription = str(modes[selectedMode][1])
    isCustomColorMode = modes[selectedMode][5]
    
    return jsonify({
        "selectedMode": interruptMode,
        "currentModeDescription": currentModeDescription,
        "HAMode": str(f"{interruptMode} - {currentModeDescription}"),
        "brightness": max(min(round(tempBrightness * 255), 255), 0),
        "power": power,
        "isSleeping": sleepTimeCheck(),
        "customColor": customColor,
        "isCustomColorMode": isCustomColorMode,
        "effect": currentModeDescription
    })


#endregion
#region ROUTES post api
@app.route('/api/post/toggle-power', methods=['POST'])
def postTogglePower():
    global power
    power = not power
    if not power:
        pixels.fill((0, 0, 0))
        pixels.show()
    return jsonify({"power": power})

@app.route('/api/post/restart-service', methods=['POST'])
def postRestartService():
    """API endpoint to restart the service."""
    try:
        subprocess.run(["sudo", "systemctl", "restart", "flaskapp.service"], check=True)
        return jsonify({"status": "success", "message": "Service restarted successfully"})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": f"Failed to restart service: {str(e)}"}), 500

@app.route('/api/post/new-brightness', methods=['POST'])
def postSetBrightness():
    global tempBrightness
    brightnessValue = max(0, min(100, int(request.json.get("brightness", 100))))
    tempBrightness = brightnessValue / 100
    pixels.brightness = tempBrightness
    pixels.show()
    return jsonify({"brightness": tempBrightness})

@app.route('/api/post/new-sleep-times', methods=['POST'])
def postSetSleepTimes():
    global sleepTimes
    weekdays = request.json.get("weekdays", {})
    weekends = request.json.get("weekends", {})

    sleepTimes["weekdays"] = {
        "startTime": weekdays.get("startTime", "00:00"),
        "endTime": weekdays.get("endTime", "00:00")
    }
    sleepTimes["weekends"] = {
        "startTime": weekends.get("startTime", "00:00"),
        "endTime": weekends.get("endTime", "00:00")
    }

    saveSleepTimes()

    return jsonify(sleepTimes)

@app.route('/api/post/new-mode', methods=['POST'])
def postSetMode():
    global selectedMode
    global power
    try:
        selectedValue = int(request.json.get("selected", 0))
        if 0 <= selectedValue and selectedValue < len(modes):
            toggleNow = power
            if toggleNow: power = False
            for mode in modes: mode[2].stop() # stop all modes
            selectedMode = selectedValue
            modes[selectedMode][2].start() # start the new mode
            if toggleNow: power = True
            saveSelectedMode()
            return jsonify({"selected": selectedMode, "mode": selectedMode})

        else: return jsonify({"error": "Invalid selection"}), 400
    except ValueError: return jsonify({"error": "Invalid data"}), 400


#endregion
#region ROUTES get api
@app.route('/api/get/modes', methods=['GET'])
def getModes():
    newModes = []
    for mode in modes: newModes.append([mode[0],mode[1]]) # filter out LEDMode objects and true/false (send only name and group)
    return jsonify(newModes)

@app.route('/api/get/settings', methods=['GET'])
def getSettings():
    currentModeDescription = str(modes[selectedMode][1])
    return jsonify({
        "selectedMode": interruptMode,
        "currentModeDescription": currentModeDescription,
        "brightness": int(tempBrightness * 100),
        "sleepTimes": sleepTimes,
        "power": power,
        "customColor": customColor
    })

@app.route('/api/get/system-info', methods=['GET'])
def getSystemInfo():
    uptime = float(os.popen('awk \'{print $1}\' /proc/uptime').read().split()[0])
    uptimeHours = int(uptime // 3600)
    uptimeMinutes = int((uptime % 3600) // 60)
    uptimeString = f"{uptimeHours} hours, {uptimeMinutes} minutes"

    try: cpuTemp = psutil.sensors_temperatures()['cpu_thermal'][0].current
    except: cpuTemp = "Unavailable"

    hostname = str(platform.node())
    osInfo = str(platform.system() + " " + platform.release())

    currentTime = datetime.now().strftime("%Y.%m.%d at %H:%M:%S")

    return jsonify({
        'uptime': uptimeString,
        'cpuTemperature': cpuTemp,
        'device': f"{hostname} ({osInfo})",
        'currentTime': currentTime
    })


#endregion
#region BUTTON POLLING
def buttonPolling():
    global power
    global selectedMode

    powerButtonPrevious = GPIO.input(powerButtonPin)
    modeButtonPrevious = GPIO.input(modeButtonPin)

    while True:
        powerButtonCurrent = GPIO.input(powerButtonPin)
        modeButtonCurrent = GPIO.input(modeButtonPin)

        if powerButtonPrevious == GPIO.HIGH and powerButtonCurrent == GPIO.LOW:
            power = not power
            if not power:
                pixels.fill((0, 0, 0))
                pixels.show()
            print(f"Power toggled: {power}")

        if modeButtonPrevious == GPIO.HIGH and modeButtonCurrent == GPIO.LOW:
            cyclableModes = []
            newMode = selectedMode + 1
            for index, mode in enumerate(modes):
                if mode[3]:
                    cyclableModes.append(index)

            while newMode != selectedMode:
                if newMode in cyclableModes:
                    selectedMode = newMode
                    toggleNow = power
                    if toggleNow: power = False
                    for mode in modes: mode[2].stop() # stop all modes
                    selectedMode = newMode
                    modes[selectedMode][2].start() # start the new mode
                    if toggleNow: power = True
                    saveSelectedMode()
                    break
                elif newMode > max(cyclableModes):
                    newMode = 0
                else:
                    newMode += 1

        powerButtonPrevious = powerButtonCurrent
        modeButtonPrevious = modeButtonCurrent

        time.sleep(0.05)

def sleepTimerMonitoring():
    global power
    global lastSleepState
    
    while True:
        currentSleepState = sleepTimeCheck()
        
        # Entering sleep period - turn off
        if currentSleepState and not lastSleepState:
            if power:  # Only turn off if currently on
                power = False
                pixels.fill((0, 0, 0))
                pixels.show()
                print("Sleep timer: Turning off")
        
        # Exiting sleep period - turn on
        elif not currentSleepState and lastSleepState:
            if not power:  # Only turn on if currently off
                power = True
                print("Sleep timer: Turning on")
        
        lastSleepState = currentSleepState
        time.sleep(60)  # Check every minute


#endregion
#region init
loadSleepTimes()
loadSelectedMode()
loadCustomColor()
pollingThread = threading.Thread(target=buttonPolling, daemon=True)
pollingThread.start()
sleepTimerThread = threading.Thread(target=sleepTimerMonitoring, daemon=True)
sleepTimerThread.start()
modes[selectedMode][2].start()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
    # please keep debug=False i spent literal hours trying to find out why the program was starting double or not at all, turns out debug=True causes that
#endregion
