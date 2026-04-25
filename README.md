# AskSafe 🛡️

**Transform silent anxiety into engaged, data-driven learning.**

AskSafe is a secure anonymous Q&A platform with real-time AI-powered confusion detection, multi-agent question clustering, and post-lecture insight reports. It helps students ask questions without fear and gives professors actionable data on where students get lost.

## Architecture

```
Student Device                    Professor Dashboard
     │                                    │
     ├─ World IDKit (proof-of-human)      │
     ├─ Voice input (Whisper Mode)        │
     │                                    │
     └──── WebSocket (Socket.IO) ─────────┘
                     │
              FastAPI Backend
                     │
          ┌──────────┼──────────┐
          │          │          │
    Confusion   Question    Insight
    Monitor     Clustering  Report
    Agent       Agent       Agent
    (Agentverse)(Agentverse)(Agentverse)
                     │
              MongoDB Atlas
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TailwindCSS, shadcn/ui |
| Backend | Python FastAPI, Socket.IO |
| Database | MongoDB Atlas |
| AI/LLM | Google Gemini 2.0 Flash |
| Agents | Fetch.ai uAgents, Agentverse |
| Auth | World IDKit (proof-of-human) |
| On-Device AI | Zetic Melange |

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
python run.py
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Agents
```bash
cd agents
pip install -r requirements.txt
cp .env.example .env
python confusion_monitor.py   # Terminal 1
python question_clustering.py # Terminal 2
python insight_report.py      # Terminal 3
```

## Features

- **Anonymous Q&A** — Students submit questions without identity exposure
- **Real-time Confusion Detection** — Live confusion index with spike alerts
- **AI Question Clustering** — Gemini groups similar questions into topics
- **Address Clusters** — Professor gets AI explanations + action options
- **Confusion Timeline** — Per-slide confusion visualization
- **Session Reports** — Post-lecture analytics and student email summaries
- **World ID Verification** — Proof-of-human without revealing identity
- **Multi-Agent Architecture** — 3 specialized agents on Fetch.ai Agentverse

## Built With

`nextjs` `tailwindcss` `fastapi` `python` `socketio` `mongodb` `gemini` `fetchai` `uagents` `agentverse` `world-idkit` `zetic-melange` `typescript`

## Team

Built at LA Hacks 2026 🚀
