"""
AskSafe Confusion Monitor — Agentverse Hosted Version
Analyzes real-time confusion data from live lecture sessions.
Provide a 6-character session code to get confusion analytics.
"""
import os
import re
from datetime import datetime
from uuid import uuid4

from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)


def create_text_chat(text: str, end_session: bool = False) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(timestamp=datetime.utcnow(), msg_id=uuid4(), content=content)


# ---------------------------------------------------------------------------
# MongoDB connection using pymongo (synchronous — motor not available on Agentverse)
# ---------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
_mongo_client = None
_mongo_db = None


def _get_db():
    global _mongo_client, _mongo_db
    if _mongo_client is None:
        from pymongo import MongoClient
        _mongo_client = MongoClient(MONGODB_URI)
        _mongo_db = _mongo_client["asksafe"]
    return _mongo_db


def _extract_session_code(text):
    """Extract a 6-char alphanumeric session code from text.
    
    Tries multiple strategies:
    1. Look for any 6-char uppercase alphanumeric pattern
    2. If multiple found, prefer ones with mixed letters+digits
    3. If none found, check if user is asking about recent sessions
    """
    # Strategy 1: Find all 6-char alphanumeric patterns
    codes = re.findall(r"\b([A-Z0-9]{6})\b", text.upper())
    if codes:
        # Prefer codes with mixed letters and digits (more likely to be session codes)
        mixed = [c for c in codes if any(ch.isdigit() for ch in c) and any(ch.isalpha() for ch in c)]
        if mixed:
            return mixed[0]
        # Fall back to any 6-char code (even all-letters like KKJCIO)
        return codes[0]
    
    # Strategy 2: Look for codes mentioned with context like "session XXXXXX" or "code: XXXXXX"
    pattern = re.search(r"(?:session|code|room)[:\s]+([A-Z0-9]{4,8})", text.upper())
    if pattern:
        return pattern.group(1)
    
    return None


def _list_recent_sessions():
    """List recent active sessions so the user can pick one."""
    db = _get_db()
    sessions = list(db.sessions.find(
        {"status": {"$ne": "ended"}},
    ).sort("created_at", -1).limit(5))
    
    if not sessions:
        return "No active sessions found."
    
    lines = ["Here are the recent sessions:"]
    for s in sessions:
        lines.append(f"  - {s.get('code', '?')} — \"{s.get('title', 'Untitled')}\" ({s.get('status', 'unknown')})")
    lines.append("\nPlease include the session code in your message.")
    return "\n".join(lines)


def _compute_confusion_analytics(session_code):
    db = _get_db()

    session = db.sessions.find_one({"code": session_code.upper()})
    if not session:
        return (
            f"I couldn't find a session with code {session_code}. "
            "Please double-check the 6-character session code and try again."
        )

    session_id = session["_id"]
    title = session.get("title", "Untitled Session")
    threshold = session.get("confusion_threshold", 60)

    checkins = list(db.checkins.find({"session_id": session_id}))

    if not checkins:
        return (
            f"Session **{title}** ({session_code}) has no check-in data yet. "
            "No confusion ratings have been submitted."
        )

    total = len(checkins)
    confused_count = sum(1 for c in checkins if c.get("confusion_rating", 0) >= 4)
    overall_index = round((confused_count / total) * 100) if total > 0 else 0
    avg_rating = round(sum(c.get("confusion_rating", 3) for c in checkins) / total, 2)

    # Per-slide breakdown
    slide_data = {}
    for c in checkins:
        slide = c.get("slide")
        if slide is None:
            continue
        if slide not in slide_data:
            slide_data[slide] = []
        slide_data[slide].append(c.get("confusion_rating", 3))

    slide_breakdown = []
    spikes = []
    for slide_num in sorted(slide_data.keys()):
        ratings = slide_data[slide_num]
        slide_total = len(ratings)
        slide_confused = sum(1 for r in ratings if r >= 4)
        slide_pct = round((slide_confused / slide_total) * 100) if slide_total > 0 else 0
        slide_breakdown.append({"slide": slide_num, "confusion_pct": slide_pct, "responses": slide_total})
        if slide_pct >= threshold:
            spikes.append({"slide": slide_num, "confusion_pct": slide_pct})

    # Spike summaries with question correlation
    spike_summaries = []
    for spike in spikes:
        slide_num = spike["slide"]
        q_count = db.questions.count_documents({
            "session_id": session_id,
            "slide": {"$gte": slide_num - 1, "$lte": slide_num + 1},
        })
        sample_questions = list(db.questions.find(
            {"session_id": session_id, "slide": slide_num}
        ).limit(3))
        sample_texts = [q.get("text", "") for q in sample_questions if q.get("text")]
        
        summary = f"Slide {slide_num}: {spike['confusion_pct']}% confused ({q_count} questions nearby)"
        if sample_texts:
            summary += "\n      Participants asked: " + " / ".join(['"' + t[:50] + '"' for t in sample_texts[:2]])
        spike_summaries.append(summary)

    # Build response — conversational and well-formatted for ASI:One chat
    lines = []
    
    # Header with status emoji
    status_emoji = "🟢" if overall_index < 40 else ("🟡" if overall_index < 70 else "🔴")
    lines.append(f"{status_emoji} Confusion Report: {title}")
    lines.append(f"Session: {session_code}")
    lines.append("")

    # Quick summary
    if overall_index < 30:
        mood = "Participants are following along well!"
    elif overall_index < 50:
        mood = "Some participants are struggling — a few areas need attention."
    elif overall_index < 70:
        mood = "Significant confusion detected — consider revisiting key topics."
    else:
        mood = "High confusion across the session — participants need help."
    
    lines.append(f"📊 Overall Confusion: {overall_index}% — {mood}")
    lines.append(f"📝 {total} check-ins | Average rating: {avg_rating}/5")
    lines.append("")

    # Spikes — the most important part
    if spikes:
        lines.append(f"🚨 {len(spikes)} Confusion Spike{'s' if len(spikes) > 1 else ''} Detected:")
        lines.append("")
        for spike in spike_summaries:
            lines.append(f"  ⚠️ {spike}")
        lines.append("")
    else:
        lines.append("✅ No confusion spikes — participants stayed within comfort zone.")
        lines.append("")

    # Compact slide breakdown — visual bar chart style
    if slide_breakdown:
        lines.append("📈 Per-Slide Breakdown:")
        for sb in slide_breakdown:
            pct = sb["confusion_pct"]
            bar_len = pct // 10  # 0-10 blocks
            bar = "█" * bar_len + "░" * (10 - bar_len)
            spike_mark = " 🔥" if pct >= threshold else ""
            lines.append(f"  Slide {sb['slide']:>2} │{bar}│ {pct:>3}% ({sb['responses']}){spike_mark}")
        lines.append("")

    # Actionable next step
    if spikes:
        lines.append(
            "💡 Next step: Ask the AskSafe Question Clustering Agent about this session "
            "to see exactly what topics participants are struggling with on the spike slides."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent + Chat Protocol
# ---------------------------------------------------------------------------
agent = Agent()
protocol = Protocol(spec=chat_protocol_spec)


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )

    text = msg.text()
    if not text:
        return

    session_code = _extract_session_code(text)

    if session_code:
        response = _compute_confusion_analytics(session_code)
    else:
        response = (
            "Hi! I'm the AskSafe Confusion Monitor Agent.\n\n"
            "I analyze real-time confusion data from lecture sessions. "
            "Just include a 6-character session code in your message.\n\n"
            "Try asking:\n"
            "- What's the confusion level for session ABC123?\n"
            "- Show me confusion spikes for ABC123\n"
            "- Is the class confused right now? Session: ABC123\n\n"
            "I'll give you the overall confusion index, per-slide breakdown, "
            "spike detection, and question correlation."
        )

    await ctx.send(sender, create_text_chat(response))


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
