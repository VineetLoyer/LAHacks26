# OmegaClaw-Core Integration Guide

Step-by-step instructions for configuring OmegaClaw-Core with the ASI1 LLM, Telegram channel, message-driven behavior, and adding new Agentverse skills.

Each section is self-contained and includes the exact files to touch, what to change, and how to verify it works.

---

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Adding ASI1 as the LLM Provider](#1-adding-asi1-as-the-llm-provider)
3. [Hooking Up Telegram as a Communication Channel](#2-hooking-up-telegram-as-a-communication-channel)
4. [Making the Agent Message-Driven (Stop Continuous LLM Calls)](#3-making-the-agent-message-driven)
5. [Adding a New Agentverse Skill](#4-adding-a-new-agentverse-skill)
6. [Running the Agent](#5-running-the-agent)

---

## Installation & Setup

These are the prerequisites that must be in place before any of the configuration sections below will work.

### 0.1 — Install PeTTa

OmegaClaw-Core runs on the **PeTTa** MeTTa runtime (which is itself built on **SWI-Prolog** + Janus for the Python bridge).

```bash
# SWI-Prolog (PeTTa's backend) — macOS
brew install swi-prolog

# Clone PeTTa to your home directory
git clone https://github.com/trueagi-io/hyperon-experimental.git ~/PeTTa
# (or whichever PeTTa distribution you're using; the rest of this guide
#  assumes the runtime lives at ~/PeTTa with run.sh and a repos/ folder)
```

Confirm PeTTa is working:

```bash
cd ~/PeTTa && sh run.sh --help
```

### 0.2 — Clone OmegaClaw-Core

```bash
git clone https://github.com/patham9/OmegaClaw-Core.git ~/OmegaClaw-Core
```

### 0.3 — Symlink the repo into PeTTa's library path

PeTTa resolves `(library OmegaClaw-Core ...)` imports from `~/PeTTa/repos/OmegaClaw-Core/`. Symlinking your local clone there means PeTTa runs your local code (instead of cloning a fresh copy from GitHub when `git-import!` fires):

```bash
ln -sfn ~/OmegaClaw-Core ~/PeTTa/repos/OmegaClaw-Core
```

Verify:

```bash
ls -la ~/PeTTa/repos/OmegaClaw-Core
# should show:  OmegaClaw-Core -> /Users/<you>/OmegaClaw-Core
```

> **Sandbox note:** if you get `Operation not permitted`, run this command in a regular shell outside any sandboxed environment.

### 0.4 — Install Python dependencies

PeTTa's Janus bridge invokes the **system** Python interpreter (Python 3.13 on this setup), not a venv. Install all dependencies into that interpreter:

```bash
pip3.13 install --break-system-packages \
    openai \
    requests \
    uagents \
    chromadb \
    sentence-transformers \
    websocket-client
```

What each is for:

| Package | Used by |
|---------|---------|
| `openai` | `lib_llm_ext.py` (ASI1, ASICloud, Anthropic — all OpenAI-compatible) |
| `requests` | `channels/telegram.py` (Bot API HTTP calls) |
| `uagents` | `src/agentverse.py` (Agentverse `send_sync_message`) |
| `chromadb` | semantic memory store |
| `sentence-transformers` | local embedding model `intfloat/e5-large-v2` |
| `websocket-client` | mattermost / IRC channel adapters |

Verify the install picked up the right interpreter:

```bash
python3.13 -c "import openai, uagents, chromadb, sentence_transformers, requests; print('ok')"
```

### 0.5 — Create `~/PeTTa/run.metta`

This is the entry point PeTTa loads. It must register the OmegaClaw-Core library path, import the master library, and call the agent:

```metta
!(import! &self (library lib_import))
!(git-import! "https://github.com/patham9/OmegaClaw-Core.git")
!(import! &self (library OmegaClaw-Core lib_omegaclaw))

!(omegaclaw)
```

The `git-import!` line is what registers the library name `OmegaClaw-Core` with PeTTa's library resolver. Because of the symlink in step 0.3, PeTTa won't actually re-clone from GitHub — it'll use your local code.

> **Switching projects:** PeTTa runs whatever `~/PeTTa/run.metta` points at. If you previously had a different project (e.g. `mettaclaw`) wired up, save its `run.metta` aside (`cp ~/PeTTa/run.metta ~/PeTTa/run.mettaclaw.metta`) before overwriting, so you can swap back later by copying it back over `run.metta`.

### 0.6 — Create `.env` in the OmegaClaw-Core repo

```bash
cd ~/OmegaClaw-Core
cat > .env <<'EOF'
ASI1_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxx
TG_BOT_TOKEN=8604479905:AAF8_xxxxxxxxxxxxxxxxxxxxxxxx
TG_CHAT_ID=6549349825
EOF
```

Replace the placeholder values with the keys/IDs you obtain in sections 1.4 and 2.1 below. The `_load_dotenv()` helper in `lib_llm_ext.py` reads this file automatically at import time, so you don't need to `export` anything manually.

### 0.7 — Sanity check

At this point you should be able to start PeTTa and have it cleanly load OmegaClaw-Core (it'll fail to actually do anything useful until you complete sections 1–3, but it shouldn't crash):

```bash
cd ~/PeTTa && sh run.sh run.metta provider=Anthropic commchannel=irc
```

Press Ctrl+C to exit. If you see `ModuleNotFoundError`, go back to step 0.4 and re-install the missing package against `python3.13`.

---

## 1. Adding ASI1 as the LLM Provider

ASI1 (`https://api.asi1.ai/v1`) is OpenAI-compatible, so we add it alongside the existing OpenAI/Anthropic/ASICloud providers.

### Step 1.1 — Register the ASI1 client in `lib_llm_ext.py`

Add the client initialization and a wrapper function in `lib_llm_ext.py`:

```python
ASI1_CLIENT = _init_openai_client(
    var_name="ASI1_API_KEY",
    base_url="https://api.asi1.ai/v1"
)

def useASI1(content):
    return _chat(
        client=ASI1_CLIENT,
        model="asi1",
        content=content
    )
```

The `_init_openai_client` helper reads the `ASI1_API_KEY` env var and returns an OpenAI client pointing at the ASI1 endpoint. The `useASI1` function uses the model name `"asi1"`.

### Step 1.2 — Auto-load `.env` so env vars don't need to be passed on the CLI

At the top of `lib_llm_ext.py`, add a small `.env` loader that runs at import time:

```python
def _load_dotenv():
    for path in [".env", os.path.join(os.path.dirname(__file__), ".env")]:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            break

_load_dotenv()
```

This means you only need `ASI1_API_KEY=...` in `.env` — no need to export it before running.

### Step 1.3 — Wire ASI1 into the loop dispatcher in `src/loop.metta`

Inside `(= (omegaclaw $k) ...)`, the LLM call cascade routes by `(provider)`. Add ASI1 to that chain:

```metta
($respi (if (== (provider) OpenAI)
            (useGPT (LLM) (maxOutputToken) (reasoningMode) $send)
            (if (== (provider) Anthropic)
                (py-call (lib_llm_ext.useClaude $send))
                (if (== (provider) ASI1)
                    (py-call (lib_llm_ext.useASI1 $send))
                    (py-call (lib_llm_ext.useMiniMax $send))))))
```

### Step 1.4 — Add `ASI1_API_KEY` to `.env`

```
ASI1_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 1.5 — Select the provider at runtime

Pass `provider=ASI1` on the run command (Section 5).

---

## 2. Hooking Up Telegram as a Communication Channel

OmegaClaw uses an adapter pattern for channels. Each channel implements three Python functions: `start_<channel>`, `getLastMessage`, and `send_message`. Then a small block in `src/channels.metta` routes calls based on `commchannel`.

### Step 2.1 — Get a Telegram bot token and chat id

1. In Telegram, open `@BotFather` and run `/newbot`. Save the bot token it gives you.
2. Find your bot (e.g. `@YourBot_bot`) and **send it any message first** (Telegram's API only returns updates from chats that have messaged the bot at least once).
3. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in a browser.
4. Find `"chat":{"id":<NUMBER>...}` in the JSON response. That number is your `TG_CHAT_ID`.

### Step 2.2 — Create the Telegram adapter at `channels/telegram.py`

The adapter must expose three functions used by MeTTa:

| Function | Purpose |
|----------|---------|
| `start_telegram(bot_token, chat_id, auth_secret=None)` | Spawns a background polling thread |
| `getLastMessage()` | Returns and clears the most recent buffered message |
| `send_message(text)` | Sends a message to the configured chat |

Internals:
- Long polling loop hits `https://api.telegram.org/bot<TOKEN>/getUpdates` every ~10 seconds with the next `update_id` offset.
- Incoming messages are filtered by `chat_id` and (optionally) by `OMEGACLAW_AUTH_SECRET` so only authenticated users can talk to the bot.
- Messages are formatted as `"<display_name>: <text>"` and buffered (multiple inbound messages are joined with `" | "`).
- `send_message` POSTs to `/sendMessage`; `\\n` literals are converted to real newlines so MeTTa-escaped strings render properly.

The full implementation is in `channels/telegram.py` in this repo — copy it as-is.

### Step 2.3 — Register the adapter in `lib_omegaclaw.metta`

Add this import alongside the existing channel imports:

```metta
!(import! &self (library OmegaClaw-Core ./channels/telegram.py))
```

### Step 2.4 — Wire telegram into `src/channels.metta`

Add `TG_BOT_TOKEN` and `TG_CHAT_ID` config slots at the top:

```metta
(= (TG_BOT_TOKEN) (empty))
(= (TG_CHAT_ID) (empty))
```

Extend `initChannels` so `commchannel=telegram` starts the Telegram poller:

```metta
(if (== (commchannel) telegram)
    (progn (configure TG_BOT_TOKEN "")
           (configure TG_CHAT_ID "")
           (py-call (telegram.start_telegram (TG_BOT_TOKEN) (TG_CHAT_ID))))
    ...)
```

Extend `receive` to read from Telegram:

```metta
(if (== (commchannel) telegram)
    (py-call (telegram.getLastMessage))
    ...)
```

Extend `send` to write to Telegram:

```metta
(if (== (commchannel) telegram)
    (let $temp (cut) (py-call (telegram.send_message $safemsg)))
    ...)
```

### Step 2.5 — Add Telegram credentials to `.env`

```
TG_BOT_TOKEN=8604479905:AAF8_xxxxxxxxxxxxxxxxxxxxxxxx
TG_CHAT_ID=6549349825
```

### Step 2.6 — Select the channel at runtime

Pass `commchannel=telegram` on the run command (Section 5).

---

## 3. Making the Agent Message-Driven

By default, the loop calls the LLM continuously even when no user message has arrived, burning tokens. The fix is to gate LLM calls on **either** a new inbound message **or** a long-interval timer wakeup.

### Step 3.1 — Update `initLoop` in `src/loop.metta`

Set the four loop-control values like this:

```metta
(= (initLoop)
   (progn (configure maxNewInputLoops 5)
          (configure maxWakeLoops 0)
          (configure sleepInterval 2)
          ...
          (configure wakeupInterval 600)
          (change-state! &prevmsg "")
          (change-state! &lastresults "")
          (change-state! &nextWakeAt (+ (get_time) (wakeupInterval)))
          (change-state! &loops 0)))
```

What each value does:

| Setting | Value | Behavior |
|---------|-------|----------|
| `maxNewInputLoops` | 5 | When a new user message arrives, the LLM is allowed up to 5 follow-up iterations to handle it (multi-step reasoning) |
| `maxWakeLoops` | 0 | Disable unprompted wakeup-driven LLM calls entirely |
| `sleepInterval` | 2 | Wait 2 seconds between channel polls |
| `wakeupInterval` | 600 | (Unused while `maxWakeLoops=0`, but keeps timer state sane) |
| Initial `&loops` | 0 | Don't fire the LLM on startup with no message |
| Initial `&nextWakeAt` | `(+ (get_time) (wakeupInterval))` | Initialize timer state so the loop body never reads an undefined variable |

### Step 3.2 — Why the `&nextWakeAt` init matters

The main loop reads `(get-state &nextWakeAt)` on each iteration. With `&loops` starting at 0, the first iteration immediately falls into the wake-check branch — and previously this crashed with `nb_getval/2: variable '&nextWakeAt' does not exist`. Initializing it in `initLoop` fixes that.

### Step 3.3 — How the loop now behaves

1. `initLoop` runs; `&loops = 0`.
2. Each iteration calls `receive`. If there's no new message and `&loops` is 0, the LLM is **not** called.
3. When a new message arrives, `&loops` is set to `(maxNewInputLoops)` (5) and the LLM kicks in.
4. Each iteration decrements `&loops`. When it hits 0, the LLM stops being called again until either a new message arrives or `(get_time)` exceeds `&nextWakeAt`.
5. With `maxWakeLoops=0`, even the wakeup branch only sets `&loops` to 1, giving a single status check rather than a runaway burst.

The result: cost is bounded per message, idle periods are silent.

---

## 4. Adding a New Agentverse Skill

Walkthrough using the Caltrain agent as the example. The pattern is the same for any Agentverse agent that exposes a synchronous request/response Model (like the Tavily Search or Technical Analysis agents).

### Step 4.0 — Important: synchronous vs. async agents

OmegaClaw calls Agentverse agents using `uagents.query.send_sync_message`, which spawns an ephemeral identity, sends one request, and waits for one reply.

This works only for agents that **respond synchronously** to a custom `Model`. Agents built on the **uAgents Chat Protocol** (`ChatMessage`/`ChatAcknowledgement`) reply asynchronously — `send_sync_message` only catches the immediate ack and misses the actual answer.

**If the target agent only speaks the chat protocol, you must add a synchronous Model handler to it** (see Step 4.5 below for an example).

### Step 4.1 — Add the Python function in `src/agentverse.py`

Define the request Model and the wrapper function:

```python
class CaltrainRequest(Model):
    question: str

CALTRAIN_AGENT_ADDRESS = os.environ.get(
    "CALTRAIN_AGENT_ADDRESS",
    "agent1qtuuyttz8ujuxceq0gllcerlksjneenrh2mfcm67st8qrm9lzzh3cd7f9h6",
)

def caltrain_schedule(question: str, timeout: int = 60) -> str:
    try:
        request = CaltrainRequest(question=question)
        return asyncio.run(
            _ask_agent(CALTRAIN_AGENT_ADDRESS, request, int(timeout))
        )
    except Exception as e:
        return f"error: {e}"
```

The shared `_ask_agent` helper is already in `agentverse.py`:

```python
async def _ask_agent(destination: str, request: Model, timeout: int = 60) -> str:
    envelope_or_status = await send_sync_message(
        destination=destination,
        message=request,
        timeout=timeout,
    )
    return str(envelope_or_status)
```

### Step 4.2 — Expose the skill to the LLM in `src/skills.metta`

Two edits:

**a) Add a one-line description inside `(getSkills)`** so the LLM knows the skill exists and how to call it:

```metta
"- Ask Caltrain schedule questions like next train times, routes, departures: (caltrain question_in_quotes)"
```

**b) Add the MeTTa binding** that maps `(caltrain ...)` to the Python function:

```metta
(= (caltrain $question)
   (py-call (agentverse.caltrain_schedule $question)))
```

That's all the OmegaClaw side needs — the LLM will start calling `(caltrain "...")` whenever the user asks something the skill description matches.

### Step 4.3 — Verify the skill independently

Before running the full agent, smoke-test the call from a standalone script. Create `test_caltrain.py`:

```python
import asyncio
from uagents import Model
from uagents.query import send_sync_message

CALTRAIN_AGENT_ADDRESS = "agent1qtuuyttz8ujuxceq0gllcerlksjneenrh2mfcm67st8qrm9lzzh3cd7f9h6"

class CaltrainRequest(Model):
    question: str

async def main():
    response = await send_sync_message(
        destination=CALTRAIN_AGENT_ADDRESS,
        message=CaltrainRequest(question="When is the next train from San Francisco to Sunnyvale?"),
        timeout=60,
    )
    print(response)

asyncio.run(main())
```

Run `python3.13 test_caltrain.py`. A successful response looks like:

```json
{"answer": "Trains from San Francisco to Sunnyvale: ..."}
```

If you only see `{"acknowledged_msg_id": "..."}`, the agent is using the chat protocol and you need Step 4.5.

### Step 4.4 — Use the skill

Once running, ask in Telegram: *"When's the next Caltrain from SF to Sunnyvale?"* The LLM will emit `(caltrain "next train from sf to sunnyvale")`, the response is captured, and a reply is sent back to you.

### Step 4.5 — (When you control the remote agent) Adding a synchronous handler

If the target Agentverse agent only speaks the chat protocol (like the original Caltrain agent did), add a synchronous handler **alongside** the existing chat protocol. Don't replace it — both can coexist on the same agent.

In the remote agent's source (e.g. `caltrain.py`):

```python
from uagents import Agent, Context, Model, Protocol
from uagents.experimental.quota import QuotaProtocol, RateLimit
from uagents_core.models import ErrorMessage

class CaltrainRequest(Model):
    question: str

class CaltrainResponse(Model):
    answer: str

sync_proto = QuotaProtocol(
    storage_reference=agent.storage,
    name="Caltrain-Schedule",
    version="0.1.0",
    default_rate_limit=RateLimit(window_size_minutes=60, max_requests=30),
)

@sync_proto.on_message(CaltrainRequest, replies={CaltrainResponse, ErrorMessage})
async def handle_sync_request(ctx: Context, sender: str, msg: CaltrainRequest):
    answer = compute_answer(msg.question)  # whatever your agent does
    await ctx.send(sender, CaltrainResponse(answer=answer))

agent.include(sync_proto, publish_manifest=True)
agent.include(chat_proto, publish_manifest=True)  # keep the existing chat protocol
```

Redeploy the agent. The uAgents framework routes inbound messages to the right handler by Model type, so chat users still get the conversational experience and OmegaClaw gets a one-shot synchronous answer.

---

## 5. Running the Agent

### 5.1 — `.env` should contain

```
ASI1_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxx
TG_BOT_TOKEN=8604479905:AAF8_xxxxxxxxxxxxxxxxxxxxxxxx
TG_CHAT_ID=6549349825
```

(Optional) Override Agentverse agent addresses via `CALTRAIN_AGENT_ADDRESS`, `TAVILY_SEARCH_AGENT_ADDRESS`, `TECHNICAL_ANALYSIS_AGENT_ADDRESS`.

### 5.2 — Make sure PeTTa loads OmegaClaw-Core

`~/PeTTa/run.metta` should import this repo. Either:

```metta
!(git-import! "https://github.com/patham9/OmegaClaw-Core.git")
!(import! &self (library OmegaClaw-Core lib_omegaclaw))
```

(`git-import!` registers the library path. The symlink in Prerequisites makes PeTTa pick up your local code instead of the GitHub clone.)

### 5.3 — Run

```bash
cd ~/PeTTa && sh run.sh run.metta \
  commchannel=telegram \
  provider=ASI1 \
  embeddingprovider=Local
```

`ASI1_API_KEY`, `TG_BOT_TOKEN`, and `TG_CHAT_ID` are loaded from `.env` automatically (Step 1.2).

### 5.4 — Verify

- Console prints `Initializing channels` then `[Telegram] Starting polling (chat_id filter: <id>)`.
- The loop logs `(---------iteration N)` every 2 seconds but does **not** call the LLM until you message the bot.
- Send a Telegram message. You should see the LLM call, the parsed s-expression response, the command results, and a reply back in Telegram.

---

## File Reference

| File | Purpose |
|------|---------|
| `lib_llm_ext.py` | LLM client init (ASI1, Anthropic, ASICloud), `.env` loader, embedding model |
| `channels/telegram.py` | Telegram Bot API adapter (poller + sender) |
| `src/channels.metta` | Channel routing (irc / telegram / mattermost) |
| `src/loop.metta` | Main loop, LLM dispatch, message-driven gating |
| `src/skills.metta` | Skill descriptions for the LLM + MeTTa bindings |
| `src/agentverse.py` | Bridge to Agentverse agents via `send_sync_message` |
| `lib_omegaclaw.metta` | Master import file |
| `.env` | API keys and channel credentials |
