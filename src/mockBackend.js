import { CONFIG, tierFromCount, clamp } from "./config";
import { SEED, H } from "./seed";

export function createMockBackend(onMessage) {
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
    ss.temp = clamp(ss.baseTemp + (Math.random() - 0.5) * 0.6 + (ss.inject > 0 ? 1.8 : 0), 15, 40);
    let t = ss.baseTurb + Math.random() * 0.7;
    if (ss.inject > 0) { t += 6 + Math.random() * 3; ss.inject--; }
    else if (Math.random() < 0.012) { t += 3 + Math.random() * 2; }
    ss.turb = Math.max(0, t);
    onMessage({ type: "reading", ts: now, sensorId: ss.id, temp: ss.temp, turbidity: ss.turb });

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
      state.forEach(emitStatus);
      timer = setInterval(() => state.forEach(step), CONFIG.EMIT_MS);
    },
    stop() { clearInterval(timer); timer = null; },
    inject(id) { const ss = state.find((s) => s.id === id); if (ss) ss.inject = CONFIG.INJECT_TICKS; },
  };
}
