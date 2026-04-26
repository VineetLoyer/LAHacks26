import json
from typing import List, Optional, Set

from fastapi import APIRouter, HTTPException
from bson import ObjectId
from google import genai

from app.database import get_db
from app.sio_instance import sio
from app.config import GEMINI_API_KEY
from app.models import AddressClusterRequest, ClusterStatus
from app import agent_client

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

    # Fetch existing clusters so Gemini can merge new questions into them
    existing_clusters_cursor = db.clusters.find({"session_id": ObjectId(session_id)})
    existing_clusters = await existing_clusters_cursor.to_list(length=100)
    existing_cluster_info = []
    for ec in existing_clusters:
        existing_cluster_info.append({
            "id": str(ec["_id"]),
            "label": ec.get("label", ""),
            "representative_question": ec.get("representative_question", ""),
            "question_count": len(ec.get("question_ids", [])),
        })

    existing_section = ""
    if existing_cluster_info:
        existing_section = f"""
EXISTING CLUSTERS (from previous rounds):
{json.dumps(existing_cluster_info, indent=2)}

If a new question fits an existing cluster, assign it to that cluster using the existing cluster's "id".
If a new question does NOT fit any existing cluster, create a new cluster with a new label.
"""

    # Build slide context from session document — include ALL slides for context
    slide_contexts = session.get("slide_contexts", [])
    slide_context_text = _build_slide_context_text(slide_contexts)  # all slides, no filter

    # Build the prompt with optional slide context
    slide_section = ""
    if slide_context_text:
        slide_section = f"""
{slide_context_text}

Use the slide content above to better understand the context of each question and 
determine whether questions are on-topic or off-topic relative to the lecture material.
"""

    prompt = f"""You are an educational AI assistant. Given student questions from a lecture 
titled "{session['title']}", group them into semantic clusters.
{existing_section}
IMPORTANT CLUSTERING RULES:
- If a new question is similar to an existing cluster, ADD it to that existing cluster (use the existing cluster's "id" in the "existing_cluster_id" field).
- Only create a NEW cluster if the question doesn't fit any existing cluster.
- Do NOT lump unrelated questions together just because there are few of them.
- Logistical questions (homework deadlines, exam dates, grading) should be their OWN cluster, separate from conceptual questions.
- If a question is unique and doesn't fit any cluster, put it in its own single-question cluster.
- Each cluster should contain questions about the SAME specific topic.
- A question is ON-TOPIC if it relates to ANY concept that could reasonably be covered in a course called "{session['title']}". This includes data streams, algorithms, data structures, filtering, sampling, counting, sliding windows, Bloom filters, DGIM, Flajolet-Martin, or any related computer science concept.
- Only mark as OFF-TOPIC if the question is completely unrelated to the course (e.g., "what time is lunch?", "when is the midterm?", "can we get the slides posted?").
{slide_section}
Questions:
{json.dumps(q_list, indent=2)}

Return ONLY valid JSON (no markdown fences) as an array of clusters:
[
  {{
    "label": "Short descriptive label (5-7 words)",
    "question_ids": ["id1", "id2"],
    "representative_question": "The best single question from this cluster",
    "summary": "A 1-2 sentence description explaining what students in this cluster are asking about.",
    "on_topic": true,
    "existing_cluster_id": null
  }}
]

IMPORTANT FIELDS:
- "existing_cluster_id": Set to the existing cluster's "id" if these questions should be MERGED into an existing cluster. Set to null if this is a NEW cluster.
- "summary": CRITICAL — must capture the nuance of what students are confused about, not just repeat the label."""

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
        new_q_ids = [ObjectId(qid) for qid in c["question_ids"]]
        existing_id = c.get("existing_cluster_id")

        if existing_id:
            # Merge into existing cluster
            try:
                await db.clusters.update_one(
                    {"_id": ObjectId(existing_id)},
                    {
                        "$push": {"question_ids": {"$each": new_q_ids}},
                        "$set": {"summary": c.get("summary", "")},
                    },
                )
                # Update questions with the existing cluster_id
                await db.questions.update_many(
                    {"_id": {"$in": new_q_ids}},
                    {"$set": {"cluster_id": ObjectId(existing_id)}},
                )
                # Fetch updated cluster for response
                updated = await db.clusters.find_one({"_id": ObjectId(existing_id)})
                if updated:
                    created_clusters.append({
                        "id": existing_id,
                        "label": updated.get("label", c["label"]),
                        "question_count": len(updated.get("question_ids", [])),
                        "representative_question": updated.get("representative_question", ""),
                        "summary": c.get("summary", updated.get("summary", "")),
                        "on_topic": updated.get("on_topic", True),
                    })
            except Exception:
                # If merge fails, create as new cluster
                existing_id = None

        if not existing_id:
            # Create new cluster
            cluster_doc = {
                "session_id": ObjectId(session_id),
                "label": c["label"],
                "question_ids": new_q_ids,
                "representative_question": c.get("representative_question", ""),
                "summary": c.get("summary", ""),
                "upvotes": 0,
                "status": ClusterStatus.pending,
                "on_topic": c.get("on_topic", True),
                "ai_explanation": None,
                "professor_response": None,
                "response_type": None,
            }
            result = await db.clusters.insert_one(cluster_doc)

            # Update questions with new cluster_id
            await db.questions.update_many(
                {"_id": {"$in": new_q_ids}},
                {"$set": {"cluster_id": result.inserted_id}},
            )

            created_clusters.append({
                "id": str(result.inserted_id),
                "label": c["label"],
                "question_count": len(c["question_ids"]),
                "representative_question": c.get("representative_question", ""),
                "summary": c.get("summary", ""),
                "on_topic": c.get("on_topic", True),
            })

    # Emit clusters_updated event so students see new clusters in real-time
    if session.get("code"):
        await sio.emit("clusters_updated", {
            "clusters": [
                {
                    **cl,
                    "upvotes": 0,
                    "status": "pending",
                    "ai_explanation": None,
                    "professor_response": None,
                    "response_type": None,
                }
                for cl in created_clusters
            ],
        }, room=session["code"])

    # Call the Question Clustering Agent on Agentverse (non-blocking enrichment)
    # This demonstrates the agent is integrated into the app flow
    agent_analysis = None
    try:
        agent_result = await agent_client.call_question_clustering(
            session_code=session.get("code", ""),
            title=session.get("title", ""),
            question_count=len(questions),
        )
        if agent_result:
            agent_analysis = agent_result.get("agent_response")
            print(f"[Agentverse] Question Clustering Agent responded for session {session.get('code')}")
    except Exception as e:
        print(f"[Agentverse] Question Clustering Agent call failed (non-critical): {e}")

    return {
        "clusters": created_clusters,
        "agent_analysis": agent_analysis,
    }


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
                "summary": c.get("summary", ""),
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

    cluster = await db.clusters.find_one({"_id": ObjectId(cluster_id)})
    if cluster:
        session = await db.sessions.find_one({"_id": cluster["session_id"]})
        if session:
            await sio.emit("cluster_upvoted", {
                "cluster_id": cluster_id,
                "upvotes": cluster["upvotes"],
            }, room=session["code"])

    return {"status": "upvoted", "upvotes": cluster["upvotes"] if cluster else 0}


@router.post("/downvote/{cluster_id}")
async def downvote_cluster(cluster_id: str):
    """Remove an upvote from a cluster (toggle)."""
    db = get_db()
    # Only decrement if upvotes > 0
    result = await db.clusters.update_one(
        {"_id": ObjectId(cluster_id), "upvotes": {"$gt": 0}},
        {"$inc": {"upvotes": -1}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cluster not found or no upvotes")

    cluster = await db.clusters.find_one({"_id": ObjectId(cluster_id)})
    if cluster:
        session = await db.sessions.find_one({"_id": cluster["session_id"]})
        if session:
            await sio.emit("cluster_upvoted", {
                "cluster_id": cluster_id,
                "upvotes": cluster["upvotes"],
            }, room=session["code"])

    return {"status": "downvoted", "upvotes": cluster["upvotes"] if cluster else 0}


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
    """Professor addresses a question cluster."""
    db = get_db()
    cluster = await db.clusters.find_one({"_id": ObjectId(req.cluster_id)})
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    session = await db.sessions.find_one({"_id": cluster["session_id"]})

    explanation = ""

    # Only generate AI explanation for "explained_now" response type
    if req.response_type == "explained_now" and gemini_client:
        q_cursor = db.questions.find({"cluster_id": ObjectId(req.cluster_id)})
        questions = await q_cursor.to_list(length=50)
        q_texts = [q["text"] for q in questions]

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

    # Determine cluster status based on response type
    if req.response_type == "flagged_next_class":
        new_status = ClusterStatus.flagged
    else:
        new_status = ClusterStatus.addressed

    update_data = {
        "status": new_status,
        "ai_explanation": explanation if explanation else None,
        "response_type": req.response_type,
    }
    if req.custom_response:
        update_data["professor_response"] = req.custom_response

    await db.clusters.update_one(
        {"_id": ObjectId(req.cluster_id)},
        {"$set": update_data},
    )

    # Only broadcast to students if the professor is actually responding
    # (not for "flagged_next_class" — that's internal)
    if session and req.response_type != "flagged_next_class":
        broadcast_response = req.custom_response or explanation
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
        "status": new_status,
    }
