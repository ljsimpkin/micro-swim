import math
import network
import urequests
import ujson
import utime
import ntptime
from env import SSID, PASSWORD
from machine import Pin, PWM, SoftI2C

# --- Config ---
LOCATION         = "murrays-bay"
UTC_OFFSET_HOURS = 12  # 12 = NZST, 13 = NZDT (summer)
TIDE_MIN         = 0.6  # approx low water (m) for this beach
TIDE_MAX         = 2.7  # approx high water (m) for this beach

# --- RGB LED (GP16=R, GP17=G, GP18=B) ---
RED   = PWM(Pin(16), freq=1000)
GREEN = PWM(Pin(17), freq=1000)
BLUE  = PWM(Pin(18), freq=1000)

def set_color(r, g, b):
    RED.duty_u16(r)
    GREEN.duty_u16(g)
    BLUE.duty_u16(b)

def flash_sleep(quality, seconds):
    if quality == "BLACK":
        for _ in range(seconds * 2):
            set_color(65535, 0, 0)
            utime.sleep(0.25)
            set_color(0, 0, 0)
            utime.sleep(0.25)
    else:
        utime.sleep(seconds)

# --- LCD (ST7032, GP14=SDA, GP15=SCL, addr=0x3e) ---
i2c  = SoftI2C(sda=Pin(14), scl=Pin(15))
ADDR = 0x3e

def cmd(c):
    i2c.writeto(ADDR, bytes([0x00, c]))
    utime.sleep_ms(1)

def data(d):
    i2c.writeto(ADDR, bytes([0x40, d]))
    utime.sleep_us(50)

def write(text):
    for ch in text:
        data(ord(ch))

def write_line(n, text):
    cmd(0x80 if n == 1 else 0xC0)
    t = text[:8]
    write(t + " " * (8 - len(t)))

# LCD init
utime.sleep_ms(40)
for c in [0x38, 0x39, 0x14, 0x7C, 0x55, 0x6C]:
    cmd(c)
utime.sleep_ms(250)
for c in [0x38, 0x0C, 0x01]:
    cmd(c)
utime.sleep_ms(3)

# --- WiFi ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    utime.sleep(1)
    wlan.connect(SSID, PASSWORD)
    write_line(2, "WiFi...")
    for _ in range(30):
        if wlan.isconnected():
            return
        utime.sleep(1)
    reset()

# --- Tide fetch ---
def fetch_next_tides():
    url = "https://safeswim.org.nz/api/locations/" + LOCATION
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://safeswim.org.nz/locations/" + LOCATION,
    }
    try:
        r      = urequests.get(url, headers=headers)
        result = ujson.loads(r.text)
        r.close()
    except:
        return None, None, None

    quality = result["forecasts"]["WATER_QUALITY"][0]
    tides   = result["forecasts"]["TIDE"]

    # Array index 0 = the UTC hour when the request is made
    now_utc     = utime.time()
    array_start = (now_utc // 3600) * 3600

    next_high = next_low = None
    for i, v in enumerate(tides):
        if v is None:
            continue
        height_s, min_s = v.split(":")
        height   = float(height_s)
        ev_epoch = array_start + i * 3600 + int(min_s) * 60
        if ev_epoch <= now_utc:
            continue
        if height > 1.5 and next_high is None:
            next_high = (ev_epoch, height)
        elif height <= 1.5 and next_low is None:
            next_low = (ev_epoch, height)
        if next_high and next_low:
            break

    return next_high, next_low, quality

def fmt_time(epoch):
    t = utime.localtime(epoch + UTC_OFFSET_HOURS * 3600)
    return "{:02d}:{:02d}".format(t[3], t[4])

def current_height(next_high, next_low, now):
    ht_epoch, ht_h = next_high
    lt_epoch, lt_h = next_low
    if ht_epoch < lt_epoch:
        next_ext = (ht_epoch, ht_h)
        prev_ext = (ht_epoch - (lt_epoch - ht_epoch), lt_h)
    else:
        next_ext = (lt_epoch, lt_h)
        prev_ext = (lt_epoch - (ht_epoch - lt_epoch), ht_h)
    t0, h0 = prev_ext
    t1, h1 = next_ext
    frac = max(0.0, min(1.0, (now - t0) / (t1 - t0)))
    return h0 + (h1 - h0) * (1 - math.cos(math.pi * frac)) / 2

def safe_color(height):
    frac = max(0.0, min(1.0, (height - TIDE_MIN) / (TIDE_MAX - TIDE_MIN)))
    # frac=1 (high tide) → full physical green (b channel)
    # frac=0 (low tide)  → full physical blue  (g channel)
    return (0, round((1 - frac) * 65535), round(frac * 65535))

def tide_bar(next_high, next_low, now):
    height = current_height(next_high, next_low, now)
    fill   = round((height - TIDE_MIN) / (TIDE_MAX - TIDE_MIN) * 8)
    fill   = max(0, min(8, fill))
    if fill == 0:
        return "|" + " " * 7
    return "=" * fill + " " * (8 - fill)


# --- Main ---
connect_wifi()
for _ in range(5):
    try:
        ntptime.settime()
        break
    except:
        utime.sleep(2)
write_line(2, "Synced")
utime.sleep(1)

next_high, next_low, quality = fetch_next_tides()
last_fetch = utime.time()

while True:
    now = utime.time()

    if now - last_fetch > 1800:
        next_high, next_low, quality = fetch_next_tides()
        last_fetch = now

    if quality in ("RED", "BLACK"):
        set_color(65535, 0, 0)
    elif quality == "GREEN" and next_high and next_low:
        set_color(*safe_color(current_height(next_high, next_low, now)))
    elif quality == "GREEN":
        set_color(0, 0, 65535)   # fallback: solid green if no tide data yet
    else:
        set_color(0, 0, 0)

    if next_high and next_low:
        ht_epoch, _ = next_high
        lt_epoch, _ = next_low
        if ht_epoch < lt_epoch:
            write_line(1, "HT " + fmt_time(ht_epoch))
        else:
            write_line(1, "LT " + fmt_time(lt_epoch))
        write_line(2, tide_bar(next_high, next_low, now))
        flash_sleep(quality, 6)
    else:
        write_line(1, "No tide")
        write_line(2, "")
        flash_sleep(quality, 6)
