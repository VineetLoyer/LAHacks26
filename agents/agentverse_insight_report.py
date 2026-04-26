"""
AskSafe Insight Report Agent — Agentverse Hosted Version
Generates comprehensive post-session analytics reports.
Provide a 6-character session code to get full session analytics.
"""
import os
import re
import json
from datetime import datetime
from uuid import uuid4
from typing import Optional

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


# MongoDB
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
    """Extract a 6-char alphanumeric session code from text."""
    codes = re.findall(r"\b([A-Z0-9]{6})\b", text.upper())
    if codes:
        mixed = [c for c in codes if any(ch.isdigit() for ch in c) and any(ch.isalpha() for ch in c)]
        if mixed:
            return mixed[0]
        return codes[0]
    pattern = re.search(r"(?:session|code|room)[:\s]+([A-Z0-9]{4,8})", text.upper())
    if pattern:
        return pattern.group(1)
    return None


def _generate_session_report(session_code):
    db = _get_db()
    session = db.sessions.find_one({"code": session_code.upper()})
    if not session:
        return f"I couldn't find a session with code {session_code}. Please check the code."

    session_id = session["_id"]
    title = session.get("title", "Untitled Session")
    threshold = session.get("confusion_threshold", 60)
    status = session.get("status", "active")

    total_participants = max(session.get("live_participant_count", 0), session.get("demo_participant_count", 0))
    checkins = list(db.checkins.find({"session_id": session_id}).limit(5000))
    questions = list(db.questions.find({"session_id": session_id}).limit(500))
    clusters = list(db.clusters.find({"session_id": session_id}).limit(100))

    total_checkins = len(checkins)
    total_questions = len(questions)
    total_clusters = len(clusters)
    clusters_addressed = sum(1 for c in clusters if c.get("status") == "addressed")

    # Per-slide confusion
    slide_data = {}
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
    for s in sorted(slide_data.keys()):
        sd = slide_data[s]
        pct = round((sd["confused"] / sd["total"]) * 100) if sd["total"] > 0 else 0
        timeline.append({"slide": s, "pct": pct, "responses": sd["total"]})
        if pct >= threshold:
            spikes.append({"slide": s, "pct": pct})

    overall_confused = sum(1 for c in checkins if c.get("confusion_rating", 0) >= 4)
    overall_index = round((overall_confused / total_checkins) * 100) if total_checkins > 0 else 0

    # Build report — conversational, well-structured for ASI:One chat
    lines = []
    session_status = "🔴 Ended" if status == "ended" else "🟢 Active"
    status_emoji = "🟢" if overall_index < 40 else ("🟡" if overall_index < 70 else "🔴")
    
    lines.append(f"📊 Session Report: {title}")
    lines.append(f"Session: {session_code} | Status: {session_status}")
    lines.append(f"Compiled by AskSafe Report Agent (coordinating Confusion Monitor + Question Clustering agents)")
    lines.append("")

    # Key stats in a compact block
    lines.append("━━━ Key Statistics ━━━")
    lines.append(f"  👥 Participants: {total_participants}")
    lines.append(f"  📝 Check-ins: {total_checkins} | Questions: {total_questions}")
    lines.append(f"  📋 Clusters: {total_clusters} ({clusters_addressed} addressed)")
    lines.append(f"  {status_emoji} Overall Confusion: {overall_index}%")
    lines.append("")

    # Confusion timeline — visual bar chart
    lines.append("━━━ Confusion Timeline (via Confusion Monitor Agent) ━━━")
    if timeline:
        for t in timeline:
            pct = t["pct"]
            bar_len = pct // 10
            bar = "█" * bar_len + "░" * (10 - bar_len)
            spike_mark = " 🔥" if pct >= threshold else ""
            lines.append(f"  Slide {t['slide']:>2} │{bar}│ {pct:>3}%{spike_mark}")
        lines.append("")

    if spikes:
        lines.append(f"🚨 {len(spikes)} Spike{'s' if len(spikes) > 1 else ''} Detected:")
        for spike in spikes:
            spike_qs = [q.get("text", "") for q in questions if q.get("slide") == spike["slide"]]
            context = ""
            if spike_qs:
                context = f'\n      Participants asked: "{spike_qs[0][:70]}"'
            lines.append(f"  ⚠️ Slide {spike['slide']}: {spike['pct']}% confused{context}")
        lines.append("")
    else:
        lines.append("✅ No confusion spikes detected.")
        lines.append("")

    # Cluster analysis
    lines.append("━━━ Question Clusters (via Question Clustering Agent) ━━━")
    if clusters:
        sorted_c = sorted(clusters, key=lambda c: len(c.get("question_ids", [])), reverse=True)
        for c in sorted_c[:6]:
            status_icon = "✅" if c.get("status") == "addressed" else "📌" if c.get("status") == "flagged" else "⏳"
            label = c.get("label", "Unnamed")
            q_count = len(c.get("question_ids", []))
            upvotes = c.get("upvotes", 0)
            summary = c.get("summary", "")
            lines.append(f"  {status_icon} {label} ({q_count} questions, {upvotes} upvotes)")
            if summary:
                lines.append(f"     {summary[:100]}")
        lines.append("")
    else:
        lines.append("  No clusters generated yet.")
        lines.append("")

    # Recommendations
    lines.append("━━━ Recommendations ━━━")
    unaddressed = [c.get("label", "") for c in clusters if c.get("status") not in ("addressed",) and c.get("on_topic", True)]
    if unaddressed:
        lines.append("📌 Topics to revisit next session:")
        for topic in unaddressed:
            lines.append(f"  • {topic}")
        lines.append("")

    if total_clusters > 0:
        rate = round((clusters_addressed / total_clusters) * 100)
        lines.append(f"📊 Resolution Rate: {rate}%")
        if rate < 50:
            lines.append("💡 Consider dedicating more time to addressing participant questions during the session.")
        elif rate >= 80:
            lines.append("🎉 Great job! Most participant concerns were addressed during the session.")

    # Participant feedback
    feedback_docs = list(db.session_feedback.find({"session_id": session_id}).limit(100))
    if feedback_docs:
        lines.append("")
        lines.append("━━━ Participant Feedback ━━━")
        ratings = [f.get("rating", 0) for f in feedback_docs if f.get("rating")]
        if ratings:
            avg = round(sum(ratings) / len(ratings), 1)
            stars = "★" * round(avg) + "☆" * (5 - round(avg))
            lines.append(f"  {stars} {avg}/5 (from {len(ratings)} participant{'s' if len(ratings) > 1 else ''})")
        comments = [f.get("comment", "").strip() for f in feedback_docs if f.get("comment", "").strip()]
        if comments:
            lines.append("  Comments:")
            for c in comments[:5]:
                lines.append(f'    • "{c[:100]}"')

    return "\n".join(lines)


# Agent + Protocol
agent = Agent()
protocol = Protocol(spec=chat_protocol_spec)


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id))

    text = msg.text()
    if not text:
        return

    session_code = _extract_session_code(text)

    if session_code:
        response = _generate_session_report(session_code)
    else:
        # Try to list recent sessions to help the user
        db = _get_db()
        sessions = list(db.sessions.find().sort("_id", -1).limit(5))
        session_list = ""
        if sessions:
            session_list = "\n\nRecent sessions:\n" + "\n".join(
                f"  - {s.get('code', '?')} — \"{s.get('title', 'Untitled')}\""
                for s in sessions
            )
        response = (
            "Hi! I'm the AskSafe Insight Report Agent.\n\n"
            "I generate comprehensive post-session analytics reports "
            "by coordinating with the Confusion Monitor Agent and Question Clustering Agent.\n\n"
            "Try asking:\n"
            "- Generate a report for session ABC123\n"
            "- How did my DSCI553 lecture go? Session ABC123\n\n"
            "Include a 6-character session code and I'll compile the full analytics."
            + session_list
        )

    await ctx.send(sender, create_text_chat(response))


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


# ---------------------------------------------------------------------------
# Synchronous Model handler for OmegaClaw integration
# ---------------------------------------------------------------------------
from uagents import Model
from uagents.experimental.quota import QuotaProtocol, RateLimit

class AskSafeRequest(Model):
    session_code: str

class AskSafeResponse(Model):
    response: str

sync_proto = QuotaProtocol(
    storage_reference=agent.storage,
    name="AskSafe-Insight-Report",
    version="0.1.0",
    default_rate_limit=RateLimit(window_size_minutes=60, max_requests=30),
)

@sync_proto.on_message(AskSafeRequest, replies={AskSafeResponse})
async def handle_sync_request(ctx: Context, sender: str, msg: AskSafeRequest):
    result = _generate_session_report(msg.session_code)
    await ctx.send(sender, AskSafeResponse(response=result))

agent.include(sync_proto, publish_manifest=True)
agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
