"""Your apps as a little hand-drawn town; quiet ones grow wild.

Services run from /home/user/workspace (the repo root). Conventions:

- Persistent state (anything written and read across runs -- cursors,
  caches, snapshots, user records): read and write it under ``DATA_DIR``
  (defined below), never a hardcoded ``data/.apps/studio-town/`` at the
  call site. ``DATA_DIR`` defaults to ``data/.apps/studio-town/`` but
  honors the ``STUDIO_TOWN_DATA_DIR`` env var, so an editing agent can point a
  throwaway instance at a *copy* of the data instead of the live store
  (see the update-app skill). Do NOT use ``Path(__file__)``-based
  paths for state -- the bug to avoid is one process writing to
  ``/home/user/workspace/data/.apps/...`` while another reads from
  ``/home/user/workspace/system/apps/<pkg>/data/...``.
- Static assets shipped alongside this file (templates, default
  configs, bundled JSON): ``Path(__file__).parent / "assets/..."`` is
  fine and is the right pattern.
- Listen port: bind ``PORT`` (defined below), which defaults to this
  app's assigned port but honors the ``STUDIO_TOWN_PORT`` env var, so
  an editing agent can boot a throwaway instance on a *spare* port
  alongside the live one (see the update-app skill). Never hardcode
  the port at the ``run_simple`` call.

This is a synchronous Flask app served by the threaded Werkzeug server.
The app owns its own browser origin (the forwarder routes
``http://studio-town.<workspace-host>/`` straight to this port), so it serves
at ``/`` and root-absolute URLs, cookies, and service workers all work
unmodified -- nothing rewrites anything. Use ``flask_sock`` if you need
WebSockets.
"""

import os
from pathlib import Path

import logging
import subprocess
import threading
import time

import json

from flask import Flask, Response, abort, jsonify, request, send_file, stream_with_context

from studio_town.book import render_book
from studio_town.chats import ChatIndex
from studio_town.me import ACCESSORIES, COLOURS
from studio_town.me import DEFAULT as ME_DEFAULT
from studio_town.me import render_me
from studio_town.memorybook import MemoryBook
from studio_town.page import render_page
from studio_town.littleme import LittleMe, build_context
from studio_town.places import Town, greeting, local_now, read_desktop, subtitle
from studio_town.render import ensure_painted, image_path, state_key
from studio_town.sky import Sky
from studio_town.island import draw_island
from studio_town.town import kind_and_label
from werkzeug.serving import run_simple

# Persistent state for this app lives under DATA_DIR. It defaults to
# ``data/.apps/studio-town/`` but is overridable via the ``STUDIO_TOWN_DATA_DIR`` env var
# so a throwaway instance can run against a *copy* of the data while editing --
# see the update-app skill. Always read/write state through DATA_DIR;
# never hardcode ``data/.apps/studio-town/`` at a call site, or the override is
# bypassed. A writing call site should ``DATA_DIR.mkdir(parents=True,
# exist_ok=True)`` before writing.
DATA_DIR = Path(os.environ.get("STUDIO_TOWN_DATA_DIR", "data/.apps/studio-town"))

# Listen port. Defaults to this app's assigned port but is overridable via
# the ``STUDIO_TOWN_PORT`` env var so an editing agent can boot a throwaway
# instance on a spare port next to the live one (see the update-app skill).
# Never hardcode the port at the ``run_simple`` call, or the override is bypassed.
PORT = int(os.environ.get("STUDIO_TOWN_PORT", "8086"))

ASSETS = Path(__file__).parent / "assets"

app = Flask("studio_town", static_folder=None)
log = logging.getLogger("studio_town")

RENDERS_DIR = DATA_DIR / "renders"
TOWN = Town(DATA_DIR)
SKY = Sky(DATA_DIR, str(local_now().tzinfo))
CHATS = ChatIndex(DATA_DIR)
LOT_DRAFT = "I'd like a new app for my town: "
PACKAGES_DIR = Path("system/apps")
ME_COLOURS = set(COLOURS)
ME_ACCESSORIES = {acc for acc, _ in ACCESSORIES}


def _shape() -> str:
    return "wide" if request.args.get("shape") == "wide" else "tall"


def _town(places: list[dict], shape: str, night: bool = False) -> tuple[str, dict, str]:
    """Draw the town, make sure its picture is (being) painted, and return (hotspots, layout, key)."""
    art, hotspots, lay = draw_island(places, shape, night)
    ensure_painted(art, (ASSETS / "fonts.css").read_text(), RENDERS_DIR, lay["art_width"], lay["height"])
    return hotspots, lay, state_key(art)


def _places() -> tuple[list[dict], list[dict]]:
    if not TOWN.apps:
        TOWN.look()
    in_town, away = TOWN.places(TOWN.apps)
    for p in in_town:
        p["chats"] = [{"chat_id": c["chat_id"], "title": c["title"]} for c in CHATS.for_app(p["app"])[:8]]
    return in_town, away


def _chat_apps() -> dict[str, dict]:
    """The town's apps with what the chat matcher needs: a label and the code folder, if any."""
    out = {}
    for app, display in TOWN.apps.items():
        _, label = kind_and_label(app, display)
        pkg = app.replace("-", "_")
        out[app] = {"label": label, "package": pkg if (PACKAGES_DIR / pkg).is_dir() else None}
    return out


@app.route("/")
def index() -> Response:
    # The page carries the location beacon (see page.py's script), which lets the
    # workspace shell reopen this window at the same place.
    shape = _shape()
    in_town, away = _places()
    now = local_now()
    weather = SKY.now(now)
    hotspots, lay, key = _town(in_town, shape, weather["night"])
    picture = f"/town/{key}.jpg" if image_path(RENDERS_DIR, key).exists() else None
    me = TOWN.me()
    pos = TOWN.me_position(shape) or lay["me"]
    return Response(render_page(greeting(me["name"]), subtitle(in_town), me["name"], in_town, picture, hotspots, lay,
                                shape, me, pos, tucked=away, weather=weather, tz=str(now.tzinfo)),
                    mimetype="text/html")


def _layout(*args: str) -> tuple[bool, str]:
    """Run the workspace's window tool; returns (ok, the window id it printed or its last error line)."""
    done = subprocess.run(["python3", "system/scripts/layout.py", *args], capture_output=True, text=True, timeout=60)
    if done.returncode == 0:
        return True, done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""
    detail = (done.stderr or done.stdout).strip().splitlines()
    return False, (detail[-1] if detail else "")


def _client_args(body: dict) -> list[str]:
    client = body.get("client")
    return ["--client", client] if isinstance(client, str) and client.replace("-", "").isalnum() else []


BOOK = MemoryBook(DATA_DIR)


@app.route("/book")
def book_page() -> Response:
    book, notes, status = BOOK.current()
    chapters = book["chapters"] if book else []
    return Response(render_book(chapters, notes, owner=TOWN.me()["name"], status=status), mimetype="text/html")


@app.route("/api/book/<kind>", methods=["POST"])
def book_edit(kind: str) -> Response:
    if kind not in ("fix", "add"):
        abort(404)
    body = request.get_json(silent=True) or {}
    text = str(body.get("text") or "").strip()[:500]
    detail = str(body.get("detail") or "").strip()[:500]
    if not text:
        return jsonify(detail="Nothing to save."), 400
    BOOK.record(kind, text, detail)
    return jsonify(ok=True)


@app.route("/me")
def me_page() -> Response:
    return Response(render_me(TOWN.me()), mimetype="text/html")


@app.route("/api/me", methods=["POST"])
def save_me() -> Response:
    body = request.get_json(silent=True) or {}
    colour = body.get("colour")
    accessory = body.get("accessory")
    name = str(body.get("name") or "").strip()[:24]
    if colour not in ME_COLOURS or accessory not in ME_ACCESSORIES:
        return jsonify(detail="Pick a colour and something to wear from the list."), 400
    TOWN.set_me({"colour": colour, "accessory": accessory, "name": name or ME_DEFAULT["name"]})
    return jsonify(ok=True)


@app.route("/api/me/position", methods=["POST"])
def move_me() -> Response:
    body = request.get_json(silent=True) or {}
    shape = "wide" if body.get("shape") == "wide" else "tall"
    try:
        x, y = int(body["x"]), int(body["y"])
    except (KeyError, TypeError, ValueError):
        return jsonify(detail="Where should little me go?"), 400
    TOWN.set_me_position(shape, x, y)
    return jsonify(ok=True)


LITTLE_ME = LittleMe(DATA_DIR)


def _town_lines() -> str:
    in_town, away = _places()
    rows = [f"- {p['label']}: {p['status']}" + (" (growing wild)" if p["wild"] else "") for p in in_town]
    rows += [f"- {p['label']}: tucked away" for p in away]
    return "\n".join(rows) or "(no apps yet)"


def _little_me_context() -> str:
    stamp = local_now().strftime("%A %d %B %Y, %H:%M")
    return build_context(_town_lines(), LITTLE_ME.history(), stamp)


@app.route("/api/warm", methods=["POST"])
def warm() -> Response:
    """Tapping little me wakes it up, so the first answer comes quickly."""
    LITTLE_ME.warm(_little_me_context)
    return jsonify(ok=True)


@app.route("/api/ask", methods=["POST"])
def ask() -> Response:
    """Little me answers right in the town, streamed as server-sent events."""
    body = request.get_json(silent=True) or {}
    question = str(body.get("text") or "").strip()[:2000]
    if not question:
        return jsonify(detail="Say something first."), 400
    def events():
        for kind, payload in LITTLE_ME.ask(question, _little_me_context):
            yield f"data: {json.dumps({'kind': kind, 'payload': payload})}\n\n"

    resp = Response(stream_with_context(events()), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@app.route("/api/say", methods=["POST"])
def say() -> Response:
    """Whatever you tell little me starts a new chat with that as the first message."""
    body = request.get_json(silent=True) or {}
    text = str(body.get("text") or "").strip()
    if not text:
        return jsonify(detail="Say something first."), 400
    ok, detail = _layout("open", "chat", "--launch", "new", "--param", f"message={text[:4000]}", *_client_args(body))
    if not ok:
        log.warning("could not start a chat: %s", detail)
        return jsonify(detail="Couldn't reach little me just now. Try again in a moment."), 502
    return jsonify(ok=True)


@app.route("/api/places/<name>/<action>", methods=["POST"])
def place_action(name: str, action: str) -> Response:
    body = request.get_json(silent=True) or {}
    client = _client_args(body)
    if name == "__lot__" and action == "open":
        ok, detail = _layout("open", "chat", "--launch", "draft", "--param", f"message={LOT_DRAFT}", *client)
    elif name not in TOWN.apps:
        return jsonify(detail="That place isn't in town any more."), 404
    elif action == "open":
        ok, detail = _open_with_chat(name, body.get("chat"), client)
    elif action == "keep-wild":
        TOWN.keep_wild(name)
        ok, detail = True, ""
    elif action == "tuck-away":
        TOWN.set_tucked(name, True)
        ok, detail = True, ""
    elif action == "bring-back":
        TOWN.set_tucked(name, False)
        ok, detail = True, ""
    else:
        abort(404)
    if not ok:
        log.warning("layout op failed for %s %s: %s", name, action, detail)
        return jsonify(detail="Couldn't open that just now. Try again in a moment."), 502
    return jsonify(ok=True)


def _open_with_chat(app_name: str, chat_id, client: list[str]) -> tuple[bool, str]:
    """Open the chat on the left half and the app on the right half (how the user likes to work).

    The chat is shown in the chat's own main window (the one your avatar opens), so the list of
    all your other chats stays right there beside the conversation."""
    ok, app_win = _layout("open", app_name, *client)
    if not ok:
        return ok, app_win
    TOWN.visited(app_name)
    known = {c["chat_id"] for c in CHATS.for_app(app_name)}
    pinned = _pinned_chat_window()
    if not (isinstance(chat_id, str) and chat_id in known and pinned):
        if app_win.startswith("win-"):
            _layout("place", app_win, "--zone", "maximized", *client)
        return True, app_win
    _layout("navigate", pinned, f"/?chat={chat_id}", *client)
    placed, detail = _layout("place", pinned, "--zone", "left", *client)
    if not placed:
        log.warning("could not place the chat beside the app: %s", detail)
        _layout("focus", pinned, *client)
    if app_win.startswith("win-"):
        _layout("place", app_win, "--zone", "right", *client)
    return True, app_win


def _pinned_chat_window() -> str | None:
    """The chat app's pinned window: the one your avatar opens."""
    try:
        desktop = read_desktop()
    except Exception:
        return None
    for a in desktop.get("apps", []):
        if a.get("name") == "chat":
            for w in a.get("windows", []):
                if w.get("is_pinned"):
                    return w["id"]
    return None


@app.route("/town/<key>.jpg")
def town_picture(key: str) -> Response:
    if not key.isalnum():
        abort(404)
    pic = image_path(RENDERS_DIR, key)
    if not pic.exists():
        abort(404)
    resp = send_file(pic.resolve(), mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


@app.route("/static/fonts.css")
def fonts() -> Response:
    resp = Response((ASSETS / "fonts.css").read_text(), mimetype="text/css")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route("/health")
def health() -> Response:
    return Response('{"status": "ok"}', mimetype="application/json")


def _keep_painted() -> None:
    """Keep day and night pictures of today's town ready in both shapes, so sunset never shows a blank."""
    time.sleep(5)
    while True:
        try:
            places = _places()[0]
            night = SKY.now(local_now())["night"]
            for n in (night, not night):
                for shape in ("wide", "tall"):
                    _town(places, shape, n)
        except Exception:
            log.exception("could not prepare the town's pictures")
        time.sleep(600)


def main() -> None:
    TOWN.start_looking()
    CHATS.start_refreshing(_chat_apps)
    # Paint today's town in both shapes before anyone asks, so the first visit is instant.
    threading.Thread(target=_keep_painted, daemon=True).start()
    run_simple(
        "127.0.0.1", PORT, app, threaded=True, use_reloader=False, use_debugger=False
    )


if __name__ == "__main__":
    main()
