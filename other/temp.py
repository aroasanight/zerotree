import board
import colorsys
import json
import math
import neopixel
import os
import platform
import psutil
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
GPIO.setmode(GPIO.BCM)
GPIO.setup(powerButtonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(modeButtonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

app = Flask(__name__)


power = True
tempBrightness = pixelsBrightness
sleepTimes = {"weekdays": {"startTime": "00:00", "endTime": "00:00"}, "weekends": {"startTime": "00:00", "endTime": "00:00"}}
selectedMode = 0
interruptMode = 0
coordinates = [[281, 712], [198, 713], [164, 716], [111, 705], [57, 718], [72, 622], [0, 593], [65, 534], [62, 568], [104, 580], [152, 575], [229, 604], [256, 607], [333, 572], [342, 539], [360, 497], [340, 453], [320, 505], [280, 519], [244, 489], [189, 448], [114, 516], [58, 513], [48, 457], [82, 398], [95, 399], [117, 380], [212, 381], [230, 393], [278, 403], [312, 419], [320, 369], [342, 311], [268, 294], [282, 244], [257, 231], [216, 249], [174, 261], [150, 279], [78, 301], [135, 244], [89, 170], [132, 147], [111, 142], [156, 155], [230, 174], [237, 166], [270, 112], [208, 91], [192, 0]]


# button stuff
def buttonFunctionTogglePower():
    global power
    power = not power
    if not power:
        pixels.fill((0, 0, 0))
        pixels.show()

def buttonFunctionCycleMode(channel):
    global selectedMode
    active_modes = [i for i, mode in enumerate(modes) if mode[3]]  # List of active modes
    if not active_modes:
        print("No active modes to cycle.")
        return
    current_index = active_modes.index(selectedMode) if selectedMode in active_modes else -1
    next_index = (current_index + 1) % len(active_modes)
    next_mode = active_modes[next_index]
    for mode in modes:
        mode[2].stop()
    selectedMode = next_mode
    modes[selectedMode][2].start()

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
            if (self._paused) or (not power) or (sleepTimeCheck()):
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


# --------------------------------- #
# [        !!   MODES   !!        ] #
# --------------------------------- #

# solid colours
def solidRed():
    pixels.fill((255, 0, 0))
    pixels.show()
    time.sleep(0.1)

def solidOrange():
    pixels.fill((255, 175, 0))
    pixels.show()
    time.sleep(0.1)

# insert other modes here...

modes = [
    ["Solid Colours", "Red", LEDMode(solidRed), False],
    ["Solid Colours", "Orange", LEDMode(solidOrange), False],
    ["Solid Colours", "Yellow", LEDMode(solidYellow), False],
    ["Solid Colours", "Green", LEDMode(solidGreen), False],
    ["Solid Colours", "Turquoise", LEDMode(solidCyan), False],
    ["Solid Colours", "Light blue", LEDMode(solidLightBlue), False],
    ["Solid Colours", "Blue", LEDMode(solidBlue), False],
    ["Solid Colours", "Purple", LEDMode(solidPurple), False],
    ["Solid Colours", "Pink", LEDMode(solidPink), False],
    ["Solid Colours", "Magenta", LEDMode(solidMagenta), False],
    ["Test Modes", "Chase", LEDMode(rgbChase), False],
    ["Test Modes", "RGB cycle", LEDMode(cycleColours), False],
    ["StandUpMaths", "Rotate", LEDMode(standUpRotate), False],
    ["Static", "Rainbow across", LEDMode(spectrumHorizontal), False],
    ["Static", "Rainbow up", LEDMode(spectrumVertical), False],
    ["Christmas Typical (ROBG)", "Steady on", LEDMode(christmasTypical), True],
    ["Christmas Typical (ROBG)", "In waves", LEDMode(christmasInWaves), True],
    ["Christmas Typical (ROBG)", "Sequential", LEDMode(christmasSequential), True],
    ["Christmas Typical (ROBG)", "Slo go", LEDMode(christmasSloGo), True],
    ["Christmas Typical (ROBG)", "Chasing/flash", LEDMode(christmasChasing), True],
    ["Christmas Typical (ROBG)", "Slow fade", LEDMode(christmasSlowFade), True],
    ["Christmas Typical (ROBG)", "Twinkle/flash", LEDMode(christmasTwinkle), True],
    ["Christmas Typical (White)", "Steady on", LEDMode(christmasWhiteTypical), False],
    ["Christmas Typical (White)", "In waves", LEDMode(christmasWhiteInWaves), False],
    ["Christmas Typical (White)", "Sequential", LEDMode(christmasWhiteSequential), False],
    ["Christmas Typical (White)", "Slo go", LEDMode(christmasWhiteSloGo), False],
    ["Christmas Typical (White)", "Chasing/flash", LEDMode(christmasWhiteChasing), False],
    ["Christmas Typical (White)", "Slow fade", LEDMode(christmasWhiteSlowFade), False],
    ["Christmas Typical (White)", "Twinkle/flash", LEDMode(christmasWhiteTwinkle), False],
]


# file routes
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


# api routes (post)
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
        # Restart the service (this is just an example, modify for your specific service)
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
            if power: toggleNow = True
            if toggleNow: power = False
            for mode in modes: mode[2].stop() # stop all modes
            selectedMode = selectedValue
            modes[selectedMode][2].start() # start the new mode
            if toggleNow: power = True
            saveSelectedMode()
            return jsonify({"selected": selectedMode, "mode": selectedMode})
        
        else: return jsonify({"error": "Invalid selection"}), 400
    except ValueError: return jsonify({"error": "Invalid data"}), 400


# api routes (get)
@app.route('/api/get/modes', methods=['GET'])
def getModes():
    newModes = []
    for mode in modes: newModes.append([mode[0],mode[1]]) # filter out LEDMode objects (send only name and group)
    return jsonify(newModes)

@app.route('/api/get/settings', methods=['GET'])
def getSettings():
    currentModeDescription = str(modes[selectedMode][1])
    return jsonify({
        "selectedMode": interruptMode,
        "currentModeDescription": currentModeDescription,
        "brightness": int(tempBrightness * 100),
        "sleepTimes": sleepTimes,
        "power": power
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



# init
loadSleepTimes()
loadSelectedMode()
modes[selectedMode][2].start()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
    # please keep debug=False i spent literal hours trying to find out why the program was starting double or not at all, turns out debug=True causes that