"""
Insight Report Agent — Registered on Agentverse
Generates post-session analytics: confusion timeline, participation stats,
flagged items for next lecture, and student email summary.

Also implements the Chat Protocol for ASI:One integration,
allowing natural-language queries to generate session reports.
"""
import os
import re
import json
from uagents import Agent, Context, Model
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Protocol models (existing — used by the AskSafe backend)
# ---------------------------------------------------------------------------


class SlideStats(Model):
    slide: int
    confusion_pct: int
    responses: int


class ClusterSummary(Model):
    label: str
    question_count: int
    status: str
    upvotes: int


class ReportRequest(Model):
    session_id: str
    title: str
    total_participants: int
    timeline: List[SlideStats]
    clusters: List[ClusterSummary]


class ReportResponse(Model):
    session_id: str
    summary: str
    confusion_spikes: List[str]
    flagged_for_next: List[str]
    student_email_body: str


# ---------------------------------------------------------------------------
# Chat Protocol models (for ASI:One / Agentverse Chat Protocol)
# ---------------------------------------------------------------------------


class ChatMessage(Model):
    message: str


class ChatResponse(Model):
    message: str


# ---------------------------------------------------------------------------
# MongoDB helper
# ---------------------------------------------------------------------------

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
_mongo_client = None
_mongo_db = None


def _get_db():
    """Lazy-initialise the async MongoDB connection."""
    global _mongo_client, _mongo_db
    if _mongo_client is None:
        from motor.motor_asyncio import AsyncIOMotorClient
        _mongo_client = AsyncIOMotorClient(MONGODB_URI)
        _mongo_db = _mongo_client["asksafe"]
    return _mongo_db


# ---------------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------------

agent = Agent(
    name="insight_report",
    seed="asksafe-insight-report-seed-2026",
    port=8003,
    endpoint=["http://localhost:8003/submit"],
)

print(f"Insight Report Agent address: {agent.address}")


# ---------------------------------------------------------------------------
# Shared Gemini report generation
# ---------------------------------------------------------------------------


async def _generate_report_via_gemini(
    title: str,
    total_participants: int,
    timeline_str: str,
    clusters_str: str,
    questions_str: str,
) -> dict:
    """Call Gemini to generate a narrative report."""
    prompt = f"""You are an educational analytics AI. Generate a post-lecture report.

Lecture: "{title}"
Participants: {total_participants}
Confusion Timeline (per slide): {timeline_str}
Question Clusters: {clusters_str}
Sample Student Questions: {questions_str}

Return ONLY valid JSON (no markdown fences):
{{
  "summary": "2-3 sentence overview of the session including key stats and overall student engagement",
  "confusion_spikes": ["Slide X: description of spike and what students struggled with"],
  "flagged_for_next": ["Topics that need revisiting next class with specific recommendations"],
  "student_email_body": "Friendly email summary for students covering key topics discussed and questions answered"
}}"""

    try:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY", "")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Existing protocol handler (backend HTTP calls)
# ---------------------------------------------------------------------------


@agent.on_message(model=ReportRequest)
async def handle_report(ctx: Context, sender: str, msg: ReportRequest):
    ctx.logger.info(f"Generating report for session '{msg.title}'")

    timeline_str = json.dumps(
        [{"slide": t.slide, "confusion": t.confusion_pct} for t in msg.timeline]
    )
    clusters_str = json.dumps(
        [
            {"label": c.label, "questions": c.question_count, "status": c.status}
            for c in msg.clusters
        ]
    )

    data = await _generate_report_via_gemini(
        msg.title, msg.total_participants, timeline_str, clusters_str, "[]"
    )

    if not data:
        ctx.logger.error("Report generation failed — using fallback")
        data = {
            "summary": f"Session '{msg.title}' had {msg.total_participants} participants.",
            "confusion_spikes": [],
            "flagged_for_next": [],
            "student_email_body": f"Thank you for attending {msg.title}!",
        }

    result = ReportResponse(
        session_id=msg.session_id,
        summary=data.get("summary", ""),
        confusion_spikes=data.get("confusion_spikes", []),
        flagged_for_next=data.get("flagged_for_next", []),
        student_email_body=data.get("student_email_body", ""),
    )

    await ctx.send(sender, result)


# ---------------------------------------------------------------------------
# Chat Protocol handler (ASI:One / Agentverse)
# ---------------------------------------------------------------------------


def _extract_session_code(text: str) -> Optional[str]:
    """Extract a 6-character alphanumeric session code from text."""
    match = re.search(r"\b([A-Z0-9]{6})\b", text.upper())
    return match.group(1) if match else None


async def _generate_session_report(session_code: str) -> str:
    """Query MongoDB for full session data and generate a narrative report."""
    db = _get_db()

    # Look up the session
    session = await db.sessions.find_one({"code": session_code.upper()})
    if not session:
        return (
            f"I couldn't find a session with code {session_code}. "
            "Please double-check the 6-character session code and try again."
        )

    session_id = session["_id"]
    title = session.get("title", "Untitled Session")
    threshold = session.get("confusion_threshold", 60)
    status = session.get("status", "active")

    # ---- Gather all session data ----

    # Participants
    total_participants = max(
        session.get("live_participant_count", 0),
        session.get("demo_participant_count", 0),
    )

    # Check-ins
    checkins = await db.checkins.find(
        {"session_id": str(session_id)}
    ).to_list(length=5000)

    # Questions
    questions = await db.questions.find(
        {"session_id": str(session_id)}
    ).to_list(length=500)

    # Clusters
    clusters = await db.clusters.find(
        {"session_id": str(session_id)}
    ).to_list(length=100)

    # Check for existing report
    existing_report = await db.reports.find_one({"session_id": str(session_id)})

    total_checkins = len(checkins)
    total_questions = len(questions)
    total_clusters = len(clusters)
    clusters_addressed = sum(1 for c in clusters if c.get("status") == "addressed")

    # ---- Per-slide confusion timeline ----
    slide_data = {}  # type: dict
    for c in checkins:
        slide = c.get("slide")
        if slide is None:
            continue
        if slide not in slide_data:
            slide_data[slide] = {"total": 0, "confused": 0}
        slide_data[slide]["total"] += 1
        if c.get("confusion_rating", 0) >= 4:
            slide_data[slide]["confused"] += 1

    timeline = []
    spikes = []
    for slide_num in sorted(slide_data.keys()):
        sd = slide_data[slide_num]
        pct = round((sd["confused"] / sd["total"]) * 100) if sd["total"] > 0 else 0
        timeline.append({
            "slide": slide_num,
            "confusion_pct": pct,
            "responses": sd["total"],
        })
        if pct >= threshold:
            spikes.append({"slide": slide_num, "confusion_pct": pct})

    # ---- Overall confusion ----
    overall_confused = sum(1 for c in checkins if c.get("confusion_rating", 0) >= 4)
    overall_index = round((overall_confused / total_checkins) * 100) if total_checkins > 0 else 0

    # ---- Try Gemini for narrative report ----
    timeline_str = json.dumps(timeline)
    clusters_str = json.dumps([
        {
            "label": c.get("label", ""),
            "questions": len(c.get("question_ids", [])),
            "status": c.get("status", "pending"),
            "upvotes": c.get("upvotes", 0),
        }
        for c in clusters
    ])
    sample_q = [q.get("text", "") for q in questions[:10]]
    questions_str = json.dumps(sample_q)

    gemini_data = await _generate_report_via_gemini(
        title, total_participants, timeline_str, clusters_str, questions_str
    )

    # ---- Build the response ----
    lines = []
    lines.append(f"📄 **Session Report: \"{title}\" ({session_code})**\n")

    session_status = "🔴 Ended" if status == "ended" else "🟢 Active"
    lines.append(f"**Status:** {session_status}\n")

    # Key stats
    lines.append("📊 **Key Statistics:**")
    lines.append(f"  👥 Participants: {total_participants}")
    lines.append(f"  📝 Check-ins submitted: {total_checkins}")
    lines.append(f"  💬 Questions submitted: {total_questions}")
    lines.append(f"  🔍 Clusters generated: {total_clusters}")
    lines.append(f"  ✅ Clusters addressed: {clusters_addressed}/{total_clusters}")

    status_emoji = "🟢" if overall_index < 40 else ("🟡" if overall_index < 70 else "🔴")
    lines.append(f"  {status_emoji} Overall confusion: {overall_index}%")
    lines.append("")

    # AI-generated summary
    if gemini_data and gemini_data.get("summary"):
        lines.append("📝 **AI Summary:**")
        lines.append(f"  {gemini_data['summary']}")
        lines.append("")

    # Confusion timeline narrative
    if timeline:
        lines.append("📈 **Confusion Timeline:**")
        for t in timeline:
            bar = "█" * (t["confusion_pct"] // 10) + "░" * (10 - t["confusion_pct"] // 10)
            marker = " ⚠️ SPIKE" if t["confusion_pct"] >= threshold else ""
            lines.append(
                f"  Slide {t['slide']:>2}: {bar} {t['confusion_pct']:>3}%{marker}"
            )
        lines.append("")

    # Spike descriptions
    if spikes:
        lines.append(f"🚨 **Confusion Spikes ({len(spikes)}):**")
        if gemini_data and gemini_data.get("confusion_spikes"):
            for spike_desc in gemini_data["confusion_spikes"]:
                lines.append(f"  • {spike_desc}")
        else:
            for spike in spikes:
                # Find questions near this slide for context
                spike_questions = [
                    q.get("text", "")
                    for q in questions
                    if q.get("slide") == spike["slide"]
                ]
                context = ""
                if spike_questions:
                    context = f" — students asked: \"{spike_questions[0][:80]}\""
                lines.append(
                    f"  • Slide {spike['slide']}: confusion at {spike['confusion_pct']}%{context}"
                )
        lines.append("")

    # Top clusters
    if clusters:
        lines.append("🔍 **Top Question Clusters:**")
        sorted_clusters = sorted(
            clusters,
            key=lambda c: len(c.get("question_ids", [])),
            reverse=True,
        )
        for c in sorted_clusters[:5]:
            status_icon = "✅" if c.get("status") == "addressed" else "⏳"
            lines.append(
                f"  {status_icon} {c.get('label', 'Unnamed')} "
                f"({len(c.get('question_ids', []))} questions, "
                f"{c.get('upvotes', 0)} upvotes)"
            )
        lines.append("")

    # Flagged for next lecture
    if gemini_data and gemini_data.get("flagged_for_next"):
        lines.append("🏳️ **Flagged for Next Lecture:**")
        for item in gemini_data["flagged_for_next"]:
            lines.append(f"  • {item}")
        lines.append("")
    else:
        # Fallback: flag unaddressed clusters with high upvotes
        unaddressed = [
            c for c in clusters
            if c.get("status") != "addressed" and c.get("upvotes", 0) >= 3
        ]
        if unaddressed:
            lines.append("🏳️ **Flagged for Next Lecture:**")
            for c in unaddressed:
                lines.append(f"  • {c.get('label', 'Unnamed')} ({c.get('upvotes', 0)} upvotes)")
            lines.append("")

    # Resolution rate
    if total_clusters > 0:
        resolution_rate = round((clusters_addressed / total_clusters) * 100)
        lines.append(f"📊 **Resolution Rate:** {resolution_rate}% of clusters addressed")

    return "\n".join(lines)


@agent.on_message(model=ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Chat Protocol handler — responds to natural-language queries via ASI:One."""
    ctx.logger.info(f"Chat message from {sender}: {msg.message}")

    query = msg.message.strip()

    # Extract session code
    session_code = _extract_session_code(query)

    if session_code:
        response_text = await _generate_session_report(session_code)
    else:
        response_text = (
            "👋 Hi! I'm the **AskSafe Insight Report Agent**.\n\n"
            "I can generate comprehensive post-session analytics reports "
            "for lecture sessions, including confusion timelines, spike analysis, "
            "question cluster summaries, and recommendations.\n\n"
            "**Try asking:**\n"
            "• \"Generate a report for session ABC123\"\n"
            "• \"Summarize this lecture session ABC123\"\n"
            "• \"What should I review for next class? Session: ABC123\"\n\n"
            "Just include a 6-character session code and I'll compile "
            "the full analytics report."
        )

    await ctx.send(sender, ChatResponse(message=response_text))


if __name__ == "__main__":
    agent.run()
