"""
Confusion Monitor Agent — Registered on Agentverse
Receives real-time check-in data, calculates confusion index,
and fires spike alerts when threshold is exceeded.

Also implements the Chat Protocol for ASI:One integration,
allowing natural-language queries about session confusion data.
"""
import os
import re
from uagents import Agent, Context, Model
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Protocol models (existing — used by the AskSafe backend)
# ---------------------------------------------------------------------------


class CheckinBatch(Model):
    session_id: str
    ratings: List[int]  # list of 1-5 ratings
    slide: Optional[int] = None
    threshold: int = 60  # confusion threshold percentage


class ConfusionResult(Model):
    session_id: str
    slide: Optional[int]
    confusion_index: int  # 0-100 percentage
    avg_rating: float
    total_responses: int
    spike_detected: bool


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
    name="confusion_monitor",
    seed="asksafe-confusion-monitor-seed-2026",
    port=8001,
    endpoint=["http://localhost:8001/submit"],
)

print(f"Confusion Monitor Agent address: {agent.address}")


# ---------------------------------------------------------------------------
# Existing protocol handler (backend HTTP calls)
# ---------------------------------------------------------------------------


@agent.on_message(model=CheckinBatch)
async def handle_checkin(ctx: Context, sender: str, msg: CheckinBatch):
    ctx.logger.info(
        f"Received {len(msg.ratings)} check-ins for session {msg.session_id}"
    )

    if not msg.ratings:
        return

    total = len(msg.ratings)
    confused_count = sum(1 for r in msg.ratings if r >= 4)
    confusion_pct = round((confused_count / total) * 100)
    avg_rating = round(sum(msg.ratings) / total, 2)
    spike = confusion_pct >= msg.threshold

    result = ConfusionResult(
        session_id=msg.session_id,
        slide=msg.slide,
        confusion_index=confusion_pct,
        avg_rating=avg_rating,
        total_responses=total,
        spike_detected=spike,
    )

    if spike:
        ctx.logger.warning(
            f"SPIKE DETECTED! Confusion at {confusion_pct}% "
            f"(threshold: {msg.threshold}%) on slide {msg.slide}"
        )

    await ctx.send(sender, result)


# ---------------------------------------------------------------------------
# Chat Protocol handler (ASI:One / Agentverse)
# ---------------------------------------------------------------------------


def _extract_session_code(text: str) -> Optional[str]:
    """Extract a 6-character alphanumeric session code from text."""
    match = re.search(r"\b([A-Z0-9]{6})\b", text.upper())
    return match.group(1) if match else None


async def _compute_confusion_analytics(session_code: str) -> str:
    """Query MongoDB and compute full confusion analytics for a session."""
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

    # Fetch all check-ins for this session
    checkins = await db.checkins.find({"session_id": str(session_id)}).to_list(length=5000)

    if not checkins:
        return (
            f"Session **{title}** ({session_code}) has no check-in data yet. "
            "Students haven't submitted any confusion ratings."
        )

    # ---- Overall confusion index ----
    total = len(checkins)
    confused_count = sum(1 for c in checkins if c.get("confusion_rating", 0) >= 4)
    overall_index = round((confused_count / total) * 100) if total > 0 else 0
    avg_rating = round(sum(c.get("confusion_rating", 3) for c in checkins) / total, 2)

    # ---- Per-slide breakdown ----
    slide_data = {}  # type: dict
    for c in checkins:
        slide = c.get("slide")
        if slide is None:
            continue
        if slide not in slide_data:
            slide_data[slide] = {"ratings": [], "timestamps": []}
        slide_data[slide]["ratings"].append(c.get("confusion_rating", 3))
        ts = c.get("timestamp")
        if ts:
            slide_data[slide]["timestamps"].append(ts)

    slide_breakdown = []
    spikes = []
    for slide_num in sorted(slide_data.keys()):
        ratings = slide_data[slide_num]["ratings"]
        slide_total = len(ratings)
        slide_confused = sum(1 for r in ratings if r >= 4)
        slide_pct = round((slide_confused / slide_total) * 100) if slide_total > 0 else 0
        slide_breakdown.append({
            "slide": slide_num,
            "confusion_pct": slide_pct,
            "responses": slide_total,
        })
        if slide_pct >= threshold:
            spikes.append({
                "slide": slide_num,
                "confusion_pct": slide_pct,
                "responses": slide_total,
            })

    # ---- Trending analysis (rising confusion across consecutive slides) ----
    trending_segments = []
    if len(slide_breakdown) >= 3:
        run_start = None
        for i in range(1, len(slide_breakdown)):
            if slide_breakdown[i]["confusion_pct"] > slide_breakdown[i - 1]["confusion_pct"]:
                if run_start is None:
                    run_start = i - 1
            else:
                if run_start is not None and (i - run_start) >= 3:
                    trending_segments.append((
                        slide_breakdown[run_start]["slide"],
                        slide_breakdown[i - 1]["slide"],
                        slide_breakdown[run_start]["confusion_pct"],
                        slide_breakdown[i - 1]["confusion_pct"],
                    ))
                run_start = None
        # Close any open run
        if run_start is not None and (len(slide_breakdown) - run_start) >= 3:
            trending_segments.append((
                slide_breakdown[run_start]["slide"],
                slide_breakdown[-1]["slide"],
                slide_breakdown[run_start]["confusion_pct"],
                slide_breakdown[-1]["confusion_pct"],
            ))

    # ---- Correlation: questions submitted near spike slides ----
    spike_summaries = []
    for spike in spikes:
        slide_num = spike["slide"]
        # Count questions tagged to this slide or adjacent slides
        q_count = await db.questions.count_documents({
            "session_id": str(session_id),
            "slide": {"$gte": slide_num - 1, "$lte": slide_num + 1},
        })

        # Try to get sample question texts for context
        sample_questions = await db.questions.find(
            {"session_id": str(session_id), "slide": slide_num}
        ).limit(3).to_list(length=3)
        sample_texts = [q.get("text", "") for q in sample_questions if q.get("text")]

        topic_hint = ""
        if sample_texts:
            topic_hint = " about " + ", ".join(
                ['"' + t[:60] + '"' for t in sample_texts[:2]]
            )

        spike_summaries.append(
            f"Confusion spiked to {spike['confusion_pct']}% on slide {slide_num} "
            f"— {q_count} question(s){topic_hint} submitted around that slide"
        )

    # ---- Build the response ----
    lines = []
    lines.append(f"📊 **Confusion Report for \"{title}\" ({session_code})**\n")

    # Overall stats
    status_emoji = "🟢" if overall_index < 40 else ("🟡" if overall_index < 70 else "🔴")
    lines.append(f"{status_emoji} **Overall Confusion Index:** {overall_index}%")
    lines.append(f"📝 Average rating: {avg_rating}/5 across {total} check-ins")
    lines.append(f"🎯 Spike threshold: {threshold}%\n")

    # Spike detection
    if spikes:
        lines.append(f"🚨 **{len(spikes)} confusion spike(s) detected:**")
        for summary in spike_summaries:
            lines.append(f"  • {summary}")
        lines.append("")
    else:
        lines.append("✅ No confusion spikes detected — students seem to be following along.\n")

    # Per-slide breakdown
    if slide_breakdown:
        lines.append("📋 **Per-Slide Breakdown:**")
        for sb in slide_breakdown:
            bar = "█" * (sb["confusion_pct"] // 10) + "░" * (10 - sb["confusion_pct"] // 10)
            marker = " ⚠️" if sb["confusion_pct"] >= threshold else ""
            lines.append(
                f"  Slide {sb['slide']:>2}: {bar} {sb['confusion_pct']:>3}% "
                f"({sb['responses']} responses){marker}"
            )
        lines.append("")

    # Trending
    if trending_segments:
        lines.append("📈 **Trending Confusion:**")
        for start_slide, end_slide, start_pct, end_pct in trending_segments:
            lines.append(
                f"  • Rising confusion from slide {start_slide} ({start_pct}%) "
                f"to slide {end_slide} ({end_pct}%)"
            )
        lines.append("")

    # Inter-agent hint
    if spikes:
        lines.append(
            "💡 **Tip:** Try querying the **Question Clustering Agent** "
            "(asksafe-question-clustering) with this session code to see "
            "what specific topics students are struggling with on the spike slides."
        )

    return "\n".join(lines)


@agent.on_message(model=ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Chat Protocol handler — responds to natural-language queries via ASI:One."""
    ctx.logger.info(f"Chat message from {sender}: {msg.message}")

    query = msg.message.strip()

    # Extract session code
    session_code = _extract_session_code(query)

    if session_code:
        response_text = await _compute_confusion_analytics(session_code)
    else:
        response_text = (
            "👋 Hi! I'm the **AskSafe Confusion Monitor Agent**.\n\n"
            "I can analyze real-time confusion data from lecture sessions. "
            "Just include a 6-character session code in your message.\n\n"
            "**Try asking:**\n"
            "• \"What's the confusion level for session ABC123?\"\n"
            "• \"Show me confusion spikes for ABC123\"\n"
            "• \"Is the class confused right now? Session: ABC123\"\n\n"
            "I'll give you the overall confusion index, per-slide breakdown, "
            "spike detection, trending analysis, and question correlation."
        )

    await ctx.send(sender, ChatResponse(message=response_text))


if __name__ == "__main__":
    agent.run()
