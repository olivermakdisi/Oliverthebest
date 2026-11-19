import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Forex Signals", layout="centered")

st.markdown(
    "<style>.stApp{background:#000}#MainMenu{visibility:hidden}footer{visibility:hidden}"
    "header{visibility:hidden}.block-container{padding:0}</style>",
    unsafe_allow_html=True,
)

HTML = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:sans-serif;max-width:480px;margin:auto;padding:16px;background:#000;color:#00e676}
h2{text-align:center;color:#00e676;margin:4px 0 12px}
.msg{direction:ltr;text-align:left;background:#0a0a0a;border:1px solid #1b5e20;border-radius:14px;padding:12px 14px;margin:10px 0;font-size:17px;line-height:1.6;color:#00e676}
.msg .t{display:block;text-align:right;font-size:12px;color:#2e7d32}
.sig{border:2px solid #00e676}
.wait{text-align:center;direction:rtl;color:#2e7d32}
.res{display:inline-block;padding:0 8px;border-radius:6px;font-weight:bold}
.WIN{background:#00e676;color:#000}
.LOSS{background:#000;color:#00e676;border:1px solid #00e676}
.DRAW{background:#1b5e20;color:#000}
.sum{direction:ltr;text-align:center;background:#0a0a0a;border:1px solid #00e676;border-radius:14px;padding:12px;margin:10px 0;font-size:16px;color:#00e676}
.sum b{font-size:28px;display:block}
.sum span{color:#2e7d32;font-size:13px}
small{color:#2e7d32;display:block;text-align:center;margin:10px 0}
</style>
</head>
<body>
<h2>إشارات الفوركس</h2>
<div id="sum"></div>
<div id="cur"></div>
<div id="reports"></div>
<small>Not financial advice. Trading involves risk of loss.</small>

<script>
const PAIRS = ["EURUSDT", "GBPUSDT", "AUDUSDT", "USDTTRY", "USDTBRL"];
const KL = "https://api.binance.com/api/v3/klines?interval=1m&limit=60&symbol=";
const PX = "https://api.binance.com/api/v3/ticker/price?symbol=";
const MIN_SAMPLES = 5;

let hist = [], stats = {}, reports = [], n = 1, act = null, lastMin = "", busy = false;

try {
  const s = JSON.parse(localStorage.getItem("fx_state") || "null");
  if (s) { hist = s.hist; stats = s.stats; reports = s.reports; n = s.n; }
} catch (e) {}

function save() {
  try { localStorage.setItem("fx_state", JSON.stringify({ hist, stats, reports, n })); } catch (e) {}
}

function ema(v, p) {
  const k = 2 / (p + 1);
  let e = v[0];
  for (let i = 1; i < v.length; i++) e = v[i] * k + e * (1 - k);
  return e;
}

function rsi(v, p = 14) {
  let g = 0, l = 0;
  const a = v.slice(-(p + 1));
  for (let i = 1; i < a.length; i++) {
    const d = a[i] - a[i - 1];
    if (d > 0) g += d; else l -= d;
  }
  if (l === 0) return 100;
  return 100 - 100 / (1 + (g / p) / (l / p));
}

async function analyze(sym) {
  const kl = await (await fetch(KL + sym)).json();
  const c = kl.slice(0, -1).map(k => parseFloat(k[4]));
  const n = c.length;
  const e9 = ema(c, 9), e21 = ema(c, 21), r = rsi(c);
  const e9p = ema(c.slice(0, -3), 9);
  const last = c[n - 1];
  const up = [
    e9 > e21,
    r > 50 && r < 70,
    last > e21,
    c[n - 1] > c[n - 2] && c[n - 2] > c[n - 3],
    e9 > e9p
  ];
  const dn = [
    e9 < e21,
    r > 30 && r < 50,
    last < e21,
    c[n - 1] < c[n - 2] && c[n - 2] < c[n - 3],
    e9 < e9p
  ];
  const us = up.filter(x => x).length;
  const ds = dn.filter(x => x).length;
  if (up[0] && up[1] && us >= 4)
    return { sym, dir: "UP", why: us + "/5 confirmations: EMA trend, RSI " + r.toFixed(1) + ", momentum" };
  if (dn[0] && dn[1] && ds >= 4)
    return { sym, dir: "DOWN", why: ds + "/5 confirmations: EMA trend, RSI " + r.toFixed(1) + ", momentum" };
  return null;
}

async function price(sym) {
  return (await (await fetch(PX + sym)).json()).price;
}

function reliability(sym, dir) {
  const s = stats[sym + "|" + dir];
  if (!s || s[1] < MIN_SAMPLES) return 50;
  return s[0] * 100 / s[1];
}

function hm(d) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function notify(a) {
  const txt = a.sym + " " + (a.dir === "UP" ? "⬆ UP" : "⬇ DOWN") + " - enter at " + hm(new Date(a.startAt));
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("Signal #" + a.n, { body: txt });
  }
  if (navigator.vibrate) navigator.vibrate(200);
}

function render() {
  let W = 0, T = 0;
  for (const k in stats) { W += stats[k][0]; T += stats[k][1]; }
  document.getElementById("sum").innerHTML = T
    ? "Real win rate<b>" + (W * 100 / T).toFixed(1) + "%</b><span>" + W + " WIN / " + (T - W) + " LOSS (" + T + " trades)</span>"
    : "Real win rate<b>--</b><span>0 trades</span>";
  const cur = document.getElementById("cur");
  if (act) {
    const left = Math.max(0, Math.ceil((act.closeAt - Date.now()) / 1000));
    const pending = !act.entry;
    const wait = Math.max(0, Math.ceil((act.startAt - Date.now()) / 1000));
    cur.innerHTML = '<div class="msg sig">SIGNAL #' + act.n + "<br>" + act.sym + " " +
      (act.dir === "UP" ? "⬆ UP" : "⬇ DOWN") + (pending ? "<br>Enter in: " + wait + "s (" + hm(new Date(act.startAt)) + ")" : "<br>Entry: " + act.entry) +
      "<br>Reason: " + act.why + "<br>Duration: 1 min" +
      '<span class="t">' + hm(act.openAt) + "</span></div>";
  } else {
    cur.innerHTML = '<div class="msg wait">جاري البحث عن إشارة...</div>';
  }
  document.getElementById("reports").innerHTML = reports.map(r => {
    return '<div class="msg">REPORT #' + r.n + "<br>" + r.sym + " " + r.dir +
      "<br>Entry: " + r.entry + "<br>Close: " + r.close +
      '<br>Result: <span class="res ' + r.res + '">' + r.res + "</span>" +
      "<br>Last " + r.total + ": " + r.w + " WIN / " + r.l + " LOSS / " + r.d + " DRAW" +
      '<span class="t">' + r.time + "</span></div>";
  }).join("");
}

async function closeTrade() {
  const kl = await (await fetch(KL + act.sym)).json();
  const k = kl.find(x => x[0] === act.startAt);
  const closed = kl.some(x => x[0] >= act.closeAt);
  if (!k || !closed) {
    if (Date.now() > act.closeAt + 20000) act = null;
    return;
  }
  act.entry = String(parseFloat(k[1]));
  const cp = String(parseFloat(k[4]));
  const d = parseFloat(cp) - parseFloat(act.entry);
  const up = act.dir === "UP";
  const key = act.sym + "|" + act.dir;
  let res;
  if (d === 0) res = "DRAW";
  else if ((d > 0) === up) res = "WIN";
  else res = "LOSS";
  if (res !== "DRAW") {
    if (!stats[key]) stats[key] = [0, 0];
    stats[key][1] += 1;
    if (res === "WIN") stats[key][0] += 1;
  }
  hist.push(res);
  if (hist.length > 30) hist.shift();
  const w = hist.filter(x => x === "WIN").length;
  const l = hist.filter(x => x === "LOSS").length;
  const dr = hist.filter(x => x === "DRAW").length;
  reports.unshift({
    n: act.n, sym: act.sym, dir: act.dir, entry: act.entry, close: cp,
    res, total: hist.length, w, l, d: dr, time: hm(new Date())
  });
  if (reports.length > 20) reports.pop();
  act = null;
  save();
}

async function openTrade() {
  const found = (await Promise.all(PAIRS.map(s => analyze(s).catch(() => null))))
    .filter(x => x);
  if (!found.length) return;
  let best = null, bs = -1;
  for (const f of found) {
    const sc = reliability(f.sym, f.dir);
    if (sc > bs) { bs = sc; best = f; }
  }
  const now = new Date();
  const startAt = Math.ceil(now.getTime() / 60000) * 60000;
  act = { n, sym: best.sym, dir: best.dir, why: best.why, entry: null,
          openAt: now, startAt, closeAt: startAt + 60000 };
  n += 1;
  save();
  notify(act);
}

async function tick() {
  if (!busy) {
    busy = true;
    try {
      const now = new Date();
      if (act && !act.entry && now.getTime() >= act.startAt + 1000) {
        const kl = await (await fetch(KL + act.sym)).json();
        const k = kl.find(x => x[0] === act.startAt);
        if (k) act.entry = String(parseFloat(k[1]));
      }
      if (act && now.getTime() >= act.closeAt + 1000) await closeTrade();
      const key = now.getHours() + ":" + now.getMinutes();
      if (!act && key !== lastMin && now.getSeconds() >= 40) {
        lastMin = key;
        await openTrade();
      }
    } catch (e) {}
    busy = false;
  }
  render();
}

document.addEventListener("click", () => {
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }
}, { once: true });

render();
setInterval(tick, 1000);
</script>
</body>
</html>
"""

components.html(HTML, height=900, scrolling=True)
