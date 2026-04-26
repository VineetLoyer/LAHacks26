# AskSafe 🛡️

**Anonymous real-time Q&A for live sessions — powered by AI agents.**

Most people stay silent when they're confused. AskSafe lets participants anonymously signal confusion in real time, so hosts can see exactly where understanding breaks down and address it before anyone falls behind.

Works for university lectures, company townhalls, board meetings, training sessions — any one-to-many setting where people hold back.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PARTICIPANTS                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Join via  │  │ World ID │  │ Submit   │  │ Confusion│           │
│  │ 6-char   │→ │ Verify   │→ │ Questions│  │ Check-in │           │
│  │ code     │  │ (human)  │  │ or Voice │  │ (1-5)    │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Socket.IO (real-time)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                                 │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │ Sessions &  │  │ Check-ins & │  │ Questions & │                │
│  │ Auth API    │  │ Confusion   │  │ Clusters    │                │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                │
│         │                │                │                        │
│         ▼                ▼                ▼                        │
│  ┌─────────────────────────────────────────────┐                   │
│  │            MongoDB Atlas                     │                   │
│  │  sessions │ checkins │ questions │ clusters  │                   │
│  │  reports  │ feedback │ emails               │                   │
│  └─────────────────────────────────────────────┘                   │
│         │                │                │                        │
│         ▼                ▼                ▼                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │ Confusion   │  │ Question    │  │ Insight     │                │
│  │ Monitor     │  │ Clustering  │  │ Report      │                │
│  │ Agent       │  │ Agent       │  │ Agent       │                │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                │
│         └────────────────┼────────────────┘                        │
│                          │                                         │
└──────────────────────────┼─────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ ASI:One  │ │ OmegaClaw│ │ Resend   │
        │ Chat     │ │ Telegram │ │ Email    │
        └──────────┘ └──────────┘ └──────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        HOST DASHBOARD                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Live     │  │ Confusion│  │ Question │  │ Address  │           │
│  │ Confusion│  │ Timeline │  │ Clusters │  │ & Send   │           │
│  │ Gauge    │  │ Chart    │  │ (AI)     │  │ Response │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │
│  │ End      │  │ Session  │  │ Feedback │                         │
│  │ Session  │→ │ Report   │  │ Summary  │                         │
│  └──────────┘  └──────────┘  └──────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```


## How It Works

### For Participants
1. Join with a 6-character session code — no app install, no account
2. Verify you're human via World ID (privacy-preserving, no personal data stored)
3. Ask questions anonymously by typing or whispering (voice-to-text)
4. Rate confusion with a single tap when the host checks in
5. Upvote question clusters that matter to you
6. Get a post-session email summary

### For Hosts
1. Create a session and share the code
2. See a live confusion gauge, participant count, and question count
3. Trigger check-ins to pulse the room's understanding
4. AI clusters similar questions into topics with rich summaries
5. Address clusters with AI-drafted answers, links, custom responses, or flag for later
6. End session to generate a full analytics report with AI insights

---

## Agent Architecture (Fetch.ai Agentverse)

Three autonomous agents deployed on Agentverse, each with dual protocols:
- **Chat Protocol** — conversational queries via ASI:One
- **Sync Model** — structured queries via OmegaClaw (`send_sync_message`)

| Agent | Purpose | Trigger |
|-------|---------|---------|
| **Confusion Monitor** | Analyzes confusion data, detects spikes, correlates with questions | After each check-in batch |
| **Question Clustering** | Groups questions by topic, tracks on/off-topic, resolution status | When host generates clusters |
| **Insight Report** | Compiles full session analytics with multi-agent coordination | When host ends session |

### OmegaClaw Integration
OmegaClaw queries AskSafe agents as registered skills via Telegram:
```
User: "Check the confusion level for session Q3L6NF"
OmegaClaw → (asksafe-confusion "Q3L6NF") → Agentverse Agent → Response
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16, Tailwind, shadcn/ui | Responsive UI for host + participant |
| Backend | Python FastAPI, Socket.IO | Real-time API + WebSocket communication |
| Database | MongoDB Atlas | Sessions, check-ins, questions, clusters, reports, feedback |
| AI/LLM | Google Gemini | Clustering, explanations, reports, email summaries |
| Agents | Fetch.ai uAgents, Agentverse | 3 autonomous agents with dual-protocol support |
| Identity | World ID (IDKit v4) | Proof-of-human without revealing identity |
| Voice | ElevenLabs / Web Speech API | Whisper mode — speak questions quietly |
| Email | Resend | Post-session summaries to opted-in participants |
| Hosting | Railway (backend), Vercel (frontend) | Production deployment |

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- MongoDB Atlas cluster (or local MongoDB)
- API keys: Gemini, World ID, Resend (optional), ElevenLabs (optional)

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
python run.py         # runs on http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local  # set NEXT_PUBLIC_BACKEND_URL
npm run dev                  # runs on http://localhost:3000
```

### Agents (for Agentverse deployment)
The agent files in `agents/` are designed to run on Agentverse:
- `agentverse_confusion_monitor.py` — deploy as Confusion Monitor
- `agentverse_question_clustering.py` — deploy as Question Clustering
- `agentverse_insight_report.py` — deploy as Insight Report

Each agent needs `MONGODB_URI` and `GEMINI_API_KEY` set as environment variables on Agentverse.

### OmegaClaw Skill Setup
```bash
# Copy skill files into OmegaClaw container
docker cp agents/omegaclaw_skill/asksafe_agents.py omegaclaw:/PeTTa/repos/OmegaClaw-Core/src/asksafe_agents.py
docker cp agents/omegaclaw_skill/asksafe_skills.metta omegaclaw:/PeTTa/repos/OmegaClaw-Core/src/asksafe_skills.metta
# Then add skill entries to src/skills.metta (see agents/omegaclaw_skill/README.md)
docker restart omegaclaw
```

---

## Project Structure

```
├── frontend/              # Next.js participant + host UI
│   └── src/
│       ├── app/           # Pages: join, session, professor dashboard
│       ├── components/    # UI components: gauges, charts, broadcast feed
│       └── lib/           # API client, socket client, utilities
├── backend/               # FastAPI server
│   └── app/
│       ├── routes/        # API routes: sessions, checkins, questions, clusters, reports
│       ├── socket_events.py  # Real-time Socket.IO handlers
│       ├── agent_client.py   # Agentverse agent integration
│       └── config.py         # Environment configuration
├── agents/                # Fetch.ai agent code
│   ├── agentverse_confusion_monitor.py
│   ├── agentverse_question_clustering.py
│   ├── agentverse_insight_report.py
│   └── omegaclaw_skill/   # OmegaClaw MeTTa skills + Python bridge
└── README.md
```

---

## Agentverse Agent Links

| Agent | ASI:One Chat |
|-------|-------------|
| Confusion Monitor | [Chat →](https://asi1.ai/ai/agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt) |
| Question Clustering | [Chat →](https://asi1.ai/ai/agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd) |
| Insight Report | [Chat →](https://asi1.ai/ai/agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy) |

---

## License

Built at LA Hacks 2026 🚀
