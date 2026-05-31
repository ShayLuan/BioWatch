import React from "react";
import { CONFIG, TIERS, tierFromCount, clamp } from "../config";

export default function FlagMeter({ count }) {
  const marks = [
    { n: CONFIG.FLAG_WARN,  k: "warn" },
    { n: CONFIG.FLAG_WARN2, k: "warn2" },
    { n: CONFIG.FLAG_PANIC, k: "panic" },
  ];
  const max = CONFIG.FLAG_PANIC + 2;
  return (
    <div className="meter">
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${clamp(count / max, 0, 1) * 100}%`, background: TIERS[tierFromCount(count)].color }} />
        {marks.map((m) => (
          <span key={m.k} className="meter-mark" style={{ left: `${(m.n / max) * 100}%`, background: TIERS[m.k].color }} title={`${TIERS[m.k].label} @ ${m.n}`} />
        ))}
      </div>
      <div className="meter-legend">
        <span>0</span>
        <span style={{ color: TIERS.warn.color }}>warn {CONFIG.FLAG_WARN}</span>
        <span style={{ color: TIERS.warn2.color }}>warn2 {CONFIG.FLAG_WARN2}</span>
        <span style={{ color: TIERS.panic.color }}>panic {CONFIG.FLAG_PANIC}+</span>
      </div>
    </div>
  );
}
