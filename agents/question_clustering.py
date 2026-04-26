"""
Question Clustering Agent — Registered on Agentverse
Receives raw student questions, uses Gemini to semantically cluster them,
and returns ranked clusters with labels.

Also implements the Chat Protocol for ASI:One integration,
allowing natural-language queries about session question clusters.
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


class QuestionItem(Model):
    id: str
    text: str


class ClusterRequest(Model):
    session_id: str
    title: str
    questions: List[QuestionItem]


class ClusterItem(Model):
    label: str
    question_ids: List[str]
    representative_question: str
    on_topic: bool = True


class ClusterResponse(Model):
    session_id: str
    clusters: List[ClusterItem]


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
    name="question_clustering",
    seed="asksafe-question-clustering-seed-2026",
    port=8002,
    endpoint=["http://localhost:8002/submit"],
)

print(f"Question Clustering Agent address: {agent.address}")


# ---------------------------------------------------------------------------
# Shared Gemini clustering logic
# ---------------------------------------------------------------------------


def _build_clustering_prompt(
    title: str,
    questions: List[dict],
    slide_contexts: Optional[List[dict]] = None,
) -> str:
    """Build the Gemini prompt for semantic clustering."""
    slide_context_block = ""
    if slide_contexts:
        slide_lines = []
        for sc in slide_contexts:
            slide_lines.append(
                f"  Slide {sc.get('slide_number', '?')}: "
                f"{sc.get('text_content', '')[:200]}"
            )
        slide_context_block = (
            "\n\nLecture slide content for context:\n" + "\n".join(slide_lines)
        )

    return f"""You are an educational AI. Given student questions from a lecture
titled "{title}", group them into semantic clusters.
{slide_context_block}

Questions:
{json.dumps(questions, indent=2)}

For each cluster, determine:
1. A short descriptive label
2. Which question IDs belong to it
3. The most representative question
4. Whether the cluster is on-topic for the lecture

Return ONLY valid JSON (no markdown) as an array:
[{{"label":"Short label","question_ids":["id1"],"representative_question":"Best question","on_topic":true}}]"""


async def _run_gemini_clustering(prompt: str) -> List[dict]:
    """Call Gemini and parse the clustering result."""
    try:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY", "")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemma-4-26b-a4b-it", contents=prompt
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Existing protocol handler (backend HTTP calls)
# ---------------------------------------------------------------------------


@agent.on_message(model=ClusterRequest)
async def handle_clustering(ctx: Context, sender: str, msg: ClusterRequest):
    ctx.logger.info(
        f"Clustering {len(msg.questions)} questions for '{msg.title}'"
    )

    q_list = [{"id": q.id, "text": q.text} for q in msg.questions]
    prompt = _build_clustering_prompt(msg.title, q_list)

    cluster_data = await _run_gemini_clustering(prompt)

    if not cluster_data:
        ctx.logger.error("Gemini clustering failed — using fallback single cluster")
        cluster_data = [
            {
                "label": "All Questions",
                "question_ids": [q.id for q in msg.questions],
                "representative_question": msg.questions[0].text
                if msg.questions
                else "",
                "on_topic": True,
            }
        ]

    clusters = [
        ClusterItem(
            label=c["label"],
            question_ids=c["question_ids"],
            representative_question=c.get("representative_question", ""),
            on_topic=c.get("on_topic", True),
        )
        for c in cluster_data
    ]

    await ctx.send(
        sender, ClusterResponse(session_id=msg.session_id, clusters=clusters)
    )


# ---------------------------------------------------------------------------
# Chat Protocol handler (ASI:One / Agentverse)
# ---------------------------------------------------------------------------


def _extract_session_code(text: str) -> Optional[str]:
    """Extract a 6-character alphanumeric session code from text."""
    match = re.search(r"\b([A-Z0-9]{6})\b", text.upper())
    return match.group(1) if match else None


async def _cluster_session_questions(session_code: str) -> str:
    """Fetch questions from MongoDB, cluster them, and return a formatted response."""
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

    # Fetch questions for this session
    questions = await db.questions.find(
        {"session_id": str(session_id)}
    ).to_list(length=500)

    if not questions:
        return (
            f"Session **{title}** ({session_code}) has no student questions yet. "
            "Students haven't submitted any questions."
        )

    # Fetch slide contexts if available
    slide_contexts = session.get("slide_contexts", [])

    # Prepare question list for clustering
    q_list = []
    for q in questions:
        q_list.append({
            "id": str(q["_id"]),
            "text": q.get("text", ""),
            "slide": q.get("slide"),
        })

    # Also check for existing clusters in the DB
    existing_clusters = await db.clusters.find(
        {"session_id": str(session_id)}
    ).to_list(length=100)

    # If we have existing clusters, use them; otherwise run Gemini clustering
    if existing_clusters:
        cluster_data = existing_clusters
        used_existing = True
    else:
        # Build prompt with slide context
        prompt_questions = [{"id": q["id"], "text": q["text"]} for q in q_list]
        prompt = _build_clustering_prompt(title, prompt_questions, slide_contexts)
        raw_clusters = await _run_gemini_clustering(prompt)

        if raw_clusters:
            cluster_data = raw_clusters
            used_existing = False
        else:
            # Fallback: single cluster
            cluster_data = [{
                "label": "All Questions",
                "question_ids": [q["id"] for q in q_list],
                "representative_question": q_list[0]["text"] if q_list else "",
                "on_topic": True,
            }]
            used_existing = False

    # ---- Compute urgency ranking ----
    # Fetch confusion data per slide for correlation
    checkins = await db.checkins.find(
        {"session_id": str(session_id)}
    ).to_list(length=5000)

    slide_confusion = {}  # type: dict
    for c in checkins:
        slide = c.get("slide")
        if slide is None:
            continue
        if slide not in slide_confusion:
            slide_confusion[slide] = {"total": 0, "confused": 0}
        slide_confusion[slide]["total"] += 1
        if c.get("confusion_rating", 0) >= 4:
            slide_confusion[slide]["confused"] += 1

    # ---- Build the response ----
    lines = []
    lines.append(f"🔍 **Question Clusters for \"{title}\" ({session_code})**\n")
    lines.append(f"📝 {len(questions)} total questions analyzed")

    if used_existing:
        lines.append(f"📦 Using {len(cluster_data)} existing clusters from the database\n")
    else:
        lines.append(f"🤖 AI generated {len(cluster_data)} clusters\n")

    # Format each cluster
    for i, cluster in enumerate(cluster_data, 1):
        # Handle both DB documents and raw Gemini output
        if used_existing:
            label = cluster.get("label", "Unnamed Cluster")
            q_ids = cluster.get("question_ids", [])
            rep_q = cluster.get("representative_question", "")
            on_topic = cluster.get("on_topic", True)
            upvotes = cluster.get("upvotes", 0)
            status = cluster.get("status", "pending")
        else:
            label = cluster.get("label", "Unnamed Cluster")
            q_ids = cluster.get("question_ids", [])
            rep_q = cluster.get("representative_question", "")
            on_topic = cluster.get("on_topic", True)
            upvotes = 0
            status = "new"

        topic_badge = "📗 On-topic" if on_topic else "📕 Off-topic"
        status_badge = ""
        if status == "addressed":
            status_badge = " ✅ Addressed"
        elif status == "flagged":
            status_badge = " 🏳️ Flagged for next class"

        lines.append(f"**Cluster {i}: {label}** {topic_badge}{status_badge}")
        lines.append(f"  💬 {len(q_ids)} question(s) | 👍 {upvotes} upvotes")
        if rep_q:
            lines.append(f"  📌 Representative: \"{rep_q}\"")

        # Show a few sample questions from this cluster
        cluster_questions = [
            q for q in q_list if q["id"] in [str(qid) for qid in q_ids]
        ]
        if cluster_questions and len(cluster_questions) > 1:
            lines.append("  📋 Sample questions:")
            for cq in cluster_questions[:3]:
                slide_tag = f" (slide {cq['slide']})" if cq.get("slide") else ""
                lines.append(f"    • \"{cq['text']}\"{slide_tag}")

        # Urgency hint based on confusion correlation
        if cluster_questions:
            cluster_slides = [cq.get("slide") for cq in cluster_questions if cq.get("slide")]
            if cluster_slides:
                max_confusion = 0
                for s in cluster_slides:
                    if s in slide_confusion and slide_confusion[s]["total"] > 0:
                        pct = round(
                            (slide_confusion[s]["confused"] / slide_confusion[s]["total"]) * 100
                        )
                        max_confusion = max(max_confusion, pct)
                if max_confusion >= 60:
                    lines.append(
                        f"  🚨 High urgency — confusion at {max_confusion}% on related slides"
                    )

        lines.append("")

    # Summary
    on_topic_count = sum(
        1 for c in cluster_data if c.get("on_topic", True)
    )
    off_topic_count = len(cluster_data) - on_topic_count
    lines.append(
        f"📊 **Summary:** {on_topic_count} on-topic clusters, "
        f"{off_topic_count} off-topic clusters"
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
        response_text = await _cluster_session_questions(session_code)
    else:
        response_text = (
            "👋 Hi! I'm the **AskSafe Question Clustering Agent**.\n\n"
            "I can analyze and cluster student questions from lecture sessions "
            "using AI to identify common topics and confusion areas.\n\n"
            "**Try asking:**\n"
            "• \"Cluster the questions for session ABC123\"\n"
            "• \"What are students confused about in ABC123?\"\n"
            "• \"Show me question topics for session ABC123\"\n\n"
            "Just include a 6-character session code and I'll group the "
            "questions into meaningful clusters with urgency rankings."
        )

    await ctx.send(sender, ChatResponse(message=response_text))


if __name__ == "__main__":
    agent.run()
