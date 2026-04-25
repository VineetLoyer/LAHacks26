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
    """Extract a 6-char alphanumeric session code that contains at least one digit."""
    codes = re.findall(r"\b([A-Z0-9]{6})\b", text.upper())
    for c in codes:
        if any(ch.isdigit() for ch in c):
            return c
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
    lines.append(f"Question Clusters for \"{title}\" ({session_code})\n")
    lines.append(f"{len(questions)} total questions | Source: {source}\n")

    for i, c in enumerate(clusters, 1):
        label = c.get("label", "Unnamed")
        q_ids = c.get("question_ids", [])
        rep = c.get("representative_question", "")
        on_topic = c.get("on_topic", True)
        upvotes = c.get("upvotes", 0)
        status = c.get("status", "pending")

        topic = "On-topic" if on_topic else "Off-topic"
        status_mark = " [Addressed]" if status == "addressed" else ""

        lines.append(f"Cluster {i}: {label} ({topic}){status_mark}")
        lines.append(f"  {len(q_ids)} question(s) | {upvotes} upvotes")
        if rep:
            lines.append(f"  Representative: \"{rep}\"")
        lines.append("")

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


agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
