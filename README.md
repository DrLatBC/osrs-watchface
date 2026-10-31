# OSRS watch face

An Old School RuneScape face for the Amazfit Active 2 (Round, 466x466, Zepp OS 4),
installed through Gadgetbridge. Personal use only; not published anywhere.

- **Orbs** (official in-game sprites) fill from the bottom in 5% steps:
  - HP: last heart rate. Full at resting HR, empty at 220 - age.
  - Prayer: SpO2. Empty at 85%, full at 100%.
  - Run: steps toward the daily step goal.
  - World map: current temperature (needs Gadgetbridge to send weather).
- **Compass** (official minimap sprite) on top of the ring turns so N points north;
  left out if the watch won't give a face the compass.
- **Time** in the OSRS Bold-12 font, everything else in Plain-11. 12h shows am/pm
  with no leading zero; 24h is zero-padded.
- **Always-on**: time and date only, on black.
- Battery in the potion plaque.

## Build (local Windows, from this folder)

```powershell
npm install -g @zeppos/zeus-cli@1.9.3   # once; a local install breaks its module aliases
python art/make_art.py                  # images, art/mockup.png, watchface/layout.js
zeus build                              # dist/<appId>-OSRS-<version>-<stamp>.zab; no Zepp login needed
zeus prune --ip                         # drops intermediate products (1.1 MB -> ~230 KB)
```

Bump `app.version` in `app.json` for each build you install.

## Install

Copy the `.zab` to the phone, open it with Gadgetbridge's **FW/App installer**, tap
**Install**. Gadgetbridge picks the package by the watch's deviceSource (all eight
Active 2 Round values are in `app.json`). Don't use the Zepp app.

## Layout

- `art/make_art.py` draws everything: stonework, ring, plates, orb fill levels,
  compass dials, digit images. It writes `watchface/layout.js` (positions and every
  image size), so the mockup and the watch share one set of numbers.
- `art/osrs_font.py` renders the RuneStar font dumps in `art/fonts` (CC0).
- `art/sprites` holds the OSRS Wiki sprites.
- `watchface/index.js` is the face.

## Runtime traps (Active 2, Zepp OS 4)

- There are no `hmUI`/`hmSensor` globals; import `@zos/ui`, `@zos/sensor`, `@zos/app`,
  `@zos/user`. An exception in `build()` is swallowed into a black screen, so every
  platform call is guarded.
- Sensors throw without their `app.json` permission.
- `HeartRate.getCurrent()` reads 0 on the watch; use `getLast()`.
- `BloodOxygen.getCurrent()` stays empty even after a manual reading; the face falls
  back to `getLastFewHour()` and `getLastDay()`.
- Image digits need fixed-width cells, and an `IMG` can't be scaled: its w/h must
  match the file.
