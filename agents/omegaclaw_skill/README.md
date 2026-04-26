# AskSafe OmegaClaw Skill — Agentverse Integration

This skill connects OmegaClaw to the three AskSafe agents on Agentverse, allowing
hosts to check lecture analytics directly from Telegram.

## How It Works

The AskSafe agents expose **two protocols**:
- **Chat Protocol** — for conversational chat on ASI:One
- **Synchronous AskSafeRequest/AskSafeResponse** — for OmegaClaw's `send_sync_message`

OmegaClaw calls the agents using `send_sync_message` with an `AskSafeRequest(session_code=...)` Model.
The agent processes the request and returns an `AskSafeResponse(response=...)` synchronously.

## Setup

### 1. Start OmegaClaw

```bash
docker pull singularitynet/omegaclaw:hackathon2604
curl -fsSL https://raw.githubusercontent.com/asi-alliance/OmegaClaw-Core/refs/tags/hackathon2604/scripts/omegaclaw | bash -s -- singularitynet/omegaclaw:hackathon2604
```

### 2. Install the AskSafe skill

Copy skill files into the OmegaClaw container:

```bash
docker cp asksafe_agents.py omegaclaw:/app/repos/OmegaClaw-Core/src/agentverse/asksafe_agents.py
docker cp asksafe_skills.metta omegaclaw:/app/repos/OmegaClaw-Core/src/asksafe_skills.metta
```

Add skill entries to `src/skills.metta` inside the container (in the `getSkills` function):

```metta
;AGENTVERSE AGENTS:
"- Check lecture confusion levels using AskSafe Confusion Monitor: (asksafe-confusion \"SESSION_CODE\")"
"- Cluster participant questions using AskSafe Question Clustering: (asksafe-clusters \"SESSION_CODE\")"
"- Generate lecture session report using AskSafe Insight Report: (asksafe-report \"SESSION_CODE\")"
```

Restart OmegaClaw:
```bash
docker restart omegaclaw
```

### 3. Test in Telegram

Message your bot naturally — no shell commands needed:

- "Check the confusion level for session Q3L6NF"
- "What are participants asking about in session Q3L6NF?"
- "Generate a report for session Q3L6NF"

OmegaClaw's LLM will recognize the intent, call the appropriate AskSafe skill,
and return the formatted analytics.

## Agent Addresses

| Agent | Address |
|-------|---------|
| Confusion Monitor | `agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt` |
| Question Clustering | `agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd` |
| Insight Report | `agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy` |

## Demo Session

Use session code `Q3L6NF` for testing — it has pre-seeded data:
- 40+ participants, 23+ questions, 5+ clusters
- Confusion spikes on slides 6-7
- Topic: "DSCI553 - Data Streams"
