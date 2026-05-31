import React, { useState, useEffect } from "react";
import Sparkline from "./Sparkline";

// Each character slides down from above with staggered cubic-bezier timing.
// animKey increments on every value change so React remounts the spans,
// re-triggering the CSS animation even when the same digit reappears.
function AnimatedValue({ value }) {
  const [animKey, setAnimKey] = useState(0);
  useEffect(() => { setAnimKey((k) => k + 1); }, [value]);
  return (
    <>
      {String(value).split("").map((ch, i) => (
        <span
          key={`${animKey}-${i}`}
          className="anim-char"
          style={{ animationDelay: `${i * 28}ms` }}
        >
          {ch}
        </span>
      ))}
    </>
  );
}

export default function StatTile({ icon: Icon, name, value, unit, hot, data, color }) {
  return (
    <div className={"glass tile" + (hot ? " tile-hot" : "")}>
      <div className="tile-head">
        <span className="tile-ico" style={{ color }}><Icon size={18} /></span>
        <span className="tile-name">{name}</span>
        {hot && <span className="tile-tag">over threshold</span>}
      </div>
      <div className="tile-val">
        <AnimatedValue value={value} />
        <span className="tile-unit">{unit}</span>
      </div>
      <Sparkline data={data} color={color} />
    </div>
  );
}
