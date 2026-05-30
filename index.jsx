import React, { useState, useEffect, useRef } from "react";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";
import {
  Thermometer, Droplets, Flag, ShieldAlert, Activity,
  Waves, Beaker, Clock, Radio, AlertTriangle, CheckCircle2,
} from "lucide-react";

/* =========================================================================
   hospital sink-trap bacterial-risk monitor
   -------------------------------------------------------------------------
   ARCHITECTURE (read this first)
   The React app below is a PURE RENDERER. It does no math.
   All logic — rolling readings, flag detection (turbidity + warm temp),
   sliding-window counting, tier escalation — lives in `createMockBackend`,
   which stands in for your Flask/FastAPI server fed by the ESP32.

   THE PLUG POINT
   The backend talks to the UI through three message types only:
     { type:"reading", ts, sensorId, temp, turbidity }
     { type:"flag",    ts, sensorId, temp, turbidity }
     { type:"status",  sensorId, tier, flagsInWindow, windowHours }
   When the hardware is ready, delete createMockBackend and do:
     const ws = new WebSocket(BACKEND_URL);
     ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
   Nothing else in the UI changes.
   ========================================================================= */

const CONFIG = {
  WARM_TEMP_C: 26,        // at/above this, growth is favored  (backend tunable)
  TURB_FLAG_NTU: 4.5,     // at/above this, water reads "cloudy"
  WINDOW_HOURS: 6,        // sliding window for counting flags
  TIER_WATCH: 1,          // 1–3 flags
  TIER_ELEVATED: 4,       // 4–5 flags  -> close surveillance
  TIER_CRITICAL: 6,       // 6+ flags   -> intervention / quarantine
  EMIT_MS: 1500,          // reading cadence (demo speed)
  INJECT_TICKS: 2,        // length of a simulated contamination pulse
  FLAG_DEBOUNCE_MS: 1200, // min gap between flags on one sensor
  HISTORY: 40,            // sparkline points kept
  TURB_VIS_MAX: 12,       // turbidity that fully clouds the pipe motif
  MONITOR_HOURS: 36,      // 24–48h incubation window (display)
};

/* ---------- tiers ---------- */
const TIERS = {
  normal:   { label: "Normal",   color: "#1fae6f", glow: "rgba(31,174,111,.45)",  icon: CheckCircle2 },
  watch:    { label: "Watch",    color: "#e8a800", glow: "rgba(232,168,0,.5)",    icon: Activity },
  elevated: { label: "Elevated", color: "#f2790f", glow: "rgba(242,121,15,.55)",  icon: AlertTriangle },
  critical: { label: "Critical", color: "#e23b3b", glow: "rgba(226,59,59,.6)",    icon: ShieldAlert },
};
function tierFromCount(n) {
  if (n >= CONFIG.TIER_CRITICAL) return "critical";
  if (n >= CONFIG.TIER_ELEVATED) return "elevated";
  if (n >= CONFIG.TIER_WATCH) return "watch";
  return "normal";
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

/* ---------- seed (used by both the mock backend and initial UI state) ---------- */
const NOW0 = Date.now();
const H = 3600 * 1000;
function pastFlags(n, temps, turbs) {
  // n flags scattered across the last ~5h, within the 6h window
  return Array.from({ length: n }, (_, i) => ({
    ts: NOW0 - Math.floor((i + 1) * (5 * H) / (n + 1)) - Math.random() * 600000,
    temp: temps + Math.random() * 1.5,
    turbidity: turbs + Math.random() * 2,
  }));
}
const SEED = [
  { id: "S-01", room: "Room 312", label: "Sink · Patient Bay", baseTemp: 27.2, baseTurb: 1.1, seedFlags: [] },
  { id: "S-02", room: "Room 312", label: "Drain · Handwash",   baseTemp: 22.8, baseTurb: 0.9, seedFlags: [] },
  { id: "S-03", room: "Room 308", label: "Sink · ICU Bay",     baseTemp: 28.4, baseTurb: 2.0, seedFlags: pastFlags(4, 28, 6) },
  { id: "S-04", room: "Ward 401", label: "Sink · West Ward",   baseTemp: 29.1, baseTurb: 2.4, seedFlags: pastFlags(7, 29, 7) },
];

function genHist(base, spread, n) {
  return Array.from({ length: n }, (_, i) => ({
    t: NOW0 - (n - i) * CONFIG.EMIT_MS,
    v: +(base + (Math.random() - 0.5) * spread).toFixed(2),
  }));
}

/* =========================================================================
   THE BACKEND  (everything math-heavy lives here)
   ========================================================================= */
function createMockBackend(onMessage) {
  const state = SEED.map((s) => ({
    id: s.id, baseTemp: s.baseTemp, baseTurb: s.baseTurb,
    temp: s.baseTemp, turb: s.baseTurb,
    flags: s.seedFlags.map((f) => ({ ...f })),
    inject: 0, lastFlagAt: 0, lastTier: null, lastCount: -1,
  }));
  let timer = null;

  function emitStatus(ss) {
    const cutoff = Date.now() - CONFIG.WINDOW_HOURS * H;
    const count = ss.flags.filter((f) => f.ts >= cutoff).length;
    const tier = tierFromCount(count);
    if (tier !== ss.lastTier || count !== ss.lastCount) {
      ss.lastTier = tier; ss.lastCount = count;
      onMessage({ type: "status", sensorId: ss.id, tier, flagsInWindow: count, windowHours: CONFIG.WINDOW_HOURS });
    }
  }

  function step(ss) {
    const now = Date.now();
    // temperature: drift around the sensor's base, warms slightly during a pulse
    ss.temp = clamp(ss.baseTemp + (Math.random() - 0.5) * 0.6 + (ss.inject > 0 ? 1.8 : 0), 15, 40);
    // turbidity: baseline noise + contamination pulse or rare natural bump
    let t = ss.baseTurb + Math.random() * 0.7;
    if (ss.inject > 0) { t += 6 + Math.random() * 3; ss.inject--; }
    else if (Math.random() < 0.012) { t += 3 + Math.random() * 2; }
    ss.turb = Math.max(0, t);
    onMessage({ type: "reading", ts: now, sensorId: ss.id, temp: ss.temp, turbidity: ss.turb });

    // FLAG RULE: turbidity high AND temperature warm  (debounced into discrete moments)
    if (ss.turb >= CONFIG.TURB_FLAG_NTU && ss.temp >= CONFIG.WARM_TEMP_C &&
        now - ss.lastFlagAt >= CONFIG.FLAG_DEBOUNCE_MS) {
      ss.lastFlagAt = now;
      ss.flags.push({ ts: now, temp: ss.temp, turbidity: ss.turb });
      onMessage({ type: "flag", ts: now, sensorId: ss.id, temp: ss.temp, turbidity: ss.turb });
    }
    emitStatus(ss);
  }

  return {
    start() {
      if (timer) return;
      state.forEach(emitStatus);                 // initial tiers
      timer = setInterval(() => state.forEach(step), CONFIG.EMIT_MS);
    },
    stop() { clearInterval(timer); timer = null; },
    inject(id) { const ss = state.find((s) => s.id === id); if (ss) ss.inject = CONFIG.INJECT_TICKS; },
  };
}

/* =========================================================================
   UI PIECES
   ========================================================================= */
const fmtTime = (ts) => new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

function Sparkline({ data, color }) {
  return (
    <div style={{ height: 46, width: "100%" }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, bottom: 4, left: 0, right: 0 }}>
          <YAxis hide domain={["dataMin - 1", "dataMax + 1"]} />
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2.4} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function StatTile({ icon: Icon, name, value, unit, hot, data, color }) {
  return (
    <div className={"glass tile" + (hot ? " tile-hot" : "")}>
      <div className="tile-head">
        <span className="tile-ico" style={{ color }}><Icon size={18} /></span>
        <span className="tile-name">{name}</span>
        {hot && <span className="tile-tag">over threshold</span>}
      </div>
      <div className="tile-val">{value}<span className="tile-unit">{unit}</span></div>
      <Sparkline data={data} color={color} />
    </div>
  );
}

function WaterPipe({ turbidity }) {
  const ratio = clamp(turbidity / CONFIG.TURB_VIS_MAX, 0, 1);
  // clear aqua -> murky olive as turbidity climbs
  const r = Math.round(72 + ratio * 70), g = Math.round(190 - ratio * 70), b = Math.round(205 - ratio * 150);
  return (
    <div className="pipe-wrap">
      <div className="pipe">
        <div className="pipe-water" style={{ background: `linear-gradient(180deg, rgba(${r},${g},${b},.55), rgba(${r - 20},${g - 20},${b - 10},.9))` }}>
          <span className="bubble b1" /><span className="bubble b2" /><span className="bubble b3" />
        </div>
        <div className="pipe-gloss" />
      </div>
      <div className="pipe-cap">{turbidity.toFixed(1)} <small>NTU</small></div>
    </div>
  );
}

function TierBadge({ tier, count, windowHours }) {
  const t = TIERS[tier]; const Icon = t.icon;
  return (
    <div className="tier-badge" style={{ "--tc": t.color, "--tg": t.glow }}>
      <Icon size={26} />
      <div>
        <div className="tier-label">{t.label}</div>
        <div className="tier-sub">{count} flag{count === 1 ? "" : "s"} in {windowHours} h window</div>
      </div>
    </div>
  );
}

function FlagMeter({ count }) {
  const marks = [
    { n: CONFIG.TIER_WATCH, k: "watch" },
    { n: CONFIG.TIER_ELEVATED, k: "elevated" },
    { n: CONFIG.TIER_CRITICAL, k: "critical" },
  ];
  const max = CONFIG.TIER_CRITICAL + 2;
  return (
    <div className="meter">
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${clamp(count / max, 0, 1) * 100}%`, background: TIERS[tierFromCount(count)].color }} />
        {marks.map((m) => (
          <span key={m.k} className="meter-mark" style={{ left: `${(m.n / max) * 100}%`, background: TIERS[m.k].color }} title={`${TIERS[m.k].label} @ ${m.n}`} />
        ))}
      </div>
      <div className="meter-legend">
        <span>0</span><span style={{ color: TIERS.watch.color }}>watch {CONFIG.TIER_WATCH}</span>
        <span style={{ color: TIERS.elevated.color }}>elevated {CONFIG.TIER_ELEVATED}</span>
        <span style={{ color: TIERS.critical.color }}>critical {CONFIG.TIER_CRITICAL}+</span>
      </div>
    </div>
  );
}

/* =========================================================================
   MAIN
   ========================================================================= */
export default function WaterSentinelDashboard() {
  const [sensors, setSensors] = useState(() => {
    const o = {};
    for (const s of SEED) {
      const cutoff = NOW0 - CONFIG.WINDOW_HOURS * H;
      const count = s.seedFlags.filter((f) => f.ts >= cutoff).length;
      o[s.id] = {
        id: s.id, room: s.room, label: s.label,
        temp: s.baseTemp, turbidity: s.baseTurb,
        tempHist: genHist(s.baseTemp, 1.2, 24),
        turbHist: genHist(s.baseTurb, 0.8, 24),
        flags: [...s.seedFlags].sort((a, b) => b.ts - a.ts),
        tier: tierFromCount(count), flagsInWindow: count, windowHours: CONFIG.WINDOW_HOURS,
      };
    }
    return o;
  });
  const [selected, setSelected] = useState("S-01");
  const [clock, setClock] = useState(Date.now());
  const backend = useRef(null);
  const monitorStart = useRef(NOW0 - 14 * H);

  function handleMessage(msg) {
    setSensors((prev) => {
      const s = prev[msg.sensorId]; if (!s) return prev;
      if (msg.type === "reading") {
        return { ...prev, [msg.sensorId]: {
          ...s, temp: msg.temp, turbidity: msg.turbidity,
          tempHist: [...s.tempHist, { t: msg.ts, v: +msg.temp.toFixed(2) }].slice(-CONFIG.HISTORY),
          turbHist: [...s.turbHist, { t: msg.ts, v: +msg.turbidity.toFixed(2) }].slice(-CONFIG.HISTORY),
        }};
      }
      if (msg.type === "flag") {
        return { ...prev, [msg.sensorId]: {
          ...s, flags: [{ ts: msg.ts, temp: msg.temp, turbidity: msg.turbidity }, ...s.flags].slice(0, 60),
        }};
      }
      if (msg.type === "status") {
        return { ...prev, [msg.sensorId]: {
          ...s, tier: msg.tier, flagsInWindow: msg.flagsInWindow, windowHours: msg.windowHours,
        }};
      }
      return prev;
    });
  }

  useEffect(() => {
    const b = createMockBackend(handleMessage);
    backend.current = b; b.start();
    const c = setInterval(() => setClock(Date.now()), 1000);
    return () => { b.stop(); clearInterval(c); };
  }, []);

  const sel = sensors[selected];
  const tempHot = sel.temp >= CONFIG.WARM_TEMP_C;
  const turbHot = sel.turbidity >= CONFIG.TURB_FLAG_NTU;
  const rooms = [...new Set(SEED.map((s) => s.room))];
  const elapsedH = (clock - monitorStart.current) / H;
  const monPct = clamp(elapsedH / CONFIG.MONITOR_HOURS, 0, 1) * 100;

  return (
    <div className="app">
      <style>{CSS}</style>
      <div className="bg-orb o1" /><div className="bg-orb o2" /><div className="bg-orb o3" />

      {/* top bar */}
      <header className="topbar glass">
        <div className="brand">
          <span className="brand-mark"><Waves size={22} /></span>
          <div>
            <div className="brand-name">Water<b>Sentinel</b></div>
            <div className="brand-sub">Sink-trap bacterial-risk monitoring · {CONFIG.MONITOR_HOURS} h incubation watch</div>
          </div>
        </div>
        <div className="live-pill">
          <Radio size={13} className="pulse" /> Live · <span className="muted">mock feed</span>
          <span className="live-clock">{new Date(clock).toLocaleTimeString()}</span>
        </div>
      </header>

      <div className="layout">
        {/* rail */}
        <aside className="rail glass">
          <div className="rail-title"><Beaker size={15} /> Rooms &amp; Sensors</div>
          {rooms.map((room) => (
            <div key={room} className="rail-room">
              <div className="rail-room-name">{room}</div>
              {SEED.filter((s) => s.room === room).map((s) => {
                const d = sensors[s.id]; const t = TIERS[d.tier];
                return (
                  <button key={s.id} className={"rail-item" + (selected === s.id ? " active" : "")} onClick={() => setSelected(s.id)}>
                    <span className="rail-dot" style={{ background: t.color, boxShadow: `0 0 8px ${t.glow}` }} />
                    <span className="rail-item-label">{s.label}</span>
                    <span className="rail-item-turb">{d.turbidity.toFixed(1)}<small> NTU</small></span>
                  </button>
                );
              })}
            </div>
          ))}
          <div className="rail-foot">All sensors stream to one dashboard.<br />Add a sink → it appears here.</div>
        </aside>

        {/* main */}
        <main className="main">
          <section className="hero glass" style={{ "--tc": TIERS[sel.tier].color, "--tg": TIERS[sel.tier].glow }}>
            <div className="hero-id">
              <div className="hero-room">{sel.room}</div>
              <div className="hero-label">{sel.label}</div>
              <div className="hero-meta"><span className="mono">{sel.id}</span></div>
            </div>
            <TierBadge tier={sel.tier} count={sel.flagsInWindow} windowHours={sel.windowHours} />
            <WaterPipe turbidity={sel.turbidity} />
          </section>

          <section className="grid2">
            <StatTile icon={Thermometer} name="Temperature" value={sel.temp.toFixed(1)} unit="°C"
              hot={tempHot} data={sel.tempHist} color="#ff7a59" />
            <StatTile icon={Droplets} name="Turbidity" value={sel.turbidity.toFixed(1)} unit=" NTU"
              hot={turbHot} data={sel.turbHist} color="#1ba9d6" />
          </section>

          <section className="grid2">
            <div className="glass panel">
              <div className="panel-head"><Activity size={16} /> Escalation meter</div>
              <FlagMeter count={sel.flagsInWindow} />
              <p className="panel-note">
                A flag fires when turbidity ≥ {CONFIG.TURB_FLAG_NTU} NTU <b>and</b> temp ≥ {CONFIG.WARM_TEMP_C} °C.
                Tiers come from flag count in the rolling {CONFIG.WINDOW_HOURS} h window.
              </p>
            </div>

            <div className="glass panel">
              <div className="panel-head"><Clock size={16} /> Monitoring window</div>
              <div className="mon-bar"><div className="mon-fill" style={{ width: `${monPct}%` }} /></div>
              <div className="mon-row"><span>{elapsedH.toFixed(1)} h elapsed</span><span>{CONFIG.MONITOR_HOURS} h target</span></div>
              <div className="demo">
                <span className="demo-tag">demo control</span>
                <button className="demo-btn" onClick={() => backend.current?.inject(selected)}>
                  <Droplets size={15} /> Simulate contamination pulse
                </button>
              </div>
            </div>
          </section>

          <section className="glass panel">
            <div className="panel-head"><Flag size={16} /> Flag log <span className="muted">· {sel.label}</span></div>
            <div className="log-head"><span>Time</span><span>Turbidity</span><span>Temp</span></div>
            <div className="log">
              {sel.flags.length === 0 && <div className="log-empty">No flags yet — conditions nominal.</div>}
              {sel.flags.map((f, i) => (
                <div className="log-row" key={f.ts + "-" + i}>
                  <span className="mono">{fmtTime(f.ts)}</span>
                  <span><b>{f.turbidity.toFixed(1)}</b> NTU</span>
                  <span><b>{f.temp.toFixed(1)}</b> °C</span>
                </div>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

/* =========================================================================
   STYLE  ·  Frutiger Aero — glossy glass, aqua sky, water motif
   ========================================================================= */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@500;600;700&family=Mulish:wght@400;500;600;700&display=swap');

.app{
  --ink:#143b4a; --ink-soft:#3f6573; --line:rgba(255,255,255,.6);
  position:relative; min-height:100%; padding:18px;
  font-family:'Mulish',-apple-system,system-ui,sans-serif; color:var(--ink);
  background:
    radial-gradient(120% 90% at 12% 0%, #d8f3ff 0%, transparent 55%),
    radial-gradient(120% 100% at 100% 10%, #c9ffe9 0%, transparent 50%),
    linear-gradient(180deg,#9fdcff 0%, #b6ecff 30%, #d9f7ee 75%, #eafff6 100%);
  overflow:hidden;
}
.app *{box-sizing:border-box;}
.bg-orb{position:absolute;border-radius:50%;filter:blur(8px);opacity:.5;pointer-events:none;
  background:radial-gradient(circle at 30% 30%, #ffffff, rgba(255,255,255,0));}
.o1{width:240px;height:240px;top:-40px;right:18%;}
.o2{width:160px;height:160px;bottom:8%;left:6%;opacity:.4;}
.o3{width:120px;height:120px;top:42%;right:4%;opacity:.35;}

.glass{
  position:relative; background:linear-gradient(180deg, rgba(255,255,255,.72), rgba(255,255,255,.42));
  border:1px solid var(--line); border-radius:20px;
  box-shadow:0 10px 30px rgba(31,108,140,.18), inset 0 1px 0 rgba(255,255,255,.9);
  backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
}
.glass::before{content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  background:linear-gradient(180deg, rgba(255,255,255,.55), rgba(255,255,255,0) 42%);}

/* top bar */
.topbar{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;margin-bottom:16px;}
.brand{display:flex;align-items:center;gap:13px;}
.brand-mark{display:grid;place-items:center;width:42px;height:42px;border-radius:14px;color:#fff;
  background:linear-gradient(160deg,#39c6f0,#1f8fd1);box-shadow:0 6px 16px rgba(31,143,209,.45), inset 0 1px 0 rgba(255,255,255,.7);}
.brand-name{font-family:'Quicksand';font-weight:600;font-size:22px;letter-spacing:.2px;}
.brand-name b{font-weight:700;color:#1f8fd1;}
.brand-sub{font-size:12px;color:var(--ink-soft);}
.live-pill{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:600;
  padding:8px 14px;border-radius:999px;background:rgba(255,255,255,.6);border:1px solid var(--line);}
.live-clock{font-family:'Quicksand';font-weight:600;color:var(--ink);margin-left:4px;}
.muted{color:var(--ink-soft);font-weight:500;}
.pulse{color:#1fae6f;animation:pulse 1.6s infinite;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

.layout{display:grid;grid-template-columns:248px 1fr;gap:16px;}

/* rail */
.rail{padding:16px 14px;align-self:start;}
.rail-title{display:flex;align-items:center;gap:7px;font-family:'Quicksand';font-weight:600;font-size:14px;margin-bottom:12px;}
.rail-room{margin-bottom:12px;}
.rail-room-name{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink-soft);margin:6px 4px;}
.rail-item{display:flex;align-items:center;gap:9px;width:100%;text-align:left;cursor:pointer;
  padding:9px 11px;margin-bottom:6px;border-radius:13px;border:1px solid transparent;background:rgba(255,255,255,.35);
  font-family:'Mulish';font-size:13px;color:var(--ink);transition:.18s;}
.rail-item:hover{background:rgba(255,255,255,.7);}
.rail-item.active{background:linear-gradient(180deg,rgba(255,255,255,.95),rgba(231,248,255,.85));
  border-color:rgba(31,143,209,.4);box-shadow:0 4px 14px rgba(31,143,209,.2);}
.rail-dot{width:10px;height:10px;border-radius:50%;flex:none;}
.rail-item-label{flex:1;font-weight:600;}
.rail-item-turb{font-family:'Quicksand';font-weight:600;font-size:12px;color:var(--ink-soft);}
.rail-item-turb small{font-size:9px;}
.rail-foot{font-size:11px;color:var(--ink-soft);line-height:1.5;margin-top:8px;padding:10px;border-radius:12px;background:rgba(255,255,255,.3);}

/* hero */
.main{display:flex;flex-direction:column;gap:16px;}
.hero{display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:20px;padding:22px 24px;
  border-left:5px solid var(--tc);}
.hero-room{font-size:13px;color:var(--ink-soft);font-weight:600;}
.hero-label{font-family:'Quicksand';font-weight:700;font-size:26px;line-height:1.1;margin:2px 0 6px;}
.hero-meta .mono{font-family:'Quicksand';font-weight:600;font-size:12px;color:#fff;background:var(--tc);
  padding:3px 9px;border-radius:8px;box-shadow:0 2px 8px var(--tg);}
.tier-badge{display:flex;align-items:center;gap:12px;padding:13px 18px;border-radius:16px;color:#fff;
  background:linear-gradient(160deg, var(--tc), color-mix(in srgb, var(--tc) 72%, #000 8%));
  box-shadow:0 8px 22px var(--tg), inset 0 1px 0 rgba(255,255,255,.5);}
.tier-label{font-family:'Quicksand';font-weight:700;font-size:19px;line-height:1;}
.tier-sub{font-size:11.5px;opacity:.92;margin-top:3px;}

/* water pipe */
.pipe-wrap{display:flex;flex-direction:column;align-items:center;gap:6px;}
.pipe{position:relative;width:46px;height:96px;border-radius:14px;overflow:hidden;
  background:linear-gradient(180deg, rgba(220,245,255,.6), rgba(200,235,250,.5));
  border:1px solid rgba(255,255,255,.8);box-shadow:inset 0 0 14px rgba(40,120,150,.25);}
.pipe-water{position:absolute;left:0;right:0;bottom:0;height:82%;border-radius:0 0 13px 13px;transition:background .6s;}
.pipe-gloss{position:absolute;top:0;left:6px;width:9px;height:100%;border-radius:8px;
  background:linear-gradient(180deg,rgba(255,255,255,.85),rgba(255,255,255,0));}
.bubble{position:absolute;width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.7);left:50%;bottom:6px;animation:rise 3.4s infinite;}
.b1{left:30%;animation-delay:0s;} .b2{left:58%;animation-delay:1.2s;width:4px;height:4px;} .b3{left:44%;animation-delay:2.3s;}
@keyframes rise{0%{transform:translateY(0);opacity:0}20%{opacity:.9}100%{transform:translateY(-70px);opacity:0}}
.pipe-cap{font-family:'Quicksand';font-weight:700;font-size:13px;color:var(--ink);}
.pipe-cap small{font-size:9px;color:var(--ink-soft);}

/* tiles */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.tile{padding:16px 18px;transition:.25s;}
.tile-hot{box-shadow:0 10px 30px rgba(226,59,59,.22), inset 0 1px 0 rgba(255,255,255,.9), 0 0 0 1.5px rgba(242,121,15,.5);}
.tile-head{display:flex;align-items:center;gap:8px;margin-bottom:4px;}
.tile-ico{display:grid;place-items:center;}
.tile-name{font-weight:700;font-size:13px;}
.tile-tag{margin-left:auto;font-size:10px;font-weight:700;color:#fff;background:#f2790f;padding:2px 8px;border-radius:7px;}
.tile-val{font-family:'Quicksand';font-weight:700;font-size:34px;line-height:1;margin:2px 0 4px;}
.tile-unit{font-size:15px;color:var(--ink-soft);font-weight:600;margin-left:2px;}

/* panels */
.panel{padding:16px 18px;}
.panel-head{display:flex;align-items:center;gap:8px;font-family:'Quicksand';font-weight:600;font-size:14px;margin-bottom:12px;}
.panel-note{font-size:11.5px;color:var(--ink-soft);line-height:1.5;margin:12px 0 0;}

/* meter */
.meter-track{position:relative;height:12px;border-radius:8px;background:rgba(255,255,255,.55);
  border:1px solid var(--line);overflow:visible;}
.meter-fill{height:100%;border-radius:8px;transition:width .5s, background .5s;}
.meter-mark{position:absolute;top:-3px;width:3px;height:18px;border-radius:2px;transform:translateX(-50%);opacity:.8;}
.meter-legend{display:flex;justify-content:space-between;font-size:10.5px;font-weight:700;margin-top:10px;color:var(--ink-soft);}

/* monitoring */
.mon-bar{height:12px;border-radius:8px;background:rgba(255,255,255,.55);border:1px solid var(--line);overflow:hidden;}
.mon-fill{height:100%;background:linear-gradient(90deg,#39c6f0,#1fae6f);transition:width 1s;}
.mon-row{display:flex;justify-content:space-between;font-size:11.5px;font-weight:600;color:var(--ink-soft);margin:8px 0 14px;}
.demo{display:flex;align-items:center;gap:10px;}
.demo-tag{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--ink-soft);
  background:rgba(255,255,255,.5);padding:3px 7px;border-radius:6px;border:1px dashed rgba(63,101,115,.4);}
.demo-btn{display:flex;align-items:center;gap:7px;cursor:pointer;font-family:'Quicksand';font-weight:600;font-size:13px;color:#fff;
  padding:9px 14px;border:none;border-radius:11px;background:linear-gradient(160deg,#39c6f0,#1f8fd1);
  box-shadow:0 6px 16px rgba(31,143,209,.4), inset 0 1px 0 rgba(255,255,255,.6);transition:.18s;}
.demo-btn:hover{transform:translateY(-1px);box-shadow:0 9px 22px rgba(31,143,209,.5);}
.demo-btn:active{transform:translateY(0);}

/* log */
.log-head,.log-row{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:8px;padding:8px 12px;font-size:12.5px;}
.log-head{font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink-soft);font-weight:700;}
.log{max-height:190px;overflow-y:auto;border-radius:12px;}
.log-row{border-radius:10px;background:rgba(255,255,255,.4);margin-bottom:5px;align-items:center;}
.log-row:first-child{animation:flash 1.2s ease;}
@keyframes flash{0%{background:rgba(242,121,15,.45)}100%{background:rgba(255,255,255,.4)}}
.log-row b{font-family:'Quicksand';font-weight:700;}
.log-empty{padding:18px;text-align:center;color:var(--ink-soft);font-size:12.5px;}
.mono{font-family:'Quicksand';font-weight:600;}

@media(max-width:880px){
  .layout{grid-template-columns:1fr;}
  .hero{grid-template-columns:1fr;gap:14px;justify-items:start;}
  .grid2{grid-template-columns:1fr;}
}
`;
