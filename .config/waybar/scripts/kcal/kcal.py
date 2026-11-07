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
CELL_W, CELL_H = 64, 56


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
        self.updating = False
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

    # ---- layout ----
    def build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.get_style_context().add_class("pad")
        self.add(root)

        head = Gtk.Overlay()
        tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.title = label("", "title", xalign=0.5)
        self.subtitle = label("", "subtitle", xalign=0.5)
        tbox.pack_start(self.title, False, False, 0)
        tbox.pack_start(self.subtitle, False, False, 0)
        head.add(tbox)
        self.today_btn = Gtk.Button(label="Today")
        self.today_btn.set_focus_on_click(False)
        self.today_btn.set_tooltip_text("Jump to today (t)")
        self.today_btn.set_halign(Gtk.Align.END)
        self.today_btn.set_valign(Gtk.Align.CENTER)
        self.today_btn.connect("clicked", lambda *_: self.go_today())
        head.add_overlay(self.today_btn)
        root.pack_start(head, False, False, 0)

        bar = Gtk.Box(spacing=6)
        prev = Gtk.Button(label="‹")
        prev.get_style_context().add_class("nav")
        prev.set_focus_on_click(False)
        prev.set_tooltip_text("Previous month (PageUp)")
        prev.connect("clicked", lambda *_: self.shift(-1))
        nxt = Gtk.Button(label="›")
        nxt.get_style_context().add_class("nav")
        nxt.set_focus_on_click(False)
        nxt.set_tooltip_text("Next month (PageDown)")
        nxt.connect("clicked", lambda *_: self.shift(1))
        self.month_box = Gtk.ComboBoxText()
        for m in MONTHS:
            self.month_box.append_text(m)
        self.year_box = Gtk.ComboBoxText()
        for y in range(2000, 2051):
            self.year_box.append_text(str(y))
        self.month_box.connect("changed", self.on_pick)
        self.year_box.connect("changed", self.on_pick)
        mid = Gtk.Box(spacing=6)
        mid.pack_start(self.month_box, False, False, 0)
        mid.pack_start(self.year_box, False, False, 0)
        bar.pack_start(prev, False, False, 0)
        bar.pack_end(nxt, False, False, 0)
        bar.set_center_widget(mid)
        root.pack_start(bar, False, False, 0)

        self.note = label("", "note", xalign=0)
        self.note.set_no_show_all(True)
        root.pack_start(self.note, False, False, 0)

        grid = Gtk.Grid(column_spacing=2, row_spacing=2, column_homogeneous=True)
        for c, wd in enumerate(WEEKDAYS):
            grid.attach(label(wd, "wd", *(["red"] if c == 0 else [])), c, 0, 1, 1)
        for r in range(6):
            for c in range(7):
                cell = self.make_cell()
                grid.attach(cell["box"], c, r + 1, 1, 1)
                self.cells[(r, c)] = cell
        root.pack_start(grid, False, False, 0)

        self.list_box = Gtk.Grid(column_spacing=12, row_spacing=2, column_homogeneous=True)
        self.list_box.get_style_context().add_class("list")
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_propagate_natural_height(True)
        sw.set_max_content_height(112)
        sw.add(self.list_box)
        root.pack_start(sw, False, False, 0)

        self.foot = label("", "foot", xalign=0.5)
        root.pack_start(self.foot, False, False, 0)
        legend = Gtk.Box(spacing=14)
        legend.set_halign(Gtk.Align.CENTER)
        for txt, cls in (("■ holiday", "lg-red"), ("● gazette day", "lg-muted"), ("~ moon-dependent", "lg-muted")):
            legend.pack_start(label(txt, "legend", cls), False, False, 0)
        root.pack_start(legend, False, False, 0)

    def make_cell(self):
        box = Gtk.EventBox()
        box.set_size_request(CELL_W, CELL_H)
        box.get_style_context().add_class("cell")
        ov = Gtk.Overlay()
        num = label("", "num")
        num.set_halign(Gtk.Align.CENTER)
        num.set_valign(Gtk.Align.CENTER)
        mal = label("", "ml")
        mal.set_halign(Gtk.Align.END)
        mal.set_valign(Gtk.Align.END)
        mal.set_margin_end(4)
        dot = label("●", "dot")
        dot.set_halign(Gtk.Align.START)
        dot.set_valign(Gtk.Align.START)
        dot.set_margin_start(5)
        dot.set_margin_top(3)
        ov.add(num)
        ov.add_overlay(mal)
        ov.add_overlay(dot)
        box.add(ov)
        cell = {"box": box, "num": num, "ml": mal, "dot": dot, "date": None}
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
            self.today_btn.set_sensitive(True)
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

    def on_pick(self, *_):
        if self.updating:
            return
        m, y = self.month_box.get_active(), self.year_box.get_active()
        if m >= 0 and y >= 0:
            self.goto(2000 + y, m + 1)

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
        self.destroy()
        Gtk.main_quit()

    def set_cls(self, w, cls, on):
        ctx = w.get_style_context()
        (ctx.add_class if on else ctx.remove_class)(cls)

    def render(self):
        y, m = self.year, self.month
        self.updating = True
        self.month_box.set_active(m - 1)
        self.year_box.set_active(y - 2000)
        self.updating = False
        self.title.set_text(ml.header_ml(y, m))
        self.subtitle.set_text(f"{ml.header(y, m)}  ·  {MONTHS[m - 1]} {y}")
        self.today_btn.set_sensitive((y, m) != (self.today.year, self.today.month) or self.sel not in (None, self.today))
        has_year = any(k.startswith(str(y)) for k in self.cal.days)
        if y in self.cal.kyears:
            self.note.set_text("")
        elif has_year:
            self.note.set_text(f"Kerala list not published for {y}: national holidays only")
        else:
            self.note.set_text(f"no holiday data for {y}")
        self.note.set_visible(bool(self.note.get_text()))
        first = dt.date(y, m, 1)
        start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # Sunday first
        for r in range(6):
            for c in range(7):
                self.fill(self.cells[(r, c)], start + dt.timedelta(days=r * 7 + c), m)
        self.fill_list()
        self.update_foot()

    def fill(self, cell, d, month):
        info = self.cal.info(d)
        cell["date"], cell["info"] = d, info
        cell["num"].set_text(str(d.day))
        cell["ml"].set_text(str(ml.day_number(d)))
        box = cell["box"]
        self.set_cls(box, "dim", d.month != month)
        self.set_cls(box, "today", d == self.today)
        self.set_cls(box, "sel", d == self.sel)
        self.set_cls(box, "red", info["red"])
        self.set_cls(box, "muted", info["muted"])
        self.set_cls(box, "holiday", bool(info["holidays"]))
        cell["dot"].set_visible(info["muted"])
        cell["dot"].set_no_show_all(True)
        cell["dot"].set_visible(info["muted"])

    def fill_list(self):
        for ch in self.list_box.get_children():
            self.list_box.remove(ch)
        items = self.cal.month_list(self.year, self.month)
        if not items:
            self.list_box.attach(label("No gazette holidays this month", "note", xalign=0), 0, 0, 2, 1)
        for i, (d, h) in enumerate(items):
            txt = f"{d.day:>2} {d.strftime('%a')}  {h['name']}" + (" ~" if h["tentative"] else "")
            row = label(txt, "row", "red" if h["red"] else "muted", xalign=0)
            row.set_ellipsize(Pango.EllipsizeMode.END)
            eb = Gtk.EventBox()
            eb.get_style_context().add_class("rowbox")
            eb.add(row)
            eb.set_tooltip_text(h["name"] + (" (tentative)" if h["tentative"] else "") + "\nClick to search")
            eb.connect("enter-notify-event", lambda w, _e: set_pointer(w, True))
            eb.connect("button-release-event", self.on_row_click, h, d.year)
            self.list_box.attach(eb, i % 2, i // 2, 1, 1)
        self.list_box.show_all()

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
    a = ap.parse_args()
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
    pop = Popup(cal, today, month_arg(a.month, today), layer=False)
    child = pop.get_child()
    pop.remove(child)
    frame = Gtk.Box()
    frame.get_style_context().add_class("kcal")
    frame.pack_start(child, True, True, 0)
    off.add(frame)
    off.set_default_size(560, -1)
    off.show_all()
    if a.hover:
        card = hover_card(pop, dt.date.fromisoformat(a.hover))
        off.remove(frame)
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        wrap.pack_start(frame, True, True, 0)
        wrap.pack_start(card, False, False, 8)
        off.add(wrap)
        off.show_all()
    for _ in range(20):
        while Gtk.events_pending():
            Gtk.main_iteration()
    pb = off.get_pixbuf()
    pb.savev(a.screenshot, "png", [], [])
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
