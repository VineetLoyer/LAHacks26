import json
from typing import List, Optional, Set

from fastapi import APIRouter, HTTPException
from bson import ObjectId
from google import genai

from app.database import get_db
from app.sio_instance import sio
from app.config import GEMINI_API_KEY
from app.models import AddressClusterRequest, ClusterStatus

router = APIRouter()

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def _build_slide_context_text(
    slide_contexts: List[dict],
    slide_numbers: Optional[Set[int]] = None,
) -> str:
    """Build a text block of relevant slide content for Gemini prompts.

    If slide_numbers is provided, only include those slides.
    Otherwise include all slides.
    Returns empty string if no slide contexts are available.
    """
    if not slide_contexts:
        return ""

    relevant = slide_contexts
    if slide_numbers:
        relevant = [
            sc for sc in slide_contexts
            if sc.get("slide_number") in slide_numbers
        ]

    if not relevant:
        return ""

    lines = ["Lecture slide content for context:"]
    for sc in sorted(relevant, key=lambda x: x.get("slide_number", 0)):
        text = sc.get("text_content", "").strip()
        if text:
            lines.append(f"  Slide {sc['slide_number']}: {text}")

    return "\n".join(lines)


@router.post("/generate/{session_id}")
async def generate_clusters(session_id: str):
    """AI clusters all unclustered questions for a session."""
    db = get_db()
    session = await db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get unclustered questions
    cursor = db.questions.find({
        "session_id": ObjectId(session_id),
        "cluster_id": None,
    })
    questions = await cursor.to_list(length=500)
    if not questions:
        return {"clusters": [], "message": "No new questions to cluster"}

    q_list = [{"id": str(q["_id"]), "text": q["text"], "slide": q.get("slide")} for q in questions]

    # Build slide context from session document
    slide_contexts = session.get("slide_contexts", [])
    tagged_slides = set()
    for q in questions:
        if q.get("slide") is not None:
            tagged_slides.add(q["slide"])
    slide_context_text = _build_slide_context_text(slide_contexts, tagged_slides)

    # Build the prompt with optional slide context
    slide_section = ""
    if slide_context_text:
        slide_section = f"""
{slide_context_text}

Use the slide content above to better understand the context of each question and 
determine whether questions are on-topic or off-topic relative to the lecture material.
"""

    prompt = f"""You are an educational AI. Given student questions from a lecture 
titled "{session['title']}", group them into semantic clusters.
{slide_section}
Questions:
{json.dumps(q_list, indent=2)}

Return ONLY valid JSON (no markdown fences) as an array of clusters:
[
  {{
    "label": "Short descriptive label (5-7 words)",
    "question_ids": ["id1", "id2"],
    "representative_question": "The best single question from this cluster",
    "on_topic": true
  }}
]"""

    if not gemini_client:
        return {"clusters": [], "message": "Gemini API key not configured"}

    response = gemini_client.models.generate_content(
        model="gemma-3-27b-it",
        contents=prompt,
    )

    try:
        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        cluster_data = json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        raise HTTPException(status_code=500, detail="Failed to parse AI response")

    created_clusters = []
    for c in cluster_data:
        cluster_doc = {
            "session_id": ObjectId(session_id),
            "label": c["label"],
            "question_ids": [ObjectId(qid) for qid in c["question_ids"]],
            "representative_question": c.get("representative_question", ""),
            "upvotes": 0,
            "status": ClusterStatus.pending,
            "on_topic": c.get("on_topic", True),
            "ai_explanation": None,
            "professor_response": None,
            "response_type": None,
        }
        result = await db.clusters.insert_one(cluster_doc)

        # Update questions with cluster_id
        await db.questions.update_many(
            {"_id": {"$in": [ObjectId(qid) for qid in c["question_ids"]]}},
            {"$set": {"cluster_id": result.inserted_id}},
        )

        created_clusters.append({
            "id": str(result.inserted_id),
            "label": c["label"],
            "question_count": len(c["question_ids"]),
            "representative_question": c.get("representative_question", ""),
            "on_topic": c.get("on_topic", True),
        })

    return {"clusters": created_clusters}


@router.get("/list/{session_id}")
async def list_clusters(session_id: str):
    db = get_db()
    cursor = db.clusters.find({"session_id": ObjectId(session_id)})
    clusters = await cursor.to_list(length=100)

    return {
        "clusters": [
            {
                "id": str(c["_id"]),
                "label": c["label"],
                "question_count": len(c.get("question_ids", [])),
                "representative_question": c.get("representative_question", ""),
                "upvotes": c.get("upvotes", 0),
                "status": c.get("status", "pending"),
                "on_topic": c.get("on_topic", True),
                "ai_explanation": c.get("ai_explanation"),
                "professor_response": c.get("professor_response"),
                "response_type": c.get("response_type"),
            }
            for c in clusters
        ]
    }


@router.post("/upvote/{cluster_id}")
async def upvote_cluster(cluster_id: str):
    db = get_db()
    result = await db.clusters.update_one(
        {"_id": ObjectId(cluster_id)},
        {"$inc": {"upvotes": 1}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Fetch updated cluster to get new upvote count and session_id
    cluster = await db.clusters.find_one({"_id": ObjectId(cluster_id)})
    if cluster:
        session = await db.sessions.find_one({"_id": cluster["session_id"]})
        if session:
            await sio.emit("cluster_upvoted", {
                "cluster_id": cluster_id,
                "upvotes": cluster["upvotes"],
            }, room=session["code"])

    return {"status": "upvoted"}


@router.patch("/{cluster_id}/hide")
async def hide_cluster(cluster_id: str):
    """Hide a question cluster (moderation)."""
    db = get_db()
    result = await db.clusters.update_one(
        {"_id": ObjectId(cluster_id)},
        {"$set": {"status": ClusterStatus.hidden}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return {"cluster_id": cluster_id, "status": "hidden"}


@router.patch("/{cluster_id}/restore")
async def restore_cluster(cluster_id: str):
    """Restore a hidden cluster back to pending."""
    db = get_db()
    result = await db.clusters.update_one(
        {"_id": ObjectId(cluster_id)},
        {"$set": {"status": ClusterStatus.pending}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return {"cluster_id": cluster_id, "status": "pending"}


@router.post("/address")
async def address_cluster(req: AddressClusterRequest):
    """Professor addresses a question cluster with AI-generated explanation."""
    db = get_db()
    cluster = await db.clusters.find_one({"_id": ObjectId(req.cluster_id)})
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    session = await db.sessions.find_one({"_id": cluster["session_id"]})

    # Get questions in this cluster
    q_cursor = db.questions.find({"cluster_id": ObjectId(req.cluster_id)})
    questions = await q_cursor.to_list(length=50)
    q_texts = [q["text"] for q in questions]

    explanation = ""
    if gemini_client:
        # Build slide context for the questions in this cluster
        slide_contexts = session.get("slide_contexts", []) if session else []
        tagged_slides = set()
        for q in questions:
            if q.get("slide") is not None:
                tagged_slides.add(q["slide"])
        slide_context_text = _build_slide_context_text(slide_contexts, tagged_slides)

        slide_section = ""
        if slide_context_text:
            slide_section = f"""
{slide_context_text}

Use the slide content above to provide a more specific, context-aware explanation 
that references the actual lecture material.
"""

        prompt = f"""You are helping a professor address student confusion.

Lecture topic: {session['title']}
Question cluster: "{cluster['label']}"
{slide_section}
Student questions:
{json.dumps(q_texts, indent=2)}

Provide a clear, concise explanation (2-3 paragraphs) that addresses the core 
confusion. Include a helpful analogy or example. Keep the tone warm and 
encouraging — these students were anxious about asking."""

        response = gemini_client.models.generate_content(
            model="gemma-3-27b-it",
            contents=prompt,
        )
        explanation = response.text

    update_data = {
        "status": ClusterStatus.addressed,
        "ai_explanation": explanation,
        "response_type": req.response_type,
    }
    if req.custom_response:
        update_data["professor_response"] = req.custom_response

    await db.clusters.update_one(
        {"_id": ObjectId(req.cluster_id)},
        {"$set": update_data},
    )

    # Emit cluster_addressed Socket.IO event to the session room
    if session:
        await sio.emit("cluster_addressed", {
            "cluster_id": req.cluster_id,
            "label": cluster["label"],
            "ai_explanation": explanation,
            "professor_response": req.custom_response,
            "response_type": req.response_type,
        }, room=session["code"])

    return {
        "cluster_id": req.cluster_id,
        "ai_explanation": explanation,
        "response_type": req.response_type,
        "status": "addressed",
    }
