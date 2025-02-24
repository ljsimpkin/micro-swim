# Safeswim Bay Monitor

A MicroPython project for Raspberry Pi Pico that monitors swimming conditions at Auckland Bays using the Safeswim API and displays the status via an RGB LED.

## Features

- Real-time water quality monitoring
- Visual LED status indicators:
  - Red LED: Swimming not recommended
  - Green LED: Safe for swimming
  - Disco mode: Special conditions/warnings
- Automatic WiFi connection with fallback options
- Hourly updates
- Connection status feedback via onboard LED

## Hardware Requirements

- Raspberry Pi Pico W
- RGB LED
- Resistors for LED (if needed)
- USB cable for power and programming

## Pin Configuration

- Red LED: GPIO 16 (PWM)
- Green LED: GPIO 17 (PWM)
- Blue LED: GPIO 18 (PWM)
- Onboard LED: Used for WiFi status

## Setup

1. Clone this repository
2. Create an `env.py` file with your WiFi credentials:
```python
SSID_ANDROID = "your_android_hotspot_name"
PASSWORD_ANDROID = "your_android_password"
SSID_IPHONE = "your_iphone_hotspot_name"
PASSWORD_IPHONE = "your_iphone_password"
```

3. Upload all files to your Pico W
4. Power up the Pico W

## How It Works

1. The device attempts to connect to WiFi using provided credentials
2. Once connected, it queries the Safeswim API every hour
3. LED colors indicate swimming conditions:
   - Red: Not safe for swimming
   - Green: Safe for swimming
   - Disco mode (random colors): Special conditions
   - LED off: Error state or no data

## WiFi Connection

The system tries to connect in this order:
1. Android hotspot
2. iPhone hotspot

The onboard LED indicates connection status:
- Flashing: Attempting to connect
- Solid On: Connected
- Off: Connection failed

## Error Handling

- Network issues: Automatic reconnection attempts
- API errors: LED turns off, error logged to console
- Invalid responses: LED turns off, error logged to console

## Dependencies

- MicroPython for Raspberry Pi Pico W
- urequests library (included in MicroPython)

## Contributing

Feel free to submit issues and pull requests.

## License

MIT License
