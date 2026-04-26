"""
AskSafe Question Clustering Agent — Agentverse Hosted Version
Clusters student questions from lecture sessions using AI.
Provide a 6-character session code to get question topic analysis.
"""
import os
import re
import json
from datetime import datetime
from uuid import uuid4
from typing import Optional, List

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


def _run_gemini_clustering(questions, title, slide_contexts=None):
    slide_block = ""
    if slide_contexts:
        lines = []
        for sc in slide_contexts:
            lines.append(f"  Slide {sc.get('slide_number', '?')}: {sc.get('text_content', '')[:200]}")
        slide_block = "\nLecture slide content:\n" + "\n".join(lines)

    q_list = [{"id": str(q["_id"]), "text": q.get("text", "")} for q in questions]
    prompt = f"""You are an educational AI. Given student questions from a lecture
titled "{title}", group them into semantic clusters.
{slide_block}

Questions:
{json.dumps(q_list, indent=2)}

Return ONLY valid JSON (no markdown) as an array:
[{{"label":"Short label","question_ids":["id1"],"representative_question":"Best question","on_topic":true}}]"""

    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY", "")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model="gemma-3-27b-it", contents=prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return []


def _cluster_session_questions(session_code):
    db = _get_db()
    session = db.sessions.find_one({"code": session_code.upper()})
    if not session:
        return f"I couldn't find a session with code {session_code}. Please check the code."

    session_id = session["_id"]
    title = session.get("title", "Untitled Session")

    questions = list(db.questions.find({"session_id": session_id}).limit(500))
    if not questions:
        return f"Session **{title}** ({session_code}) has no questions yet."

    # Check for existing clusters
    existing = list(db.clusters.find({"session_id": session_id}).limit(100))

    if existing:
        clusters = existing
        source = "existing database clusters"
    else:
        slide_contexts = session.get("slide_contexts", [])
        raw = _run_gemini_clustering(questions, title, slide_contexts)
        if raw:
            clusters = raw
            source = "AI-generated clusters"
        else:
            clusters = [{"label": "All Questions", "question_ids": [str(q["_id"]) for q in questions], "representative_question": questions[0].get("text", ""), "on_topic": True}]
            source = "fallback (single cluster)"

    lines = []
    lines.append(f"📋 Question Clusters: {title}")
    lines.append(f"Session: {session_code}")
    lines.append(f"📝 {len(questions)} total questions | Source: {source}")
    lines.append("")

    on_topic_clusters = [c for c in clusters if c.get("on_topic", True)]
    off_topic_clusters = [c for c in clusters if not c.get("on_topic", True)]

    if on_topic_clusters:
        lines.append("📚 On-Topic Clusters:")
        for i, c in enumerate(on_topic_clusters, 1):
            label = c.get("label", "Unnamed")
            q_ids = c.get("question_ids", [])
            rep = c.get("representative_question", "")
            upvotes = c.get("upvotes", 0)
            status = c.get("status", "pending")

            status_icon = "✅" if status == "addressed" else "📌" if status == "flagged" else "⏳"
            lines.append(f"  {status_icon} {label}")
            lines.append(f"     {len(q_ids)} questions · {upvotes} upvotes")
            if rep:
                lines.append(f'     Example: "{rep[:80]}"')
            lines.append("")

    if off_topic_clusters:
        lines.append("🔀 Off-Topic / Logistics:")
        for c in off_topic_clusters:
            label = c.get("label", "Unnamed")
            q_ids = c.get("question_ids", [])
            rep = c.get("representative_question", "")
            lines.append(f"  💬 {label} ({len(q_ids)} questions)")
            if rep:
                lines.append(f'     Example: "{rep[:80]}"')
            lines.append("")

    addressed = sum(1 for c in clusters if c.get("status") == "addressed")
    if clusters:
        lines.append(f"📊 Resolution: {addressed}/{len(clusters)} clusters addressed")

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
        response = _cluster_session_questions(session_code)
    else:
        response = (
            "Hi! I'm the AskSafe Question Clustering Agent.\n\n"
            "I analyze and cluster student questions from lecture sessions.\n\n"
            "Try asking:\n"
            "- Cluster the questions for session ABC123\n"
            "- What are students confused about in ABC123?\n\n"
            "Include a 6-character session code and I'll group questions into topics."
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
    name="AskSafe-Question-Clustering",
    version="0.1.0",
    default_rate_limit=RateLimit(window_size_minutes=60, max_requests=30),
)

@sync_proto.on_message(AskSafeRequest, replies={AskSafeResponse})
async def handle_sync_request(ctx: Context, sender: str, msg: AskSafeRequest):
    result = _cluster_session_questions(msg.session_code)
    await ctx.send(sender, AskSafeResponse(response=result))

agent.include(sync_proto, publish_manifest=True)
agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
