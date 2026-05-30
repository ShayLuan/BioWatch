import React, { useState, useEffect, useRef } from "react";
import {
  Thermometer, Droplets, Flag, Activity,
  Waves, Beaker, Clock, Radio,
} from "lucide-react";
import { CONFIG, TIERS } from "./config";
import { SEED, NOW0, H, genHist } from "./seed";
import { createMockBackend } from "./mockBackend";
import { CSS } from "./styles";
import Sparkline from "./components/Sparkline";
import StatTile from "./components/StatTile";
import WaterPipe from "./components/WaterPipe";
import TierBadge from "./components/TierBadge";
import FlagMeter from "./components/FlagMeter";

const fmtTime = (ts) => new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

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
        tier: "normal", flagsInWindow: count, windowHours: CONFIG.WINDOW_HOURS,
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
  const monPct = Math.max(0, Math.min(1, elapsedH / CONFIG.MONITOR_HOURS)) * 100;

  return (
    <div className="app">
      <style>{CSS}</style>
      <div className="bg-orb o1" /><div className="bg-orb o2" /><div className="bg-orb o3" />

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
