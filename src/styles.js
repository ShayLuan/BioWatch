export const CSS = `
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

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.tile{padding:16px 18px;transition:.25s;}
.tile-hot{box-shadow:0 10px 30px rgba(226,59,59,.22), inset 0 1px 0 rgba(255,255,255,.9), 0 0 0 1.5px rgba(242,121,15,.5);}
.tile-head{display:flex;align-items:center;gap:8px;margin-bottom:4px;}
.tile-ico{display:grid;place-items:center;}
.tile-name{font-weight:700;font-size:13px;}
.tile-tag{margin-left:auto;font-size:10px;font-weight:700;color:#fff;background:#f2790f;padding:2px 8px;border-radius:7px;}
.tile-val{font-family:'Quicksand';font-weight:700;font-size:34px;line-height:1;margin:2px 0 4px;}
.tile-unit{font-size:15px;color:var(--ink-soft);font-weight:600;margin-left:2px;}

.panel{padding:16px 18px;}
.panel-head{display:flex;align-items:center;gap:8px;font-family:'Quicksand';font-weight:600;font-size:14px;margin-bottom:12px;}
.panel-note{font-size:11.5px;color:var(--ink-soft);line-height:1.5;margin:12px 0 0;}

.meter-track{position:relative;height:12px;border-radius:8px;background:rgba(255,255,255,.55);
  border:1px solid var(--line);overflow:visible;}
.meter-fill{height:100%;border-radius:8px;transition:width .5s, background .5s;}
.meter-mark{position:absolute;top:-3px;width:3px;height:18px;border-radius:2px;transform:translateX(-50%);opacity:.8;}
.meter-legend{display:flex;justify-content:space-between;font-size:10.5px;font-weight:700;margin-top:10px;color:var(--ink-soft);}

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

.log-head,.log-row{display:grid;grid-template-columns:12px 18px 1.1fr 1fr 1fr;gap:8px;padding:8px 12px;font-size:12.5px;align-items:center;}
.log-head{font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink-soft);font-weight:700;}
.log{max-height:220px;overflow-y:auto;border-radius:12px;}
.log-row{border-radius:10px;background:rgba(255,255,255,.4);margin-bottom:5px;}
.log-row:first-child{animation:flash 1.2s ease;}
@keyframes flash{0%{background:rgba(242,121,15,.45)}100%{background:rgba(255,255,255,.4)}}
.log-row b{font-family:'Quicksand';font-weight:700;}
.log-empty{padding:18px;text-align:center;color:var(--ink-soft);font-size:12.5px;}
.mono{font-family:'Quicksand';font-weight:600;}
.log-flag-dot{width:10px;height:10px;border-radius:50%;flex:none;border:1.5px solid rgba(0,0,0,.1);}
.log-flag-num{font-family:'Quicksand';font-weight:700;font-size:11px;color:var(--ink-soft);}

/* ── Flag dots (topbar) ─────────────────────── */
.flag-dots{display:flex;align-items:center;gap:5px;margin:0 4px;}
.flag-dot{width:12px;height:12px;border-radius:50%;border:2px solid rgba(255,255,255,.35);
  background:rgba(255,255,255,.1);transition:.3s;}
.flag-dot.lit{border-color:transparent;box-shadow:0 0 6px currentColor;}

/* ── Action panel ───────────────────────────── */
.action-panel{display:flex;align-items:flex-start;gap:14px;padding:14px 18px;border-radius:16px;}
.action-panel.tier-warn{border-left:5px solid #e8a800;background:rgba(232,168,0,.1);}
.action-panel.tier-warn2{border-left:5px solid #f2790f;background:rgba(242,121,15,.1);}
.action-panel.tier-panic{border-left:5px solid #e23b3b;background:rgba(226,59,59,.1);}
.action-icon{font-size:24px;line-height:1;flex:none;margin-top:1px;}
.action-title{font-family:'Quicksand';font-weight:700;font-size:15px;line-height:1.3;}
.action-sub{font-size:12px;color:var(--ink-soft);margin-top:3px;}
.panic-steps{margin:8px 0 0;padding-left:18px;}
.panic-steps li{font-size:12.5px;line-height:1.7;color:var(--ink);}

/* ── Panic log ──────────────────────────────── */
.panic-log-head{display:grid;grid-template-columns:1.4fr .7fr .7fr .7fr;gap:8px;
  padding:8px 12px;font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;
  color:var(--ink-soft);font-weight:700;}
.panic-log-row{display:grid;grid-template-columns:1.4fr .7fr .7fr .7fr;gap:8px;padding:9px 12px;
  border-radius:10px;background:rgba(226,59,59,.08);margin-bottom:5px;font-size:12.5px;align-items:center;}
.panic-log-row b{font-family:'Quicksand';font-weight:700;}

@media(max-width:880px){
  .layout{grid-template-columns:1fr;}
  .hero{grid-template-columns:1fr;gap:14px;justify-items:start;}
  .grid2{grid-template-columns:1fr;}
}
`;
