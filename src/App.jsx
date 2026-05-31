import React, { useState, useEffect, useRef } from "react";
import {
  Thermometer, Droplets, Flag, Activity,
  Waves, Beaker, Clock, Radio,
  AlertTriangle, AlertOctagon, ShieldAlert,
} from "lucide-react";
import { CONFIG, TIERS, flagDotColor } from "./config";
import { SEED, NOW0, H, genHist } from "./seed";
import { CSS } from "./styles";
import Sparkline from "./components/Sparkline";
import StatTile from "./components/StatTile";
import WaterPipe from "./components/WaterPipe";
import TierBadge from "./components/TierBadge";
import FlagMeter from "./components/FlagMeter";

const fmtTime = (ts) =>
  new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

// ── Flag dots — 4 dots showing last 4 flags, coloured by level ───────────────
function FlagDots({ count }) {
  const dots = [];
  if (count === 0) {
    for (let i = 0; i < 4; i++) dots.push({ lit: false, color: "transparent" });
  } else {
    const start = Math.max(1, count - 3);
    const empty = 4 - (count - start + 1);
    for (let i = 0; i < empty; i++) dots.push({ lit: false, color: "transparent" });
    for (let n = start; n <= count; n++)
      dots.push({ lit: true, color: flagDotColor(n) });
  }
  return (
    <div className="flag-dots">
      {dots.map((d, i) => (
        <span
          key={i}
          className={"flag-dot" + (d.lit ? " lit" : "")}
          style={d.lit ? { background: d.color, color: d.color } : {}}
        />
      ))}
    </div>
  );
}

// ── Action panel — shown when tier is warn / warn2 / panic ───────────────────
function ActionPanel({ tier, action, steps }) {
  const icons = { warn: "⚠️", warn2: "🚨", panic: "🆘" };
  const titles = {
    warn:  "Warning — Human Action Required",
    warn2: "Warning Level 2 — Urgent Action Required",
    panic: "PANIC — Immediate Sanitisation Required",
  };
  return (
    <div className={`glass action-panel tier-${tier}`}>
      <div className="action-icon">{icons[tier]}</div>
      <div>
        <div className="action-title" style={{ color: TIERS[tier].color }}>{titles[tier]}</div>
        {action && <div className="action-sub">{action}</div>}
        {tier === "panic" && steps && steps.length > 0 && (
          <ol className="panic-steps">
            {steps.map((s, i) => <li key={i}>{s}</li>)}
          </ol>
        )}
      </div>
    </div>
  );
}

// ── Blank sensor template for dynamically discovered devices ─────────────────
function blankSensor(id) {
  return {
    id, room: "Live Device", label: id,
    temp: 0, turbidity: 0,
    tempHist: [], turbHist: [],
    flags: [],
    tier: "passed", flagsInWindow: 0, windowHours: CONFIG.WINDOW_HOURS,
    action: null, panicSteps: null,
  };
}

export default function WaterSentinelDashboard() {
  const [sensors, setSensors] = useState(() => {
    const o = {};
    for (const s of SEED) {
      const cutoff = NOW0 - CONFIG.WINDOW_HOURS * H;
      const count  = s.seedFlags.filter((f) => f.ts >= cutoff).length;
      o[s.id] = {
        id: s.id, room: s.room, label: s.label,
        temp: s.baseTemp, turbidity: s.baseTurb,
        tempHist: genHist(s.baseTemp, 1.2, 24),
        turbHist: genHist(s.baseTurb, 0.8, 24),
        flags: [...s.seedFlags].sort((a, b) => b.ts - a.ts),
        tier: "passed", flagsInWindow: count, windowHours: CONFIG.WINDOW_HOURS,
        action: null, panicSteps: null,
      };
    }
    return o;
  });

  const [selected, setSelected]   = useState("S-01");
  const [clock, setClock]         = useState(Date.now());
  const [panicLog, setPanicLog]   = useState([]);
  const backend  = useRef(null);
  const monitorStart = useRef(NOW0 - 14 * H);

  // ── Auto-select sink_01 when it first appears ─────────────────────────────
  useEffect(() => {
    if (sensors["sink_01"] && selected === "S-01") setSelected("sink_01");
  }, [Object.keys(sensors).join(",")]);

  // ── WebSocket ─────────────────────────────────────────────────────────────
  function handleMessage(msg) {
    const { sensorId } = msg;
    if (!sensorId) return;

    setSensors((prev) => {
      const s = prev[sensorId] ?? blankSensor(sensorId);
      if (msg.type === "reading") {
        return { ...prev, [sensorId]: {
          ...s,
          temp:     msg.temp,
          turbidity: msg.turbidity,
          tempHist: [...s.tempHist, { t: msg.ts, v: +msg.temp.toFixed(2) }].slice(-CONFIG.HISTORY),
          turbHist: [...s.turbHist, { t: msg.ts, v: +msg.turbidity.toFixed(2) }].slice(-CONFIG.HISTORY),
        }};
      }
      if (msg.type === "flag") {
        return { ...prev, [sensorId]: {
          ...s,
          flags: [{ ts: msg.ts, temp: msg.temp, turbidity: msg.turbidity,
                    flagNumber: msg.flagNumber, flagTier: msg.flagTier },
                  ...s.flags].slice(0, 60),
        }};
      }
      if (msg.type === "status") {
        return { ...prev, [sensorId]: {
          ...s,
          tier:          msg.tier,
          flagsInWindow: msg.flagsInWindow,
          windowHours:   msg.windowHours,
          action:        msg.action ?? s.action,
          panicSteps:    msg.steps  ?? s.panicSteps,
        }};
      }
      return prev;
    });
  }

  const wsRef        = useRef(null);
  const reconnectRef = useRef(null);

  useEffect(() => {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl   = `${wsProto}//${window.location.host}/ws/dashboard`;

    function connect() {
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
      ws.onerror   = () => {};
      ws.onclose   = () => {
        reconnectRef.current = setTimeout(connect, 3000);
      };
      wsRef.current = ws;
      backend.current = { inject: (id) => ws.send(JSON.stringify({ cmd: "inject", sensorId: id })) };
    }
    connect();

    const clock_t = setInterval(() => setClock(Date.now()), 1000);
    const panic_t = setInterval(() => {
      fetch("/api/panic-log")
        .then((r) => r.json())
        .then((d) => setPanicLog(d.entries ?? []))
        .catch(() => {});
    }, 10_000);

    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
      clearInterval(clock_t);
      clearInterval(panic_t);
    };
  }, []);

  const sel      = sensors[selected] ?? blankSensor(selected);
  const tempHot  = sel.temp >= CONFIG.WARM_TEMP_C;
  const turbHot  = sel.turbidity >= CONFIG.TURB_FLAG_NTU;
  const allRooms = [...new Set([...SEED.map((s) => s.room), "Live Device"])];
  const elapsedH = (clock - monitorStart.current) / H;
  const monPct   = Math.max(0, Math.min(1, elapsedH / CONFIG.MONITOR_HOURS)) * 100;

  const sensorsByRoom = Object.values(sensors).reduce((acc, s) => {
    (acc[s.room] = acc[s.room] || []).push(s);
    return acc;
  }, {});

  return (
    <div className="app">
      <style>{CSS}</style>
      <div className="bg-orb o1" /><div className="bg-orb o2" /><div className="bg-orb o3" />

      <header className="topbar glass">
        <div className="brand">
          <span className="brand-mark"><Waves size={22} /></span>
          <div>
            <div className="brand-name">Bio<b>Watch</b></div>
            <div className="brand-sub">Sink-trap bacterial-risk monitoring · {CONFIG.MONITOR_HOURS} h incubation watch</div>
          </div>
        </div>
        <div className="live-pill">
          <Radio size={13} className="pulse" /> Live · <span className="muted">ws://localhost:8000</span>
          <FlagDots count={sel.flagsInWindow} />
          <span className="live-clock">{new Date(clock).toLocaleTimeString()}</span>
        </div>
      </header>

      <div className="layout">
        <aside className="rail glass">
          <div className="rail-title"><Beaker size={15} /> Rooms &amp; Sensors</div>
          {Object.entries(sensorsByRoom).map(([room, snList]) => (
            <div key={room} className="rail-room">
              <div className="rail-room-name">{room}</div>
              {snList.map((s) => {
                const t = TIERS[s.tier] || TIERS.passed;
                return (
                  <button key={s.id} className={"rail-item" + (selected === s.id ? " active" : "")} onClick={() => setSelected(s.id)}>
                    <span className="rail-dot" style={{ background: t.color, boxShadow: `0 0 8px ${t.glow}` }} />
                    <span className="rail-item-label">{s.label}</span>
                    <span className="rail-item-turb">{s.turbidity.toFixed(1)}<small> NTU</small></span>
                  </button>
                );
              })}
            </div>
          ))}
          <div className="rail-foot">Real devices appear automatically when they connect.</div>
        </aside>

        <main className="main">
          <section className="hero glass" style={{ "--tc": TIERS[sel.tier]?.color ?? TIERS.passed.color, "--tg": TIERS[sel.tier]?.glow ?? TIERS.passed.glow }}>
            <div className="hero-id">
              <div className="hero-room">{sel.room}</div>
              <div className="hero-label">{sel.label}</div>
              <div className="hero-meta"><span className="mono">{sel.id}</span></div>
            </div>
            <TierBadge tier={sel.tier} count={sel.flagsInWindow} windowHours={sel.windowHours} />
            <WaterPipe turbidity={sel.turbidity} />
          </section>

          {sel.tier !== "passed" && (
            <ActionPanel tier={sel.tier} action={sel.action} steps={sel.panicSteps} />
          )}

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
                Flag fires when turbidity ≥ {CONFIG.TURB_FLAG_NTU} NTU <b>and</b> temp ≥ {CONFIG.WARM_TEMP_C} °C.
                Tiers: 0–{CONFIG.FLAG_WARN - 1} passed · {CONFIG.FLAG_WARN}–{CONFIG.FLAG_WARN2 - 1} warn · {CONFIG.FLAG_WARN2}–{CONFIG.FLAG_PANIC - 1} warn2 · {CONFIG.FLAG_PANIC}+ panic.
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
            <div className="log-head">
              <span></span><span>#</span><span>Time</span><span>Turbidity</span><span>Temp</span>
            </div>
            <div className="log">
              {sel.flags.length === 0 && <div className="log-empty">No flags yet — conditions nominal.</div>}
              {sel.flags.map((f, i) => {
                const dc = flagDotColor(f.flagNumber ?? (sel.flags.length - i));
                return (
                  <div className="log-row" key={f.ts + "-" + i}>
                    <span className="log-flag-dot" style={{ background: dc, boxShadow: `0 0 5px ${dc}` }} />
                    <span className="log-flag-num">{f.flagNumber ?? "—"}</span>
                    <span className="mono">{fmtTime(f.ts)}</span>
                    <span><b>{f.turbidity.toFixed(1)}</b> NTU</span>
                    <span><b>{f.temp.toFixed(1)}</b> °C</span>
                  </div>
                );
              })}
            </div>
          </section>

          {panicLog.length > 0 && (
            <section className="glass panel">
              <div className="panel-head"><ShieldAlert size={16} style={{ color: "#e23b3b" }} /> Panic log</div>
              <div className="panic-log-head">
                <span>Time · Device</span><span>Peak Temp</span><span>Peak Turb</span><span>Avg Turb</span>
              </div>
              {panicLog.slice().reverse().map((e, i) => (
                <div className="panic-log-row" key={i}>
                  <span><span className="mono">{fmtTime(e.ts)}</span><br /><small>{e.device_id}</small></span>
                  <span><b>{e.peak_temp}</b> °C</span>
                  <span><b>{e.peak_turb}</b> NTU</span>
                  <span>{e.avg_turb} NTU</span>
                </div>
              ))}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
