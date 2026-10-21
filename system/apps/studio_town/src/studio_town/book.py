"""The memory book page: what little me knows about you, in one hand-written book."""

import html

from studio_town.page import CSS as TOWN_CSS

BOOK_CSS = """
.back { display:inline-block; margin-bottom:12px; color:var(--forest); font:600 14px 'DM Sans', sans-serif; text-decoration:none; }
.book { background:#FFFDF8; border-radius:6px 22px 22px 6px; padding:26px 22px 30px 30px; position:relative;
  box-shadow:0 18px 34px -24px rgba(74,64,53,.6), inset 6px 0 0 #E8C5C0; }
.book::before { content:''; position:absolute; left:14px; top:0; bottom:0; border-left:1.5px dashed rgba(194,109,83,.35); }
.chapter { margin-top:26px; } .chapter:first-child { margin-top:0; }
.chapter h2 { font-family:'Fraunces', serif; font-weight:600; font-size:21px; margin:0 0 6px; display:flex; align-items:center; gap:10px; }
.dot { width:12px; height:12px; border-radius:50%; border:1.3px solid var(--ink); display:inline-block; flex:none; }
.entry { font-family:'Gaegu'; font-size:20px; line-height:1.3; padding:9px 0 7px; border-bottom:1px solid #EDE4D3; }
.entry .tools { display:flex; gap:14px; margin-top:2px; }
.entry .tools button, .entry .tools a { background:none; border:0; padding:0; font:500 12.5px 'DM Sans', sans-serif; color:var(--ink-l); cursor:pointer; text-decoration:none; }
.entry .tools button:hover, .entry .tools a:hover { color:var(--forest); }
.entry.crossed .text { text-decoration:line-through; text-decoration-color:#C26D53; text-decoration-thickness:2px; color:var(--ink-l); }
.fix { font-family:'Gaegu'; font-size:19px; color:#5F7A95; }
.empty { font-family:'Gaegu'; font-size:19px; color:var(--ink-l); padding:8px 0; }
.add { display:flex; gap:8px; margin-top:10px; align-items:center; }
.add input { flex:1; min-width:0; border:0; border-bottom:1.5px solid #CBD3C1; background:transparent; font:19px 'Gaegu'; color:var(--ink); padding:6px 2px; outline:none; }
.add button { flex:none; border:0; background:var(--forest); color:var(--oat); border-radius:999px; padding:6px 14px; font:600 13px 'DM Sans', sans-serif; cursor:pointer; }
.banner { font-family:'Gaegu'; font-size:18px; color:#5F7A95; background:#E6ECF2; border-radius:14px; padding:8px 14px; margin:0 0 14px; }
.raw { position:fixed; inset:0; background:rgba(62,82,67,.25); display:none; align-items:flex-end; justify-content:center; }
.raw.show { display:flex; }
.raw .card { background:#FFFDF8; width:min(460px, 100%); max-height:80vh; overflow:auto; border-radius:22px 22px 0 0; padding:20px 22px 28px; }
.raw pre { white-space:pre-wrap; font:13px/1.5 ui-monospace, Menlo, monospace; color:#5E5346; }
.raw h3 { font-family:'Fraunces', serif; margin:0 0 8px; font-size:18px; }
"""

BOOK_JS = """
function toast(msg) {
  const t = document.querySelector('.toast'); t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 1800);
}
document.querySelectorAll('[data-cross]').forEach(b => b.addEventListener('click', () => {
  const entry = b.closest('.entry');
  if (entry.classList.contains('crossed') || entry.querySelector('.fixing')) return;
  const form = document.createElement('form'); form.className = 'add fixing';
  form.innerHTML = '<input placeholder="what is it really? (or leave empty)"><button>Save</button>';
  entry.append(form); form.querySelector('input').focus();
  form.addEventListener('submit', e => {
    e.preventDefault();
    const fix = form.querySelector('input').value.trim(); form.remove();
    entry.classList.add('crossed');
    if (fix) { const f = document.createElement('div'); f.className = 'fix'; f.textContent = fix; entry.querySelector('.text').after(f); }
      send('fix', {text: entry.querySelector('.text').textContent, detail: fix});
  });
}));
async function send(kind, payload) {
  if (window.BOOK_MOCK) { toast('would tell little me'); return; }
  const r = await fetch('/api/book/' + kind, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
  toast(r.ok ? (kind === 'fix' ? 'Little me will remember that.' : 'Added to the book.') : 'That did not save. Try again.');
}
document.querySelectorAll('.add').forEach(form => form.addEventListener('submit', e => {
  e.preventDefault();
  const input = form.querySelector('input'); const text = input.value.trim(); if (!text) return;
  const entry = document.createElement('div'); entry.className = 'entry'; entry.innerHTML = '<div class="text"></div>';
  entry.querySelector('.text').textContent = text; form.before(entry); input.value = '';
  send('add', {text, detail: form.dataset.chapter});
}));
if (window.BOOK_WRITING) setTimeout(() => location.reload(), 8000);
const raw = document.querySelector('.raw');
document.querySelectorAll('[data-note]').forEach(a => a.addEventListener('click', e => {
  e.preventDefault();
  raw.querySelector('h3').textContent = a.dataset.title;
  raw.querySelector('pre').textContent = document.getElementById('note-' + a.dataset.note).textContent;
  raw.classList.add('show');
}));
raw.addEventListener('click', e => { if (e.target === raw) raw.classList.remove('show'); });
if (window.parent !== window) window.parent.postMessage({type: 'shell:location', path: location.pathname + location.search}, '*');
"""


def _script_safe(text: str) -> str:
    return text.replace("</", "<\\/")


def render_book(chapters: list[dict], notes: dict[str, dict], mock: bool = False, owner: str = "friend",
                status: dict | None = None) -> str:
    """chapters: [{title, colour, entries: [{text, note}], empty}]; notes: {id: {title, body}}."""
    status = status or {}
    banner = ""
    if status.get("paused"):
        banner = ('<p class="banner">Little me paused rewriting the book this month to keep costs down. '
                  "Your notes are all still here; ask in chat if you'd like it to carry on.</p>")
    elif status.get("writing"):
        banner = ('<p class="banner">Little me is updating your book with what it learned recently. '
                  "This takes about a minute.</p>")
    parts = []
    for ch in chapters:
        rows = []
        for e in ch["entries"]:
            note = e.get("note")
            source = (f'<a href="#" data-note="{html.escape(note)}" data-title="{html.escape(notes[note]["title"])}">'
                      f"where this came from</a>") if note in notes else ""
            rows.append(f'<div class="entry"><div class="text">{html.escape(e["text"])}</div>'
                        f'<div class="tools"><button data-cross>not quite right?</button>{source}</div></div>')
        if not rows:
            rows.append(f'<div class="empty">{html.escape(ch.get("empty", "Nothing here yet."))}</div>')
        parts.append(f'<section class="chapter"><h2><span class="dot" style="background:{ch["colour"]}"></span>'
                     f'{html.escape(ch["title"])}</h2>{"".join(rows)}'
                     f'<form class="add" data-chapter="{html.escape(ch["title"])}"><input placeholder="add something..." aria-label="Add to {html.escape(ch["title"])}">'
                     f'<button>Add</button></form></section>')
    raw_notes = "".join(f'<script type="text/plain" id="note-{html.escape(k)}">{_script_safe(v["body"])}</script>'
                        for k, v in notes.items())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Memory book</title>
<link rel="stylesheet" href="/static/fonts.css">
<style>{TOWN_CSS}{BOOK_CSS}</style></head>
<body>
<main>
  <a class="back" href="/">&larr; back to town</a>
  <div class="label">{html.escape(owner)}'s memory book</div>
  <h1>All about you</h1>
  <p class="sub">what little me knows, all in one place. fix anything that's off.</p>
  {banner}
  <div class="book">{"".join(parts) or '<div class="empty">little me is writing your book for the first time...</div>'}</div>
</main>
<div class="raw"><div class="card"><h3></h3><pre></pre></div></div>
<div class="toast"></div>
{raw_notes}
<script>window.BOOK_MOCK = {str(mock).lower()}; window.BOOK_WRITING = {str(bool(status.get("writing"))).lower()};</script>
<script>{BOOK_JS}</script>
</body></html>"""
