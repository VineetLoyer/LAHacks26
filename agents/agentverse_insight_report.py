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
    """Extract a 6-char alphanumeric session code that contains at least one digit."""
    codes = re.findall(r"\b([A-Z0-9]{6})\b", text.upper())
    for c in codes:
        if any(ch.isdigit() for ch in c):
            return c
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

    # Build report
    lines = []
    session_status = "Ended" if status == "ended" else "Active"
    lines.append(f"Session Report: \"{title}\" ({session_code})\n")
    lines.append(f"Status: {session_status}\n")

    lines.append("Key Statistics:")
    lines.append(f"  Participants: {total_participants}")
    lines.append(f"  Check-ins: {total_checkins}")
    lines.append(f"  Questions: {total_questions}")
    lines.append(f"  Clusters: {total_clusters} ({clusters_addressed} addressed)")
    lines.append(f"  Overall confusion: {overall_index}%\n")

    if timeline:
        lines.append("Confusion Timeline:")
        for t in timeline:
            marker = " << SPIKE" if t["pct"] >= threshold else ""
            lines.append(f"  Slide {t['slide']:>2}: {t['pct']:>3}% ({t['responses']} responses){marker}")
        lines.append("")

    if spikes:
        lines.append(f"Confusion Spikes ({len(spikes)}):")
        for spike in spikes:
            spike_qs = [q.get("text", "") for q in questions if q.get("slide") == spike["slide"]]
            context = ""
            if spike_qs:
                context = f" -- students asked: \"{spike_qs[0][:80]}\""
            lines.append(f"  Slide {spike['slide']}: {spike['pct']}% confused{context}")
        lines.append("")

    if clusters:
        lines.append("Top Question Clusters:")
        sorted_c = sorted(clusters, key=lambda c: len(c.get("question_ids", [])), reverse=True)
        for c in sorted_c[:5]:
            icon = "[Done]" if c.get("status") == "addressed" else "[Pending]"
            lines.append(f"  {icon} {c.get('label', 'Unnamed')} ({len(c.get('question_ids', []))} questions, {c.get('upvotes', 0)} upvotes)")
        lines.append("")

    unaddressed = [c.get("label", "") for c in clusters if c.get("status") != "addressed" and c.get("on_topic", True)]
    if unaddressed:
        lines.append("Flagged for Next Session:")
        for topic in unaddressed:
            lines.append(f"  - {topic}")
        lines.append("")

    if total_clusters > 0:
        rate = round((clusters_addressed / total_clusters) * 100)
        lines.append(f"Resolution Rate: {rate}%")

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
        response = (
            "Hi! I'm the AskSafe Insight Report Agent.\n\n"
            "I generate comprehensive post-session analytics reports.\n\n"
            "Try asking:\n"
            "- Generate a report for session ABC123\n"
            "- Summarize this lecture session ABC123\n\n"
            "Include a 6-character session code and I'll compile the full analytics."
        )

    await ctx.send(sender, create_text_chat(response))


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
