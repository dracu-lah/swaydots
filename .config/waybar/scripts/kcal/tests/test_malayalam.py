import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import malayalam as m  # noqa: E402
from table import MONTH_STARTS  # noqa: E402


class Kollavarsham(unittest.TestCase):
    def test_anchors(self):
        # Chingam 1 (new year): 2025-08-17 and 2026-08-17 (plan, printed calendars)
        self.assertEqual(m.kdate(dt.date(2025, 8, 17)), (1201, 1, 1))
        self.assertEqual(m.kdate(dt.date(2026, 8, 17)), (1202, 1, 1))
        self.assertEqual(m.kdate(dt.date(2026, 8, 16)), (1201, 12, 31))
        self.assertEqual(m.long_date(dt.date(2026, 11, 7)), "Thulam 21, 1202")

    def test_header(self):
        self.assertEqual(m.header(2026, 11), "Thulam – Vrischikam 1202")
        self.assertEqual(m.header(2026, 8), "Karkidakam 1201 – Chingam 1202")

    def test_month_start_table(self):
        got = []
        d = dt.date(2020, 1, 1)
        while d <= dt.date(2035, 12, 31):
            y, mo, k = m.kdate(d)
            if k == 1:
                got.append(f"{d.isoformat()[2:]}:{y}:{mo}")
            d += dt.timedelta(1)
        self.assertEqual(got, MONTH_STARTS)

    def test_continuity_and_lengths(self):
        starts = [dt.date.fromisoformat("20" + r.split(":")[0]) for r in MONTH_STARTS]
        for a, b in zip(starts, starts[1:]):
            self.assertTrue(29 <= (b - a).days <= 32, (a, b))
        # year rolls over exactly at Chingam
        for r in MONTH_STARTS:
            _, y, mo = r.split(":")
            if mo == "1":
                d = dt.date.fromisoformat("20" + r.split(":")[0])
                self.assertEqual(m.kdate(d - dt.timedelta(1))[0], int(y) - 1)


if __name__ == "__main__":
    unittest.main()
