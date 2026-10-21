"""The town page: the drawn town filling the window, little me on top, and sheets for taps."""

import html
import json

from studio_town.drawing import FILTERS, avatar

CSS = """
:root { --oat:#F7F1E6; --paper:#FDFAF3; --ink:#4A4035; --ink-l:#978B7B; --forest:#3E5243; --clay:#C26D53; }
* { box-sizing:border-box; }
html, body { margin:0; background:var(--oat); color:var(--ink); font-family:'DM Sans', ui-sans-serif, system-ui, sans-serif; }
body { background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.35  0 0 0 0 0.28  0 0 0 0 0.2  0 0 0 0.09 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
main { max-width:460px; margin:0 auto; padding:22px 16px 40px; }
.label { font-size:11px; letter-spacing:.2em; text-transform:uppercase; font-weight:700; color:var(--clay); }
h1 { font-family:'Fraunces', serif; font-weight:400; font-size:34px; line-height:1.1; margin:8px 0 4px; letter-spacing:-.01em; }
.sub { font-family:'Gaegu'; font-size:19px; color:#6D6152; margin:0 0 14px; }
.town-wrap { background:var(--paper); border-radius:24px; padding:8px; box-shadow:0 16px 30px -22px rgba(74,64,53,.55); }
.stage { position:relative; }
img.town { display:block; width:100%; height:auto; border-radius:18px; }
svg.hotspots { position:absolute; inset:0; width:100%; height:100%; }
.painting { display:flex; align-items:center; justify-content:center; border-radius:18px; background:#EEF0E6;
  font-family:'Gaegu'; font-size:20px; color:#6D6152; animation:breathe 1.6s ease-in-out infinite alternate; }
@keyframes breathe { from { opacity:.55 } to { opacity:1 } }
.place { cursor:pointer; outline:none; }
.place:hover .hit, .place:focus-visible .hit { fill:rgba(255,253,248,.18); }
.place .hit { pointer-events:all; }
.sheet-bg { position:fixed; inset:0; background:rgba(62,82,67,.18); opacity:0; pointer-events:none; transition:opacity .2s; }
.sheet { position:fixed; left:50%; bottom:0; width:min(460px, 100%); transform:translate(-50%, 110%); transition:transform .25s ease;
  background:var(--paper); border-radius:24px 24px 0 0; padding:22px 22px 28px; box-shadow:0 -12px 30px -18px rgba(74,64,53,.5); }
.sheet { visibility:hidden; }
.open .sheet:not(.me-sheet), .open-me .me-sheet { transform:translate(-50%, 0); visibility:visible; }
.open-me .sheet-bg { opacity:1; pointer-events:all; }
.me-head { display:flex; align-items:center; gap:12px; margin:0 0 10px; }
.me-head svg { width:64px; height:66px; flex:none; }
.whatsup { font-family:'Gaegu'; font-weight:700; font-size:34px; color:var(--ink); }
#say { width:100%; border:1.5px solid #CBD3C1; border-radius:16px; background:#FFFDF8; padding:12px 14px; font:20px 'Gaegu'; color:var(--ink); resize:none; outline:none; }
a.btn { text-align:center; text-decoration:none; }
.open .sheet-bg { opacity:1; pointer-events:all; }
.sheet h2 { font-family:'Fraunces', serif; font-weight:600; font-size:24px; margin:0 0 4px; }
.sheet .status { font-family:'Gaegu'; font-size:19px; color:#6D6152; margin:0 0 16px; }
.btn { display:block; width:100%; border:0; border-radius:999px; padding:13px 16px; font:600 15px 'DM Sans', sans-serif; cursor:pointer; margin-top:10px; }
.btn.primary { background:var(--forest); color:var(--oat); }
.btn.soft { background:transparent; color:var(--forest); box-shadow:inset 0 0 0 1.5px #A3AE9A; }
.row { display:flex; gap:10px; } .row .btn { flex:1; }
.hidden { display:none !important; }
.tucked { margin-top:22px; }
.tucked ul { list-style:none; padding:0; margin:8px 0 0; }
.tucked li { display:flex; justify-content:space-between; align-items:center; padding:10px 2px; border-bottom:1px dashed rgba(74,64,53,.2); font-family:'Gaegu'; font-size:19px; }
.link { background:none; border:0; color:var(--forest); font:600 14px 'DM Sans', sans-serif; cursor:pointer; }
.note { font-family:'Gaegu'; font-size:16px; color:var(--ink-l); text-align:center; margin-top:14px; }
.toast { position:fixed; left:50%; top:16px; transform:translateX(-50%); background:var(--forest); color:var(--oat); padding:9px 16px; border-radius:999px; font-size:14px; opacity:0; transition:opacity .2s; pointer-events:none; }
.toast.show { opacity:1; }
"""

TOWN_CSS = """
body.town-page { background:#FBF3E2; }
.town-head { padding:18px 20px 6px; }
.town-head h1 { font-size:30px; margin:4px 0 2px; }
.town-head .sub { margin:0; }
.wide .town-head { position:absolute; left:2.4%; top:1.6%; z-index:2; padding:0; max-width:40%; }
.stage { position:relative; width:100%; }
img.town { display:block; width:100%; height:auto; max-width:none; border-radius:0; }
html, body { overflow-x:hidden; }
svg.hotspots { position:absolute; inset:0; width:100%; height:100%; }
.painting { width:100%; display:flex; align-items:center; justify-content:center; background:#EEF0E6;
  font-family:'Gaegu'; font-size:20px; color:#6D6152; animation:breathe 1.6s ease-in-out infinite alternate; }
.me-sprite { position:absolute; transform:translate(-50%, -100%); cursor:grab; touch-action:none; z-index:3; user-select:none; }
.me-sprite svg { display:block; width:100%; height:auto; pointer-events:none; }
.me-sprite.dragging { cursor:grabbing; animation:wiggle .35s ease-in-out infinite alternate; }
.me-sprite .hint { position:absolute; left:50%; bottom:100%; transform:translateX(-50%); white-space:nowrap; font:17px 'Gaegu';
  color:#6D6152; background:rgba(255,253,248,.85); border-radius:10px; padding:1px 8px; opacity:0; transition:opacity .3s; }
.me-sprite:hover .hint { opacity:1; }
.stage.talking .me-sprite .hint { opacity:0; }
@keyframes wiggle { from { rotate:-5deg } to { rotate:5deg } }
.below { padding:6px 20px 30px; }
.sheet-bg { z-index:5; } .sheet { z-index:6; } .toast { z-index:7; }
.pick { margin:4px 0 2px; }
.wcard { position:absolute; z-index:2; right:3%; top:2.2%; padding:9px 14px 10px; min-width:180px; font-family:'Gaegu'; color:var(--ink); }
.tall .wcard { right:4%; top:1.5%; min-width:0; padding:7px 11px; }
.wcard .wbg { position:absolute; inset:0; width:100%; height:100%; overflow:visible; z-index:-1; }
.wdate { font-size:19px; font-weight:700; line-height:1.1; }
.wline { display:flex; align-items:center; gap:6px; font-size:17px; margin-top:3px; color:#6D6152; }
.wicon { width:22px; height:22px; flex:none; }
.night body.town-page { background:linear-gradient(#2F3352 0%, #4C5784 25%, #7F75AE 45%, #B793C4 60%, #E6B8C8 75%, #FAEBCF 100%); }
.night .town-head .label { color:#F3C7BE; } .night .town-head h1 { color:#F7F1E6; } .night .town-head .sub { color:#E1DACB; }
.wide body.town-page { overflow:hidden; height:100vh; }
.wide .stage { width:min(100%, calc(100vh * var(--ratio))); margin:0 auto; }
.wide .below { position:fixed; left:16px; bottom:10px; padding:0; z-index:4; }
.wide .tucked { margin:0; background:rgba(253,250,243,.9); border-radius:14px; padding:8px 12px; }
.bubble { position:absolute; z-index:4; transform:translate(-50%, -100%); width:max-content; max-width:min(320px, 72vw); min-width:150px;
  padding:12px 16px 14px; font:19px/1.3 'Gaegu'; color:var(--ink); background:none; }
.bubble > svg.bg { position:absolute; left:0; top:0; overflow:visible; pointer-events:none; z-index:-1; }
.bubble .text { position:relative; max-height:180px; overflow:auto; white-space:pre-wrap; }
.bubble .more { position:relative; display:inline-block; margin-top:8px; font:600 13px 'DM Sans', sans-serif; color:var(--forest);
  background:#E4EADF; border:1.2px solid #8C7A66; border-radius:999px; padding:4px 10px; cursor:pointer; }
.bubble.thinking { min-width:0; padding:12px 22px 14px; }
.bubble.thinking .think-space { width:52px; height:22px; }
.tdot { opacity:0; animation:tdot 1.8s steps(1) infinite; }
.tdot1 { animation-name:tdot1; } .tdot2 { animation-name:tdot2; }
@keyframes tdot { 0% { opacity:1 } 83% { opacity:0 } }
@keyframes tdot1 { 0% { opacity:0 } 28% { opacity:1 } 83% { opacity:0 } }
@keyframes tdot2 { 0% { opacity:0 } 56% { opacity:1 } 83% { opacity:0 } }
.bubble .asked { position:relative; font:14px/1.2 'Gaegu'; color:#978B7B; margin:0 18px 4px 0; }
.bubble .asked::before { content:'you: '; }
.bubble .close { position:absolute; right:8px; top:4px; z-index:1; background:none; border:0; font:20px 'Gaegu'; color:#978B7B; cursor:pointer; }
.bubble .reply { position:relative; display:flex; align-items:center; gap:6px; margin-top:8px; border-top:1.2px dashed #CDBFAE; padding-top:6px; }
.bubble .reply input { flex:1; min-width:0; border:0; background:transparent; font:18px 'Gaegu'; color:var(--ink); outline:none; padding:2px 0; }
.bubble .reply button { border:1.3px solid #8C7A66; background:#F2D4CF; color:var(--ink); border-radius:50%; width:26px; height:26px; cursor:pointer; font:15px 'DM Sans', sans-serif; }
.dots { position:relative; } .dots span { display:inline-block; width:8px; height:8px; margin:0 3px; border-radius:50%; background:#8C7A66;
  animation:bob 1s ease-in-out infinite; }
.dots span:nth-child(2) { animation-delay:.15s } .dots span:nth-child(3) { animation-delay:.3s }
@keyframes bob { 0%,100% { transform:translateY(0); opacity:.5 } 50% { transform:translateY(-5px); opacity:1 } }
.pick label { display:block; font-size:11px; letter-spacing:.18em; text-transform:uppercase; font-weight:700; color:var(--ink-l); margin-bottom:6px; }
.pick select { width:100%; border:1.5px solid #CBD3C1; border-radius:14px; background:#FFFDF8; padding:10px 12px; font:16px 'DM Sans', sans-serif; color:var(--ink); }
"""

JS = """
const PLACES = JSON.parse(document.getElementById('places-data').textContent);
const TOWN = JSON.parse(document.getElementById('town-data').textContent);
const root = document.documentElement;
const sheet = document.querySelector('.sheet');
let current = null;

// Pick the town's shape from the window, and redraw when that changes.
function wantedShape() { return (innerWidth >= 700 && innerWidth > innerHeight * 1.05) ? 'wide' : 'tall'; }
if (wantedShape() !== TOWN.shape) location.replace('/?shape=' + wantedShape());
let resizeTimer = null;
addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => {
  if (wantedShape() !== TOWN.shape) location.replace('/?shape=' + wantedShape()); }, 400); });

function openSheet(app) {
  if (app === '__me__') {
    root.classList.add('open-me'); setTimeout(() => document.getElementById('say').focus(), 250);
    fetch('/api/warm', {method: 'POST'}).catch(() => {});
    return;
  }
  current = PLACES[app];
  if (!current) return;
  sheet.querySelector('h2').textContent = current.label;
  sheet.querySelector('.status').textContent = current.status;
  document.getElementById('open-btn').textContent = current.action;
  document.getElementById('wild-row').classList.toggle('hidden', !current.wild);
  const pick = document.getElementById('chat-pick'); pick.innerHTML = '';
  (current.chats || []).forEach((c, i) => {
    const o = document.createElement('option'); o.value = c.chat_id;
    o.textContent = c.title + (i === 0 ? '  (where it was made)' : ''); pick.append(o);
  });
  const none = document.createElement('option'); none.value = ''; none.textContent = 'no chat, just the app'; pick.append(none);
  document.querySelector('.pick').classList.toggle('hidden', !(current.chats || []).length);
  root.classList.add('open');
}
function closeSheet() { root.classList.remove('open', 'open-me'); current = null; }
document.querySelectorAll('.place').forEach(el => {
  el.addEventListener('click', () => openSheet(el.dataset.app));
  el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openSheet(el.dataset.app); } });
});
document.querySelector('.sheet-bg').addEventListener('click', closeSheet);
function toast(msg) {
  const t = document.querySelector('.toast'); t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}
async function act(kind) {
  if (!current) return;
  const place = current;
  const chat = document.getElementById('chat-pick').value || null;
  closeSheet();
  const r = await fetch(`/api/places/${encodeURIComponent(place.app)}/${kind}`, {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({client: window.SHELL_CLIENT || null, chat})});
  const body = await r.json().catch(() => ({}));
  if (!r.ok) { toast(body.detail || 'That did not work. Try again.'); return; }
  if (kind === 'keep-wild') toast(`Left ${place.label} wild.`);
  else if (kind !== 'open') location.reload();
}
document.getElementById('open-btn').addEventListener('click', () => act('open'));
document.getElementById('keep-btn').addEventListener('click', () => act('keep-wild'));
document.getElementById('tuck-btn').addEventListener('click', () => act('tuck-away'));
const bubble = document.getElementById('bubble');
function placeBubble() {
  bubble.style.left = sprite.style.left;
  const top = parseFloat(sprite.style.top) - (sprite.offsetHeight + 14) / stage.getBoundingClientRect().height * 100;
  bubble.style.top = top + '%';
}
const observer = new MutationObserver(() => stage.classList.toggle('talking', !bubble.classList.contains('hidden')));
observer.observe(bubble, {attributes: true, attributeFilter: ['class']});
// Hand-drawn bubbles: an SVG outline sized to the text, pencil-roughened like the island.
function jit(n) { return (Math.random() - 0.5) * n; }
function speechPath(w, h) {
  const r = 16, tx = w / 2, th = 14;
  return `M${r} ${jit(2)} Q${w / 2} ${-2 + jit(2)} ${w - r} ${jit(2)} Q${w + jit(2)} ${jit(2)} ${w + jit(1)} ${r} ` +
    `Q${w + 2 + jit(2)} ${h / 2} ${w + jit(1)} ${h - r} Q${w + jit(2)} ${h + jit(2)} ${w - r} ${h + jit(1)} ` +
    `L${tx + 10} ${h} Q${tx + 4} ${h + th * 0.6} ${tx - 2} ${h + th} Q${tx - 2} ${h + th * 0.5} ${tx - 9} ${h} ` +
    `L${r} ${h + jit(1)} Q${jit(2)} ${h + jit(2)} ${jit(1)} ${h - r} Q${-2 + jit(2)} ${h / 2} ${jit(1)} ${r} Q${jit(2)} ${jit(2)} ${r} ${jit(2)} Z`;
}
function cloudPath(w, h) {
  const cx = w / 2, cy = h / 2, rx = w / 2 + 4, ry = h / 2 + 3, n = Math.max(7, Math.round(w / 16));
  const pts = [];
  for (let i = 0; i < n; i++) { const a = 2 * Math.PI * i / n; pts.push([cx + rx * Math.cos(a) + jit(2), cy + ry * Math.sin(a) + jit(2)]); }
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < n; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % n];
    const rr = Math.hypot(x2 - x1, y2 - y1) * 0.62;
    d += ` A${rr} ${rr} 0 0 1 ${x2} ${y2}`;
  }
  return d + ' Z';
}
function drawBubble() {
  let svg = bubble.querySelector('svg.bg');
  if (!svg) { svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.classList.add('bg'); bubble.prepend(svg); }
  const w = bubble.offsetWidth, h = bubble.offsetHeight;
  svg.setAttribute('width', w); svg.setAttribute('height', h);
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  const ink = '#5A4A3C';
  if (bubble.classList.contains('thinking')) {
    // a watercolour cloud in the speech bubble's paper colour, pencil outline, and three drawn dots appearing one by one
    const d = cloudPath(w, h), paper = '#FFFBF2';
    const dots = [0, 1, 2].map(i => `<path class="tdot tdot${i}" d="M${w / 2 - 16 + i * 16 + jit(1)} ${h / 2 + 1} ` +
      `q2 -3 4 0 q-1 3 -4 0 Z" fill="${ink}" stroke="${ink}" stroke-width="2.2" stroke-linecap="round"/>`).join('');
    svg.innerHTML = `<g filter="url(#wash)"><path d="${d}" fill="${paper}" opacity="0.93"/>` +
      `<circle cx="${w / 2 - 6}" cy="${h + 11}" r="5" fill="${paper}" opacity="0.93"/>` +
      `<circle cx="${w / 2 - 13}" cy="${h + 23}" r="3" fill="${paper}" opacity="0.93"/></g>` +
      `<g filter="url(#rough)"><path d="${d}" fill="none" stroke="${ink}" stroke-width="1.6"/>` +
      `<circle cx="${w / 2 - 6}" cy="${h + 11}" r="5" fill="none" stroke="${ink}" stroke-width="1.4"/>` +
      `<circle cx="${w / 2 - 13}" cy="${h + 23}" r="3" fill="none" stroke="${ink}" stroke-width="1.3"/>${dots}</g>`;
  } else {
    const d = speechPath(w, h);
    svg.innerHTML = `<g filter="url(#wash)"><path d="${d}" fill="#FFFBF2" opacity="0.93"/></g>` +
      `<g filter="url(#rough)"><path d="${d}" fill="none" stroke="${ink}" stroke-width="1.6" stroke-linejoin="round"/>` +
      `<path d="${speechPath(w, h)}" fill="none" stroke="${ink}" stroke-width="0.7" opacity="0.45" transform="translate(1.2 1)"/></g>`;
  }
}
function showThinking(asked) {
  bubble.className = 'bubble thinking';
  bubble.innerHTML = '<div class="think-space"></div>';
  placeBubble(); drawBubble();
}
function showSpeech(asked) {
  bubble.className = 'bubble';
  bubble.innerHTML = `<button class="close" aria-label="Close">&times;</button>` +
    (asked ? `<div class="asked"></div>` : '') + `<div class="text"></div>`;
  if (asked) bubble.querySelector('.asked').textContent = asked;
  bubble.querySelector('.close').addEventListener('click', e => { e.stopPropagation(); hideBubble(); });
  placeBubble(); drawBubble();
  return bubble.querySelector('.text');
}
function hideBubble() { bubble.className = 'bubble hidden'; bubble.innerHTML = ''; }
function addReply() {
  // a hand-lettered line to answer little me right in the bubble
  const form = document.createElement('form'); form.className = 'reply';
  form.innerHTML = '<input placeholder="say something back..." aria-label="Reply to little me"><button aria-label="Send">&rarr;</button>';
  form.addEventListener('submit', e => {
    e.preventDefault();
    const t = form.querySelector('input').value.trim(); if (!t) return;
    askLittleMe(t);
  });
  bubble.append(form); bubbleChanged();
}
let redraw = null;
function bubbleChanged() { cancelAnimationFrame(redraw); redraw = requestAnimationFrame(() => { placeBubble(); drawBubble(); }); }
bubble.addEventListener('click', e => e.stopPropagation());
document.querySelector('.stage').addEventListener('click', e => {
  // tapping the island away from little me and the bubble puts the conversation away
  if (!bubble.classList.contains('hidden') && !e.target.closest('#bubble') && !e.target.closest('#me')) hideBubble();
});
async function askLittleMe(text) {
  showThinking(text);
  let out = null, got = '';
  const speak = () => out || (out = showSpeech(text));
  try {
    const r = await fetch('/api/ask', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text})});
    if (!r.ok || !r.body) throw new Error('no answer');
    const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = '';
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      buf += dec.decode(value, {stream: true});
      let cut;
      while ((cut = buf.indexOf('\\n\\n')) >= 0) {
        const chunk = buf.slice(0, cut); buf = buf.slice(cut + 2);
        if (!chunk.startsWith('data: ')) continue;
        const ev = JSON.parse(chunk.slice(6));
        if (ev.kind === 'delta') { speak(); got += ev.payload; out.textContent = got; out.scrollTop = out.scrollHeight; bubbleChanged(); }
        else if (ev.kind === 'done') {
          speak(); out.textContent = ev.payload.answer;
          if (ev.payload.handoff) {
            const b = document.createElement('button'); b.className = 'more'; b.textContent = 'take this to a chat';
            b.addEventListener('click', async () => {
              hideBubble();
              const r2 = await fetch('/api/say', {method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text, client: window.SHELL_CLIENT || null})});
              toast(r2.ok ? 'Opening a chat for this.' : "Couldn't open a chat. Try again.");
            });
            bubble.append(b);
          }
          addReply();
          const inp = bubble.querySelector('.reply input'); if (inp) inp.focus({preventScroll: true});
        } else if (ev.kind === 'error') { speak(); out.textContent = ev.payload; addReply(); }
      }
    }
  } catch (err) { speak(); out.textContent = "hmm i couldn't answer just now. try again in a sec?"; addReply(); }
}
document.getElementById('say-form').addEventListener('submit', e => {
  e.preventDefault();
  const text = document.getElementById('say').value.trim(); if (!text) return;
  closeSheet();
  document.getElementById('say').value = '';
  askLittleMe(text);
});
document.getElementById('say').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); document.getElementById('say-form').requestSubmit(); }
});
document.querySelectorAll('[data-bring-back]').forEach(b => b.addEventListener('click', async () => {
  const r = await fetch(`/api/places/${encodeURIComponent(b.dataset.bringBack)}/bring-back`, {method: 'POST'});
  if (r.ok) location.reload(); else toast('That did not work. Try again.');
}));

// Little me: drag to move, tap to talk.
const sprite = document.getElementById('me');
const stage = document.querySelector('.stage');
function place(x, y) {
  sprite.style.left = (x / TOWN.width * 100) + '%'; sprite.style.top = (y / TOWN.height * 100) + '%';
  if (!bubble.classList.contains('hidden')) placeBubble();
}
place(TOWN.me[0], TOWN.me[1]);
let drag = null;
sprite.addEventListener('pointerdown', e => {
  sprite.setPointerCapture(e.pointerId);
  drag = {sx: e.clientX, sy: e.clientY, moved: false};
});
sprite.addEventListener('pointermove', e => {
  if (!drag) return;
  if (!drag.moved && Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) < 6) return;
  drag.moved = true; sprite.classList.add('dragging');
  const r = stage.getBoundingClientRect();
  const x = Math.min(Math.max((e.clientX - r.left) / r.width * TOWN.width, 20), TOWN.width - 20);
  const y = Math.min(Math.max((e.clientY - r.top + sprite.offsetHeight * 0.45) / r.height * TOWN.height, 70), TOWN.height - 4);
  drag.x = x; drag.y = y; place(x, y);
});
sprite.addEventListener('pointerup', async () => {
  if (!drag) return;
  const d = drag; drag = null; sprite.classList.remove('dragging');
  if (!d.moved) { openSheet('__me__'); return; }
  await fetch('/api/me/position', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({shape: TOWN.shape, x: Math.round(d.x), y: Math.round(d.y)})});
});
sprite.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openSheet('__me__'); } });

// The card's clock, in your own time zone, and a quiet reload when the sun sets or rises.
const fmtDate = new Intl.DateTimeFormat('en-US', {timeZone: TOWN.tz, weekday: 'short', month: 'short', day: 'numeric'});
const fmtTime = new Intl.DateTimeFormat('en-US', {timeZone: TOWN.tz, hour: 'numeric', minute: '2-digit'});
const fmtStamp = new Intl.DateTimeFormat('sv-SE', {timeZone: TOWN.tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'});
function tick() {
  const now = new Date();
  document.getElementById('clock').textContent = (fmtDate.format(now) + ' \u00b7 ' + fmtTime.format(now)).toLowerCase();
  if (TOWN.sunrise && TOWN.sunset) {
    const stamp = fmtStamp.format(now).replace(' ', 'T');
    const night = !(TOWN.sunrise <= stamp && stamp < TOWN.sunset);
    if (night !== TOWN.night) location.reload();
  }
}
const LOADED = Date.now();
tick(); setInterval(() => { tick(); if (Date.now() - LOADED > 3600e3) location.reload(); }, 30000);
(function drawCard() {
  const card = document.querySelector('.wcard'); if (!card) return;
  const svg = card.querySelector('.wbg'); const w = card.offsetWidth, h = card.offsetHeight;
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  const d = `M6 ${2 + jit(2)} Q${w / 2} ${jit(2)} ${w - 6} ${2 + jit(2)} Q${w + jit(1)} ${h / 2} ${w - 4} ${h - 2 + jit(2)} ` +
    `Q${w / 2} ${h + 2 + jit(2)} 4 ${h - 3} Q${jit(2)} ${h / 2} 6 ${2 + jit(2)} Z`;
  svg.innerHTML = `<g filter="url(#wash)"><path d="${d}" fill="#FFFBF2" opacity="0.93"/></g>` +
    `<g filter="url(#rough)"><path d="${d}" fill="none" stroke="#5A4A3C" stroke-width="1.5"/></g>`;
})();
window.addEventListener('message', e => {
  if (e.source === window.parent && e.data && e.data.type === 'shell:handshake') window.SHELL_CLIENT = e.data.clientId;
});
if (window.STUDIO_TOWN_WAITING) setTimeout(() => location.reload(), 2500);
if (window.parent !== window) window.parent.postMessage({type: 'shell:location', path: location.pathname + location.search}, '*');
"""


def _tucked_html(tucked: list[dict]) -> str:
    if not tucked:
        return ""
    items = "".join(f'<li><span>{html.escape(p["label"])}</span>'
                    f'<button class="link" data-bring-back="{html.escape(p["app"])}">Bring back</button></li>' for p in tucked)
    return f'<section class="tucked"><div class="label">Tucked away</div><ul>{items}</ul></section>'


LOT = {"app": "__lot__", "label": "Build something new", "wild": False, "chats": [],
       "status": "An empty lot, waiting. Tell little me what you'd like, and it'll go up here.",
       "action": "Ask little me to build it"}


def me_svg(me: dict, size: int = 56) -> str:
    wash, ink = avatar(30, 62, size, me["colour"], acc=me.get("accessory"), mouth="open", wave=True)
    return (f'<svg viewBox="0 -8 66 74" xmlns="http://www.w3.org/2000/svg"><g filter="url(#wash)">{wash}</g>'
            f'<g filter="url(#rough)">{ink}</g></svg>')


ICONS = {
    "sun": '<circle cx="14" cy="14" r="6" fill="#F2D98C" stroke="#5A4A3C" stroke-width="1.3"/>'
           '<path d="M14 2v4M14 22v4M2 14h4M22 14h4M5.5 5.5l3 3M19.5 19.5l3 3M22.5 5.5l-3 3M8.5 19.5l-3 3" stroke="#5A4A3C" stroke-width="1.2" stroke-linecap="round"/>',
    "moon": '<path d="M16 4a10 10 0 1 0 8 15A8 8 0 1 1 16 4Z" fill="#F6EBC4" stroke="#5A4A3C" stroke-width="1.3"/>',
    "cloud": '<path d="M7 21a5 5 0 0 1 1-10 7 7 0 0 1 13 2 4 4 0 0 1 0 8Z" fill="#FFFBF2" stroke="#5A4A3C" stroke-width="1.3"/>',
    "partly": '<circle cx="10" cy="10" r="5" fill="#F2D98C" stroke="#5A4A3C" stroke-width="1.2"/>'
              '<path d="M9 23a4.5 4.5 0 0 1 1-9 6 6 0 0 1 11 2 3.5 3.5 0 0 1 0 7Z" fill="#FFFBF2" stroke="#5A4A3C" stroke-width="1.3"/>',
    "fog": '<path d="M4 10h20M2 15h22M6 20h18" stroke="#5A4A3C" stroke-width="1.4" stroke-linecap="round"/>',
    "rain": '<path d="M7 17a5 5 0 0 1 1-10 7 7 0 0 1 13 2 4 4 0 0 1 0 8Z" fill="#FFFBF2" stroke="#5A4A3C" stroke-width="1.3"/>'
            '<path d="M9 21l-1 4M14 21l-1 4M19 21l-1 4" stroke="#8FA1B2" stroke-width="1.5" stroke-linecap="round"/>',
    "snow": '<path d="M7 17a5 5 0 0 1 1-10 7 7 0 0 1 13 2 4 4 0 0 1 0 8Z" fill="#FFFBF2" stroke="#5A4A3C" stroke-width="1.3"/>'
            '<circle cx="9" cy="22" r="1.3" fill="#8FA1B2"/><circle cx="14" cy="24" r="1.3" fill="#8FA1B2"/><circle cx="19" cy="22" r="1.3" fill="#8FA1B2"/>',
    "storm": '<path d="M7 17a5 5 0 0 1 1-10 7 7 0 0 1 13 2 4 4 0 0 1 0 8Z" fill="#FFFBF2" stroke="#5A4A3C" stroke-width="1.3"/>'
             '<path d="M14 18l-3 5h4l-2 4" stroke="#C26D53" stroke-width="1.5" fill="none" stroke-linecap="round"/>',
}


def weather_card(weather: dict | None) -> str:
    """A small hand-drawn card: the date and time (kept current in the page) and the weather, if known."""
    weather = weather or {}
    icon_key = weather.get("icon")
    if icon_key == "sun" and weather.get("night"):
        icon_key = "moon"
    icon = (f'<svg class="wicon" viewBox="0 0 28 28" aria-hidden="true"><g filter="url(#rough)">{ICONS[icon_key]}</g></svg>'
            if icon_key in ICONS else "")
    line2 = ""
    if weather.get("temp") is not None:
        place = f" in {html.escape(weather['place'].lower())}" if weather.get("place") else ""
        line2 = f'<div class="wline">{icon}<span>{weather["temp"]}&deg; {html.escape(weather.get("words", ""))}{place}</span></div>'
    return (f'<div class="wcard"><svg class="wbg" aria-hidden="true"></svg><div class="wdate" id="clock"></div>{line2}</div>')


def render_page(greeting: str, subtitle: str, owner: str, places: list[dict], picture_url: str | None, hotspots: str,
                lay: dict, shape: str, me: dict, me_pos: tuple[int, int], tucked: list[dict] | None = None,
                weather: dict | None = None, tz: str = "UTC") -> str:
    """places: dicts with app, label, kind, wild, status, action, chats.
    picture_url is the painted town, or None while it is still being painted."""
    width, height = lay["width"], lay["height"]
    if picture_url:
        pad = lay.get("pad", 0)
        art = (f'<img class="town" src="{picture_url}" alt="Your town" width="{width + 2 * pad}" height="{height}" '
               f'style="width:{(width + 2 * pad) / width * 100:.3f}%;margin-left:{-pad / width * 100:.3f}%">')
    else:
        art = f'<div class="painting" style="aspect-ratio:{width}/{height}"><span>painting your town...</span></div>'
    sprite_w = 54 / width * 100
    sprite = (f'<div class="me-sprite" id="me" tabindex="0" role="button" aria-label="Little me" style="width:{sprite_w:.2f}%">'
              f'<span class="hint">drag me, or tap to talk</span>{me_svg(me)}</div>')
    header = (f'<header class="town-head"><div class="label">{html.escape(owner)}\'s town</div>'
              f'<h1>{html.escape(greeting)}</h1><p class="sub">{html.escape(subtitle)}</p></header>')
    safe_json = json.dumps({**{p["app"]: p for p in places}, "__lot__": LOT}).replace("</", "<\\/")
    town_json = json.dumps({"shape": shape, "width": width, "height": height, "me": list(me_pos), "tz": tz,
                            "night": bool((weather or {}).get("night")),
                            "sunrise": (weather or {}).get("sunrise"), "sunset": (weather or {}).get("sunset")})
    card = weather_card(weather)
    return f"""<!doctype html>
<html lang="en" class="{shape}{' night' if (weather or {}).get('night') else ''}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your town</title>
<link rel="stylesheet" href="/static/fonts.css">
<style>{CSS}{TOWN_CSS}</style></head>
<body class="town-page">{FILTERS}
{header if shape == "tall" else ""}
<div class="stage" style="--ratio:{width / height:.4f}">{header if shape == "wide" else ""}{card}{art}{hotspots}{sprite}<div id="bubble" class="bubble hidden"></div></div>
<div class="below">{_tucked_html(tucked or [])}</div>
<div class="sheet-bg"></div>
<div class="sheet" role="dialog" aria-modal="true">
  <h2></h2>
  <p class="status"></p>
  <div class="pick"><label for="chat-pick">Chat to open beside it</label><select id="chat-pick"></select></div>
  <button class="btn primary" id="open-btn"></button>
  <div class="row hidden" id="wild-row">
    <button class="btn soft" id="keep-btn">Keep it wild</button>
    <button class="btn soft" id="tuck-btn">Tuck it away</button>
  </div>
</div>
<div class="sheet me-sheet" role="dialog" aria-modal="true">
  <div class="me-head">{me_svg(me)}<div class="whatsup">what's up?</div></div>
  <form id="say-form">
    <textarea id="say" rows="3" placeholder="tell me anything..."></textarea>
    <button class="btn primary">Ask little me</button>
  </form>
  <div class="row">
    <a class="btn soft" href="/book">Memory book</a>
    <a class="btn soft" href="/me">Change how I look</a>
  </div>
</div>
<div class="toast"></div>
<script id="places-data" type="application/json">{safe_json}</script>
<script id="town-data" type="application/json">{town_json}</script>
<script>window.STUDIO_TOWN_WAITING = {str(not picture_url).lower()};</script>
<script>{JS}</script>
</body></html>"""
