# AskSafe — Test Scenarios

## Demo Session
- **Code:** `Q3L6NF`
- **Title:** DSCI553 - Data Streams
- **ID:** 69ed755ae5c18e4f0179d961
- **Host URL:** http://localhost:3000/professor/dashboard?id=69ed755ae5c18e4f0179d961&code=Q3L6NF
- **Participant URL:** http://localhost:3000/join → enter `Q3L6NF`

## Setup
- Tab 1: Host dashboard (regular browser)
- Tab 2: Participant session (incognito/different browser)

---

## TEST 1: Upvote / Unselect Upvote

### 1A: Participant upvotes a cluster
**Steps:**
1. Participant tab: look at "Popular Questions" section
2. Click the upvote arrow on "DGIM Algorithm Mechanics" cluster (currently ~14 upvotes)
3. Note the count increments by 1 on participant side immediately

**Expected:**
- Upvote count increases by 1 on participant side (instant, optimistic)
- Arrow/button turns green (primary color) to show it's upvoted
- Host dashboard: upvote count updates within 5 seconds (polling fallback)

**Result:** [ ]

### 1B: Participant removes upvote (toggle)
**Steps:**
1. Participant tab: click the same upvote button again (should be green)
2. Note the count decrements by 1

**Expected:**
- Upvote count decreases by 1 on participant side (instant)
- Button returns to default color (no longer green)
- Host dashboard: count updates within 5 seconds

**Result:** [ ]

### 1C: Upvote persists across page refresh
**Steps:**
1. Participant upvotes a cluster
2. Refresh the participant page (F5)
3. Check if the upvote state is preserved

**Expected:**
- After refresh, the upvoted cluster's button should still be green
- Count should match what was shown before refresh

**Result:** [ ]

### 1D: Multiple clusters upvoted
**Steps:**
1. Participant upvotes 3 different clusters
2. Check host dashboard

**Expected:**
- All 3 clusters show updated counts on host side within 5 seconds
- Participant sees all 3 buttons in green

**Result:** [ ]

---

## TEST 2: Question Clustering

### 2A: Submit new questions and generate clusters
**Steps:**
1. Participant tab: submit these questions one by one:
   - "What is the difference between DGIM and exponential histograms?"
   - "How do you handle late-arriving data in a stream?"
   - "When is the midterm exam?"
   - "Can we use Bloom filters for counting?"
2. Host tab: verify question count increases in real-time
3. Host tab: click "Generate Clusters"

**Expected:**
- Question count updates live on host dashboard after each submission
- After clustering: new clusters appear (may merge with existing or create new ones)
- Logistical question ("When is the midterm exam?") should be in its own off-topic cluster
- Technical questions should be grouped by topic
- Each cluster has a rich summary (not just a label)

**Result:** [ ]

### 2B: Clusters appear on participant side in real-time
**Steps:**
1. After host generates clusters in 2A
2. Check participant tab without refreshing

**Expected:**
- New clusters appear on participant side automatically (via clusters_updated Socket.IO event)
- Participant can see and upvote the new clusters

**Result:** [ ]

### 2C: Cluster summaries are descriptive
**Steps:**
1. Read the cluster summaries on host dashboard

**Expected:**
- Summaries are 1-2 sentences describing what students are confused about
- NOT just a short label like "Midterm Questions"
- Should mention specific sub-topics within the cluster

**Result:** [ ]

---

## TEST 3: Participant Exits Early

### 3A: Participant leaves and participant count updates
**Steps:**
1. Note the current participant count on host dashboard
2. Close the participant tab (or navigate away)
3. Check host dashboard participant count

**Expected:**
- Participant count decreases (for non-demo sessions)
- For demo sessions: count should NOT go below demo_participant_count (40)
- Host dashboard continues to function normally

**Result:** [ ]

### 3B: Participant rejoins after leaving
**Steps:**
1. After closing participant tab, open a new incognito tab
2. Go to http://localhost:3000/join → enter `Q3L6NF`
3. Check if participant can see existing clusters and broadcasts

**Expected:**
- Participant joins successfully (demo mode skips World ID)
- Existing clusters are loaded and visible
- Previously submitted questions are NOT visible (different browser session)
- Participant count updates on host dashboard

**Result:** [ ]

### 3C: Host triggers check-in after participant left
**Steps:**
1. Close participant tab
2. Host triggers a check-in
3. Open new participant tab and join

**Expected:**
- No error on host side when triggering check-in with no participants
- New participant does NOT see the old check-in prompt (it was sent before they joined)

**Result:** [ ]

### 3D: Session data persists after host refreshes
**Steps:**
1. Host tab: note all current data (confusion index, questions, clusters)
2. Refresh the host dashboard page (F5)

**Expected:**
- All data restores: confusion index, question count, participant count, clusters, timeline
- Demo mode badge still shows
- LIVE indicator still pulses

**Result:** [ ]

---

## TEST 4: Address Cluster — All 4 Options

### 4A: Answer Now (AI Draft)
**Steps:**
1. Host tab: click "Address" on a pending cluster
2. Select "💡 Answer Now"
3. Click "Generate AI Suggestion"
4. Wait for AI draft to appear
5. Edit the draft slightly (add a sentence)
6. Click "Send to Students"

**Expected:**
- AI draft appears in an editable textarea after a few seconds
- Draft is relevant to the cluster topic (not generic)
- After sending: cluster status changes to "Addressed" (green checkmark)
- Participant tab: broadcast card appears with the cluster label and explanation
- Broadcast shows in real-time without page refresh

**Result:** [ ]

### 4B: Send Link
**Steps:**
1. Host tab: click "Address" on another pending cluster
2. Select "🔗 Send Link"
3. Paste a URL: `https://www.youtube.com/watch?v=example`
4. Add a note: "This video explains DGIM buckets step by step"
5. Click "Send to Students"

**Expected:**
- Cluster status changes to "Addressed"
- Participant tab: broadcast card appears with the link and note
- The link text includes "📎 Resource:" prefix

**Result:** [ ]

### 4C: Mark for Later
**Steps:**
1. Host tab: click "Address" on another pending cluster
2. Select "📌 Mark for Later"
3. Click "Flag for Later"

**Expected:**
- Cluster status changes to "Flagged" (NOT "Addressed")
- NO broadcast sent to participants (this is internal only)
- NO AI explanation generated (Gemini should NOT be called)
- Cluster appears in the "Flagged for Next Session" section of the report later

**Result:** [ ]

### 4D: Type Response
**Steps:**
1. Host tab: click "Address" on the last pending cluster
2. Select "✏️ Type Response"
3. Type: "Great question! We'll cover this in more detail next week."
4. Click "Send to Students"

**Expected:**
- Cluster status changes to "Addressed"
- Participant tab: broadcast card appears with the typed response
- No AI explanation generated

**Result:** [ ]

### 4E: Verify addressed clusters are visually distinct
**Steps:**
1. After addressing multiple clusters, look at the cluster section

**Expected:**
- Addressed clusters have green checkmark and reduced opacity
- Flagged cluster has different styling (not green checkmark)
- Pending clusters still have "Address" and "Hide" buttons

**Result:** [ ]

---

## TEST 5: End Session Flow

### 5A: End session and generate report
**Steps:**
1. Host tab: click "End Session & Generate Report"
2. Wait for report to generate

**Expected:**
- Report modal appears with: stats, confusion spikes, AI summary, flagged topics
- "Session Ended" banner appears at top of dashboard
- Trigger Check-in and Generate Clusters buttons are disabled
- End Session button shows "Session Ended" (disabled)

**Result:** [ ]

### 5B: Participant sees session ended
**Steps:**
1. After host ends session, check participant tab

**Expected:**
- "Session ended" banner appears on participant side
- Feedback form appears with 5-star rating and comment field
- Question submission is still visible but session is ended

**Result:** [ ]

### 5C: Participant submits feedback
**Steps:**
1. Participant tab: select 4 stars
2. Type comment: "The DGIM section was confusing but the examples helped"
3. Click "Submit Feedback"

**Expected:**
- "Thanks for your feedback!" confirmation appears
- Stars and comment are submitted successfully

**Result:** [ ]

### 5D: Host sees feedback in report
**Steps:**
1. Host tab: open the report modal (or click to view report)
2. Scroll to "Student Feedback" section
3. Click "Refresh" button

**Expected:**
- Star rating appears (e.g., ★★★★☆ 4.0/5)
- "Based on 1 student" text
- If AI insights are available, summary bullets appear
- Student comment appears in quotes

**Result:** [ ]

---

## TEST 6: World ID Verification (Non-Demo Session)

### 6A: Create a non-demo session and test World ID
**Steps:**
1. Go to http://localhost:3000/professor → create session WITHOUT demo mode
2. Note the session code
3. Open incognito → join page → enter the code
4. Click "Verify with World ID"

**Expected:**
- Real World ID widget appears with QR code
- Scanning with World App completes verification
- After verification, participant enters the session

**Result:** [ ]

### 6B: Demo session skips World ID
**Steps:**
1. Open incognito → join page → enter `Q3L6NF`

**Expected:**
- "Demo Mode — verification skipped" message
- "Continue without verification" button
- Clicking it goes straight to the session

**Result:** [ ]


---

## TEST 7: Agentverse Integration (Prize: $2,500)

### 7A: Confusion Monitor Agent responds on check-in
**Steps:**
1. Host tab: trigger a check-in on slide 3
2. Participant tab: submit a confusion rating (e.g., 4 - Confused)
3. Check Railway logs for agent response

**Expected:**
- Railway logs show: `[Agentverse] Confusion Monitor Agent responded for session Q3L6NF`
- Check-in still works normally (agent call is non-blocking)
- Confusion gauge updates on host dashboard

**Result:** [ ]

### 7B: Question Clustering Agent responds on cluster generation
**Steps:**
1. Host tab: click "Generate Clusters"
2. Check Railway logs

**Expected:**
- Railway logs show: `[Agentverse] Question Clustering Agent responded for session Q3L6NF`
- Clusters still generate normally (agent call is non-blocking enrichment)

**Result:** [ ]

### 7C: Insight Report Agent responds on session end
**Steps:**
1. Host tab: click "End Session & Generate Report"
2. Check Railway logs

**Expected:**
- Railway logs show: `[Agentverse] Insight Report Agent responded for session Q3L6NF`
- Report still generates normally

**Result:** [ ]

### 7D: ASI:One direct chat with Confusion Monitor
**Steps:**
1. Go to: https://asi1.ai/ai/agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt
2. Send: "What's the confusion level for session Q3L6NF?"

**Expected:**
- Agent responds with confusion report: overall index, per-slide breakdown, spike detection
- Response mentions session title "DSCI553 - Data Streams" (or the seeded "Data Mining - Stream Processing")
- Response includes per-slide confusion percentages

**Result:** [ ]

### 7E: ASI:One direct chat with Question Clustering Agent
**Steps:**
1. Go to: https://asi1.ai/ai/agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd
2. Send: "What are students asking about in session Q3L6NF?"

**Expected:**
- Agent responds with cluster list: labels, question counts, on-topic/off-topic
- Shows existing clusters from the demo session

**Result:** [ ]

### 7F: ASI:One direct chat with Insight Report Agent
**Steps:**
1. Go to: https://asi1.ai/ai/agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy
2. Send: "Generate a report for session Q3L6NF"

**Expected:**
- Agent responds with full session report: stats, confusion timeline, cluster summaries, resolution rate

**Result:** [ ]

### 7G: Save ASI:One shared chat URL (required deliverable)
**Steps:**
1. After chatting with each agent on ASI:One, look for a "Share" button
2. Copy the shared chat URL

**Expected:**
- Shared URL is accessible and shows the conversation
- Save this URL for Devpost submission

**Result:** [ ]

---

## TEST 8: OmegaClaw Integration (Prize: $1,500)

### 8A: OmegaClaw queries session data via Telegram
**Steps:**
1. Make sure OmegaClaw Docker is running (`sudo docker start omegaclaw` in WSL)
2. Open Telegram → @AskSafe_bot
3. Send: "I'm a professor. Use your shell to run: python3 -c \"import urllib.request, json; data=json.loads(urllib.request.urlopen('https://lahacks26-production.up.railway.app/api/sessions/69ed755ae5c18e4f0179d961/stats').read()); print(json.dumps(data, indent=2))\""

**Expected:**
- OmegaClaw executes the shell command
- Returns confusion_index, total_questions, participant_count, cluster_count
- OmegaClaw may add its own analysis/commentary

**Result:** [ ]

### 8B: OmegaClaw fetches per-slide confusion breakdown
**Steps:**
1. Send to @AskSafe_bot: "Now also run: python3 -c \"import urllib.request, json; data=json.loads(urllib.request.urlopen('https://lahacks26-production.up.railway.app/api/checkins/stats/69ed755ae5c18e4f0179d961').read()); print(json.dumps(data, indent=2))\""

**Expected:**
- Returns per-slide confusion data
- Shows spikes on slides 6-7

**Result:** [ ]

### 8C: Screenshot/record the OmegaClaw conversation
**Steps:**
1. Screenshot the full Telegram conversation showing the query and response

**Expected:**
- Clear screenshots showing: user request → OmegaClaw reasoning → data returned
- Save for Devpost submission

**Result:** [ ]

---

## TEST 9: ElevenLabs Whisper Mode (Prize: Earbuds)

### 9A: Voice-to-text question submission
**Steps:**
1. Participant tab: click the microphone button next to the question input
2. Speak a question: "What is the difference between sliding windows and decaying windows?"
3. Wait for transcription

**Expected:**
- Recording indicator appears while speaking
- After stopping, transcribed text appears in the question input field
- Text can be edited before submitting
- If ElevenLabs key is not set, falls back to Web Speech API

**Result:** [ ]

### 9B: Whisper mode fallback
**Steps:**
1. Check if the microphone button is visible
2. If ElevenLabs key is not configured, verify Web Speech API fallback works

**Expected:**
- Microphone button visible (browser supports speech)
- Transcription works via either ElevenLabs Scribe or Web Speech API

**Result:** [ ]

---

## TEST 10: MongoDB Atlas (Prize: IoT Kit)

### 10A: Verify data persistence
**Steps:**
1. Submit a question from participant
2. Trigger a check-in and submit a rating
3. Upvote a cluster
4. Refresh both host and participant pages

**Expected:**
- All data persists after refresh: questions, check-ins, upvotes, clusters
- Host dashboard restores all stats from MongoDB on mount

**Result:** [ ]

### 10B: Verify demo seed data
**Steps:**
1. Check host dashboard for session Q3L6NF

**Expected:**
- 40+ participants (demo_participant_count)
- 23 pre-seeded questions
- 5 pre-seeded clusters
- Confusion timeline with data across slides 1-12
- Confusion spikes visible on slides 6-7

**Result:** [ ]

---

## TEST 11: Google Gemini (Prize: Swag)

### 11A: AI clustering uses Gemini
**Steps:**
1. Submit 3-4 new questions from participant
2. Host clicks "Generate Clusters"

**Expected:**
- Clusters are generated with meaningful labels and rich summaries
- On-topic vs off-topic classification is correct
- Logistical questions separated from technical ones

**Result:** [ ]

### 11B: AI explanation uses Gemini
**Steps:**
1. Host addresses a cluster with "Answer Now" → "Generate AI Suggestion"

**Expected:**
- AI draft is relevant to the cluster topic
- Explanation references lecture content (slide context)
- Tone is warm and encouraging

**Result:** [ ]

### 11C: AI report summary uses Gemini
**Steps:**
1. Host ends session and generates report

**Expected:**
- AI summary is a coherent 2-3 paragraph overview
- Mentions key stats, confusion points, and recommendations
- Not generic — references actual session data

**Result:** [ ]

---

## TEST 12: Resend Email (Post-Session)

### 12A: Student opts in for email after session ends
**Steps:**
1. After host ends session, participant sees feedback form
2. Below the feedback, enter email and click "Send me summary"

**Expected:**
- "You'll receive a summary at your email shortly" confirmation
- Railway logs show: `[Email] Sent summary via Resend to 1 student(s)` (if RESEND_API_KEY is set on Railway)
- OR `[Email] No RESEND_API_KEY` if not configured on Railway
- Actual email arrives if Resend is configured

**Result:** [ ]

---

## Summary Checklist

| Test | Count | Status |
|---|---|---|
| 1. Upvote toggle | 4 | [ ] |
| 2. Clustering | 3 | [ ] |
| 3. Early exit | 4 | [ ] |
| 4. Address cluster | 5 | [ ] |
| 5. End session | 4 | [ ] |
| 6. World ID | 2 | [ ] |
| 7. Agentverse | 7 | [ ] |
| 8. OmegaClaw | 3 | [ ] |
| 9. ElevenLabs | 2 | [ ] |
| 10. MongoDB | 2 | [ ] |
| 11. Gemini | 3 | [ ] |
| 12. Resend Email | 1 | [ ] |
| **TOTAL** | **40** | |
