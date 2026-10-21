"""The avatar maker: pick a colour, an accessory and a name for your little me."""

import html
import json

from studio_town.book import BOOK_CSS
from studio_town.drawing import BUTTER, EUC, FILTERS, HAZE_L, PEONY, avatar
from studio_town.page import CSS as TOWN_CSS

COLOURS = [PEONY, EUC, HAZE_L, BUTTER, "#E3B9A6", "#D9CFE6"]
ACCESSORIES = [("sprout", "sprout"), (None, "nothing"), ("glasses", "glasses"), ("beret", "beret"), ("bow", "bow"),
               ("headphones", "headphones"), ("flower", "flower"), ("bun", "bun")]
DEFAULT = {"colour": PEONY, "accessory": "sprout", "name": "friend"}

ME_CSS = """
.maker { background:#FFFDF8; border-radius:24px; padding:18px 18px 22px; box-shadow:0 16px 30px -22px rgba(74,64,53,.55); }
.preview { display:flex; justify-content:center; background:#F4EEE2; border-radius:18px; padding:8px 0 4px; }
.preview svg { width:180px; height:190px; }
.row-label { font-size:11px; letter-spacing:.2em; text-transform:uppercase; font-weight:700; color:var(--ink-l); margin:18px 0 8px; }
.swatches { display:flex; gap:12px; flex-wrap:wrap; }
.swatch { width:34px; height:34px; border-radius:50%; border:1.5px solid var(--ink); cursor:pointer; padding:0; }
.swatch.on { box-shadow:0 0 0 3px #FFFDF8, 0 0 0 5px var(--forest); }
.chips { display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; }
.chip { border:1.5px solid #CBD3C1; background:#FFFDF8; border-radius:14px; padding:4px 2px 6px; cursor:pointer; font:600 11.5px 'DM Sans', sans-serif; color:var(--ink); }
.chip svg { width:54px; height:56px; display:block; margin:0 auto; }
.chip.on { background:#E4EADF; border-color:var(--forest); }
.name { width:100%; border:0; border-bottom:1.5px solid #CBD3C1; background:transparent; font:22px 'Gaegu'; color:var(--ink); padding:6px 2px; outline:none; }
"""

ME_JS = """
const ART = JSON.parse(document.getElementById('art').textContent);
const state = JSON.parse(document.getElementById('state').textContent);
const preview = document.querySelector('.preview');
function draw() {
  preview.innerHTML = ART[state.accessory || 'none'].replaceAll('__C__', state.colour);
  document.querySelectorAll('.swatch').forEach(s => s.classList.toggle('on', s.dataset.colour === state.colour));
  document.querySelectorAll('.chip').forEach(c => c.classList.toggle('on', c.dataset.acc === (state.accessory || 'none')));
}
document.querySelectorAll('.swatch').forEach(s => s.addEventListener('click', () => { state.colour = s.dataset.colour; draw(); }));
document.querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => { state.accessory = c.dataset.acc === 'none' ? null : c.dataset.acc; draw(); }));
document.querySelector('.name').addEventListener('input', e => { state.name = e.target.value; });
function toast(msg) {
  const t = document.querySelector('.toast'); t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 1800);
}
document.getElementById('save').addEventListener('click', async () => {
  if (window.ME_MOCK) { toast(`would save ${state.name || 'you'}`); return; }
  const r = await fetch('/api/me', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(state)});
  if (r.ok) location.href = '/'; else toast('That did not save. Try again.');
});
draw();
if (window.parent !== window) window.parent.postMessage({type: 'shell:location', path: location.pathname + location.search}, '*');
"""


def _art(accessory: str | None, size: int, box: tuple[int, int]) -> str:
    wash, ink = avatar(box[0] / 2, box[1] - 6, size, "__C__", acc=accessory, mouth="happy" if size < 80 else "open",
                       wave=size >= 80)
    return (f'<svg viewBox="0 0 {box[0]} {box[1]}" xmlns="http://www.w3.org/2000/svg">'
            f'<g filter="url(#wash)">{wash}</g><g filter="url(#rough)">{ink}</g></svg>')


def render_me(me: dict, mock: bool = False) -> str:
    art = {(acc or "none"): _art(acc, 130, (180, 190)) for acc, _ in ACCESSORIES}
    chips = "".join(f'<button class="chip" data-acc="{acc or "none"}">{_art(acc, 50, (60, 62)).replace("__C__", me["colour"])}'
                    f"{label}</button>" for acc, label in ACCESSORIES)
    art_json = json.dumps(art).replace("</", "<\\/")
    swatches = "".join(f'<button class="swatch" data-colour="{c}" style="background:{c}" aria-label="colour {c}"></button>'
                       for c in COLOURS)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Make a little you</title>
<link rel="stylesheet" href="/static/fonts.css">
<style>{TOWN_CSS}{BOOK_CSS}{ME_CSS}</style></head>
<body>{FILTERS}
<main>
  <a class="back" href="/">&larr; back to town</a>
  <div class="label">little me</div>
  <h1>Make a little you</h1>
  <p class="sub">it lives in your town and keeps your memory book.</p>
  <div class="maker">
    <div class="preview"></div>
    <div class="row-label">Colour</div>
    <div class="swatches">{swatches}</div>
    <div class="row-label">Something to wear</div>
    <div class="chips">{chips}</div>
    <div class="row-label">Name</div>
    <input class="name" value="{html.escape(me.get("name") or "")}" placeholder="your name" maxlength="24">
    <button class="btn primary" id="save">That's me!</button>
  </div>
</main>
<div class="toast"></div>
<script type="application/json" id="art">{art_json}</script>
<script type="application/json" id="state">{json.dumps(me)}</script>
<script>window.ME_MOCK = {str(mock).lower()};</script>
<script>{ME_JS}</script>
</body></html>"""
