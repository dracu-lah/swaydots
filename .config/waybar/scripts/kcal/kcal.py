#!/usr/bin/env python3
"""Kerala calendar popup for waybar. GTK3 + gtk-layer-shell.

  kcal.py --toggle                         open, or close if already open (pid file)
  kcal.py --screenshot out.png --month 2026-08 [--today 2026-11-07]   offscreen render for tests
"""
import argparse
import calendar
import datetime as dt
import os
import signal
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import GLib, Gdk, Gtk, Pango  # noqa: E402

import data  # noqa: E402
import malayalam as ml  # noqa: E402

ZEN = os.path.expanduser("~/.local/opt/zen/zen")
PID = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or data.CACHE_DIR, "kcal.pid")
MONTHS = list(calendar.month_name)[1:]
WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
CELL_W, CELL_H = 66, 62
SIDE_W = 124
LOGO = os.path.join(HERE, "assets", "mathrubhumi.png")
LOGO_H = 88  # px; matches the ~87px mini month boxes beside it (ink is ~90% of the image height)
MASTHEAD = None  # --masthead: a typed title instead of the logo (screenshots to share, no trademark)


def label(text, *classes, xalign=None):
    w = Gtk.Label(label=text)
    for c in classes:
        w.get_style_context().add_class(c)
    if xalign is not None:
        w.set_xalign(xalign)
    return w


def open_search(h, year):
    query = f"{h['name']} {year} Kerala"
    try:
        subprocess.Popen([ZEN, "--search", query], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError:
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)


def set_pointer(w, on):
    win = w.get_window()
    if win is not None:
        name = "pointer" if on else None
        win.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), name) if name else None)


class Popup(Gtk.Window):
    def __init__(self, cal, today, month, layer=True):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.cal, self.today = cal, today
        self.year, self.month = month
        self.cells = {}
        self.sel = None
        self.layer = layer
        self.msg_id = 0
        self.get_style_context().add_class("kcal")
        self.set_default_size(560, -1)
        self.set_resizable(False)
        if layer:
            self.setup_layer()
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        self.connect("key-press-event", self.on_key)
        self.connect("scroll-event", self.on_scroll)
        self.build()
        self.next_txt = self.find_next()
        self.render()

    def setup_layer(self):
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import GtkLayerShell as L
        L.init_for_window(self)
        L.set_namespace(self, "kcal")
        L.set_layer(self, L.Layer.OVERLAY)
        L.set_anchor(self, L.Edge.TOP, True)
        L.set_anchor(self, L.Edge.RIGHT, True)
        L.set_margin(self, L.Edge.TOP, 6)
        L.set_margin(self, L.Edge.RIGHT, 6)
        L.set_keyboard_mode(self, L.KeyboardMode.ON_DEMAND)
        self.make_backdrop(L)

    def make_backdrop(self, L):
        # Invisible full-screen surface under the popup: a click on it closes the popup.
        bd = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        bd.set_app_paintable(True)
        bd.set_visual(bd.get_screen().get_rgba_visual())
        bd.get_style_context().add_class("kcal-backdrop")
        L.init_for_window(bd)
        L.set_namespace(bd, "kcal-backdrop")
        L.set_layer(bd, L.Layer.TOP)
        for e in (L.Edge.TOP, L.Edge.BOTTOM, L.Edge.LEFT, L.Edge.RIGHT):
            L.set_anchor(bd, e, True)
        L.set_exclusive_zone(bd, -1)
        L.set_keyboard_mode(bd, L.KeyboardMode.NONE)
        bd.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        bd.connect("button-press-event", lambda *_: self.close_popup())
        bd.show_all()
        self.backdrop = bd

    # ---- layout ----
    def build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("page")
        self.add(root)

        # masthead: mini prev month | wordmark | mini next month (like the paper's corner boxes)
        mast = Gtk.Box(spacing=0)
        self.mini_prev = self.make_mini(-1, "Previous month (PageUp)")
        self.mini_next = self.make_mini(1, "Next month (PageDown)")
        mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        mid.set_valign(Gtk.Align.CENTER)
        mid.pack_start(self.logo(), False, False, 0)
        mast.pack_start(self.mini_prev["box"], False, False, 0)
        mast.pack_end(self.mini_next["box"], False, False, 0)
        mast.set_center_widget(mid)
        root.pack_start(mast, False, False, 0)

        self.strip = label("", "strip", xalign=0.5)
        self.strip.set_ellipsize(Pango.EllipsizeMode.END)
        root.pack_start(self.strip, False, False, 0)

        # month bar: ‹  1202 ● നവംബർ [2026] [NOVEMBER]  › , Today at the end
        bar = Gtk.Box(spacing=6)
        bar.get_style_context().add_class("monthbar")
        prev = self.nav_btn("◀", "Previous month (PageUp)", -1)
        nxt = self.nav_btn("▶", "Next month (PageDown)", 1)
        self.kyear = label("", "kyear")
        self.mname = label("", "mname")
        self.month_btn = self.pick_btn("pick-m", "Pick a month",
                                       [(m.upper(), (lambda i: lambda *_: self.goto(self.year, i + 1))(i))
                                        for i, m in enumerate(MONTHS)], cols=3)
        self.year_btn = self.pick_btn("pick-y", "Pick a year",
                                      [(str(y), (lambda y: lambda *_: self.goto(y, self.month))(y))
                                       for y in range(2000, 2051)], cols=6)
        c = Gtk.Box(spacing=6)
        c.set_baseline_position(Gtk.BaselinePosition.CENTER)
        for w in (self.kyear, label("◉", "bullet"), self.mname, self.year_btn, self.month_btn):
            w.set_valign(Gtk.Align.BASELINE)
            c.pack_start(w, False, False, 0)
        self.today_btn = Gtk.Button(label="ഇന്ന് · Today")
        self.today_btn.get_style_context().add_class("stamp")
        self.today_btn.set_focus_on_click(False)
        self.today_btn.set_tooltip_text("Jump to today (t)")
        self.today_btn.connect("clicked", lambda *_: self.go_today())
        self.today_btn.set_no_show_all(True)
        bar.pack_start(prev, False, False, 0)
        bar.pack_end(nxt, False, False, 0)
        bar.pack_end(self.today_btn, False, False, 0)
        bar.set_center_widget(c)
        root.pack_start(bar, False, False, 0)

        self.note = label("", "note", xalign=0.5)
        self.note.set_no_show_all(True)
        root.pack_start(self.note, False, False, 0)

        # body: holidays column | grid | Malayalam month, sun times, legend
        body = Gtk.Box(spacing=0)
        body.get_style_context().add_class("body")
        self.left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.left.get_style_context().add_class("side")
        self.left.set_size_request(SIDE_W, -1)
        self.right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.right.get_style_context().add_class("side")
        self.right.get_style_context().add_class("side-r")
        self.right.set_size_request(SIDE_W, -1)
        grid = Gtk.Grid(column_spacing=0, row_spacing=0, column_homogeneous=True)
        grid.get_style_context().add_class("grid")
        for c, wd in enumerate(WEEKDAYS):
            h = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            h.get_style_context().add_class("wdh")
            if c == 0:
                h.get_style_context().add_class("red")
            h.pack_start(label(ml.WEEKDAYS_ML[c], "wd-ml"), False, False, 0)
            h.pack_start(label(wd.upper(), "wd-en"), False, False, 0)
            grid.attach(h, c, 0, 1, 1)
        for r in range(6):
            for c in range(7):
                cell = self.make_cell()
                grid.attach(cell["box"], c, r + 1, 1, 1)
                self.cells[(r, c)] = cell
        body.pack_start(self.left, False, False, 0)
        body.pack_start(grid, False, False, 0)
        body.pack_start(self.right, False, False, 0)
        root.pack_start(body, False, False, 0)

        self.foot = label("", "foot", xalign=0.5)
        self.foot.set_ellipsize(Pango.EllipsizeMode.END)
        root.pack_start(self.foot, False, False, 0)

    def pick_btn(self, cls, tip, items, cols):
        """Printed-looking value that opens a grid menu of choices. A plain Label with a markup link,
        set straight in the month bar: Button, MenuButton and EventBox all drop the shared baseline."""
        lb = Gtk.Label()
        lb.get_style_context().add_class("pick-l")
        lb.get_style_context().add_class(cls)
        lb.set_tooltip_text(tip)
        lb.set_track_visited_links(False)
        menu = Gtk.Menu()
        menu.get_style_context().add_class("pick-menu")
        for i, (txt, cb) in enumerate(items):
            it = Gtk.MenuItem(label=txt)
            it.connect("activate", cb)
            menu.attach(it, i % cols, i % cols + 1, i // cols, i // cols + 1)
        menu.show_all()
        menu.attach_to_widget(lb, None)

        def pop(w, _uri):
            menu.popup_at_widget(w, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, Gtk.get_current_event())
            return True
        lb.connect("activate-link", pop)

        def set_text(t):
            lb.set_markup(f'<a href="pick"><span underline="none">{GLib.markup_escape_text(t)}</span></a>'
                          '<span size="60%" foreground="#8a8478" rise="1500"> ▾</span>')
        lb.set_value = set_text
        return lb

    def logo(self):
        """Masthead logo from assets/, drawn from a 2x surface so it stays sharp on HiDPI.
        Falls back to the typed wordmark when the file is missing."""
        if MASTHEAD:
            return label(MASTHEAD, "mast", xalign=0.5)
        try:
            from gi.repository import GdkPixbuf
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(LOGO, -1, LOGO_H * 2, True)
            if pb.get_has_alpha() and pb.get_n_channels() == 4:
                # The source has faint alpha haze (1..15) over its background: clear it at load time
                # (the file stays untouched) so no pale box shows on the paper colour.
                px = bytearray(pb.get_pixels())
                px[3::4] = bytes(px[3::4]).translate(bytes(0 if i < 16 else i for i in range(256)))
                pb = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(px)), pb.get_colorspace(), True, 8,
                                                     pb.get_width(), pb.get_height(), pb.get_rowstride())
            surf = Gdk.cairo_surface_create_from_pixbuf(pb, 2, None)
            img = Gtk.Image.new_from_surface(surf)
            img.get_style_context().add_class("logo")
            img.set_tooltip_text(None)
            return img
        except GLib.Error:
            return label("കേരള കലണ്ടർ", "mast", xalign=0.5)

    def nav_btn(self, txt, tip, step):
        b = Gtk.Button(label=txt)
        b.get_style_context().add_class("nav")
        b.set_focus_on_click(False)
        b.set_tooltip_text(tip)
        b.connect("clicked", lambda *_: self.shift(step))
        return b

    def make_mini(self, step, tip):
        eb = Gtk.EventBox()
        eb.get_style_context().add_class("mini")
        eb.set_size_request(SIDE_W, -1)
        eb.set_valign(Gtk.Align.CENTER)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title = label("", "mini-t", xalign=0.5)
        g = Gtk.Grid(column_homogeneous=True)
        for c, s in enumerate(ml.WEEKDAYS_ML_SHORT):
            g.attach(label(s, "mini-h", *(["red"] if c == 0 else [])), c, 0, 1, 1)
        days = []
        for r in range(6):
            for c in range(7):
                lb = label("", "mini-d")
                g.attach(lb, c, r + 1, 1, 1)
                days.append(lb)
        v.pack_start(title, False, False, 0)
        v.pack_start(g, False, False, 0)
        eb.add(v)
        eb.set_tooltip_text(tip)
        eb.connect("enter-notify-event", lambda w, _e: set_pointer(w, True))
        eb.connect("button-release-event", lambda _w, ev: ev.button == 1 and self.shift(step))
        return {"box": eb, "title": title, "days": days, "step": step}

    def make_cell(self):
        box = Gtk.EventBox()
        box.set_size_request(CELL_W, CELL_H)
        box.get_style_context().add_class("cell")
        ov = Gtk.Overlay()
        num = label("", "num")
        num.set_halign(Gtk.Align.CENTER)
        num.set_valign(Gtk.Align.START)
        num.set_margin_top(4)
        mal = label("", "ml")
        mal.set_halign(Gtk.Align.END)
        mal.set_valign(Gtk.Align.START)
        mal.set_margin_end(4)
        mal.set_margin_top(2)
        dot = label("●", "dot")
        dot.set_halign(Gtk.Align.START)
        dot.set_valign(Gtk.Align.START)
        dot.set_margin_start(4)
        dot.set_margin_top(2)
        sub = label("", "sub")
        sub.set_halign(Gtk.Align.FILL)
        sub.set_valign(Gtk.Align.END)
        sub.set_margin_bottom(3)
        sub.set_margin_start(2)
        sub.set_margin_end(2)
        sub.set_ellipsize(Pango.EllipsizeMode.END)
        sub.set_max_width_chars(1)
        ov.add(num)
        for w in (mal, dot, sub):
            ov.add_overlay(w)
        box.add(ov)
        cell = {"box": box, "num": num, "ml": mal, "dot": dot, "sub": sub, "date": None}
        box.set_has_tooltip(True)
        box.connect("query-tooltip", self.on_tip, cell)
        box.connect("button-release-event", self.on_click, cell)
        box.connect("enter-notify-event", self.on_enter, cell)
        return cell

    # ---- state ----
    def goto(self, y, m):
        self.year, self.month = y, m
        self.render()

    def go_today(self):
        self.sel = None
        self.goto(self.today.year, self.today.month)

    def select(self, d):
        if not (2000 <= d.year <= 2050):
            return
        self.sel = d
        if (d.year, d.month) != (self.year, self.month):
            self.goto(d.year, d.month)
        else:
            for c in self.cells.values():
                self.set_cls(c["box"], "sel", c["date"] == d)
            self.today_btn.set_visible(d != self.today)
            self.update_foot()

    def find_next(self):
        for i in range(0, 400):
            d = self.today + dt.timedelta(days=i)
            for h in self.cal.info(d)["holidays"]:
                if h["red"]:
                    when = "today" if i == 0 else "tomorrow" if i == 1 else f"in {i} days"
                    return f"Next: {h['name']} · {d.strftime('%a %d %b')} · {when}"
        return ""

    def update_foot(self):
        if self.msg_id:
            return
        d = self.sel
        if d is None:
            self.foot.set_text(self.next_txt)
            return
        names = ", ".join(h["name"] for h in self.cal.info(d)["holidays"])
        txt = f"{d.strftime('%a %d %b %Y')} · {ml.long_date_ml(d)}"
        self.foot.set_text(txt + (f" · {names}" if names else ""))

    def flash(self, text):
        self.msg_id += 1
        mine = self.msg_id
        self.foot.set_text(text)

        def clear():
            if self.msg_id == mine:
                self.msg_id = 0
                self.update_foot()
            return False
        GLib.timeout_add(1500, clear)

    def copy_day(self, d):
        txt = f"{d.strftime('%A, %d %B %Y')} ({ml.long_date(d)}, ME)"
        try:
            subprocess.Popen(["wl-copy", txt], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            self.flash(f"Copied: {txt}")
        except OSError:
            self.flash("wl-copy not found")

    def shift(self, n):
        i = self.year * 12 + self.month - 1 + n
        y, m = divmod(i, 12)
        if 2000 <= y <= 2050:
            self.goto(y, m + 1)

    def on_scroll(self, _w, ev):
        if ev.direction == Gdk.ScrollDirection.UP:
            self.shift(-1)
        elif ev.direction == Gdk.ScrollDirection.DOWN:
            self.shift(1)
        elif ev.direction == Gdk.ScrollDirection.SMOOTH:
            self.shift(1 if ev.delta_y > 0 else -1 if ev.delta_y < 0 else 0)
        return True

    def on_key(self, _w, ev):
        k = ev.keyval
        if k == Gdk.KEY_Escape:
            self.close_popup()
            return True
        step = {Gdk.KEY_Left: -1, Gdk.KEY_Right: 1, Gdk.KEY_Up: -7, Gdk.KEY_Down: 7}.get(k)
        if step is not None:
            if self.sel is None:
                t = self.today
                self.sel = t if (t.year, t.month) == (self.year, self.month) else dt.date(self.year, self.month, 1)
                step = 0
            self.select(self.sel + dt.timedelta(days=step))
            return True
        if k in (Gdk.KEY_Page_Up, Gdk.KEY_Page_Down):
            self.shift(-1 if k == Gdk.KEY_Page_Up else 1)
            return True
        if k in (Gdk.KEY_t, Gdk.KEY_T):
            self.go_today()
            return True
        if k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and self.sel:
            hs = self.cal.info(self.sel)["holidays"]
            if hs:
                open_search(sorted(hs, key=lambda h: not h["red"])[0], self.sel.year)
                return True
        return False

    def close_popup(self):
        bd = getattr(self, "backdrop", None)
        if bd:
            bd.destroy()
        self.destroy()
        Gtk.main_quit()

    def set_cls(self, w, cls, on):
        ctx = w.get_style_context()
        (ctx.add_class if on else ctx.remove_class)(cls)

    def render(self):
        y, m = self.year, self.month
        self.month_btn.set_value(MONTHS[m - 1].upper())
        self.year_btn.set_value(str(y))
        first = dt.date(y, m, 1)
        self.kyear.set_text(str(ml.kdate(first)[0]))
        self.mname.set_text(ml.GREG_ML[m - 1])
        n_red = sum(1 for _d, h in self.cal.month_list(y, m) if h["red"])
        self.strip.set_text(f"കേരള സർക്കാർ ഗസറ്റ് അവധി കലണ്ടർ  ·  {ml.header_ml(y, m)}  ·  {ml.header(y, m)}  ·  "
                            f"{n_red} {'അവധി' if n_red == 1 else 'അവധികൾ'} / holidays")
        self.today_btn.set_visible((y, m) != (self.today.year, self.today.month) or self.sel not in (None, self.today))
        has_year = any(k.startswith(str(y)) for k in self.cal.days)
        if y in self.cal.kyears:
            self.note.set_text("")
        elif has_year:
            self.note.set_text(f"Kerala list not published for {y}: national holidays only")
        else:
            self.note.set_text(f"no holiday data for {y}")
        self.note.set_visible(bool(self.note.get_text()))
        start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # Sunday first
        for r in range(6):
            for c in range(7):
                self.fill(self.cells[(r, c)], start + dt.timedelta(days=r * 7 + c), m)
        for mini in (self.mini_prev, self.mini_next):
            i = y * 12 + m - 1 + mini["step"]
            self.fill_mini(mini, i // 12, i % 12 + 1)
        self.fill_left()
        self.fill_right()
        self.update_foot()

    def fill(self, cell, d, month):
        info = self.cal.info(d)
        cell["date"], cell["info"] = d, info
        k = ml.kdate(d)
        cell["num"].set_text(str(d.day))
        cell["ml"].set_text(str(k[2]))
        hs = sorted(info["holidays"], key=lambda h: not h["red"])
        if hs:
            sub = hs[0]["name"] + (" ~" if hs[0]["tentative"] else "")
        elif info["sat"]:
            sub = info["sat"]
        elif k[2] == 1:
            sub = f"{ml.month_name_ml(k[1])} 1"
        else:
            sub = ""
        cell["sub"].set_text(sub)
        box = cell["box"]
        self.set_cls(box, "dim", d.month != month)
        self.set_cls(box, "today", d == self.today)
        self.set_cls(box, "sel", d == self.sel)
        self.set_cls(box, "red", info["red"])
        self.set_cls(box, "muted", info["muted"])
        self.set_cls(box, "holiday", bool(info["holidays"]))
        self.set_cls(cell["sub"], "kstart", not hs and not info["sat"] and k[2] == 1)
        cell["dot"].set_no_show_all(True)
        cell["dot"].set_visible(info["muted"])

    def fill_mini(self, mini, y, m):
        mini["title"].set_text(f"{ml.GREG_ML[m - 1]} {y}")
        first = dt.date(y, m, 1)
        lead = (first.weekday() + 1) % 7
        days = calendar.monthrange(y, m)[1]
        for i, lb in enumerate(mini["days"]):
            n = i - lead + 1
            lb.set_text(str(n) if 1 <= n <= days else "")
            red = 1 <= n <= days and self.cal.info(dt.date(y, m, n))["red"]
            self.set_cls(lb, "red", bool(red))
            self.set_cls(lb, "today", 1 <= n <= days and dt.date(y, m, n) == self.today)

    def side_head(self, box, ml_txt, en_txt):
        box.pack_start(label(ml_txt, "sec", *([] if box.get_children() else ["first"]), xalign=0), False, False, 0)
        box.pack_start(label(en_txt, "sec-en", xalign=0), False, False, 0)

    def fill_left(self):
        for ch in self.left.get_children():
            self.left.remove(ch)
        self.side_head(self.left, "അവധി ദിനങ്ങൾ", "HOLIDAYS")
        items = sorted(self.cal.month_list(self.year, self.month), key=lambda it: it[0])
        if not items:
            self.left.pack_start(label("ഈ മാസം ഗസറ്റ് അവധി ഇല്ല\nNo gazette holidays", "side-t", xalign=0),
                                 False, False, 0)
        for d, h in items:
            row = Gtk.Box(spacing=5)
            row.pack_start(label(str(d.day), "hd", "red" if h["red"] else "muted", xalign=1), False, False, 0)
            name = label(h["name"] + (" ~" if h["tentative"] else ""), "hn", *([] if h["red"] else ["muted"]), xalign=0)
            name.set_line_wrap(True)
            name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            name.set_max_width_chars(14)
            row.pack_start(name, True, True, 0)
            eb = Gtk.EventBox()
            eb.get_style_context().add_class("rowbox")
            eb.add(row)
            eb.set_tooltip_text(f"{d.strftime('%a %d %b')} · {h['name']}"
                                + (" (tentative)" if h["tentative"] else "") + "\nClick to search")
            eb.connect("enter-notify-event", lambda w, _e: set_pointer(w, True))
            eb.connect("button-release-event", self.on_row_click, h, d.year)
            self.left.pack_start(eb, False, False, 0)
        self.left.show_all()

    def fill_right(self):
        for ch in self.right.get_children():
            self.right.remove(ch)
        y, m = self.year, self.month
        self.side_head(self.right, "മലയാള മാസം", "MALAYALAM MONTH")
        last = calendar.monthrange(y, m)[1]
        rows = [(dt.date(y, m, 1), False)] + [(d, True) for d, _k in ml.month_starts(y, m) if d.day != 1]
        rows += [(dt.date(y, m, last), False)]
        for d, start in rows:
            k = ml.kdate(d)
            cls = [] if start or k[2] == 1 else ["muted"]
            row = Gtk.Box(spacing=5)
            row.pack_start(label(f"{d.day} {d.strftime('%b')}", "side-t", "dcol", *cls, xalign=1), False, False, 0)
            row.pack_start(label(f"{ml.month_name_ml(k[1])} {k[2]}", "side-t", *cls, xalign=0), False, False, 0)
            self.right.pack_start(row, False, False, 0)
        self.side_head(self.right, "ഉദയം · അസ്തമയം", "SUN · KOCHI")
        for day in (1, 8, 15, 22, 29):
            if day <= last:
                rise, sset = ml.sun_times(dt.date(y, m, day))
                self.right.pack_start(label(f"{day:>2}   ↑{rise}  ↓{sset}", "side-t", "mono", xalign=0),
                                      False, False, 0)
        self.side_head(self.right, "സൂചന", "KEY")
        for txt, cls in (("■ അവധി  holiday", "red"), ("● ഗസറ്റ് ദിനം  gazette", "muted"),
                         ("~ ചന്ദ്രദർശനം  moon", "muted"), ("↗ മലയാള തീയതി  ME day", "muted")):
            self.right.pack_start(label(txt, "side-t", cls, xalign=0), False, False, 0)
        self.right.show_all()

    # ---- interaction ----
    def on_tip(self, _w, _x, _y, _kb, tip, cell):
        d, info = cell["date"], cell["info"]
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.get_style_context().add_class("tip")
        box.pack_start(label(d.strftime("%A, %d %B %Y"), "t-date", xalign=0), False, False, 0)
        box.pack_start(label(f"{ml.long_date(d)}  ·  {ml.long_date_ml(d)}", "t-ml", xalign=0), False, False, 0)
        if info["sunday"]:
            box.pack_start(label("Sunday", "t-red", xalign=0), False, False, 0)
        if info["sat"]:
            box.pack_start(label(info["sat"] + " (holiday)", "t-red", xalign=0), False, False, 0)
        for h in info["holidays"]:
            box.pack_start(label(f"{h['name']}  ·  {'holiday' if h['red'] else 'gazette day'}",
                                 "t-red" if h["red"] else "t-muted", xalign=0), False, False, 0)
            if h["reason"]:
                r = label(h["reason"], "t-reason", xalign=0)
                r.set_line_wrap(True)
                r.set_max_width_chars(46)
                box.pack_start(r, False, False, 0)
            if h["tentative"]:
                box.pack_start(label("tentative: depends on the moon sighting", "t-tent", xalign=0), False, False, 0)
        if not info["holidays"] and not info["sunday"] and not info["sat"]:
            box.pack_start(label("No holiday", "t-reason", xalign=0), False, False, 0)
        hint = "Click to search this holiday" if info["holidays"] else \
            "Click to open this month" if (d.month, d.year) != (self.month, self.year) else "Click to select"
        box.pack_start(label(hint + "  ·  right-click to copy", "t-hint", xalign=0), False, False, 0)
        box.show_all()
        tip.set_custom(box)
        return True

    def on_enter(self, w, _ev, cell):
        d = cell["date"]
        set_pointer(w, bool(cell["info"]["holidays"]) or d.month != self.month or d.year != self.year)
        return False

    def on_click(self, _w, ev, cell):
        d, hs = cell["date"], cell["info"]["holidays"]
        if ev.button == 3:
            self.copy_day(d)
            return False
        if ev.button != 1:
            return False
        self.select(d)
        if hs:
            open_search(sorted(hs, key=lambda h: not h["red"])[0], d.year)
        return False

    def on_row_click(self, _w, ev, h, year):
        if ev.button == 1:
            open_search(h, year)
        return False

    def retag_today(self):
        now = dt.date.today()
        if now != self.today:
            self.today = now
            self.next_txt = self.find_next()
            self.render()
        return True


def css():
    p = Gtk.CssProvider()
    p.load_from_path(os.path.join(HERE, "style.css"))
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def month_arg(s, today):
    if not s:
        return today.year, today.month
    y, m = s.split("-")
    return int(y), int(m)


def alive(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return b"kcal.py" in f.read()
    except OSError:
        return False


def toggle_lock():
    """Return True if we may open; False if a running instance was asked to close."""
    try:
        with open(PID) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        pid = None
    if pid and alive(pid) and pid != os.getpid():
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        return False
    os.makedirs(os.path.dirname(PID), exist_ok=True)
    with open(PID, "w") as f:
        f.write(str(os.getpid()))
    return True


def unlock():
    try:
        with open(PID) as f:
            if int(f.read().strip()) == os.getpid():
                os.remove(PID)
    except (OSError, ValueError):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toggle", action="store_true")
    ap.add_argument("--screenshot")
    ap.add_argument("--month")
    ap.add_argument("--today")
    ap.add_argument("--hover", help="YYYY-MM-DD: also render that day's tooltip card (screenshot only)")
    ap.add_argument("--masthead", help="typed title instead of the logo")
    ap.add_argument("--scale", type=int, default=1, help="screenshot pixel scale, 2 for HiDPI")
    a = ap.parse_args()
    global MASTHEAD
    MASTHEAD = a.masthead
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    cal = data.load()
    css()
    if a.screenshot:
        return shot(a, cal, today)
    if not a.toggle:
        ap.error("use --toggle or --screenshot")
    if not toggle_lock():
        return 0
    try:
        win = Popup(cal, today, month_arg(a.month, today))
        win.connect("destroy", lambda *_: Gtk.main_quit())
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (win.close_popup(), False)[1])
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: (win.close_popup(), False)[1])
        GLib.timeout_add_seconds(60, win.retag_today)

        def reload():
            win.cal = data.load()
            win.render()
            return False
        if data.cache_age() >= data.MAX_AGE:
            data.refresh_async(lambda: GLib.idle_add(reload))
        win.show_all()
        Gtk.main()
    finally:
        unlock()
    return 0


def shot(a, cal, today):
    """Render the popup content offscreen to a PNG."""
    off = Gtk.OffscreenWindow()
    off.get_style_context().add_class("kcal")
    pop = Popup(cal, today, month_arg(a.month, today), layer=False)
    child = pop.get_child()
    pop.remove(child)
    frame = Gtk.Box()
    frame.get_style_context().add_class("kcal")
    frame.pack_start(child, True, True, 0)
    off.add(frame)
    off.set_default_size(-1, -1)
    off.show_all()
    if a.hover:
        card = hover_card(pop, dt.date.fromisoformat(a.hover))
        card.set_halign(Gtk.Align.START)  # natural width, as the real tooltip draws it
        off.remove(frame)
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        wrap.pack_start(frame, True, True, 0)
        wrap.pack_start(card, False, False, 8)
        off.add(wrap)
        off.show_all()
    for _ in range(20):
        while Gtk.events_pending():
            Gtk.main_iteration()
    if a.scale == 1:
        off.get_pixbuf().savev(a.screenshot, "png", [], [])
        return 0
    # Redraw the widget tree into a bigger surface, so text and lines are drawn at that
    # resolution instead of a 1x pixbuf being upscaled.
    import cairo
    # The window, not its child, so the paper colour and the border come along.
    al = off.get_allocation()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, al.width * a.scale, al.height * a.scale)
    ctx = cairo.Context(surf)
    ctx.scale(a.scale, a.scale)
    off.draw(ctx)
    surf.write_to_png(a.screenshot)
    return 0


def hover_card(pop, d):
    class T:
        custom = None

        def set_custom(self, w):
            self.custom = w
    cell = next(c for c in pop.cells.values() if c["date"] == d)
    t = T()
    pop.on_tip(None, 0, 0, False, t, cell)
    return t.custom


if __name__ == "__main__":
    sys.exit(main())
