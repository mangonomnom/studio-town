"""Which chats belong to which app.

A chat belongs to an app when it worked on the app's code (strongest signal) or talked
about it. We read each chat's transcript from this host, score it per app, and keep the
scores (the raw evidence) in DATA_DIR/chats.json so the ranking can be re-derived later.

Score = 3 x (tool calls touching system/apps/<package>/) + (mentions of the app by name),
plus a bonus when the chat is named after the app. The top chat is the one that opens
beside the app; the rest are offered as alternatives.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

AGENTS_DIR = Path(os.environ.get("MNGR_HOST_DIR", str(Path.home() / ".mngr"))) / "agents"
MIN_SCORE = 3
REFRESH_SECONDS = 15 * 60

# Agents that are not conversations the user had: workers, updates, automations, services.
NOT_CHATS = ("update-self", "crystallize-", "archived-", "system-services", "harden-", "update-", "heal-")


def _chat_agents() -> list[dict]:
    """The user's chats on this host, read from each agent's own record (the ground truth)."""
    chats = []
    for f in sorted(AGENTS_DIR.glob("*/data.json")):
        try:
            a = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        labels = a.get("labels") or {}
        name = a.get("name") or ""
        if labels.get("automation") or labels.get("agent_created") or name.startswith(NOT_CHATS):
            continue
        chats.append({"agent_id": a["id"], "chat_id": labels.get("chat_id") or a["id"],
                      "title": labels.get("display_name") or name, "name": name})
    return chats


def _words(app: str, label: str) -> list[str]:
    words = {app.lower(), app.replace("-", " ").lower(), label.lower()}
    return [w for w in words if len(w) >= 4]


def _texts(agent_id: str):
    """(text, tool-call blob) per step of a chat's transcript."""
    for f in AGENTS_DIR.glob(f"{agent_id}/events/*/common_transcript/events.jsonl"):
        with f.open() as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                kind = e.get("type")
                if kind == "step" and e.get("source") in ("user", "agent"):
                    yield (e.get("message") or ""), json.dumps(e.get("tool_calls") or "")
                elif kind == "user_message":
                    yield (e.get("content") or ""), ""
                elif kind == "assistant_message":
                    parts = e.get("parts", [])
                    yield (" ".join(p.get("content", "") for p in parts if p.get("type") == "text"),
                           json.dumps([p for p in parts if p.get("type") != "text"]))


def score_chats(apps: dict[str, dict]) -> dict:
    """apps: {name: {"label", "package"}} -> {"at", "chats": [...], "scores": {app: {chat_id: detail}}}."""
    chats = _chat_agents()
    scores: dict[str, dict] = {app: {} for app in apps}
    for chat in chats:
        tally = {app: {"code": 0, "mentions": 0} for app in apps}
        for text, blob in _texts(chat["agent_id"]):
            low = text.lower()
            for app, info in apps.items():
                tally[app]["mentions"] += sum(low.count(w) for w in _words(app, info["label"]))
                if blob and info.get("package"):
                    tally[app]["code"] += blob.count(f"apps/{info['package']}")
        for app, t in tally.items():
            named = 5 if chat["name"] == app else 0
            score = 3 * t["code"] + t["mentions"] + named
            if score >= MIN_SCORE:
                scores[app][chat["chat_id"]] = {**t, "named": bool(named), "score": score}
    return {"at": time.time(), "chats": chats, "scores": scores}


class ChatIndex:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "chats.json"
        self._lock = threading.Lock()

    def refresh(self, apps: dict[str, dict]) -> None:
        data = score_chats(apps)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(self.path)

    def for_app(self, app: str) -> list[dict]:
        """Chats for an app, best first: [{chat_id, title, score}]."""
        try:
            data = json.loads(self.path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        titles = {c["chat_id"]: c["title"] for c in data.get("chats", [])}
        ranked = sorted(data.get("scores", {}).get(app, {}).items(), key=lambda kv: -kv[1]["score"])
        return [{"chat_id": cid, "title": titles.get(cid, "a chat"), "score": d["score"]} for cid, d in ranked if cid in titles]

    def start_refreshing(self, apps_fn) -> None:
        def loop() -> None:
            stop = threading.Event()
            while True:
                apps = {}
                try:
                    apps = apps_fn()
                    if apps:
                        self.refresh(apps)
                except Exception:
                    log.exception("could not match chats to apps")
                stop.wait(REFRESH_SECONDS if apps else 10)

        threading.Thread(target=loop, daemon=True).start()
