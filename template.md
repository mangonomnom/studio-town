---
title: "Studio town"
description: "Your apps as a hand-drawn floating island town, with a little avatar of you that answers in speech bubbles and keeps a memory book"
thumbnail: "template.svg"
version: v1
format: v2
---

# Studio town

This file is the manifest for the **Studio town** template (slug:
`studio-town`). It is the one document a future agent reads to understand,
present, and adapt this template. If you are an agent in a workspace that was
created from this template, this file is your script: read all of it, then
follow "How to adapt it" below.

## What it is

Your apps as a hand-drawn floating island town, with a little avatar of you that answers in speech bubbles and keeps a memory book

Studio town turns a workspace into a place you can look at. Every app the user has built
stands on a hand-drawn floating island as its own little building, painted in a soft,
pastel watercolour style. Apps nobody has opened for five days grow flowering vines
(they never crumble or decay), and an empty plot with a shovel invites the user to build
something new. Tapping a building opens that app on the right and the chat that best
matches it on the left. A small pink blob avatar -- "little me" -- can be dragged around
the island and answers questions in hand-drawn speech bubbles, written in the user's own
voice. A memory book page turns the agent's memory notes into friendly entries the user
can read and correct, and the corrections flow back into what the agent remembers. A card
at the top shows the date, the time and the local weather, and after local sunset the sky
turns into a painted watercolour night.

## How it works

The snapshot includes these paths (each is a repo-root-relative path copied
from the original agent onto a clean default-workspace-template base):

- `system/apps/studio_town`
- `system/supervisord.conf.d/studio-town.conf`

- `system/apps/studio_town` -- the app itself: a Python (Flask) package with its
  `app.toml` manifest and icon. Its main pieces:
  - `places.py` / `town.py` / `chats.py` read the workspace's app registry and desktop
    (through the stock `system/scripts/layout.py list`) to work out which apps exist, when
    each was last used, and which chat best matches each app. Usage is recorded under
    `data/.apps/studio-town/` from the day the app is installed.
  - `island.py` / `drawing.py` / `render.py` draw the island as SVG and paint it to JPEG
    with headless Chromium -- Playwright driving the stock Fortress browser at
    `/opt/fortress/tilion-fortress/tilion` -- caching the renders under
    `data/.apps/studio-town/renders/`.
  - `littleme.py` runs little me: a warm, streamed `claude -p` session (Haiku) primed with
    the user's memory notes and recent activity, answering in the user's own voice.
  - `memorybook.py` / `book.py` rewrite the agent's memory notes (`data/memories/*.md`)
    into friendly memory-book entries via `claude -p` (Haiku, capped at $1 a month), and
    write the user's fixes and additions back into a memory note
    (`told-me-in-memory-book.md`, indexed in `MEMORY.md`) that every chat reads.
  - `sky.py` fetches weather from Open-Meteo and the place name from Nominatim (both free,
    keyless, public HTTP) and works out local sunset for the night sky.
  - `me.py` is the avatar maker (colour, accessory, name); `claude_p.py` is the keyless
    `claude -p` helper.
- `system/supervisord.conf.d/studio-town.conf` -- the supervisord program `studio-town`.
  It registers the app's URL with `system/scripts/forward_port.py --manifest
  system/apps/studio_town/app.toml --url http://localhost:8086` (so the app shows up as a
  window in the workspace) and then starts the `studio-town` console script, which
  listens on port 8086 (overridable with `STUDIO_TOWN_PORT`). The app keeps running with
  no window open (`stop_when_no_windows = false`) because it repaints the town on a timer,
  matches chats to apps, and runs little me's background work.

All state lives under `data/.apps/studio-town/` (overridable with `STUDIO_TOWN_DATA_DIR`);
none of it ships with the template.

## Recipe

This template is version `v1`. It is not a fork of the
workspace it came from -- it is DERIVED from it by a recipe: include these
paths, leave these out, apply these published-version rules. An update re-runs
the recipe against the current workspace and publishes the result as the next
version, so anything excluded stays excluded even though it still exists in the
source workspace.

The recipe is machine-read, so it lives in the sibling
[`template.toml`](template.toml) -- its `[recipe]` table -- along with
the structured requirements and the environment this template needs
installed. That file is authoritative for all of it; this one holds the prose.

## Requirements

Everything the adopting agent must deal with before this template is really
theirs. Two kinds of entry, handled at different times:

- **Activation** -- what must be SET UP before anything runs, in the
  machine-readable `requires_` forms below. The adopting agent acts on these
  ITSELF, first, before asking anything.
- **Adaptation** -- what must be DECIDED or REWIRED, in prose. Worked through
  interactively with the user, after activation.


**Activation**

- requires_llm: calls Claude through the keyless `claude -p` path (the copied
  `claude_p.py` helper and little me's streamed session, both on Haiku), pointing
  `claude -p` at the workspace's current account folder when no `CLAUDE_CONFIG_DIR` is
  set. An adopter on the keyed path can keep it as is -- `claude -p` works with either a
  subscription login or an API key -- so no switch is needed.

No latchkey permissions and no secrets are needed: there are no `requires_permission` or
`requires_secret` lines. The weather and place-name services (Open-Meteo, Nominatim) are
free, keyless, public HTTP.

**Adaptation**

- **Weather needs a location.** The town reads it from a foodie-map app's saved location
  (`data/.apps/foodie-map/location.json`) if one exists; otherwise no weather is shown.
  To set one directly, write `{"lat": <latitude>, "lng": <longitude>}` to
  `data/.apps/studio-town/sky/location.json` (this file wins over the foodie map's).
- **Building styles are matched by app name.** Four apps get bespoke buildings
  (foodie-map: a diner, expense-tracker: a bank, health-diary: a greenhouse, octopus: a
  newsstand); every other app gets a cottage. The adopter's apps will mostly be
  cottages until kits are added or the mapping in `town.py` is pointed at their own apps.
- **Usage history starts on install.** The town learns when each app was used from the
  day it is installed, so at first nothing is "growing wild" and the vines appear only
  after five days without use.
- **The avatar's name defaults to "friend".** Ask the user what little me should be
  called and set it in the avatar maker (it also titles the town and the memory book).

## Environment

What this template needs INSTALLED, beyond what the template already has.
Declared in `template.toml`'s `[environment]` table; an adopting agent
converges it at ITS OWN pinned apt snapshot timestamp, so package versions come
out consistent with the rest of that agent's environment rather than frozen to
whatever this publisher happened to have.

Nothing extra -- runs on the stock workspace environment. Playwright is already in the
stock root venv, the Fortress browser it drives is installed by the stock environment
setup, and the `claude` CLI is stock.

## How to adapt it

Instructions for the NEXT agent -- the one adapting this template into a
new agent. This is the `use-template` skill's template path; in short:

1. Read this entire file first, especially "Requirements" below. It holds two
   kinds of entry and they are handled at different times: the machine-readable
   `requires_` lines are ACTIVATION (set them up before anything runs), and
   the prose bullets are ADAPTATION (decide or rewire them afterwards).
2. Present the template to the user in plain, non-technical language: what
   it is, what it does, and what it needs from them (name the activation
   requirements).
3. Ask whether they want to use the same connectors (e.g. their own Slack).
   If YES: ACTIVATE FIRST -- initiate every `requires_permission` line NOW
   via a latchkey permission request (see the `latchkey` skill; the request
   opens the approval/login flow in the Imbue Studio app), wire up any
   `requires_secret` values, start the services, and get the app showing
   THE USER'S OWN DATA. Done for a data-backed app means the user can open it
   and see their own data -- NOT that a service starts or an endpoint returns
   200. Then tell them it is live and to take a look.
4. Only AFTER that (or immediately, if they chose different connectors -- the
   swap is then the first adaptation) ask: "How do you want to adapt it?"
5. Work through each requirement interactively, one at a time. Translate each
   into plain language, ask for a decision only when you genuinely need one,
   and resolve the obvious ones yourself.
6. When done, append a dated entry to "Adaptation history" below (never
   rewrite earlier entries) and commit.

## Publication history

This template's changelog: what each published version changed. The PUBLISHER
appends one entry per version (newest last); earlier entries are never rewritten.
This is distinct from "Adaptation history" below, which is the ADOPTERS' log.

### v1 (2026-10-20) -- first published: the floating-island town, little me, memory book, sky and weather

## Adaptation history

Each agent that adapts this template appends one dated entry below. Earlier
entries are never rewritten.
