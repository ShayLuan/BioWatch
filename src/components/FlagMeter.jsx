import React from "react";
import { CONFIG, TIERS, tierFromCount, clamp } from "../config";

export default function FlagMeter({ count }) {
  const marks = [
    { n: CONFIG.TIER_WATCH,    k: "watch" },
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
