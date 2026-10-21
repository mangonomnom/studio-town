"""The memory book: little me's notes about you, rewritten as a friendly book, and your fixes.

Sources are the memory notes every chat reads (data/memories/*.md). The book is a derived
view: an AI pass rewrites the notes as short, plain entries, cached by a fingerprint of the
notes so it only runs again when a note changes. The raw notes stay one tap away.

Your fixes and additions are written back as a memory note of their own
(told-me-in-memory-book.md), so every chat picks them up, and they feed the next rewrite.

Cost guard: every rewrite's cost is logged; once a calendar month passes MONTHLY_CAP_USD the
book stops rewriting itself and says so, until the user asks to resume.
"""

import hashlib
import json
import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

MEMORIES_DIR = Path("data/memories")
TOLD_ME = "told-me-in-memory-book"
WRITE_MODEL = "claude-haiku-4-5"
MONTHLY_CAP_USD = 1.00
SKIPPED_TYPES = {"reference"}  # notes about software internals, not the person

CHAPTERS = [("Your taste", "#E8C5C0"), ("What you're building", "#A3AE9A"), ("Your people", "#8FA1B2"),
            ("How you like me to be", "#EAD7A4"), ("Little things", "#C3CFDA")]
EMPTY = {"Your people": "No one here yet. Tell little me about the people in your life and they'll show up here.",
         "Little things": "Nothing yet. Little habits and favourites will collect here."}

SYSTEM = """You write a warm, plain-language "memory book" for one person, from notes an assistant keeps about them.
Rules:
- Write to the person as "you". Each entry is one short sentence, at most 20 words, in plain words a non-technical
  reader understands. No file names, code, tools, ports, or technical terms.
- Only include what the notes clearly say about the person: their taste, what they are building and why, the people in
  their life, how they want the assistant to behave, and small habits or favourites. Skip notes that are only about
  software internals.
- The note named "told-me-in-memory-book" holds the person's own corrections and additions. They override everything:
  drop or change any entry they corrected, and include what they added.
- At most 5 entries per chapter; fewer is better than padding. No numbers, sizes, usernames or account handles.
- Only say the person did, asked for or decided something if the note says so. Choices the assistant made are not theirs.
- "Your people" is only for real people in their life named in the notes (friends, family, colleagues). If there are
  none, leave that chapter's entries empty. Their own accounts are not people.
- Never invent facts. Placeholder names from example drawings are not real people.
Reply with JSON only, no prose, shaped exactly like:
{"chapters": [{"title": "<one of the given titles>", "entries": [{"text": "...", "note": "<note name it came from>"}]}]}"""


def _frontmatter_type(body: str) -> str | None:
    m = re.search(r"^\s*type:\s*(\w+)", body, re.MULTILINE)
    return m.group(1) if m else None


def read_notes() -> dict[str, dict]:
    """{note name: {"title", "body", "type"}} for the notes that are about the person."""
    notes = {}
    for f in sorted(MEMORIES_DIR.glob("*.md")):
        if f.name in ("MEMORY.md", "README.md"):
            continue
        body = f.read_text()
        kind = _frontmatter_type(body)
        if kind in SKIPPED_TYPES:
            continue
        title = next((ln.split(":", 1)[1].strip() for ln in body.splitlines() if ln.startswith("description:")), f.stem)
        notes[f.stem] = {"title": title, "body": body, "type": kind}
    return notes


def fingerprint(notes: dict[str, dict]) -> str:
    h = hashlib.sha256()
    for name in sorted(notes):
        h.update(name.encode() + b"\0" + notes[name]["body"].encode() + b"\0")
    return h.hexdigest()[:16]


class MemoryBook:
    def __init__(self, data_dir: Path):
        self.dir = data_dir / "book"
        self._lock = threading.Lock()
        self._writing: str | None = None

    # ------------------------------------------------------------ reading

    def current(self) -> tuple[dict | None, dict, dict]:
        """(book or None, notes, status). Starts a rewrite in the background when the notes changed."""
        notes = read_notes()
        key = fingerprint(notes)
        path = self.dir / f"{key}.json"
        status = {"writing": False, "paused": False, "stale": False}
        if path.exists():
            return json.loads(path.read_text()), notes, status
        latest = self._latest()
        if self.spent_this_month() >= MONTHLY_CAP_USD:
            status["paused"] = True
        else:
            self._start_writing(key, notes)
            status["writing"] = True
        status["stale"] = latest is not None
        return latest, notes, status

    def _latest(self) -> dict | None:
        books = sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return json.loads(books[0].read_text()) if books else None

    def spent_this_month(self) -> float:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        total = 0.0
        costs = self.dir / "costs.jsonl"
        if costs.exists():
            for line in costs.read_text().splitlines():
                e = json.loads(line)
                if e.get("at", "").startswith(month):
                    total += e.get("cost_usd") or 0.0
        return total

    # ------------------------------------------------------------ writing

    def _start_writing(self, key: str, notes: dict) -> None:
        with self._lock:
            if self._writing == key:
                return
            self._writing = key

        def work() -> None:
            try:
                self.write(key, notes)
            except Exception:
                log.exception("could not write the memory book")
            finally:
                with self._lock:
                    self._writing = None

        threading.Thread(target=work, daemon=True).start()

    def write(self, key: str, notes: dict) -> dict:
        from studio_town.claude_p import claude_p_completion

        titles = ", ".join(t for t, _ in CHAPTERS)
        prompt = (f"Chapter titles to use (in this order): {titles}.\n\nThe notes:\n\n"
                  + "\n\n".join(f"=== note: {name} ===\n{n['body']}" for name, n in notes.items()))
        result = claude_p_completion(prompt, system=SYSTEM, model=WRITE_MODEL)
        raw = result.text.strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        parsed = json.loads(raw)
        book = _shape(parsed, notes)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{key}.json").write_text(json.dumps(book, indent=2))
        (self.dir / f"{key}.raw.txt").write_text(result.text)
        with (self.dir / "costs.jsonl").open("a") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "key": key,
                                "cost_usd": result.cost_usd, "model": WRITE_MODEL}) + "\n")
        log.info("memory book rewritten for %s (cost $%.4f)", key, result.cost_usd or 0)
        return book

    # ------------------------------------------------------------ the person's own fixes

    def record(self, kind: str, text: str, detail: str = "") -> None:
        """Write a fix or addition into the memory note every chat reads, and log it raw."""
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if kind == "fix":
            line = (f"- {stamp}: \"{text}\" is not right." + (f" Actually: {detail}" if detail else ""))
        else:
            line = f"- {stamp}: ({detail or 'about me'}) {text}"
        path = MEMORIES_DIR / f"{TOLD_ME}.md"
        with self._lock:
            if not path.exists():
                path.write_text(
                    "---\nname: told-me-in-memory-book\ndescription: Corrections and additions the user made "
                    "directly in their Studio town memory book; these override other notes\nmetadata:\n  type: user\n"
                    "---\n\nWhat the user told me in their memory book (newest last). Trust these over older notes.\n\n")
                index = MEMORIES_DIR / "MEMORY.md"
                if index.exists() and TOLD_ME not in index.read_text():
                    with index.open("a") as f:
                        f.write(f"- [Told me in the memory book]({TOLD_ME}.md) — the user's own fixes and additions "
                                "from their memory book; they override other notes.\n")
            with path.open("a") as f:
                f.write(line + "\n")
            self.dir.mkdir(parents=True, exist_ok=True)
            with (self.dir / "edits.jsonl").open("a") as f:
                f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "kind": kind, "text": text,
                                    "detail": detail}) + "\n")


def _shape(parsed: dict, notes: dict) -> dict:
    """Keep only the known chapters, in order, with clean entries."""
    by_title = {c.get("title"): c for c in parsed.get("chapters", []) if isinstance(c, dict)}
    chapters = []
    for title, colour in CHAPTERS:
        entries = []
        for e in (by_title.get(title) or {}).get("entries", []):
            text = str(e.get("text", "")).strip()
            if text:
                note = e.get("note") if e.get("note") in notes else None
                entries.append({"text": text[:240], "note": note})
        chapters.append({"title": title, "colour": colour, "entries": entries,
                         "empty": EMPTY.get(title, "Nothing here yet.")})
    return {"chapters": chapters}
