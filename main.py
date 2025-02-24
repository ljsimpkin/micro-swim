import network
import urequests
import time
import random
from machine import Pin, PWM
from env import SSID_IPHONE, PASSWORD_IPHONE, SSID_ANDROID, PASSWORD_ANDROID

# Setup PWM for RGB LED
RED = PWM(Pin(16))
GREEN = PWM(Pin(17))
BLUE = PWM(Pin(18))

# Setup onboard LED
ONBOARD_LED = Pin("LED", Pin.OUT)

# Set PWM frequency
RED.freq(1000)
GREEN.freq(1000)
BLUE.freq(1000)

# Function to set RGB LED color (0-65535 brightness)
def set_color(r, g, b):
    RED.duty_u16(r)
    GREEN.duty_u16(g)
    BLUE.duty_u16(b)

# Function for disco mode (flashes random colors)
def disco_mode(duration=5):
    start_time = time.time()
    while time.time() - start_time < duration:
        set_color(random.randint(0, 65535), random.randint(0, 65535), random.randint(0, 65535))
        time.sleep(0.2)

# Function to connect to Wi-Fi with error handling
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Try Android credentials first, then iPhone
    credentials = [
        (SSID_ANDROID, PASSWORD_ANDROID),
        (SSID_IPHONE, PASSWORD_IPHONE)
    ]
    
    for ssid, password in credentials:
        print(f"Trying to connect to {ssid}...")
        wlan.connect(ssid, password)
        
        timeout = 10  # Max time to wait for connection
        while not wlan.isconnected() and timeout > 0:
            print("Waiting for connection...")
            ONBOARD_LED.toggle()  # Flash onboard LED
            time.sleep(1)
            timeout -= 1
            
        if wlan.isconnected():
            print(f"Connected to {ssid}! IP:", wlan.ifconfig()[0])
            ONBOARD_LED.on()  # Keep onboard LED ON when connected
            return True
            
        print(f"Failed to connect to {ssid}")
    
    print("Failed to connect to any network")
    ONBOARD_LED.off()
    return False
        
def monitor_wifi():
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True  # Stay ON if connected
    else:
        set_color(0, 0, 0)
        connect_wifi()  # Flash LED if disconnected

def check_bay(name):
    try:
        response = urequests.get("https://safeswim.org.nz/api/locations")
        if response.status_code != 200:
            print("Error: HTTP status code", response.status_code)
            response.close()
            set_color(0, 0, 0)  # Turn off LED on error
            return
        
        locations = response.json()
        response.close()
        
        quality = ""
        for location in locations["locations"]:
            if location.get("name") == name:
                quality = location["state"]["quality"]
        
        print(name, "is", quality)
        
        if quality == "RED":
            set_color(65535, 0, 0)  # Red
            print("LED: Red (0)")
        elif quality == "GREEN":
            set_color(0, 0, 65535)  # Green
            print("LED: Green (1)")
        elif quality == "BLACK":
            print("LED: BLACK")
            disco_mode()
        else:
            print("Unknown response")
            set_color(0, 0, 0)  # Turn off RGB LED in case of error

    except Exception as e:
        print("Error:", e)
        set_color(0, 0, 0)  # Turn off RGB LED in case of error

# Main Loop
if connect_wifi():  # Only run if connected
    while True:
        monitor_wifi()
        check_bay("Murrays Bay")
        time.sleep(5)  # Check every 5 seconds

