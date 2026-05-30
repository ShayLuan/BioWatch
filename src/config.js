import {
  CheckCircle2, Activity, AlertTriangle, ShieldAlert,
} from "lucide-react";

export const CONFIG = {
  WARM_TEMP_C: 26,
  TURB_FLAG_NTU: 4.5,
  WINDOW_HOURS: 6,
  TIER_WATCH: 1,
  TIER_ELEVATED: 4,
  TIER_CRITICAL: 6,
  EMIT_MS: 1500,
  INJECT_TICKS: 2,
  FLAG_DEBOUNCE_MS: 1200,
  HISTORY: 40,
  TURB_VIS_MAX: 12,
  MONITOR_HOURS: 36,
};

export const TIERS = {
  normal:   { label: "Normal",   color: "#1fae6f", glow: "rgba(31,174,111,.45)",  icon: CheckCircle2 },
  watch:    { label: "Watch",    color: "#e8a800", glow: "rgba(232,168,0,.5)",    icon: Activity },
  elevated: { label: "Elevated", color: "#f2790f", glow: "rgba(242,121,15,.55)",  icon: AlertTriangle },
  critical: { label: "Critical", color: "#e23b3b", glow: "rgba(226,59,59,.6)",    icon: ShieldAlert },
};

export function tierFromCount(n) {
  if (n >= CONFIG.TIER_CRITICAL) return "critical";
  if (n >= CONFIG.TIER_ELEVATED) return "elevated";
  if (n >= CONFIG.TIER_WATCH)    return "watch";
  return "normal";
}

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
