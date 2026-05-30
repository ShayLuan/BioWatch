import { CONFIG } from "./config";

export const NOW0 = Date.now();
export const H = 3600 * 1000;

export function pastFlags(n, temps, turbs) {
  return Array.from({ length: n }, (_, i) => ({
    ts: NOW0 - Math.floor((i + 1) * (5 * H) / (n + 1)) - Math.random() * 600000,
    temp: temps + Math.random() * 1.5,
    turbidity: turbs + Math.random() * 2,
  }));
}

export const SEED = [
  { id: "S-01", room: "Room 312", label: "Sink · Patient Bay", baseTemp: 27.2, baseTurb: 1.1, seedFlags: [] },
  { id: "S-02", room: "Room 312", label: "Drain · Handwash",   baseTemp: 22.8, baseTurb: 0.9, seedFlags: [] },
  { id: "S-03", room: "Room 308", label: "Sink · ICU Bay",     baseTemp: 28.4, baseTurb: 2.0, seedFlags: pastFlags(4, 28, 6) },
  { id: "S-04", room: "Ward 401", label: "Sink · West Ward",   baseTemp: 29.1, baseTurb: 2.4, seedFlags: pastFlags(7, 29, 7) },
];

export function genHist(base, spread, n) {
  return Array.from({ length: n }, (_, i) => ({
    t: NOW0 - (n - i) * CONFIG.EMIT_MS,
    v: +(base + (Math.random() - 0.5) * spread).toFixed(2),
  }));
}
