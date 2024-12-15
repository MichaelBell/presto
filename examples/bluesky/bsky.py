import machine
import os
from secrets import WIFI_SSID, WIFI_PASSWORD, COUNTRY, BSKY_USERNAME, BSKY_PASSWORD

machine.freq(266000000)

os.chdir("/bluesky")

import gc
import time
import pngdec
import jpegdec
from time import sleep
from picographics import PicoGraphics, DISPLAY_PRESTO_FULL_RES
from picovector import ANTIALIAS_X16, PicoVector, Polygon, Transform
from presto import Presto
import network
import ntptime
import requests
import rp2
from touch import FT6236

from text import clean_text

presto = Presto(full_res=True, direct_to_fb=True)
presto.set_backlight = presto.presto.set_backlight
presto.set_backlight(0)
display = presto.display
framebuffer = memoryview(display)
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_X16)
j = jpegdec.JPEG(display)
icons = pngdec.PNG(display)
icons.open_file("icons30.png")

# connect to wifi
rp2.country(COUNTRY)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)
while wlan.isconnected() is False:
    print('Waiting for connection...')
    sleep(1)

# Custom colours
YELLOW = display.create_pen(200, 150, 50)
GREY = display.create_pen(200, 200, 200)
WHITE = display.create_pen(215, 215, 255)
BLUE = display.create_pen(23, 52, 93)
BG = display.create_pen(0, 0, 0)
TEXT = display.create_pen(241, 243, 245)

WIDTH, HEIGHT = display.get_bounds()
BLOOT_HEIGHT = HEIGHT//3

# Make sure time is set
#ntptime.settime()

def display_jpeg(uri, x, y, scale=jpegdec.JPEG_SCALE_HALF):
    resp = requests.get(uri)
    j.open_RAM(resp.content)
    j.decode(x, y, scale)

def display_avatar(uri, x, y):
    if not 'img/avatar/plain' in uri or not uri.endswith("@jpeg"):
        return
    
    uri = uri.replace("img/avatar/plain", "img/avatar_thumbnail/plain")
    display_jpeg(uri, x, y)
    
def display_image(bloot, uri):
    print("Render image")

    display.set_pen(BG)
    display.clear()
    display.set_pen(TEXT)
    vector.set_font("osansb.af", 21)

    resp = requests.get(uri)

    if 'author' in bloot['post']:
        if 'avatar' in bloot['post']['author']:
            display_avatar(bloot['post']['author']['avatar'], 2, 22)
        display.set_pen(TEXT)
        display_name = clean_text(bloot['post']['author']['displayName'])
        if display_name == '':
            display_name = '@' + bloot['post']['author']['handle']
            vector.set_font("osans.af", 21)
        vector.text(display_name, 5, 13, max_width=400)
    
    j.open_RAM(resp.content)
    img_width = j.get_width()
    img_height = j.get_height()
    
    scale = jpegdec.JPEG_SCALE_QUARTER
    if img_width <= 400 and img_height <= 456:
        scale = jpegdec.JPEG_SCALE_FULL
    elif img_width <= 800 and img_height <= 912:
        scale = jpegdec.JPEG_SCALE_HALF
    
    j.decode(75, 22, scale)
    
def has_image(bloot):
    return ('embed' in bloot['post'] and
            (('media' in bloot['post']['embed'] and
              'images' in bloot['post']['embed']['media']) or
             'images' in bloot['post']['embed']))

def render_bloot(bloot, i):
    print("Render bloot")

    display.set_pen(TEXT)
    vector.set_font("osansb.af", 21)
    
    display.set_clip(0, i*BLOOT_HEIGHT, WIDTH, 128)
    if 'author' in bloot['post']:
        if 'avatar' in bloot['post']['author']:
            display_avatar(bloot['post']['author']['avatar'], 2, 22 + i*BLOOT_HEIGHT)
        display.set_pen(TEXT)
        display_name = clean_text(bloot['post']['author']['displayName'])
        if display_name == '':
            display_name = '@' + bloot['post']['author']['handle']
            vector.set_font("osans.af", 21)
        vector.text(display_name, 5, 13 + i*BLOOT_HEIGHT, max_width=400)
    vector.set_font("osans.af", 18)
    if 'text' in bloot['post']['record']:
        vector.text(clean_text(bloot['post']['record']['text']), 72, 33 + i*BLOOT_HEIGHT, max_width=406, max_height=100) # , wordwrap=409, scale=2
    display.remove_clip()
    if 'likeCount' in bloot['post']:
        if 'viewer' in bloot['post'] and 'like' in bloot['post']['viewer']:
            icons.decode(148, 122+i*BLOOT_HEIGHT, source=(0, 0, 30, 26))
        else:
            icons.decode(148, 122+i*BLOOT_HEIGHT, source=(0, 26, 30, 26))
        display.set_pen(TEXT)
        vector.text(str(bloot['post']['likeCount']), 180, 140+i*BLOOT_HEIGHT)
    if 'repostCount' in bloot['post']:
        if 'viewer' in bloot['post'] and 'repost' in bloot['post']['viewer']:
            icons.decode(308, 122+i*BLOOT_HEIGHT, source=(30, 0, 30, 26))
        else:
            icons.decode(308, 122+i*BLOOT_HEIGHT, source=(30, 26, 30, 26))
        display.set_pen(TEXT)
        vector.text(str(bloot['post']['repostCount']), 340, 140+i*BLOOT_HEIGHT)
    if has_image(bloot):
        icons.decode(21, 122+i*BLOOT_HEIGHT, source=(60, 0, 30, 26))

def draw_navigation_ui(num_bloots):
    display.set_pen(BLUE)
    if min_bloot_idx + 3 < num_bloots:
        display.triangle(WIDTH-25, HEIGHT-15, WIDTH-15, HEIGHT-5, WIDTH-5, HEIGHT-15)
    
    if min_bloot_idx != 0:
        display.triangle(WIDTH-25, 15, WIDTH-15, 5, WIDTH-5, 15)

def update_display(bloots):
    display.set_pen(BG)
    display.clear()
    
    draw_navigation_ui(len(bloots))
    
    for i in range(min(len(bloots) - min_bloot_idx, 3)):
        render_bloot(bloots[i + min_bloot_idx], i)
    

t = Transform()
vector.set_font_letter_spacing(100)
vector.set_font_word_spacing(100)
vector.set_font_line_height(110)
vector.set_transform(t)

min_bloot_idx = 0
fetch_bloots = True

if True:
    from atprototools import Session

    # Establish Bluesky session
    print("Connect to Bluesky...")
    session = Session(BSKY_USERNAME, BSKY_PASSWORD)
    print("  connected.")

    display.set_pen(BG)
    display.clear()
    #presto.update(display)
    sleep(0.05)
        
    touch = FT6236(False, True)
        
    try:
        while True:
            presto.set_backlight(0.2)
            if fetch_bloots:
                num_bloots = 25
                print("Fetch bloots...")
                resp = session.getSkyline(num_bloots)
                js = resp.json()
                if 'error' in js:
                    print(f"Session error: {js['message']}")
                    session = Session(BSKY_USERNAME, BSKY_PASSWORD)
                    print("Fetching again...")
                    resp = session.getSkyline(num_bloots)
                    js = resp.json()
                skyline = js['feed']
                print("  fetched.")

                root_bloots = []
                bloot_cids = []
                for bloot in skyline:
                    if 'record' not in bloot['post']: continue
                    if 'reply' in bloot['post']['record']: continue
                    if bloot['post']['cid'] in bloot_cids: continue
                    root_bloots.append(bloot)
                    bloot_cids.append(bloot['post']['cid'])
            fetch_bloots = True
                
            update_display(root_bloots)

            print("Display update")
            #presto.update(display)
            presto.set_backlight(0.8)
            gc.collect()
            print("Wait for touch")
            countdown = 600
            while countdown > 0:
                countdown -= 1
                if touch.state:
                    interacted = False
                    print("Touch: ", touch.x, touch.y)
                    
                    if touch.x > 60 and touch.x < 100:
                        for i in range(3):
                            if touch.y > 50 + i*80 and touch.y < 90 + i*80:
                                print(f"Like {i}")
                                icons.decode(148, 122+i*BLOOT_HEIGHT, source=(0, 0, 30, 26))
                                #presto.partial_update(display, 128, 122+i*BLOOT_HEIGHT, 30, 26)
                                session.like(root_bloots[i + min_bloot_idx]['post']['cid'], root_bloots[i + min_bloot_idx]['post']['uri'])
                                interacted = True
                                countdown = 0
                                break
                                
                    elif touch.x > 140 and touch.x < 180:
                        for i in range(3):
                            if touch.y > 50 + i*80 and touch.y < 90 + i*80:
                                print(f"Repost {i}")
                                icons.decode(308, 122+i*BLOOT_HEIGHT, source=(30, 0, 30, 26))
                                #presto.partial_update(display, 288, 122+i*BLOOT_HEIGHT, 30, 26)
                                session.rebloot(root_bloots[i + min_bloot_idx]['post']['cid'], root_bloots[i + min_bloot_idx]['post']['uri'])
                                interacted = True
                                countdown = 0
                                break
                    
                    elif touch.x > 200:
                        if touch.y > 200:
                            min_bloot_idx += 1
                            
                            presto.set_backlight(0.2)
                            framebuffer[0:WIDTH*2*2*HEIGHT//3] = framebuffer[WIDTH*2*HEIGHT//3:WIDTH*2*HEIGHT]
                            display.set_pen(BG)
                            display.rectangle(WIDTH-25, 2*HEIGHT//3-15, 20, 10)
                            display.rectangle(0, 2*HEIGHT//3, WIDTH, HEIGHT//3)
                            if min_bloot_idx + 2 < len(root_bloots):
                                render_bloot(root_bloots[min_bloot_idx+2], 2)
                            draw_navigation_ui(len(root_bloots))
                            #presto.update(display)
                            presto.set_backlight(1)
                            
                            if countdown < 200: countdown = 200
                            interacted = True
                            
                        elif touch.y < 40:
                            if min_bloot_idx > 0:
                                min_bloot_idx -= 1
                                
                                presto.set_backlight(0.2)
                                framebuffer[WIDTH*2*HEIGHT//3:WIDTH*2*HEIGHT] = framebuffer[0:WIDTH*2*2*HEIGHT//3]
                                display.set_pen(BG)
                                display.rectangle(WIDTH-25, HEIGHT//3+5, 20, 10)
                                display.rectangle(0, 0, WIDTH, HEIGHT//3)
                                if min_bloot_idx < len(root_bloots):
                                    render_bloot(root_bloots[min_bloot_idx], 0)
                                draw_navigation_ui(len(root_bloots))
                                #presto.update(display)
                                presto.set_backlight(1)

                                if countdown < 200: countdown = 200
                                interacted = True

                    elif touch.x < 40:
                        if touch.y < 40:
                            min_bloot_idx = 0
                            break
                    
                    if not interacted:
                        if ((touch.x > 40 and touch.y % 80 <= 70) or
                            touch.x <= 40 and (touch.y - 10) % 80 > 40):
                            i = touch.y
                            if touch.x <= 40:
                                i -= 10
                            i = i // 80
                            
                            if has_image(root_bloots[i + min_bloot_idx]):
                                presto.set_backlight(0.2)
                                if 'media' in root_bloots[i + min_bloot_idx]['post']['embed']:
                                    display_image(root_bloots[i + min_bloot_idx], root_bloots[i + min_bloot_idx]['post']['embed']['media']['images'][0]['thumb'])
                                else:
                                    display_image(root_bloots[i + min_bloot_idx], root_bloots[i + min_bloot_idx]['post']['embed']['images'][0]['thumb'])
                                #presto.update(display)
                                presto.set_backlight(1)
                                while not touch.state:
                                    sleep(0.1)
                                fetch_bloots = False
                                break
                            
                sleep(0.1)
    except Exception as e:
        print(e)
