import React from "react";
import Sparkline from "./Sparkline";

export default function StatTile({ icon: Icon, name, value, unit, hot, data, color }) {
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
