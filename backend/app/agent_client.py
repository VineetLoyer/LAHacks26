"""
Agentverse Agent Integration — runs the same analysis logic used by the
three AskSafe agents deployed on Agentverse, directly from the backend.

The agents are deployed on Agentverse for ASI:One chat and OmegaClaw discovery.
The backend calls the same core analysis functions to power the app's features.
This means the SAME intelligence runs in both contexts:
  - On Agentverse: users chat with agents via ASI:One
  - In the app: backend calls the agent logic for clustering, spike detection, reports

Integration points:
1. Confusion Monitor — called after check-in batches for spike detection + correlation
2. Question Clustering — called when professor generates clusters
3. Insight Report — called when professor ends session

All functions use synchronous pymongo (same as the Agentverse-hosted agents)
and are called from async FastAPI routes via run_in_executor when needed.
"""
import os
import re
import json
from typing import Optional, List

from pymongo import MongoClient

# MongoDB connection (synchronous — same as the Agentverse agents use)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
_mongo_client = None
_mongo_db = None


def _get_db():
    global _mongo_client, _mongo_db
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGODB_URI)
        _mongo_db = _mongo_client["asksafe"]
    return _mongo_db


def _extract_session_code(text: str) -> Optional[str]:
    codes = re.findall(r"\b([A-Z0-9]{6})\b", text.upper())
    for c in codes:
        if any(ch.isdigit() for ch in c):
            return c
    return None


# ---------------------------------------------------------------------------
# Confusion Monitor Agent Logic
# (Same as agentverse_confusion_monitor.py::_compute_confusion_analytics)
# ---------------------------------------------------------------------------

def compute_confusion_analytics(session_code: str) -> str:
    """Analyze confusion data for a session — same logic as the Agentverse agent."""
    db = _get_db()

    session = db.sessions.find_one({"code": session_code.upper()})
    if not session:
        return f"Session {session_code} not found."

    session_id = session["_id"]
    title = session.get("title", "Untitled")
    threshold = session.get("confusion_threshold", 60)

    checkins = list(db.checkins.find({"session_id": session_id}))
    if not checkins:
        return f"Session {title} ({session_code}) has no check-in data yet."

    total = len(checkins)
    confused_count = sum(1 for c in checkins if c.get("confusion_rating", 0) >= 4)
    overall_index = round((confused_count / total) * 100) if total > 0 else 0
    avg_rating = round(sum(c.get("confusion_rating", 3) for c in checkins) / total, 2)

    # Per-slide breakdown
    slide_data: dict = {}
    for c in checkins:
        slide = c.get("slide")
        if slide is None:
            continue
        slide_data.setdefault(slide, []).append(c.get("confusion_rating", 3))

    spikes = []
    for slide_num in sorted(slide_data.keys()):
        ratings = slide_data[slide_num]
        slide_confused = sum(1 for r in ratings if r >= 4)
        slide_pct = round((slide_confused / len(ratings)) * 100)
        if slide_pct >= threshold:
            # Get questions near this slide for context
            q_count = db.questions.count_documents({
                "session_id": session_id,
                "slide": {"$gte": slide_num - 1, "$lte": slide_num + 1},
            })
            sample_qs = list(db.questions.find(
                {"session_id": session_id, "slide": slide_num}
            ).limit(2))
            topics = [q.get("text", "")[:60] for q in sample_qs if q.get("text")]
            topic_hint = f' about "{", ".join(topics)}"' if topics else ""
            spikes.append(
                f"Slide {slide_num}: {slide_pct}% confused — "
                f"{q_count} question(s){topic_hint}"
            )

    lines = [f"Confusion Report for \"{title}\" ({session_code})"]
    lines.append(f"Overall: {overall_index}% | Avg rating: {avg_rating}/5 | {total} check-ins")
    if spikes:
        lines.append(f"SPIKES ({len(spikes)}):")
        for s in spikes:
            lines.append(f"  - {s}")
    else:
        lines.append("No confusion spikes detected.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Question Clustering Agent Logic
# (Same as agentverse_question_clustering.py::_cluster_session_questions)
# ---------------------------------------------------------------------------

def cluster_session_questions(session_code: str) -> str:
    """Cluster questions for a session — same logic as the Agentverse agent."""
    db = _get_db()

    session = db.sessions.find_one({"code": session_code.upper()})
    if not session:
        return f"Session {session_code} not found."

    session_id = session["_id"]
    title = session.get("title", "Untitled")

    questions = list(db.questions.find({"session_id": session_id}).limit(500))
    if not questions:
        return f"Session {title} ({session_code}) has no questions yet."

    existing = list(db.clusters.find({"session_id": session_id}).limit(100))

    lines = [f"Question Clusters for \"{title}\" ({session_code})"]
    lines.append(f"{len(questions)} total questions")

    clusters = existing if existing else []
    source = "existing clusters" if existing else "no clusters generated yet"
    lines.append(f"Source: {source}")

    for i, c in enumerate(clusters, 1):
        label = c.get("label", "Unnamed")
        q_ids = c.get("question_ids", [])
        on_topic = "On-topic" if c.get("on_topic", True) else "Off-topic"
        status = c.get("status", "pending")
        upvotes = c.get("upvotes", 0)
        status_mark = " [Addressed]" if status == "addressed" else ""

        lines.append(f"  Cluster {i}: {label} ({on_topic}){status_mark}")
        lines.append(f"    {len(q_ids)} questions | {upvotes} upvotes")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Insight Report Agent Logic
# (Same as agentverse_insight_report.py::_generate_session_report)
# ---------------------------------------------------------------------------

def generate_session_report(session_code: str) -> str:
    """Generate a session report — same logic as the Agentverse agent."""
    db = _get_db()

    session = db.sessions.find_one({"code": session_code.upper()})
    if not session:
        return f"Session {session_code} not found."

    session_id = session["_id"]
    title = session.get("title", "Untitled")
    threshold = session.get("confusion_threshold", 60)
    status = session.get("status", "active")

    total_participants = max(
        session.get("live_participant_count", 0),
        session.get("demo_participant_count", 0),
    )
    checkins = list(db.checkins.find({"session_id": session_id}).limit(5000))
    questions = list(db.questions.find({"session_id": session_id}).limit(500))
    clusters = list(db.clusters.find({"session_id": session_id}).limit(100))

    total_checkins = len(checkins)
    total_questions = len(questions)
    total_clusters = len(clusters)
    clusters_addressed = sum(1 for c in clusters if c.get("status") == "addressed")

    overall_confused = sum(1 for c in checkins if c.get("confusion_rating", 0) >= 4)
    overall_index = round((overall_confused / total_checkins) * 100) if total_checkins > 0 else 0

    lines = [f"Session Report: \"{title}\" ({session_code})"]
    lines.append(f"Status: {'Ended' if status == 'ended' else 'Active'}")
    lines.append(f"Participants: {total_participants} | Check-ins: {total_checkins}")
    lines.append(f"Questions: {total_questions} | Clusters: {total_clusters} ({clusters_addressed} addressed)")
    lines.append(f"Overall confusion: {overall_index}%")

    # Per-slide confusion
    slide_data: dict = {}
    for c in checkins:
        slide = c.get("slide")
        if slide is None:
            continue
        slide_data.setdefault(slide, {"total": 0, "confused": 0})
        slide_data[slide]["total"] += 1
        if c.get("confusion_rating", 0) >= 4:
            slide_data[slide]["confused"] += 1

    spikes = []
    for s in sorted(slide_data.keys()):
        sd = slide_data[s]
        pct = round((sd["confused"] / sd["total"]) * 100) if sd["total"] > 0 else 0
        if pct >= threshold:
            spikes.append(f"Slide {s}: {pct}% confused")

    if spikes:
        lines.append(f"Spikes: {', '.join(spikes)}")

    # Top clusters
    if clusters:
        sorted_c = sorted(clusters, key=lambda c: len(c.get("question_ids", [])), reverse=True)
        lines.append("Top clusters:")
        for c in sorted_c[:5]:
            icon = "[Done]" if c.get("status") == "addressed" else "[Pending]"
            lines.append(f"  {icon} {c.get('label', 'Unnamed')} ({len(c.get('question_ids', []))} qs)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Async wrappers (called from FastAPI routes)
# ---------------------------------------------------------------------------

import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=3)


async def call_confusion_monitor(
    session_code: str,
    ratings: List[int],
    slide: Optional[int] = None,
    threshold: int = 60,
) -> Optional[dict]:
    """Async wrapper for confusion monitor analysis."""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, compute_confusion_analytics, session_code
        )
        if result:
            return {"agent_response": result, "source": "agentverse-integrated"}
    except Exception as e:
        print(f"[AgentClient] Confusion Monitor failed: {e}")
    return None


async def call_question_clustering(
    session_code: str,
    title: str,
    question_count: int,
) -> Optional[dict]:
    """Async wrapper for question clustering analysis."""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, cluster_session_questions, session_code
        )
        if result:
            return {"agent_response": result, "source": "agentverse-integrated"}
    except Exception as e:
        print(f"[AgentClient] Question Clustering failed: {e}")
    return None


async def call_insight_report(
    session_code: str,
    title: str,
) -> Optional[dict]:
    """Async wrapper for insight report generation."""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, generate_session_report, session_code
        )
        if result:
            return {"agent_response": result, "source": "agentverse-integrated"}
    except Exception as e:
        print(f"[AgentClient] Insight Report failed: {e}")
    return None
