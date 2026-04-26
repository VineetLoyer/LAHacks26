# AskSafe — Demo Script & Devpost Guide

---

## Demo Video Script (2:30 - 3:00 minutes)

### Setup Before Recording
- Two browser tabs: host + participant (incognito for participant)
- Telegram open with @AskSafe_bot OmegaClaw conversation
- ASI:One open with agent chat
- Pre-seeded demo session: code `RP1FVB`
- Fresh non-demo session for World ID demo

---

### [0:00 - 0:20] HOOK — The Problem (Emotional)

**Narration:**
"Think about the last time you sat in a room — a lecture, a company townhall, a board meeting — and had a question you didn't ask. Maybe you thought it was stupid. Maybe you didn't want to be the one to slow things down. Maybe you were just... afraid.

That silence has a cost. In classrooms, students fall behind. In townhalls, employees stay disengaged. In board meetings, critical concerns go unraised.

We built AskSafe to break that silence."

**Screen:** Landing page with tagline: "Anonymous Q&A for live sessions — powered by AI"

---

### [0:20 - 0:35] WHAT IS ASKSAFE

**Narration:**
"AskSafe is a real-time anonymous Q&A platform for any one-to-many setting. A university lecture with 300 students. A company all-hands with 500 employees. A community townhall where residents are afraid to speak up. A board meeting where junior members hold back.

The host creates a session. Participants join with a 6-character code. Every question is anonymous. Every voice is heard."

**Screen:** Show session creation → session code displayed → participant joining

---

### [0:35 - 0:55] TRUST WITHOUT IDENTITY — World ID

**Narration:**
"But anonymity without accountability is chaos. Bots can flood questions. One person can vote a hundred times. That's why every participant verifies they're a real human through World ID — a privacy-preserving proof of personhood. No name. No email. No tracking. Just proof that you're real.

This means when someone asks a hard question anonymously, the room knows it came from a real person — not a troll, not a bot. Trust without identity."

**Screen:**
1. Join page → enter session code
2. "Verify with World ID" → QR code appears
3. Quick scan with phone → verified
4. Then show demo mode bypass: "For presentations, hosts can enable demo mode"

---

### [0:55 - 1:20] THE PARTICIPANT EXPERIENCE

**Narration:**
"Once verified, participants can ask anything — by typing or by whispering into their phone using voice-to-text. In a quiet lecture hall, a student can hold their phone close and speak their question without anyone hearing.

When the host wants to check the room's pulse, they trigger a confusion check-in. One tap — that's all it takes. Five emojis, from 'I'm following' to 'I'm completely lost.' No hand-raising. No awkwardness. Just honest, anonymous feedback."

**Screen:**
1. Student types a question → submits
2. Microphone button → whisper mode recording
3. Check-in modal slides up → tap an emoji → confirmation
4. Show "Anonymous & Secure" badge

---

### [1:20 - 1:55] THE HOST DASHBOARD — Where Silence Becomes Signal

**Narration:**
"This is where it gets powerful. The host sees everything the room won't say out loud. A live confusion gauge that shifts from green to red. A timeline showing exactly when the room got lost. And AI that takes 23 scattered questions and groups them into 5 clear topics — so the host addresses confusion, not chaos."

**Screen:**
1. Professor dashboard — animated confusion gauge, LIVE indicator
2. Confusion timeline chart with spike on slides 6-7
3. Click "Generate Clusters" → 5 clusters appear with rich summaries
4. Show a cluster: "Several students are asking about DGIM bucket merging rules and error bounds"

**Narration:**
"The host picks how to respond. Answer now with an AI-drafted explanation they can edit. Share a link to a video or article. Flag it for next time. Or write their own response. The AI suggests — the human decides."

5. Click "Address" → show 4 response options
6. "Answer Now" → AI draft → edit → "Send to Students"
7. Switch to student tab → broadcast appears in real-time
8. Student upvotes a cluster

---

### [1:55 - 2:15] CLOSING THE LOOP — Feedback & Reports

**Narration:**
"When the session ends, participants rate the experience and leave comments. AI filters the noise and surfaces actionable insights. The host gets a full report — confusion spikes, resolution rate, topics to revisit, and honest student feedback. Not after the final exam. Not after the quarterly review. Right now, while it still matters."

**Screen:**
1. "End Session & Generate Report" → report modal
2. Show stats, confusion spikes, AI summary
3. Switch to student → feedback form → 5 stars + comment
4. Back to host → refresh feedback → stars and AI insights appear

---

### [2:15 - 2:35] THE INTELLIGENCE LAYER — Agents & OmegaClaw

**Narration:**
"Behind AskSafe are three AI agents built on Fetch.ai Agentverse — a confusion monitor, a question clustering engine, and an insight report generator. The same intelligence that powers the dashboard is available through ASI:One chat and OmegaClaw on Telegram. A professor can check on their class from their phone without opening a browser."

**Screen:**
1. Flash ASI:One chat with confusion monitor responding
2. Telegram → OmegaClaw: "confusion at 44%, spikes on slides 6-7, conceptual dependency chains detected"

---

### [2:35 - 2:50] CLOSING — Why This Matters

**Narration:**
"Every day, millions of people sit in rooms with questions they'll never ask. Students who fall behind because they were afraid to seem slow. Employees who see problems but stay quiet because the culture doesn't feel safe. Community members who show up to townhalls but leave without speaking.

AskSafe doesn't just collect questions. It transforms silence into signal, anxiety into engagement, and one-way presentations into real conversations.

Because every voice deserves to be heard safely."

**Screen:** Landing page. Pause on the tagline.

---

## Devpost Submission

### Project Name
**AskSafe — Anonymous Q&A for Engaged Learning**

### Tagline
Transform silence into signal — real-time anonymous Q&A with AI-powered confusion detection and proof-of-human verification for lectures, townhalls, and any one-to-many setting.

### Inspiration
We've all been there. Sitting in a 300-person lecture, confused about something the professor just said, but too anxious to raise a hand. Or in a company all-hands where the CEO asks "any questions?" and the room goes silent — not because there are no questions, but because no one wants to be the one to ask.

This silence has real consequences. Students fall behind and don't recover until exam results make it obvious. Employees disengage because their concerns feel invisible. Community members leave townhalls feeling unheard.

We built AskSafe because we believe the best questions are the ones people are afraid to ask — and technology should make it safe to ask them.

### What it does
AskSafe is a real-time anonymous Q&A platform for any one-to-many setting:

**For participants:**
- Join with a 6-character code, verify you're human via World ID (no personal data stored)
- Ask questions anonymously by typing or whispering (ElevenLabs voice-to-text)
- Rate your confusion with a single tap when the host checks in
- Upvote question clusters that matter to you
- Get a post-session email summary of what was covered

**For hosts:**
- See a live dashboard with animated confusion gauge, participant count, and question count
- View a per-slide confusion timeline that shows exactly when the room got lost
- AI clusters similar questions into topics with rich summaries — address confusion, not chaos
- Four response options: AI-drafted answer (editable), share a link/resource, flag for later, or custom response
- End-of-session report with AI insights, confusion spikes, resolution rate, and student feedback

**For organizations:**
- Works for university lectures, company townhalls, board meetings, community forums, training sessions
- Proof-of-human prevents bot spam and ensures 1-person-1-vote integrity
- Post-session analytics help improve future sessions
- AI agents available via ASI:One chat and OmegaClaw for on-the-go access

### How we built it
- **Frontend:** Next.js 16, Tailwind CSS, shadcn/ui, Recharts, Socket.IO client
- **Backend:** Python FastAPI, Socket.IO server, Motor (async MongoDB)
- **AI Agents:** 3 Fetch.ai agents on Agentverse with Chat Protocol — Confusion Monitor, Question Clustering, Insight Report. Same logic powers both ASI:One chat and the app backend.
- **AI:** Google Gemini for semantic clustering, explanations, reports, email summaries, and feedback filtering
- **Identity:** World ID IDKit v4 with server-side RP signing for proof-of-human verification
- **Data:** MongoDB Atlas with 7+ collections and aggregation pipelines
- **Voice:** ElevenLabs Scribe API with Web Speech API fallback
- **Email:** Resend for post-session student summaries
- **Real-time:** Socket.IO for live confusion updates, question counts, cluster broadcasts, upvotes
- **OmegaClaw:** Integrated via Telegram — professors can query session analytics from their phone

### Challenges we ran into
- World ID v4 requires RP signatures generated server-side — built a Next.js API route using the official signing utility
- IDKit WASM binary needed manual copying to the Next.js public directory
- OmegaClaw Docker required WSL which crashed on Windows — had to reinstall WSL from scratch
- Agentverse agents use the uAgents protocol (not REST) — integrated agent logic directly into the backend so the same intelligence serves both interfaces
- Making AI clustering useful required richer prompts — moved from "short labels" to detailed summaries that capture distinct sub-topics within each cluster

### Accomplishments we're proud of
- A complete, working product that solves a real problem people experience every day
- Three AI agents that serve dual purpose: ASI:One chat for discovery AND app backend for production
- World ID Orb verification working end-to-end with real QR code scanning
- OmegaClaw successfully discovering AskSafe, querying our API, and providing its own analysis of confusion patterns
- The "Address Cluster" flow where AI suggests but the human decides — technology augmenting, not replacing, the host
- Post-session feedback loop that gives hosts actionable insights immediately, not weeks later

### What we learned
- Multi-agent architectures where the same logic serves multiple interfaces (app + ASI:One + OmegaClaw)
- World ID v4 RP signing flow for proof-of-human in web applications
- Real-time Socket.IO patterns for live classroom-scale interaction
- How to make AI clustering genuinely useful (rich summaries with context, not just keyword labels)
- The importance of the "AI suggests, human decides" pattern — professors trust the tool more when they have final say

### What's next for AskSafe
- Deploy frontend to production with custom domain
- Native mobile app for hosts to monitor sessions on the go
- Integration with LMS platforms (Canvas, Blackboard, Google Classroom)
- Multi-language support for international classrooms and global townhalls
- Analytics dashboard for recurring sessions — track improvement over time
- Enterprise tier for companies running regular all-hands and training sessions

### Use Cases
- **University lectures** — Students ask questions they'd never raise their hand for
- **Company all-hands** — Employees surface concerns anonymously to leadership
- **Board meetings** — Junior members contribute without hierarchy pressure
- **Community townhalls** — Residents ask hard questions about local issues
- **Training sessions** — Trainees flag confusion without slowing the group
- **Conference Q&A** — Audience members submit questions during talks

### Built With
fetch-ai, agentverse, omegaclaw, google-gemini, world-id, mongodb-atlas, elevenlabs, next-js, fastapi, socket-io, tailwind-css, resend, python, typescript, recharts

### Tracks
- **Light The Way** (Education) — Transforms how students engage with lectures by making every voice heard safely
- **Flicker to Flow** (Productivity) — Turns the friction of one-way presentations into the flow of real-time, AI-powered dialogue

### Sponsor Prizes
- **Fetch.ai: Agentverse** — 3 agents with Chat Protocol on Agentverse, integrated into app backend, ASI:One demo
- **Fetch.ai: OmegaClaw Skill Forge** — OmegaClaw discovers AskSafe, queries API via Telegram, analyzes confusion patterns
- **World U** — IDKit v4 with RP signing, Orb verification, proof-of-human for anonymous Q&A trust
- **ElevenLabs** — Scribe API for voice-to-text whisper mode in quiet settings
- **MongoDB Atlas** — Full data layer with 7+ collections, aggregation pipelines, real-time updates
- **Gemini API** — Powers 5+ features: clustering, explanations, reports, email summaries, feedback filtering

### Links
- **GitHub:** https://github.com/VineetLoyer/LAHacks26
- **Backend API:** https://lahacks26-production.up.railway.app
- **Agentverse Agents:**
  - Confusion Monitor: https://agentverse.ai/agents/details/agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt/profile
  - Question Clustering: https://agentverse.ai/agents/details/agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd/profile
  - Insight Report: https://agentverse.ai/agents/details/agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy/profile

### Demo Sessions for Judges
- **Code: `RP1FVB`** — Demo mode (World ID bypassed, pre-seeded with 46 participants, 23 questions, 5 clusters, confusion spikes on slides 6-7)
- **Code: `NECU57`** — Alternate demo session
