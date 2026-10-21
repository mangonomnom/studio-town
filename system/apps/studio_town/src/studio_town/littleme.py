"""Little me's quick answers: one fast AI call over what little me already knows, streamed word by word.

Opening a full chat takes ~20s to start and then researches from scratch. For everyday questions
little me instead answers straight from a small digest: your memory notes, your town, what's in
your apps, your recent chats, and the last few things you said to it. When a question needs real
work (building, changing things, digging deep), it says so and offers to take it to a chat.

Every exchange is logged raw in DATA_DIR/little_me/talk.jsonl (question, answer, cost, seconds).
"""

import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from studio_town.claude_p import _child_env
from studio_town.memorybook import read_notes

log = logging.getLogger(__name__)

ASK_MODEL = "claude-haiku-4-5"
HANDOFF = "[[chat]]"
ACTIVITY = Path("data/.state/system_interface/events/client_activity/events.jsonl")
APPS_DATA = Path("data/.apps")
MAX_CONTEXT_CHARS = 40_000

SYSTEM = f"""You are "little me", the user's small avatar who lives in their Studio town. You ARE a little version
of them, so you talk the way they talk. Study the samples of their own messages in the context and match that voice:
casual and warm, mostly lowercase, short, excited in a sweet way ("oo", "sooo", "yah", "hmm", "okkie", "lol", "!!").
You may use one of their faces like :> or :'O or :) when it really fits, but most replies have none, and never more
than one in a reply. Never use long dashes (no em dash or en dash); use commas, periods or "..." instead.
Keep it to one to three short sentences, like a speech bubble. No markdown, no lists, no headings.
Use only the facts in the context below. If the answer isn't there, say you're not sure rather than guessing.
If the question needs real work (building or changing an app, fetching new data, long research, anything more than a
quick answer), say so in one friendly sentence and end your reply with {HANDOFF} so they can take it to a full chat.
Never promise to do something yourself."""


def _json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def _app_facts() -> str:
    """Small, factual digests of what's inside the apps that little me can read quickly."""
    parts = []
    spots = _json(APPS_DATA / "foodie-map" / "spots.json")
    if spots:
        items = spots if isinstance(spots, list) else spots.get("spots", spots)
        items = list(items.values()) if isinstance(items, dict) else items
        lines = [f"- {s.get('name')} ({s.get('cuisine') or '?'}, {s.get('city') or s.get('location') or 'place unknown'})"
                 for s in items if isinstance(s, dict)]
        parts.append(f"Foodie map: {len(lines)} saved spots (the map does not record when each was added).\n"
                     + "\n".join(lines[:120]))
    days_dir = APPS_DATA / "health-diary" / "days"
    if days_dir.is_dir():
        days = sorted(p.stem for p in days_dir.glob("*.json"))
        latest = _json(days_dir / f"{days[-1]}.json") if days else None
        parts.append(f"Health diary: {len(days)} days logged ({', '.join(days[-7:])}). "
                     f"Latest day: {json.dumps(latest)[:1200] if latest else 'none'}")
    brief = _json(APPS_DATA / "octopus" / "briefing.json")
    if isinstance(brief, dict):
        heads = []
        for cat in brief.get("categories", [])[:8]:
            if isinstance(cat, dict):
                items = cat.get("items") or cat.get("stories") or []
                titles = [i.get("title") or i.get("headline") for i in items[:3] if isinstance(i, dict)]
                heads.append(f"{cat.get('name') or cat.get('title')}: " + "; ".join(t for t in titles if t))
        parts.append(f"Daily briefing ({brief.get('date')}):\n" + "\n".join(heads))
    return "\n\n".join(parts)


def _recent_chats(days: int = 14) -> str:
    """What the user said in their chats lately, newest last (their own words only)."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    titles = {}
    agents = Path(os.environ.get("MNGR_HOST_DIR", str(Path.home() / ".mngr"))) / "agents"
    for f in agents.glob("*/data.json"):
        d = _json(f, {})
        labels = d.get("labels") or {}
        titles[d.get("id")] = labels.get("display_name") or d.get("name")
    lines = []
    if ACTIVITY.exists():
        for line in ACTIVITY.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "message" and e.get("timestamp", "") >= since and e.get("text"):
                chat = titles.get(e.get("key"), "a chat")
                lines.append(f"{e['timestamp'][:10]} in \"{chat}\": {e['text'][:220].replace(chr(10), ' ')}")
    return "\n".join(lines[-60:])


def _style_samples(n: int = 25) -> str:
    """The user's own short messages, as samples of how they talk."""
    if not ACTIVITY.exists():
        return "(none yet)"
    msgs = []
    for line in ACTIVITY.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = (e.get("text") or "").strip().replace("\n", " ")
        if e.get("type") == "message" and 0 < len(text) <= 240:
            msgs.append(text)
    return "\n".join(f"- {m}" for m in msgs[-n:]) or "(none yet)"


def soften(text: str) -> str:
    """The user never uses long dashes, so little me doesn't either."""
    return (text.replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", ", ").replace("\u2013", "-"))


def build_context(town_lines: str, history: list[dict], now_local: str) -> str:
    notes = read_notes()
    about = "\n\n".join(f"[{name}]\n{n['body'][:3500]}" for name, n in notes.items())
    convo = "\n".join(f"You asked: {h['q']}\nLittle me said: {soften(h['a'])}" for h in history[-6:])
    ctx = (f"Right now it is {now_local}.\n\n== How the user writes (their own recent messages; talk like this) ==\n"
           f"{_style_samples()}\n\n== What little me knows about the user ==\n{about}\n\n"
           f"== Their town (their apps) ==\n{town_lines}\n\n== Inside their apps ==\n{_app_facts()}\n\n"
           f"== What they said in chats over the last two weeks ==\n{_recent_chats()}\n\n"
           f"== Earlier in this conversation with little me ==\n{convo or '(nothing yet)'}")
    return ctx[:MAX_CONTEXT_CHARS]


IDLE_SECONDS = 10 * 60      # a quiet session goes back to sleep after this long
MAX_AGE_SECONDS = 60 * 60   # and is refreshed at least hourly, so what it knows stays current
WAKE_UP = "(little me is waking up. reply with only: hi)"


class _Session:
    """One long-lived `claude -p` that stays awake for a conversation.

    Starting `claude -p` costs ~3-4s and re-reading the context costs more, so a fresh process
    per message made even "ok" take 5s+. A warm session answers short things in ~1-2s, and
    the context sits in the system prompt so it is cached across turns."""

    def __init__(self, context: str):
        self.cwd = tempfile.TemporaryDirectory(prefix="little_me_")
        argv = ["claude", "-p", "--model", ASK_MODEL, "--input-format", "stream-json", "--output-format", "stream-json",
                "--verbose", "--include-partial-messages", "--tools", "", "--system-prompt", f"{SYSTEM}\n\n{context}",
                "--no-session-persistence"]
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, cwd=self.cwd.name, env=_child_env())
        self.born = self.used = time.time()
        self.spent = 0.0
        self.lock = threading.Lock()

    def alive(self) -> bool:
        return self.proc.poll() is None

    def stale(self) -> bool:
        now = time.time()
        return not self.alive() or now - self.used > IDLE_SECONDS or now - self.born > MAX_AGE_SECONDS

    def turn(self, text: str):
        """Send one message; yield ("text", chunk) as it streams, then ("end", (error, turn_cost))."""
        self.used = time.time()
        self.proc.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": text}}) + "\n")
        self.proc.stdin.flush()
        for line in self.proc.stdout:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "stream_event":
                ev = e.get("event") or {}
                chunk = (ev.get("delta") or {}).get("text") if ev.get("type") == "content_block_delta" else None
                if chunk:
                    yield "text", chunk
            elif e.get("type") == "result":
                total = e.get("total_cost_usd") or 0.0
                cost, self.spent = max(0.0, total - self.spent), max(total, self.spent)
                self.used = time.time()
                yield "end", (str(e.get("result") or "no answer") if e.get("is_error") else None, cost)
                return
        yield "end", ("little me stopped unexpectedly", 0.0)

    def close(self) -> None:
        try:
            if self.alive():
                self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        self.cwd.cleanup()


class LittleMe:
    def __init__(self, data_dir: Path):
        self.log_path = data_dir / "little_me" / "talk.jsonl"
        self._session: _Session | None = None
        self._guard = threading.Lock()
        self._waking = threading.Event()
        self._waking.set()
        threading.Thread(target=self._reaper, daemon=True).start()

    def history(self, n: int = 6) -> list[dict]:
        if not self.log_path.exists():
            return []
        rows = [json.loads(line) for line in self.log_path.read_text().splitlines() if line.strip()]
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        return [r for r in rows if r.get("at", "") >= cutoff and r.get("a")][-n:]

    # ------------------------------------------------------------ keeping little me awake

    def _reaper(self) -> None:
        while True:
            time.sleep(60)
            with self._guard:
                s = self._session
                if s and s.stale() and not s.lock.locked():
                    self._session = None
                    s.close()

    def warm(self, context_fn) -> None:
        """Wake little me in the background (called when you tap it), so your first message is quick."""
        with self._guard:
            if (self._session and not self._session.stale()) or not self._waking.is_set():
                return
            self._waking.clear()

        def work() -> None:
            started = time.time()
            try:
                s = _Session(context_fn())
                with s.lock:
                    error, cost = None, 0.0
                    for kind, payload in s.turn(WAKE_UP):
                        if kind == "end":
                            error, cost = payload
                self._log({"at": datetime.now(timezone.utc).isoformat(), "q": None, "a": None, "wake_up": True,
                           "cost_usd": cost, "seconds": round(time.time() - started, 1), "error": error})
                with self._guard:
                    old, self._session = self._session, s
                if old:
                    old.close()
            except Exception:
                log.exception("could not wake little me")
            finally:
                self._waking.set()

        threading.Thread(target=work, daemon=True).start()

    def _get_session(self, context_fn) -> _Session:
        self._waking.wait(timeout=30)  # if it is mid-wake-up, that is still the quickest way in
        with self._guard:
            if self._session is None or self._session.stale():
                if self._session:
                    self._session.close()
                self._session = _Session(context_fn())
            return self._session

    # ------------------------------------------------------------ talking

    def ask(self, question: str, context_fn):
        """Yield ("delta", text) as the answer streams in, then ("done", {answer, handoff}) or ("error", msg)."""
        started = time.time()
        answer, cost, error = "", None, None
        try:
            s = self._get_session(context_fn)
            with s.lock:
                held = ""
                for kind, payload in s.turn(question):
                    if kind == "text":
                        answer += payload
                        held += payload
                        cut = held.rfind("[")  # hold back anything that might be the hand-off marker
                        safe, held = (held, "") if cut < 0 else (held[:cut], held[cut:])
                        if safe:
                            yield "delta", soften(safe)
                    else:
                        error, cost = payload
                if held and HANDOFF not in held:
                    yield "delta", soften(held)
        except Exception as exc:
            error = str(exc)
            with self._guard:
                if self._session:
                    self._session.close()
                    self._session = None
        seconds = round(time.time() - started, 1)
        handoff = HANDOFF in answer
        clean = soften(answer.replace(HANDOFF, "")).strip()
        self._log({"at": datetime.now(timezone.utc).isoformat(), "q": question, "a": clean, "handoff": handoff,
                   "cost_usd": cost, "seconds": seconds, "model": ASK_MODEL, "error": error})
        if error or not clean:
            log.warning("little me could not answer: %s", error)
            yield "error", "hmm i got a bit tangled up there. try asking again?"
        else:
            yield "done", {"answer": clean, "handoff": handoff}

    def _log(self, row: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as f:
            f.write(json.dumps(row) + "\n")
