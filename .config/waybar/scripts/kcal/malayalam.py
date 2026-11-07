"""Kollavarsham (Malayalam calendar) from the sun's sidereal longitude. No dependencies.

A month starts when the sun enters a 30 degree sidereal sign (Chingam = Simha). Kerala rule: if that
happens before 3/5 of the daytime (sunrise to sunset at Kochi) has passed, the month starts that day,
otherwise the next day. Sun longitude is Meeus low precision; ayanamsa is Lahiri.
"""
import datetime as dt
import math

MONTHS = ["Chingam", "Kanni", "Thulam", "Vrischikam", "Dhanu", "Makaram",
          "Kumbham", "Meenam", "Medam", "Edavam", "Mithunam", "Karkidakam"]
MONTHS_ML = ["ചിങ്ങം", "കന്നി", "തുലാം", "വൃശ്ചികം", "ധനു", "മകരം",
             "കുംഭം", "മീനം", "മേടം", "ഇടവം", "മിഥുനം", "കർക്കടകം"]
LAT, LON, TZ = 9.93, 76.26, 5.5  # Kochi, IST
CHINGAM_SIGN = 4  # Simha, counted from Mesha = 0


def _jd(d, hours_utc=0.0):
    return d.toordinal() + 1721424.5 + hours_utc / 24.0


def sidereal_sun(jd):
    t = (jd - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t
    m = math.radians(357.52911 + 35999.05029 * t)
    c = ((1.914602 - 0.004817 * t) * math.sin(m) + 0.019993 * math.sin(2 * m) + 0.000289 * math.sin(3 * m))
    omega = math.radians(125.04 - 1934.136 * t)
    tropical = l0 + c - 0.00569 - 0.00478 * math.sin(omega)
    ayanamsa = 23.85306 + 0.013969 * (jd - 2451545.0) / 365.25  # Lahiri
    return (tropical - ayanamsa) % 360.0


def _sun_times(d):
    """Sunrise and sunset in local hours (IST) for date d at Kochi."""
    jd = _jd(d, 12 - TZ)  # local noon
    n = jd - 2451545.0
    g = math.radians((357.5291 + 0.98560028 * n) % 360)
    lam = math.radians((280.459 + 0.98564736 * n + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360)
    eps = math.radians(23.439 - 0.0000004 * n)
    dec = math.asin(math.sin(eps) * math.sin(lam))
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))  # minutes
    phi = math.radians(LAT)
    cosh = (math.cos(math.radians(90.833)) - math.sin(phi) * math.sin(dec)) / (math.cos(phi) * math.cos(dec))
    h = math.degrees(math.acos(max(-1.0, min(1.0, cosh))))
    noon = 12 + TZ - LON / 15.0 - eqt / 60.0
    return noon - h / 15.0, noon + h / 15.0


def _crossing(sign, jd_hi):
    """JD (UT) when the sidereal sun entered `sign`, searching back from jd_hi (sun already past it)."""
    target = sign * 30.0
    lo, hi = jd_hi - 40.0, jd_hi
    for _ in range(50):
        mid = (lo + hi) / 2
        diff = (sidereal_sun(mid) - target + 180.0) % 360.0 - 180.0
        if diff >= 0:
            hi = mid
        else:
            lo = mid
    return hi


def _month_start(sign, jd_hi):
    """Local date the Malayalam month for `sign` starts (Kerala 3/5 daytime rule)."""
    t = _crossing(sign, jd_hi)
    local = t + TZ / 24.0  # JD at local (IST) time
    day = dt.date.fromordinal(int(math.floor(local - 1721424.5)))
    hour = ((local - 0.5) % 1.0) * 24.0
    rise, sset = _sun_times(day)
    cutoff = rise + 0.6 * (sset - rise)
    return day if hour < cutoff else day + dt.timedelta(days=1)


def kdate(d):
    """(malayalam_year, month_number 1..12, day) for a Gregorian date."""
    jd_end = _jd(d, 23.99 - TZ)  # end of the civil day: the sign that may start today
    sign = int(sidereal_sun(jd_end) // 30)
    start = _month_start(sign, jd_end)
    if d < start:
        sign = (sign - 1) % 12
        start = _month_start(sign, _jd(start, 0) - 0.01)
    month = (sign - CHINGAM_SIGN) % 12 + 1
    year = d.year - 824 if (month <= 5 and d.month >= 8) else d.year - 825
    return year, month, (d - start).days + 1


def month_name(n):
    return MONTHS[n - 1]


def day_number(d):
    return kdate(d)[2]


def long_date(d):
    y, m, k = kdate(d)
    return f"{month_name(m)} {k}, {y}"


def header(year, month, names_of=None):
    """e.g. 'Thulam – Vrischikam 1202' for the Gregorian month year/month."""
    names_of = names_of or month_name
    first = kdate(dt.date(year, month, 1))
    nxt = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    last = kdate(nxt)
    names = [names_of(first[1])]
    if last[1] != first[1]:
        names.append(names_of(last[1]))
    if last[0] != first[0]:
        return f"{names[0]} {first[0]} – {names[-1]} {last[0]}"
    return f"{' – '.join(names)} {last[0]}"


def month_name_ml(n):
    return MONTHS_ML[n - 1]


def header_ml(year, month):
    return header(year, month, month_name_ml)


def long_date_ml(d):
    y, m, k = kdate(d)
    return f"{month_name_ml(m)} {k}, {y}"


WEEKDAYS_ML = ["ഞായർ", "തിങ്കൾ", "ചൊവ്വ", "ബുധൻ", "വ്യാഴം", "വെള്ളി", "ശനി"]  # Sunday first
WEEKDAYS_ML_SHORT = ["ഞാ", "തി", "ചൊ", "ബു", "വ്യാ", "വെ", "ശ"]
GREG_ML = ["ജനുവരി", "ഫെബ്രുവരി", "മാർച്ച്", "ഏപ്രിൽ", "മേയ്", "ജൂൺ", "ജൂലൈ", "ഓഗസ്റ്റ്",
           "സെപ്റ്റംബർ", "ഒക്ടോബർ", "നവംബർ", "ഡിസംബർ"]


def sun_times(d):
    """('06:14', '18:02'): sunrise and sunset at Kochi, IST."""
    def hm(h):
        m = round(h * 60)
        return f"{m // 60:02d}:{m % 60:02d}"
    rise, sset = _sun_times(d)
    return hm(rise), hm(sset)


def month_starts(year, month):
    """[(date, malayalam month number)] for each Malayalam month that starts in this Gregorian month."""
    d, out = dt.date(year, month, 1), []
    while d.month == month:
        k = kdate(d)
        if k[2] == 1:
            out.append((d, k[1]))
        d += dt.timedelta(days=1)
    return out
