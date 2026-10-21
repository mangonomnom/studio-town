"""Paints the town into a finished picture once, so the page never has to.

The hand-drawn look comes from SVG filters, which take seconds to paint on a tall page.
The town only changes when its places change, so we paint it once per state (in a
headless browser, off the request path) and serve the picture from then on.
"""

import hashlib
import logging
import threading
from pathlib import Path

from studio_town.drawing import FILTERS

log = logging.getLogger(__name__)

BROWSER = "/opt/fortress/tilion-fortress/tilion"
SCALE = 2
KEEP = 12

_lock = threading.Lock()
_pending: set[str] = set()
_one_at_a_time = threading.Semaphore(1)  # paintings run one by one; several at once starve each other


def state_key(svg: str) -> str:
    return hashlib.sha256(svg.encode()).hexdigest()[:16]


def image_path(renders_dir: Path, key: str) -> Path:
    return renders_dir / f"{key}.jpg"


def _paint(svg: str, fonts_css: str, out: Path, width: int, height: int) -> None:
    from playwright.sync_api import sync_playwright

    doc = (f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts_css}"
           f"html,body{{margin:0;background:#FDFAF3}} svg{{display:block;width:{width}px;height:{height}px}}</style></head>"
           f"<body>{FILTERS}{svg}</body></html>")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=BROWSER, args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=SCALE)
            page.set_content(doc, wait_until="load")
            page.evaluate("document.fonts.ready")
            tmp = out.with_suffix(".tmp.jpg")
            page.locator("svg.town").screenshot(path=str(tmp), type="jpeg", quality=88, timeout=120_000)
            tmp.replace(out)
        finally:
            browser.close()


def _prune(renders_dir: Path) -> None:
    pics = sorted(renders_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in pics[KEEP:]:
        old.unlink(missing_ok=True)


def ensure_painted(svg: str, fonts_css: str, renders_dir: Path, width: int, height: int) -> None:
    """Start painting this state in the background unless it is painted or already underway."""
    key = state_key(svg)
    out = image_path(renders_dir, key)
    with _lock:
        if out.exists() or key in _pending:
            return
        _pending.add(key)

    def work() -> None:
        try:
            renders_dir.mkdir(parents=True, exist_ok=True)
            with _one_at_a_time:
                _paint(svg, fonts_css, out, width, height)
            _prune(renders_dir)
        except Exception:
            log.exception("could not paint the town")
        finally:
            with _lock:
                _pending.discard(key)

    threading.Thread(target=work, daemon=True).start()
