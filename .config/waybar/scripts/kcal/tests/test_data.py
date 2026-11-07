import datetime as dt
import json
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
import data  # noqa: E402

ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
DESCRIPTION:Vishu is the new year.\\n\\nKerala\\n\\nInformation provided
 by www.officeholidays.com
DTSTART;VALUE=DATE:20260415
SUMMARY;LANGUAGE=en-us:Kerala: Vishu (Regional Holiday)
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261021
SUMMARY;LANGUAGE=en-us:Kerala: Vijayasasami (Regional Holiday)
END:VEVENT
BEGIN:VEVENT
DESCRIPTION:Observance\\nTo hide
DTSTART;VALUE=DATE:20260102
SUMMARY:Kerala: Id-ul-Ad'ha Holiday (Regional Holiday)
END:VEVENT
END:VCALENDAR
"""


def snapshot():
    with open(os.path.join(HERE, "..", "snapshot.json"), encoding="utf-8") as f:
        return json.load(f)


class Parse(unittest.TestCase):
    def test_ics(self):
        ev = data.parse_ics(ICS)
        self.assertEqual([e["date"] for e in ev], ["2026-04-15", "2026-10-21", "2026-01-02"])
        self.assertEqual(data.clean_kerala_name(ev[0]["summary"]), "Vishu")
        self.assertEqual(data.clean_kerala_name(ev[1]["summary"]), "Vijayasasami")
        self.assertEqual(data.clean_kerala_name(ev[2]["summary"]), "Id-ul-Ad'ha")
        self.assertEqual(data.reason_of(ev[0]["desc"]), "Vishu is the new year.")
        self.assertEqual(data.reason_of(ev[2]["desc"]), "")

    def test_typo_matches(self):
        it = data.load_it_set()
        self.assertEqual(data.match_it("Vijayasasami", "kerala", it)["id"], "vijayadashami")
        self.assertIsNone(data.match_it("Christmas Eve", "google", it))
        self.assertIsNone(data.match_it("Parsi New Year", "google", it))
        self.assertEqual(data.match_it("New Year's Day", "google", it)["id"], "newyear")


class Rules(unittest.TestCase):
    def test_saturdays(self):
        want = ["01-10", "01-24", "02-14", "02-28", "03-14", "03-28", "04-11", "04-25", "05-09", "05-23",
                "06-13", "06-27", "07-11", "07-25", "08-08", "08-22", "09-12", "09-26", "10-10", "10-24",
                "11-14", "11-28", "12-12", "12-26"]
        got, d = [], dt.date(2026, 1, 1)
        while d.year == 2026:
            if data.sat_tag(d):
                got.append(d.strftime("%m-%d"))
            d += dt.timedelta(1)
        self.assertEqual(got, want)
        self.assertEqual(data.sat_tag(dt.date(2026, 11, 14)), "2nd Saturday")
        self.assertEqual(data.sat_tag(dt.date(2026, 11, 28)), "4th Saturday")

    def setUp(self):
        s = snapshot()
        self.cal = data.Calendar(s["kerala"], s["google"])

    def test_15_red_in_2026(self):
        red = [(d, h["name"]) for d, hs in self.cal.days.items() if d[:4] == "2026" for h in hs if h["red"]]
        self.assertEqual(len(red), 15, red)

    def test_multi_holiday_day(self):
        names = [h["name"] for h in self.cal.days["2026-08-28"]]
        self.assertIn("Fourth Onam", names)
        self.assertGreaterEqual(len(names), 2)
        self.assertTrue(self.cal.info(dt.date(2026, 8, 25))["red"])  # First Onam
        self.assertFalse(self.cal.info(dt.date(2026, 8, 27))["red"])  # Third Onam: muted
        self.assertTrue(self.cal.info(dt.date(2026, 8, 27))["muted"])

    def test_sunday_and_saturday_red(self):
        self.assertTrue(self.cal.info(dt.date(2026, 11, 8))["red"])   # Sunday + Deepavali
        self.assertTrue(self.cal.info(dt.date(2026, 11, 14))["red"])  # 2nd Saturday
        self.assertFalse(self.cal.info(dt.date(2026, 11, 7))["red"])  # 1st Saturday

    def test_year_without_data(self):
        info = self.cal.info(dt.date(2035, 3, 4))
        self.assertFalse(info["has_data"])
        self.assertTrue(info["red"])  # Sunday still red

    def test_google_fallback_for_uncovered_year(self):
        s = snapshot()
        cal = data.Calendar(s["kerala"], s["google"])
        self.assertNotIn(2029, cal.kyears)
        self.assertTrue(any(h["red"] for h in cal.days.get("2029-12-25", [])))

    def test_custom_wins(self):
        s = snapshot()
        custom = {"remove": [{"date": "2026-01-01", "contains": "New Year"}],
                  "add": [{"date": "2026-02-02", "name": "Test Day", "red": True}],
                  "rename": [{"date": "2026-01-26", "contains": "Republic", "to": "R Day"}],
                  "force_red": [{"date": "2026-08-27", "contains": "Third"}]}
        cal = data.Calendar(s["kerala"], s["google"], custom)
        self.assertNotIn("2026-01-01", cal.days)
        self.assertEqual(cal.days["2026-02-02"][0]["name"], "Test Day")
        self.assertEqual(cal.days["2026-01-26"][0]["name"], "R Day")
        self.assertTrue(cal.days["2026-08-27"][0]["red"])

    def test_tentative(self):
        h = self.cal.days["2026-03-20"][0]
        self.assertTrue(h["tentative"])


if __name__ == "__main__":
    unittest.main()
