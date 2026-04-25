# AskSafe OmegaClaw Skill — Agentverse Integration

This skill connects OmegaClaw to the three AskSafe agents on Agentverse, allowing
professors to check lecture analytics directly from Telegram.

## Setup

### 1. Start OmegaClaw

```bash
docker pull singularitynet/omegaclaw:hackathon2604
curl -fsSL https://raw.githubusercontent.com/asi-alliance/OmegaClaw-Core/refs/tags/hackathon2604/scripts/omegaclaw | bash -s -- singularitynet/omegaclaw:hackathon2604
```

- Accept disclaimer → type `accept`
- Choose `2` for Telegram
- Enter your Telegram bot token (from @BotFather)
- Choose LLM (recommend ASI1 or Claude)
- Enter API key

### 2. Install the AskSafe skill

Copy the skill files into the OmegaClaw container:

```bash
# Copy Python module
docker cp asksafe_agents.py omegaclaw:/app/repos/OmegaClaw-Core/src/agentverse/asksafe_agents.py

# Copy MeTTa skill definitions
docker cp asksafe_skills.metta omegaclaw:/app/repos/OmegaClaw-Core/src/asksafe_skills.metta
```

Then add the skill entries to `src/skills.metta` inside the container:

```bash
docker exec -it omegaclaw bash
# Edit src/skills.metta and add these lines to the getSkills function:
# ;AGENTVERSE AGENTS:
# "- Check lecture confusion levels using AskSafe Confusion Monitor: (asksafe-confusion \"SESSION_CODE\")"
# "- Cluster student questions using AskSafe Question Clustering: (asksafe-clusters \"SESSION_CODE\")"
# "- Generate lecture session report using AskSafe Insight Report: (asksafe-report \"SESSION_CODE\")"
```

Restart OmegaClaw:
```bash
docker restart omegaclaw
```

### 3. Test in Telegram

Message your bot:

- "Check the confusion level for lecture session NECU57"
- "What are students asking about in session NECU57?"
- "Generate a report for session NECU57"

OmegaClaw will use the AskSafe skills to call the Agentverse agents and return results.

## Agent Addresses

| Agent | Handle | Address |
|-------|--------|---------|
| Confusion Monitor | @asksafe-confmtr | `agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt` |
| Question Clustering | @asksafe-qclstr | `agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd` |
| Insight Report | @asksafe-report | `agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy` |

## Demo Session

Use session code `NECU57` for testing — it has pre-seeded data:
- 44 participants, 23 questions, 5 clusters
- Confusion spikes on slides 6-7
- Topic: "Data Mining - Stream Processing"
