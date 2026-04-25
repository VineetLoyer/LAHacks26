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
    """Extract a 6-char alphanumeric session code that contains at least one digit."""
    codes = re.findall(r"\b([A-Z0-9]{6})\b", text.upper())
    for c in codes:
        if any(ch.isdigit() for ch in c):
            return c
    return None


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
        topic_hint = ""
        if sample_texts:
            topic_hint = " about " + ", ".join(['"' + t[:60] + '"' for t in sample_texts[:2]])
        spike_summaries.append(
            f"Confusion spiked to {spike['confusion_pct']}% on slide {slide_num} "
            f"-- {q_count} question(s){topic_hint} submitted around that slide"
        )

    # Build response
    lines = []
    lines.append(f"Confusion Report for \"{title}\" ({session_code})\n")

    status_emoji = "GREEN" if overall_index < 40 else ("YELLOW" if overall_index < 70 else "RED")
    lines.append(f"[{status_emoji}] Overall Confusion Index: {overall_index}%")
    lines.append(f"Average rating: {avg_rating}/5 across {total} check-ins")
    lines.append(f"Spike threshold: {threshold}%\n")

    if spikes:
        lines.append(f"{len(spikes)} confusion spike(s) detected:")
        for summary in spike_summaries:
            lines.append(f"  - {summary}")
        lines.append("")
    else:
        lines.append("No confusion spikes detected.\n")

    if slide_breakdown:
        lines.append("Per-Slide Breakdown:")
        for sb in slide_breakdown:
            marker = " << SPIKE" if sb["confusion_pct"] >= threshold else ""
            lines.append(f"  Slide {sb['slide']:>2}: {sb['confusion_pct']:>3}% ({sb['responses']} responses){marker}")
        lines.append("")

    if spikes:
        lines.append(
            "Tip: Try querying the AskSafe Question Clustering Agent "
            "with this session code to see what specific topics students "
            "are struggling with on the spike slides."
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
