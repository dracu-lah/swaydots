# Waybar Kerala calendar popup: plan

## Decisions (user, 2026-11-07)

- Red = IT-startup set + 2nd/4th Saturdays + Sundays. Other Kerala gazette days are muted (still hoverable).
- IT set: New Year, Republic Day, Vishu, May Day, Independence Day, First Onam (Uthradom), Thiruvonam,
  Gandhi Jayanti, Mahanavami, Vijayadashami, Deepavali, Christmas, Eid ul-Fitr, Bakrid (Id-ul-Ad'ha), Good Friday.
- Click the clock to toggle the popup; Esc or a second click closes it. The clock tooltip shows the full date and today's holiday.
- Malayalam (Kollavarsham) in English: the header shows e.g. `Thulam – Vrischikam 1202`, and each cell shows the Malayalam day number in a corner. No nakshatra.
- Weeks start on Sunday; the Sunday column is red.

## Why a popup

The waybar `{calendar}` tooltip is static Pango text, so it can't have hover per day, clicks or buttons. Use Python + GTK3 +
gtk-layer-shell (all installed: `gtk-layer-shell-0.10`, PyGObject Gtk 3). No new packages.

## Data (verified with curl, 2026-11-07)

| Source | Use | Notes |
| --- | --- | --- |
| `https://www.officeholidays.com/ics/india/kerala` | primary | Kerala gazette list. 2026: 31 events, 2027: 26. Each DESCRIPTION gives the reason. SUMMARY is `Kerala: <name> (Regional Holiday)`, so strip the prefix and suffix. |
| `https://calendar.google.com/calendar/ical/en.indian%23holiday%40group.v.calendar.google.com/public/basic.ics` | fallback for years Kerala doesn't cover | 2021–2031, all-India and no reasons. Use only the names that match the IT set; show the rest muted, or skip them. |
| `holidays-custom.json` (in repo) | overrides | add, remove or rename days, or force red. Wins over both feeds. |

- Cache: `~/.cache/kcal/holidays.json`, refreshed when older than 7 days. Fetch in a background thread so the popup never waits on the network.
- Bundled `snapshot.json` (2026–2027 parsed) as the offline first-run fallback.
- Match the IT set by normalised keyword (lowercase, no punctuation). The feed has typos, e.g. `Vijayasasami`, so match `vijaya`.
  Moon-based days (Eid, Bakrid, Milad, Muharram) get a "tentative" tag in the card.
- Unparsed feed names go to the log only (`~/.cache/kcal/unmatched.log`), never into the UI.

## Kollavarsham

- First check `pip index versions kollavarsham` or PyPI for a maintained library ("tools before workarounds"). If none works offline, implement it ourselves:
  - Sidereal sun longitude = Meeus low-precision solar longitude − Lahiri ayanamsa. A month starts when the sun enters each 30° sign
    (Chingam = Simha, 120°).
  - Kerala rule: if the sankranti falls before ~3/5 of the daytime has passed (sunrise to sunset at Kochi, 9.93N 76.26E), the month starts that day; otherwise the next day.
  - Year: ME = Gregorian year − 824 from Chingam 1 onward, else − 825.
- Test against known dates: Chingam 1 1202 = 2026-08-17, Medam 1 (Vishu) 2026 = 2026-04-14 (verify against a printed calendar or Mathrubhumi).
  Precompute a table of month starts for 2020–2035 and keep it in a test.

## Files

- `.config/waybar/scripts/kcal/kcal.py`: GTK popup. `--toggle` (single instance through a pid file; a second call closes it),
  `--screenshot out.png --month 2026-08` (offscreen render, for tests).
- `.config/waybar/scripts/kcal/data.py`: fetch, parse ICS (no extra lib, small parser), cache, merge, Saturday rule, IT set.
- `.config/waybar/scripts/kcal/malayalam.py`: Kollavarsham.
- `.config/waybar/scripts/kcal/style.css`, `it_set.json`, `holidays-custom.json`, `snapshot.json`.
- `.config/waybar/scripts/kcal/tests/`: `python3 -m unittest`.
- `.config/waybar/scripts/clock.sh`: custom/clock module JSON `{text, tooltip}` via `jq` on the cache, `interval: 30`.
- `.config/waybar/config`: replace `"clock"` with `"custom/clock"`, `on-click: kcal.py --toggle`. `style.css`: `#custom-clock` joins the `#clock` rules.

## UI

- Layer-shell overlay anchored top-right, under the bar, with a 6px margin. Keyboard mode on-demand so Esc works. Opens on the focused output.
- Size: about 560×520 px. Cells 64×56, with the date in 20px bold and the Malayalam number in 11px at the bottom right. Font: JetBrainsMono Nerd Font (same as the bar).
- Header: `‹` prev month, Month dropdown, Year dropdown (2000–2050), `›` next, a `Today` button. The scroll wheel changes the month.
- Today: filled square, bright accent background and bold text. Red text = red holiday. Muted text plus a small dot = other gazette day.
  2nd/4th Sat = red text with the tag "2nd Saturday". Days from the previous and next month are dimmed (0.35 opacity).
- Hover card (custom GTK tooltip): full date, Malayalam date (e.g. `Thulam 21, 1202`), each holiday name, red or muted label, reason, tentative tag.
- Click a holiday cell: `~/.local/opt/zen/zen --search "<name> <year> Kerala"` (uses the browser's default engine). Fallback: `xdg-open`
  with a Google URL. Click a plain day: no action.
- Below the grid: a list of this month's holidays (date, name), red first.

## Edge cases to cover

- Several holidays on one day (2026-08-25 Milad + First Onam; 2026-08-28 Fourth Onam + Ayyankali + SN Guru): all shown in the card, and red if any of them is red.
- A holiday on a Sunday or a 2nd/4th Saturday: both reasons shown.
- 6-row months (e.g. Aug 2026): the grid always has 6 rows, so the size stays fixed.
- A year with no feed data: show a small note "no holiday data for YEAR" but still apply the Saturday and Sunday rules.
- Offline or the feed is down: keep the old cache; on first run use the snapshot.
- The date changes at midnight while the popup is open: a 60s timer re-marks today.
- A second click or a double toggle: pid file lock, and stale pid files are cleaned up.

## Checks (machine first)

- Unit: ICS parse, 2nd/4th Saturday for 12 months, IT matching on the 2026 feed (expect 15 red), Kollavarsham table.
- Screenshot: `kcal.py --screenshot` for 2026-08 (busy Onam month) and 2026-11 (today); read the PNGs.
- `waybar` reload: `pkill -SIGUSR2 waybar`; the clock still renders and `custom/clock` JSON passes `jq`.
- Left for the user: real hover and click feel, placement on an external monitor, Zen `--search` opening a tab.

## Progress / handoff

- Done (2026-11-07, uncommitted): research, decisions, plan; `data.py`, `it_set.json`, `holidays-custom.json`, `snapshot.json`, `malayalam.py`, `tests/` (14 pass: `cd .config/waybar/scripts/kcal && python3 -I -m unittest discover -s tests -t .`).
- Done too: `kcal.py` (popup, toggle pid file, `--screenshot/--month/--today/--hover`), `clock.sh`, waybar `custom/clock` + style; screenshots 2026-08/2026-11 checked; today = gray fill (user, 2026-11-07).
- Done 2026-11-07 (committed): sway `$mod+Shift+d` toggles the popup (`$mod+Shift+k` clashes with move up); list rows and other-month days clickable, pointer cursors, keyboard nav (arrows, PgUp/PgDn, t, Enter), next-holiday footer, legend, Malayalam-script title, right-click copies via wl-copy, symmetric nav row. Close-on-focus-loss was tried and removed (focus-follows-mouse closed it at once).
- Done 2026-11-07 (c6f337d): click outside closes the popup. An invisible full-screen layer surface (`kcal-backdrop`, TOP layer, exclusive zone -1) sits under the OVERLAY popup; a click on it closes both. It covers only the output the popup opens on.
- Done 2026-11-07 (c6f337d): paper wall-calendar restyle after the Mathrubhumi sheet (user photo, not in repo). Off-white page, black ink, red `#b3181e`; typed wordmark (no logo file: trademark, public repo); mini prev/next months in the masthead corners (click to navigate); Malayalam weekday header with red Sunday; big Adwaita Sans Black numerals; cell footers show holiday / 2nd-4th Saturday / Malayalam month start; left column = clickable holidays by date, right = Malayalam month span, Kochi sunrise/sunset (`ml.sun_times`), key. ~745x630px. Optional font: `rit-keraleeyam-fonts` for the wordmark.
- Done 2026-11-07 (c6f337d): alignment pass. Month bar pickers are Labels with a markup link (Button/MenuButton/EventBox drop the Box baseline; measured 6-7px off) so 1202, the Malayalam month, the year and the month share one baseline; grid menus (months 3 cols, years 6 cols). Today shows only when away from today. Tagline moved into the strip; side headings flush with the grid top; date columns fixed-width. Not verified: opening the year/month menu with a real click on the layer surface.
- Done 2026-11-07, removed the same day: a newspaper masthead logo was committed, then purged from all history with `git filter-repo` (trademark, public repo). The user's copy lives outside the repo in `~/.config/kcal/masthead.png`.
- Done 2026-11-07: shareable build. `settings.py` reads `~/.config/kcal/config.json` (masthead text/image/height, search command/url) plus `style.css` override; default masthead `കേരള കലണ്ടർ`. Layer-shell when supported, else an undecorated floating window that closes on focus loss (tested: sway layer, `KCAL_NO_LAYER=1` xdg_shell, `GDK_BACKEND=x11` XWayland dialog, class `Kcal`). Clipboard falls back to GTK; `/proc` check falls back to `kill -0`; XDG cache path. `clock.sh` moved into `kcal/`. README, install.sh (dnf/pacman/apt), screenshots, example SVG masthead. Branch `kcal` = the folder split out with `git filter-repo --subdirectory-filter`.

## Progress / handoff

- Re-sync the `kcal` branch after changing the folder on main (no `git subtree` on this Fedora): `rm -rf /tmp/kcal-split && git clone -q --no-local . /tmp/kcal-split && git -C /tmp/kcal-split filter-repo --force --subdirectory-filter .config/waybar/scripts/kcal && git fetch -f /tmp/kcal-split main:kcal`. The branch fast-forwards while main's history stays linear.
- Blog post updated the same day (dracufolio 06eb0e6): Sway screenshot `public/appwrite/blog/kerala-calendar-on-sway.webp` (lossless, 1280x1010 from a 1.5x capture).
- Screenshots: `KCAL_CONFIG=/nonexistent ./kcal.py --screenshot screenshots/month.png --month 2026-08 --today 2026-08-17 --hover 2026-08-28 --scale 2`; `sway.png` is a grim capture of HDMI-A-1 top-right (880x680 from x=1040) on an empty workspace, SSID painted over.
- Untested: focus-out close on a real X11 session, GNOME Wayland placement, Arch/Debian package names in install.sh.
- Blog post: dracufolio `app/blog/(posts)/kerala-calendar-for-waybar/page.mdx`.
- Published 2026-11-07 by the user: swaydots main e13aa6f (history rewritten, logo purged), branch `kcal`, dracufolio 06eb0e6.
- Next (user, 2026-11-07): give the calendar its own repo so it can be starred. The user creates the repo and publishes the `kcal` branch as its `main`. Then: update the clone URL in `kcal/README.md` and in the blog post (Install section and last paragraph), add a LICENSE (ask, MIT suggested), give the user the command to delete the `kcal` branch from swaydots, and add a re-sync line here (split as above, then send `kcal` to the new repo's `main`). Still open: GitHub Support cached-views request for the old swaydots commits.
- Next: user checks hover/click feel, external monitor, keyboard with the mouse elsewhere (keys follow focus).
- Gotchas: officeholidays SUMMARY carries `LANGUAGE=en-us:` before the text; the feed has typos; Google ICS DTSTART comes in the `;VALUE=DATE:` form.
- Kerala feed has no New Year (filled from Google) and lists Bakrid on 2 days in 2026 (27+28 May): only the first stays red (override in holidays-custom.json).
- PyPI `kollavarsham` is jsii (needs Node) so not used at runtime; own implementation in malayalam.py. SS-based oracle disagreed on 42/192 month starts (different rule), so the test table is a regression table plus pinned Chingam 1 anchors.
- OPEN: Vishu 2026: gazette says 15 Apr, Google 14 Apr, malayalam.py gives Medam 1 = 14 Apr (Mesha sankranti 09:12 IST, before the 3/5 cutoff). The user should check a printed calendar.
