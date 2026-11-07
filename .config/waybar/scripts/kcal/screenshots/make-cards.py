#!/usr/bin/env python3
"""Build the README cards: screenshots/hero.png and screenshots/mastheads.png.
Run from the kcal folder: python3 screenshots/make-cards.py .   (needs sway.png, month.png and the two masthead strips in /tmp)"""
import cairo, math, sys
K = sys.argv[1]

def bg(c, W, H):
    g = cairo.LinearGradient(0, 0, W, H)
    g.add_color_stop_rgb(0, 0x16/255, 0x16/255, 0x1a/255)
    g.add_color_stop_rgb(0.6, 0x24/255, 0x12/255, 0x15/255)
    g.add_color_stop_rgb(1, 0x5a/255, 0x10/255, 0x16/255)
    c.set_source(g); c.paint()
    r = cairo.RadialGradient(W*0.85, H*0.1, 0, W*0.85, H*0.1, W*0.6)
    r.add_color_stop_rgba(0, 0xb3/255, 0x18/255, 0x1e/255, 0.35)
    r.add_color_stop_rgba(1, 0xb3/255, 0x18/255, 0x1e/255, 0)
    c.set_source(r); c.paint()

def rrect(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x+w-r, y+r, r, -math.pi/2, 0); c.arc(x+w-r, y+h-r, r, 0, math.pi/2)
    c.arc(x+r, y+h-r, r, math.pi/2, math.pi); c.arc(x+r, y+r, r, math.pi, 3*math.pi/2)
    c.close_path()

def card(c, path, x, y, h=None, w=None, r=16):
    img = cairo.ImageSurface.create_from_png(path)
    iw, ih = img.get_width(), img.get_height()
    s = h/ih if h else w/iw
    w, h = iw*s, ih*s
    for i in range(24, 0, -2):  # soft shadow
        c.set_source_rgba(0, 0, 0, 0.035); rrect(c, x-i/2, y-i/2+i*0.6, w+i, h+i, r+i/2); c.fill()
    c.save(); rrect(c, x, y, w, h, r); c.clip()
    c.translate(x, y); c.scale(s, s)
    c.set_source_surface(img, 0, 0); c.get_source().set_filter(cairo.FILTER_BEST); c.paint()
    c.restore()
    c.set_source_rgba(1, 1, 1, 0.12); c.set_line_width(1.5); rrect(c, x, y, w, h, r); c.stroke()
    return w, h

def label(c, txt, x, y):
    import gi; gi.require_version("Pango", "1.0"); gi.require_version("PangoCairo", "1.0")
    from gi.repository import Pango, PangoCairo
    l = PangoCairo.create_layout(c); l.set_font_description(Pango.FontDescription("Adwaita Sans, RIT Rachana Bold 22"))
    l.set_text(txt, -1); c.set_source_rgba(1, 1, 1, 0.78); c.move_to(x, y - 30); PangoCairo.show_layout(c, l)

# 1) hero: Sway capture + month with hover card, same height
P, G, H = 80, 56, 1000
sw = 1280*H/1010; mw = 1484*H/1694
W = int(P*2 + sw + G + mw); HH = int(P*2 + H)
o = cairo.ImageSurface(cairo.FORMAT_RGB24, W, HH); c = cairo.Context(o); bg(c, W, HH)
card(c, f"{K}/screenshots/sway.png", P, P, h=H)
card(c, f"{K}/screenshots/month.png", P+sw+G, P, h=H)
o.write_to_png(f"{K}/screenshots/hero.png"); print("hero", W, HH)

# 2) mastheads: text above image, labelled
CW = 1484; LH = 54
W = P*2 + CW; HH = P*2 + (LH + 270)*2 + G
o = cairo.ImageSurface(cairo.FORMAT_RGB24, W, HH); c = cairo.Context(o); bg(c, W, HH)
y = P
for t, f in (('"masthead_text": "ഓഫീസ് കലണ്ടർ"', "masthead-text.png"), ('"masthead_image": "masthead.svg"', "masthead-image.png")):
    label(c, t, P+4, y+32); y += LH
    _, h = card(c, f"/tmp/{f}", P, y, w=CW); y += h + G
o.write_to_png(f"{K}/screenshots/mastheads.png"); print("mastheads", W, HH)
