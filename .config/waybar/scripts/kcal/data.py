"""Holiday data for the Kerala calendar: fetch, parse ICS, cache, merge, red-day rules."""
import datetime as dt
import json
import os
import re
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "kcal")
CACHE = os.path.join(CACHE_DIR, "holidays.json")
UNMATCHED = os.path.join(CACHE_DIR, "unmatched.log")
MAX_AGE = 7 * 86400
KERALA_URL = "https://www.officeholidays.com/ics/india/kerala"
GOOGLE_URL = ("https://calendar.google.com/calendar/ical/"
              "en.indian%23holiday%40group.v.calendar.google.com/public/basic.ics")
MOON_KEYS = ("idul", "eidul", "eidal", "milad", "muharram", "ashura", "bakrid", "hazarat")


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---------- ICS ----------

def _unescape(s):
    return (s.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\"))


def parse_ics(text):
    """Return [{date: 'YYYY-MM-DD', summary, desc}] from ICS text (small parser, no lib)."""
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events, cur = [], None
    for ln in lines:
        if ln == "BEGIN:VEVENT":
            cur = {}
        elif ln == "END:VEVENT":
            if cur is not None and cur.get("date") and cur.get("summary"):
                events.append({"date": cur["date"], "summary": cur["summary"], "desc": cur.get("desc", "")})
            cur = None
        elif cur is not None and ":" in ln:
            key, _, val = ln.partition(":")
            name = key.split(";")[0].upper()
            if name == "DTSTART":
                m = re.match(r"(\d{4})(\d{2})(\d{2})", val)
                if m:
                    cur["date"] = "-".join(m.groups())
            elif name == "SUMMARY":
                cur["summary"] = _unescape(val).strip()
            elif name == "DESCRIPTION":
                cur["desc"] = _unescape(val)
    return events


def clean_kerala_name(summary):
    s = re.sub(r"^(LANGUAGE=[\w-]+:)", "", summary)
    s = re.sub(r"^Kerala:\s*", "", s)
    s = re.sub(r"\s*\(Regional Holiday\)\s*$", "", s)
    s = re.sub(r"(?<=Ad'ha)\s+Holiday$", "", s)
    return s.strip()


def reason_of(desc):
    first = (desc or "").split("\n\n")[0].strip()
    if first.lower().startswith(("kerala", "information provided", "observance", "to hide")):
        return ""
    return re.sub(r"\s+", " ", first)


def trim(events, google=False):
    """Compact form stored in cache/snapshot."""
    out = []
    for e in events:
        name = e["summary"] if google else clean_kerala_name(e["summary"])
        out.append({"date": e["date"], "name": name, "reason": "" if google else reason_of(e["desc"])})
    return out


# ---------- IT set ----------

def load_it_set():
    return _load_json(os.path.join(HERE, "it_set.json"), [])


def match_it(name, source, it_set):
    n = norm(name)
    for item in it_set:
        if any(norm(x) in n for x in item.get("exclude", [])):
            continue
        if any(k in n for k in item.get(source, [])):
            return item
    return None


def is_tentative(name, item=None):
    n = norm(name)
    return bool((item and item.get("tentative")) or "tentative" in n or any(k in n for k in MOON_KEYS))


# ---------- merge ----------

def merge(kerala, google, custom=None, it_set=None):
    """kerala/google: trimmed events. Returns {'YYYY-MM-DD': [holiday, ...]}, set of years Kerala covers."""
    it_set = load_it_set() if it_set is None else it_set
    custom = custom or {}
    kyears = {int(e["date"][:4]) for e in kerala}
    days, seen, unmatched = {}, set(), set()

    def put(date, name, red, reason="", tentative=False, source="", it_id=None):
        key = (date, it_id or norm(name))
        if key in seen:
            return
        seen.add(key)
        days.setdefault(date, []).append({"name": name, "red": red, "reason": reason,
                                          "tentative": tentative, "source": source, "it": it_id})

    for e in kerala:
        item = match_it(e["name"], "kerala", it_set)
        if not item:
            unmatched.add(e["name"])
        put(e["date"], item["label"] if item and item["id"] in ("firstonam", "thiruvonam", "mahanavami") else e["name"],
            bool(item), e["reason"], is_tentative(e["name"], item), "kerala", item and item["id"])
    for e in google:
        item = match_it(e["name"], "google", it_set)
        if not item:
            continue
        if int(e["date"][:4]) in kyears and any(h["it"] == item["id"] and h_year(d) == int(e["date"][:4])
                                                 for d, hs in days.items() for h in hs):
            continue
        put(e["date"], item["label"], True, "", is_tentative(e["name"], item), "google", item["id"])
    # derived days (First Onam = Thiruvonam - 1) where a year has none
    have = {(h["it"], d[:4]) for d, hs in days.items() for h in hs if h["it"]}
    for item in it_set:
        dv = item.get("derive")
        if not dv:
            continue
        for d, hs in list(days.items()):
            for h in hs:
                if h["it"] == dv["from"] and (item["id"], d[:4]) not in have:
                    nd = (dt.date.fromisoformat(d) + dt.timedelta(days=dv["offset"])).isoformat()
                    put(nd, item["label"], True, "Derived from Thiruvonam.", True, "derived", item["id"])
                    have.add((item["id"], d[:4]))
    # one red day per IT item per year: a second date (e.g. Bakrid listed on 27 and 28 May) stays muted
    first = {}
    for d in sorted(days):
        for h in days[d]:
            if h["it"] and h["red"]:
                k = (h["it"], d[:4])
                if k in first:
                    h["red"] = False
                first.setdefault(k, d)
    apply_custom(days, custom, seen)
    return days, kyears, unmatched


def h_year(d):
    return int(d[:4])


def apply_custom(days, custom, seen):
    for r in custom.get("remove", []):
        hs = days.get(r["date"], [])
        days[r["date"]] = [h for h in hs if norm(r["contains"]) not in norm(h["name"])]
    for r in custom.get("rename", []):
        for h in days.get(r["date"], []):
            if norm(r["contains"]) in norm(h["name"]):
                h["name"] = r["to"]
    for r in custom.get("force_red", []):
        for h in days.get(r["date"], []):
            if norm(r["contains"]) in norm(h["name"]):
                h["red"] = True
    for r in custom.get("force_muted", []):
        for h in days.get(r["date"], []):
            if norm(r["contains"]) in norm(h["name"]):
                h["red"] = False
    for r in custom.get("add", []):
        days.setdefault(r["date"], []).append({"name": r["name"], "red": bool(r.get("red")),
                                               "reason": r.get("reason", ""), "tentative": False,
                                               "source": "custom", "it": None})
    for d in [d for d, hs in days.items() if not hs]:
        del days[d]


# ---------- day rules ----------

def sat_tag(d):
    """'2nd Saturday' / '4th Saturday' or ''."""
    if d.weekday() == 5:
        n = (d.day - 1) // 7 + 1
        if n == 2:
            return "2nd Saturday"
        if n == 4:
            return "4th Saturday"
    return ""


class Calendar:
    def __init__(self, kerala, google, custom=None, it_set=None):
        self.days, self.kyears, self.unmatched = merge(kerala, google, custom, it_set)

    def info(self, d):
        hs = self.days.get(d.isoformat(), [])
        tag = sat_tag(d)
        sunday = d.weekday() == 6
        red = sunday or bool(tag) or any(h["red"] for h in hs)
        return {"holidays": hs, "sat": tag, "sunday": sunday, "red": red,
                "muted": bool(hs) and not red, "has_data": d.year in self.kyears}

    def month_list(self, year, month):
        """Holidays of a month, red first, then by date: [(date, holiday)]."""
        out = [(dt.date.fromisoformat(d), h) for d, hs in self.days.items()
               if d[:4] == f"{year:04d}" and d[5:7] == f"{month:02d}" for h in hs]
        out.sort(key=lambda x: (not x[1]["red"], x[0]))
        return out


# ---------- cache / fetch ----------

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kcal-waybar/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def read_store():
    store = _load_json(CACHE, None)
    if store and "kerala" in store:
        return store
    snap = _load_json(os.path.join(HERE, "snapshot.json"), {"kerala": [], "google": [], "fetched": 0})
    return snap


def cache_age():
    try:
        return dt.datetime.now().timestamp() - os.path.getmtime(CACHE)
    except OSError:
        return 1e12


def refresh(force=False):
    """Fetch both feeds, keep old parts on failure. Returns True if the cache changed."""
    if not force and cache_age() < MAX_AGE:
        return False
    store = read_store()
    changed = False
    for key, url, g in (("kerala", KERALA_URL, False), ("google", GOOGLE_URL, True)):
        try:
            ev = trim(parse_ics(_fetch(url)), google=g)
            if ev:
                store[key] = ev
                changed = True
        except Exception:
            pass
    if changed:
        store["fetched"] = int(dt.datetime.now().timestamp())
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False)
        os.replace(tmp, CACHE)
    else:
        try:
            os.utime(CACHE)  # back off; retry after the next MAX_AGE
        except OSError:
            pass
    return changed


def refresh_async(callback=None, force=False):
    def run():
        if refresh(force) and callback:
            callback()
    threading.Thread(target=run, daemon=True).start()


def load():
    store = read_store()
    cal = Calendar(store["kerala"], store["google"], _load_json(os.path.join(HERE, "holidays-custom.json"), {}))
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(UNMATCHED, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(cal.unmatched)) + "\n")
    except OSError:
        pass
    return cal


def build_snapshot(kerala_ics, google_ics, out):
    g = [e for e in trim(parse_ics(google_ics), google=True) if "2026" <= e["date"][:4] <= "2031"]
    store = {"fetched": 0, "kerala": trim(parse_ics(kerala_ics)), "google": g}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=0)
