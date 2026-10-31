import * as hmUI from '@zos/ui'
import * as zapp from '@zos/app'
import * as sensor from '@zos/sensor'
import * as user from '@zos/user'

import { CENTER, FILL_STEPS, COMPASS_STEPS, LAYOUT, SIZES } from './layout.js'

// This firmware has no hmUI/hmSensor globals, and an exception thrown in
// build() is swallowed into a black screen. So every platform call that
// might be missing or refused goes through guard() and degrades to "no
// value" instead.

function guard(fn, fallback = null) {
  try {
    return fn()
  } catch (e) {
    return fallback
  }
}

function make(name) {
  const Ctor = sensor[name]
  return typeof Ctor === 'function' ? guard(() => new Ctor()) : null
}

function call(obj, method, ...args) {
  if (!obj || typeof obj[method] !== 'function') return null
  return guard(() => obj[method](...args))
}

// A count that may legitimately be 0 (steps, battery).
function count(v) {
  return typeof v === 'number' && isFinite(v) && v >= 0 ? v : null
}

// A reading where 0 means "no reading" (heart rate, SpO2, age).
function reading(v) {
  return typeof v === 'number' && isFinite(v) && v > 0 ? v : null
}

const SHOW = hmUI.show_level || {}
const NORMAL = SHOW.ONLY_NORMAL
const BOTH = SHOW.ONLY_NORMAL | SHOW.ONAL_AOD

function image(src, x, y, level) {
  const opts = { x, y, w: 1, h: 1, src: '' }
  if (src) Object.assign(opts, { w: SIZES[src][0], h: SIZES[src][1], src })
  if (level !== undefined) opts.show_level = level
  return hmUI.createWidget(hmUI.widget.IMG, opts)
}

// Images cannot be scaled, so w/h always follow the file; an empty source
// at 1x1 draws nothing.
function setImage(widget, src, x, y) {
  if (!src) {
    widget.setProperty(hmUI.prop.MORE, { x, y, w: 1, h: 1, src: '' })
    return
  }
  const [w, h] = SIZES[src]
  widget.setProperty(hmUI.prop.MORE, { x, y, w, h, src })
}

const GLYPH_NAMES = { '-': { green: 'minus', cream: 'dash' }, '°': { green: 'degree' }, '%': { white: 'percent' } }

function glyph(set, ch) {
  const name = GLYPH_NAMES[ch] ? GLYPH_NAMES[ch][set] : ch
  return `images/${set}/${name}.png`
}

function widthOf(src) {
  return SIZES[src][0]
}

// A row of image widgets showing one string, aligned inside a box.
function textRun(slots, level) {
  const widgets = []
  for (let i = 0; i < slots; i++) widgets.push(image('', 0, 0, level))
  return {
    show(srcs, box) {
      const total = srcs.reduce((sum, src) => sum + widthOf(src), 0)
      let x = box.x
      if (box.align === 'right') x = box.x + box.w - total
      else if (box.align === 'center') x = box.x + Math.round((box.w - total) / 2)
      widgets.forEach((widget, i) => {
        const src = srcs[i]
        setImage(widget, src, x, box.y)
        if (src) x += widthOf(src)
      })
    },
  }
}

function digits(set, text) {
  return String(text).split('').map((ch) => glyph(set, ch))
}

function fillLevel(fraction) {
  if (fraction === null) return FILL_STEPS
  return Math.round(Math.min(1, Math.max(0, fraction)) * FILL_STEPS)
}

function pad2(n) {
  return (n < 10 ? '0' : '') + n
}

WatchFace({
  build() {
    const isAod = guard(() => zapp.getScene() === zapp.SCENE_AOD, false)
    const time = make('Time')
    const D = SIZES['images/big/0.png'][0]
    const t = LAYOUT.time

    if (isAod) {
      hmUI.createWidget(hmUI.widget.FILL_RECT, { x: 0, y: 0, w: 466, h: 466, color: 0x000000 })
    } else {
      image('images/bg.png', 0, 0, NORMAL)
    }

    // Time and date are drawn in both scenes; everything else only when awake.
    const hourTens = image('', 0, 0, BOTH)
    const hourOnes = image('', 0, 0, BOTH)
    image('images/big/colon.png', t.colon_x, t.y, BOTH)
    const minTens = image('', 0, 0, BOTH)
    const minOnes = image('', 0, 0, BOTH)
    const ampm = image('', 0, 0, BOTH)
    const weekRun = textRun(1, BOTH)
    const dateRun = textRun(10, BOTH)
    const secsRun = isAod ? null : textRun(2, NORMAL)
    const H12 = sensor.TIME_HOUR_FORMAT_12 !== undefined ? sensor.TIME_HOUR_FORMAT_12 : 0

    let secsBox = null

    function drawClock() {
      if (!time) return
      const h = time.getHours()
      const twelve = guard(() => time.getHourFormat() === H12, false)
      const shown = twelve ? h % 12 || 12 : h
      const tens = Math.floor(shown / 10)
      setImage(hourTens, twelve && tens === 0 ? '' : `images/big/${tens}.png`, t.colon_x - 2 * D, t.y)
      setImage(hourOnes, `images/big/${shown % 10}.png`, t.colon_x - D, t.y)
      const m = time.getMinutes()
      setImage(minTens, `images/big/${Math.floor(m / 10)}.png`, t.minute_x, t.y)
      setImage(minOnes, `images/big/${m % 10}.png`, t.minute_x + D, t.y)
      setImage(ampm, twelve ? `images/ampm/${h < 12 ? 'am' : 'pm'}.png` : '', t.ampm_x, t.ampm_y)

      // "Fri, 30-10-2026" then the seconds, centred as one line.
      const d = LAYOUT.date
      const week = `images/week/${time.getDay() - 1}.png`
      const date = digits('cream', `${pad2(time.getDate())}-${pad2(time.getMonth())}-${time.getFullYear()}`)
      const dateW = date.reduce((sum, src) => sum + widthOf(src), 0)
      const secsW = 2 * widthOf('images/cream/0.png')
      const full = widthOf(week) + d.space + dateW + (secsRun ? d.secs_gap + secsW : 0)
      const x0 = Math.round(CENTER - full / 2)
      const digitsX = x0 + widthOf(week) + d.space
      weekRun.show([week], { x: x0, y: d.y })
      dateRun.show(date, { x: digitsX, y: d.y })
      secsBox = { x: digitsX + dateW + d.secs_gap, y: d.y }
    }

    function drawSeconds() {
      if (!secsRun || !secsBox || !time) return
      secsRun.show(digits('cream', pad2(time.getSeconds())), secsBox)
    }

    drawClock()
    drawSeconds()
    call(time, 'onPerMinute', () => drawClock())

    if (isAod) return

    // ---------------------------------------------------------- awake only

    const heart = make('HeartRate')
    const oxygen = make('BloodOxygen')
    const step = make('Step')
    const battery = make('Battery')
    const age = reading(guard(() => user.getProfile().age))

    const orbs = {}
    for (const key of ['hp', 'prayer', 'run']) {
      const o = LAYOUT.orbs[key]
      const src = `images/orbs/${key}/${FILL_STEPS}.png`
      orbs[key] = image(src, o.cx - SIZES[src][0] / 2, o.cy - SIZES[src][1] / 2, NORMAL)
    }

    function setOrb(key, fraction) {
      const o = LAYOUT.orbs[key]
      const src = `images/orbs/${key}/${fillLevel(fraction)}.png`
      setImage(orbs[key], src, o.cx - SIZES[src][0] / 2, o.cy - SIZES[src][1] / 2)
    }

    const plates = {}
    for (const key of ['hp', 'prayer', 'run']) {
      plates[key] = textRun(5, NORMAL)
    }
    const batteryRun = textRun(4, NORMAL)

    // Current temperature has no sensor-class getter; the face data type
    // does it, signs and all, when the firmware offers it. Gadgetbridge has
    // to be sending weather for it to show anything.
    const g = LAYOUT.plates.globe.text
    const weatherType = hmUI.data_type && hmUI.data_type.WEATHER_CURRENT
    let weatherRun = null
    const weatherWidget =
      hmUI.widget.TEXT_IMG !== undefined && weatherType !== undefined
        ? guard(() =>
            hmUI.createWidget(hmUI.widget.TEXT_IMG, {
              x: g.x,
              y: g.y,
              w: g.w + widthOf('images/green/degree.png'),
              h: SIZES['images/green/0.png'][1],
              type: weatherType,
              font_array: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `images/green/${n}.png`),
              negative_image: 'images/green/minus.png',
              unit_en: 'images/green/degree.png',
              unit_sc: 'images/green/degree.png',
              unit_tc: 'images/green/degree.png',
              align_h: hmUI.align.LEFT,
              show_level: NORMAL,
            }),
          )
        : null
    if (!weatherWidget) weatherRun = textRun(2, NORMAL)

    const spo2 = (v) => (typeof v === 'number' && v > 50 && v <= 100 ? v : null)

    // The newest SpO2 the watch has, or null. getCurrent() stays empty on
    // the watch even after a manual reading, so the reading history is
    // needed. The hourly averages come last, since which end is the latest
    // hour isn't documented.
    function readSpo2() {
      const cur = call(oxygen, 'getCurrent')
      const now = spo2(cur && typeof cur === 'object' ? cur.value : cur)
      if (now !== null) return now

      const recent = call(oxygen, 'getLastFewHour', 24)
      if (Array.isArray(recent)) {
        let best = null
        for (const r of recent) {
          if (r && spo2(r.spo2) !== null && (best === null || r.time > best.time)) best = r
        }
        if (best) return best.spo2
      }

      const hourly = call(oxygen, 'getLastDay')
      if (Array.isArray(hourly)) {
        for (let i = hourly.length - 1; i >= 0; i--) {
          if (spo2(hourly[i]) !== null) return hourly[i]
        }
      }
      return null
    }

    function plate(key, text) {
      const box = LAYOUT.plates[key].text
      plates[key].show(digits('green', text), box)
    }

    function drawStats() {
      // HP: full at resting heart rate, empty at 220 - age.
      const hr = reading(call(heart, 'getLast')) || reading(call(heart, 'getCurrent'))
      const rest = reading(call(heart, 'getResting'))
      const max = age ? 220 - age : null
      plate('hp', hr === null ? '--' : Math.round(hr))
      setOrb('hp', hr !== null && rest !== null && max !== null && max > rest ? 1 - (hr - rest) / (max - rest) : null)

      // Prayer: SpO2, empty at 85% and full at 100%.
      const ox = readSpo2()
      plate('prayer', ox === null ? '--' : Math.round(ox))
      setOrb('prayer', ox === null ? null : (ox - 85) / 15)

      // Run: steps toward the daily step goal.
      const steps = count(call(step, 'getCurrent'))
      const goal = reading(call(step, 'getTarget'))
      plate('run', steps === null ? '--' : Math.min(99999, steps))
      setOrb('run', steps !== null && goal !== null ? steps / goal : null)

      if (weatherRun) weatherRun.show(digits('green', '--'), { x: g.x, y: g.y })

      const b = count(call(battery, 'getCurrent'))
      const bt = LAYOUT.battery.text
      batteryRun.show(b === null ? digits('white', '') : digits('white', `${Math.round(b)}%`), {
        x: bt.x,
        y: bt.y,
        w: bt.w,
        align: 'center',
      })
    }

    // Compass: the dial turns so N points north. Left out entirely when the
    // firmware won't give a watch face the compass.
    const compass = make('Compass')
    const cp = LAYOUT.compass
    const compassSrc = (frame) => `images/compass/${frame}.png`
    const half = SIZES[compassSrc(0)][0] / 2
    let compassWidget = compass ? image(compassSrc(0), cp.cx - half, cp.cy - half, NORMAL) : null

    function drawCompass() {
      if (!compassWidget) return
      const angle = call(compass, 'getDirectionAngle')
      const frame = typeof angle === 'number' ? Math.round(angle / (360 / COMPASS_STEPS)) % COMPASS_STEPS : 0
      setImage(compassWidget, compassSrc(frame), cp.cx - half, cp.cy - half)
    }

    if (compass) call(compass, 'onChange', drawCompass)

    let ticker = null
    function tick() {
      drawSeconds()
      if (time && time.getSeconds() % 30 === 0) drawStats()
    }

    hmUI.createWidget(hmUI.widget.WIDGET_DELEGATE, {
      resume_call: () => {
        drawClock()
        drawStats()
        drawSeconds()
        if (compassWidget && !guard(() => (compass.start(), true), false)) {
          setImage(compassWidget, '', cp.cx, cp.cy)
          compassWidget = null
        }
        drawCompass()
        if (ticker === null) ticker = setInterval(tick, 1000)
      },
      pause_call: () => {
        if (ticker !== null) {
          clearInterval(ticker)
          ticker = null
        }
        if (compassWidget) call(compass, 'stop')
      },
    })

    drawStats()
    call(heart, 'onLastChange', drawStats)
  },

  onInit() {},
  onDestroy() {},
})
