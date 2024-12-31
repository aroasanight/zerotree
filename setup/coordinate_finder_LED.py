import time
import board
import neopixel
import sys

# Configuration
LED_PIN = board.D18  # Pin 18
NUM_LEDS = 50  # Number of addressable LEDs
BRIGHTNESS = 0.2  # Brightness (0 to 1)

# Initialize the neopixel strip
pixels = neopixel.NeoPixel(LED_PIN, NUM_LEDS, brightness=BRIGHTNESS, auto_write=False)

def wait_for_enter():
    """Wait for the user to press Enter before continuing."""
    print("Press Enter to continue to the next LED...")
    input()

def main():
    led_index = 0  # Start from the first LED
    while True:
        # Turn on the current LED to white
        pixels[led_index] = (255, 255, 255)  # White color
        pixels.show()

        # Wait for the user to press Enter
        wait_for_enter()

        # Turn off the current LED
        pixels[led_index] = (0, 0, 0)  # Off
        pixels.show()

        # Move to the next LED
        led_index += 1
        if led_index >= NUM_LEDS:
            led_index = 0  # Loop back to the first LED

if __name__ == "__main__":
    main()
