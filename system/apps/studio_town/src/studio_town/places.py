"""Which apps live in town, when each was last on the user's screen, and the user's choices.

Usage is learned by looking, never by changing another app: once a minute we read the
desktop's window list (read-only) and note which apps a connected screen is showing.
Everything is kept under DATA_DIR:

- usage.json          {app: {"first_seen": iso, "last_seen": iso | null}}
- observations.jsonl  the raw sightings the usage was derived from (one line per change)
- prefs.json          {"tucked": [app, ...], "kept_wild": {app: iso}}
"""

import json
import logging
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from studio_town.town import kind_and_label

log = logging.getLogger(__name__)

LAYOUT = "system/scripts/layout.py"
TIMEZONE_FILE = Path("data/.state/user_timezone")
WILD_AFTER = timedelta(days=5)
LAYOUT_VERSION = "island"  # little me's saved spot belongs to one town layout; a new layout starts fresh
LOOK_EVERY_SECONDS = 60

# Built into every workspace, so not part of the user's town.
BUILT_IN = {"browser", "terminal", "terminal-pty", "files", "chat", "getting-started", "system_interface",
            "owner-exec", "studio-town"}

_lock = threading.Lock()


def now() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(path)


def read_desktop() -> dict:
    """The desktop's apps, windows and screens, as the workspace's own layout tool reports them."""
    out = subprocess.run(["python3", LAYOUT, "list"], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(out.stdout)


def town_apps(desktop: dict) -> dict[str, str]:
    """{app name: display name} for the apps the user made (built-ins and previews left out)."""
    apps = {}
    for a in desktop.get("apps", []):
        name = a.get("name", "")
        if name in BUILT_IN or name.endswith("-preview") or a.get("internal"):
            continue
        apps[name] = a.get("display_name") or name
    return apps


def on_screen(desktop: dict) -> set[str]:
    """Apps with a window a connected screen is showing right now."""
    owner = {}
    for a in desktop.get("apps", []):
        for w in a.get("windows", []):
            owner[w["id"]] = a["name"]
    shown = set()
    for c in desktop.get("clients", []):
        if c.get("is_connected"):
            shown.update(owner[w] for w in c.get("shown", []) if w in owner)
    return shown


class Town:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.usage_path = data_dir / "usage.json"
        self.prefs_path = data_dir / "prefs.json"
        self.obs_path = data_dir / "observations.jsonl"
        self._last_shown: set[str] | None = None
        self.apps: dict[str, str] = {}

    # ------------------------------------------------------------ recording

    def look(self) -> None:
        """One read of the desktop: learn new apps and note which are on screen."""
        desktop = read_desktop()
        apps = town_apps(desktop)
        self.apps = apps
        shown = on_screen(desktop) & set(apps)
        stamp = now().isoformat()
        with _lock:
            usage = _read_json(self.usage_path, {})
            for app in apps:
                usage.setdefault(app, {"first_seen": stamp, "last_seen": None})
            for app in shown:
                usage[app]["last_seen"] = stamp
            _write_json(self.usage_path, usage)
            if shown != self._last_shown:
                self.obs_path.parent.mkdir(parents=True, exist_ok=True)
                with self.obs_path.open("a") as f:
                    f.write(json.dumps({"at": stamp, "on_screen": sorted(shown), "town": sorted(apps)}) + "\n")
                self._last_shown = shown

    def visited(self, app: str) -> None:
        with _lock:
            usage = _read_json(self.usage_path, {})
            entry = usage.setdefault(app, {"first_seen": now().isoformat(), "last_seen": None})
            entry["last_seen"] = now().isoformat()
            _write_json(self.usage_path, usage)

    def set_tucked(self, app: str, tucked: bool) -> None:
        with _lock:
            prefs = _read_json(self.prefs_path, {})
            items = set(prefs.get("tucked", []))
            items.add(app) if tucked else items.discard(app)
            prefs["tucked"] = sorted(items)
            _write_json(self.prefs_path, prefs)

    def keep_wild(self, app: str) -> None:
        with _lock:
            prefs = _read_json(self.prefs_path, {})
            prefs.setdefault("kept_wild", {})[app] = now().isoformat()
            _write_json(self.prefs_path, prefs)

    def me(self) -> dict:
        from studio_town.me import DEFAULT

        return {**DEFAULT, **_read_json(self.prefs_path, {}).get("me", {})}

    def set_me(self, me: dict) -> None:
        with _lock:
            prefs = _read_json(self.prefs_path, {})
            prefs["me"] = me
            _write_json(self.prefs_path, prefs)

    def me_position(self, shape: str) -> tuple[int, int] | None:
        pos = _read_json(self.prefs_path, {}).get("me_pos", {}).get(f"{shape}-{LAYOUT_VERSION}")
        return tuple(pos) if pos else None

    def set_me_position(self, shape: str, x: int, y: int) -> None:
        with _lock:
            prefs = _read_json(self.prefs_path, {})
            prefs.setdefault("me_pos", {})[f"{shape}-{LAYOUT_VERSION}"] = [x, y]
            _write_json(self.prefs_path, prefs)

    def start_looking(self) -> None:
        def loop() -> None:
            stop = threading.Event()
            while True:
                try:
                    self.look()
                except Exception:
                    log.exception("could not read the desktop")
                stop.wait(LOOK_EVERY_SECONDS)

        threading.Thread(target=loop, daemon=True).start()

    # ------------------------------------------------------------ reading

    def places(self, apps: dict[str, str]) -> tuple[list[dict], list[dict]]:
        """(places in town, tucked-away places), each a dict the page and drawing understand."""
        usage = _read_json(self.usage_path, {})
        prefs = _read_json(self.prefs_path, {})
        tucked = set(prefs.get("tucked", []))
        in_town, away = [], []
        for app in sorted(apps, key=lambda a: usage.get(a, {}).get("first_seen") or ""):
            kind, label = kind_and_label(app, apps[app])
            entry = usage.get(app, {})
            quiet = _quiet_for(entry)
            wild = quiet is not None and quiet >= WILD_AFTER
            place = {"app": app, "label": label, "kind": kind, "wild": wild,
                     "status": _status(entry, quiet, wild), "action": f"{'Visit' if wild else 'Open'} {label}"}
            (away if app in tucked else in_town).append(place)
        return in_town, away


def _quiet_for(entry: dict) -> timedelta | None:
    """How long since the app was last on screen (or since the town met it, if never)."""
    since = entry.get("last_seen") or entry.get("first_seen")
    if not since:
        return None
    return now() - datetime.fromisoformat(since)


def _status(entry: dict, quiet: timedelta | None, wild: bool) -> str:
    if quiet is None:
        return "New in town."
    days = quiet.days
    if wild:
        return (f"Resting for {days} days, and it's grown a little wild. "
                "Nothing's lost; it's just been quiet.")
    if not entry.get("last_seen"):
        return "New in town. It'll remember your visits from here on."
    if days == 0:
        return "Visited today."
    if days == 1:
        return "Visited yesterday."
    return f"Visited {days} days ago."


def local_now() -> datetime:
    try:
        tz = ZoneInfo(TIMEZONE_FILE.read_text().strip())
    except Exception:
        tz = timezone.utc
    return now().astimezone(tz)


def greeting(name: str = "friend") -> str:
    h = local_now().hour
    part = "morning" if 5 <= h < 12 else "afternoon" if 12 <= h < 17 else "evening" if 17 <= h < 23 else "night"
    return f"Good {part}, {name}"


def subtitle(in_town: list[dict]) -> str:
    n = len(in_town)
    wild = sum(1 for p in in_town if p["wild"])
    text = f"{n} place{'s' if n != 1 else ''} in town"
    return text + (f", {wild} growing wild" if wild else "")
