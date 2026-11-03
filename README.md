# OSRS watch face

An Old School RuneScape face for the Amazfit Active 2 (Round, 466x466, Zepp OS 4),
installed through Gadgetbridge. Free and non-commercial.

> *Created using intellectual property belonging to Jagex Limited under the terms
> of Jagex's [Fan Content Policy](https://legal.jagex.com/docs/policies/fan-content-policy).
> This content is not endorsed by or affiliated with Jagex.*

- **Orbs** (official in-game sprites) fill from the bottom in 5% steps:
  - HP: heart rate, measured live while the screen is on (the watch's last
    background reading until the first live one). Full at resting HR, empty at
    220 - age.
  - Prayer: SpO2. Empty at 85%, full at 100%.
  - Run: steps toward the daily step goal.
  - World map: current temperature. Tapping it or its plate opens the watch's
    Weather app. Weather comes from Breezy Weather on the phone (Settings ->
    External modules -> Gadgetbridge); Gadgetbridge has no network access of its own.
- **Compass** (official minimap sprite) on top of the ring turns so N points north;
  left out if the watch won't give a face the compass. While awake it runs at the
  high report rate and is also polled every 200 ms; an uncalibrated compass
  ('INVALID') holds the last heading.
- **Sun and moon** ride the ring: the sun from sunrise at the 9 o'clock joint over
  the top to sunset at 3, the moon through the night along the bottom, each at the
  pace of that day's daylight or darkness. Whatever they pass behind (an orb and
  its plate, the compass, the potion plaque) lights up around its edges, gold for
  the sun and silver for the moon. The moon shows its phase, worked out from the
  date. Sunrise (gold, up arrow) and sunset (orange, down arrow) times sit outside
  the 9 and 3 joints under a horizon icon. Times come from
  the weather forecast (today's and tomorrow's sunrise); without one the sky is empty.
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
  compass dials, digit images, the sun, moon phases and every glow frame (and
  `art/sky_states.png`, the sky at six times of day). It writes `watchface/layout.js` (positions and every
  image size), so the mockup and the watch share one set of numbers.
- `art/osrs_font.py` renders the RuneStar font dumps in `art/fonts` (CC0).
- `art/sprites` holds the OSRS Wiki sprites.
- `watchface/index.js` is the face.

## Runtime traps (Active 2, Zepp OS 4)

- There are no `hmUI`/`hmSensor` globals; import `@zos/ui`, `@zos/sensor`, `@zos/app`,
  `@zos/user`. An exception in `build()` is swallowed into a black screen, so every
  platform call is guarded.
- Sensors throw without their `app.json` permission.
- `HeartRate.getCurrent()` only has a value inside an `onCurrentChange` callback,
  which starts continuous measurement until `offCurrentChange`. `getLast()` is the
  background reading and never includes live results.
- `BloodOxygen.getCurrent()` stays empty even after a manual reading; the face falls
  back to `getLastFewHour()` and `getLastDay()`.
- `IMG_CLICK` with a `data_type` opens that system app on a tap; it needs a `src`,
  so the globe's tap area is a transparent `images/tap/globe.png`.
- Widgets layer in creation order. The sun and moon go in before everything they
  pass behind, and the parts of `bg.png` they pass behind (plates, globe, plaque)
  are laid back over them from `images/over/`.
- `Weather.getForecast().tideData.data[i]` holds day i's sunrise and sunset as
  `{hour, minute}`; the face takes index 0 as today.
- Image digits need fixed-width cells, and an `IMG` can't be scaled: its w/h must
  match the file.
