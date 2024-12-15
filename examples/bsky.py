import machine
import gc
import time
import pngdec
import jpegdec
from time import sleep
from picographics import PicoGraphics, DISPLAY_PRESTO
from picovector import ANTIALIAS_X16, PicoVector, Polygon, Transform
from presto import Presto
import network
from secrets import SSID, PASSWORD, COUNTRY, BSKY_USERNAME, BSKY_PASSWORD
import ntptime
import requests
import rp2
from touch import FT6236

from text import clean_text

# connect to wifi
rp2.country(COUNTRY)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
while wlan.isconnected() is False:
    print('Waiting for connection...')
    sleep(1)

presto = Presto()
display = PicoGraphics(DISPLAY_PRESTO, buffer=memoryview(presto))
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_X16)
print("1")
j = jpegdec.JPEG(display)
icons = pngdec.PNG(display)
icons.open_file("icons.png")

# Custom colours
YELLOW = display.create_pen(200, 150, 50)
GREY = display.create_pen(200, 200, 200)
WHITE = display.create_pen(215, 215, 255)
BLUE = display.create_pen(23, 52, 93)
BG = display.create_pen(0, 0, 0)
TEXT = display.create_pen(241, 243, 245)

WIDTH, HEIGHT = display.get_bounds()

# Make sure time is set
#ntptime.settime()

def display_jpeg(uri, x, y, scale):
    resp = requests.get(uri)
    j.open_RAM(resp.content)
    j.decode(x, y, scale)

def display_avatar(uri, x, y):
    #prof = session.get_profile(did).json()
    #avatar = prof['avatar']
    if not 'img/avatar/plain' in uri or not uri.endswith("@jpeg"):
        return
    
    uri = uri.replace("img/avatar/plain", "img/avatar_thumbnail/plain")
    display_jpeg(uri, x, y, jpegdec.JPEG_SCALE_QUARTER)

#t = Transform()
#vector.set_font("AdvRe.af", 1)
#vector.set_font_letter_spacing(10)
#vector.set_font_word_spacing(10)
#vector.set_transform(t)

if True:
    print("2")
    from atprototools import Session

    # Establish Bluesky session
    print("Connect to Bluesky...")
    session = Session(BSKY_USERNAME, BSKY_PASSWORD)
    print("  connected.")

    for i in range(2):
        display.set_pen(BG)
        display.clear()
        presto.update(display)
        
    touch = FT6236(True)
        
    try:
        while True:
            num_bloots = 20
            print("Fetch bloots...")
            skyline = session.getSkyline(num_bloots).json()['feed']
            print("  fetched.")

            display.set_pen(BG)
            display.clear()

            i = 0
            displayed_bloots = []
            for bloot in skyline:
                if 'record' not in bloot['post']: continue
                if 'reply' in bloot['post']['record']: continue
                
                print("Render bloot")
                displayed_bloots.append(bloot)

                display.set_pen(TEXT)
                display.set_clip(0, 2 + i*80, 240, 64)                
                if 'author' in bloot['post']:
                    if 'avatar' in bloot['post']['author']:
                        display_avatar(bloot['post']['author']['avatar'], 2, 10 + i*80)
                    display.set_pen(TEXT)
                    display.text(clean_text(bloot['post']['author']['displayName']), 5, 2 + i*80, scale=1)
                if 'text' in bloot['post']['record']:
                    display.text(clean_text(bloot['post']['record']['text']), 37, 11 + i*80, wordwrap=201, scale=1)
                display.remove_clip()
                if 'likeCount' in bloot['post']:
                    if 'viewer' in bloot['post'] and 'like' in bloot['post']['viewer']:
                        icons.decode(64, 66+i*80, source=(0, 0, 15, 13))
                    else:
                        icons.decode(64, 66+i*80, source=(0, 13, 15, 13))
                    display.set_pen(TEXT)
                    display.text(str(bloot['post']['likeCount']), 80, 69+i*80, scale=1)
                if 'repostCount' in bloot['post']:
                    if 'viewer' in bloot['post'] and 'repost' in bloot['post']['viewer']:
                        icons.decode(144, 66+i*80, source=(15, 0, 15, 13))
                    else:
                        icons.decode(144, 66+i*80, source=(15, 13, 15, 13))
                    display.set_pen(TEXT)
                    display.text(str(bloot['post']['repostCount']), 160, 69+i*80, scale=1)                    
                i += 1
                if i == 3:
                    break

            print("Display update")
            presto.update(display)
            gc.collect()
            print("Wait for touch")
            for i in range(600):
                if touch.state:
                    interacted = False
                    if touch.x > 55 and touch.x < 90:
                        for i in range(3):
                            if touch.y > 55 + i*80 and touch.y < 90 + i*80:
                                print(f"Like {i}")
                                session.like(displayed_bloots[i]['post']['cid'], displayed_bloots[i]['post']['uri'])
                                interacted = True
                                
                    elif touch.x > 135 and touch.x < 170:
                        for i in range(3):
                            if touch.y > 55 + i*80 and touch.y < 90 + i*80:
                                print(f"Repost {i}")
                                session.rebloot(displayed_bloots[i]['post']['cid'], displayed_bloots[i]['post']['uri'])
                                interacted = True
                                
                    if interacted:
                        break
                    
                sleep(0.1)
    except Exception as e:
        print(e)
