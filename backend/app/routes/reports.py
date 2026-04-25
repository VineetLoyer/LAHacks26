import json
from datetime import datetime

from typing import Optional

from fastapi import APIRouter, HTTPException
from bson import ObjectId
from google import genai

from app.database import get_db
from app.sio_instance import sio
from app.config import GEMINI_API_KEY

router = APIRouter()

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


async def _build_confusion_timeline(db, session_id: ObjectId):
    """Compute per-slide confusion data (same aggregation as checkins stats)."""
    pipeline = [
        {"$match": {"session_id": session_id}},
        {"$group": {
            "_id": "$slide",
            "avg_confusion": {"$avg": "$confusion_rating"},
            "count": {"$sum": 1},
            "confused_count": {
                "$sum": {"$cond": [{"$gte": ["$confusion_rating", 4]}, 1, 0]}
            },
        }},
        {"$sort": {"_id": 1}},
    ]
    cursor = db.checkins.aggregate(pipeline)
    results = await cursor.to_list(length=100)

    timeline = []
    for r in results:
        pct = round((r["confused_count"] / r["count"]) * 100) if r["count"] else 0
        timeline.append({
            "slide": r["_id"],
            "confusion_pct": pct,
            "avg_rating": round(r["avg_confusion"], 2),
            "responses": r["count"],
        })
    return timeline


async def _generate_gemini_summary(
    session_title: str,
    confusion_timeline: list,
    confusion_spikes: list,
    cluster_labels: list,
    total_questions: int,
    total_participants: int,
    clusters_addressed: int,
    clusters_total: int,
    flagged_for_next: list,
) -> Optional[str]:
    """Generate a 2-3 paragraph session summary using Gemini."""
    if not gemini_client:
        return None

    spike_descriptions = "; ".join(
        f"Slide {s['slide']}: {s['confusion_pct']}% confused — {s.get('description', 'N/A')}"
        for s in confusion_spikes
    ) or "No confusion spikes detected."

    prompt = f"""You are an educational analytics assistant. Generate a concise 2-3 paragraph 
summary of a live session based on the following data.

Session title: {session_title}
Total participants: {total_participants}
Total questions: {total_questions}
Clusters addressed: {clusters_addressed} of {clusters_total}

Confusion timeline (per slide):
{json.dumps(confusion_timeline, indent=2)}

Confusion spikes:
{spike_descriptions}

Question cluster topics: {', '.join(cluster_labels) if cluster_labels else 'None'}

Topics flagged for next session: {', '.join(flagged_for_next) if flagged_for_next else 'None'}

Write a professional, helpful summary that:
1. Highlights overall engagement and participation
2. Identifies the key confusion points and how they were addressed
3. Recommends focus areas for the next session
Keep the tone warm and constructive."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text
    except Exception:
        return None


def _generate_template_summary(
    session_title: str,
    total_participants: int,
    total_questions: int,
    clusters_addressed: int,
    clusters_total: int,
    confusion_spikes: list,
    flagged_for_next: list,
) -> str:
    """Generate a basic template summary when Gemini is unavailable."""
    spike_text = ""
    if confusion_spikes:
        spike_items = [
            f"Slide {s['slide']} ({s['confusion_pct']}%)"
            for s in confusion_spikes
        ]
        spike_text = f" Confusion spikes were detected on {', '.join(spike_items)}."
    else:
        spike_text = " No significant confusion spikes were detected."

    resolution_rate = round((clusters_addressed / clusters_total) * 100) if clusters_total else 0

    flagged_text = ""
    if flagged_for_next:
        flagged_text = f" The following topics have been flagged for review in the next session: {', '.join(flagged_for_next)}."

    return (
        f"Session \"{session_title}\" had {total_participants} participants who submitted "
        f"{total_questions} questions across the session.{spike_text}\n\n"
        f"{clusters_addressed} of {clusters_total} question clusters were addressed, "
        f"achieving a {resolution_rate}% resolution rate.{flagged_text}"
    )


@router.post("/generate/{session_id}")
async def generate_report(session_id: str):
    """End session and generate a comprehensive report."""
    db = get_db()
    sid = ObjectId(session_id)

    session = await db.sessions.find_one({"_id": sid})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Set session status to ended
    now = datetime.utcnow()
    await db.sessions.update_one(
        {"_id": sid},
        {"$set": {"status": "ended", "ended_at": now}},
    )

    # Gather session data
    total_questions = await db.questions.count_documents({"session_id": sid})

    # Participant count
    demo_count = session.get("demo_participant_count", 0)
    live_count = session.get("live_participant_count", 0)
    total_participants = max(demo_count, live_count)

    # Confusion timeline
    confusion_timeline = await _build_confusion_timeline(db, sid)

    # Clusters
    clusters_cursor = db.clusters.find({"session_id": sid})
    clusters = await clusters_cursor.to_list(length=200)

    clusters_total = len(clusters)
    clusters_addressed = sum(1 for c in clusters if c.get("status") == "addressed")

    # Confusion spikes: slides where confusion_pct > threshold
    threshold = session.get("confusion_threshold", 60)
    slide_contexts = session.get("slide_contexts", [])
    slide_context_map = {sc["slide_number"]: sc["text_content"] for sc in slide_contexts}

    confusion_spikes = []
    for entry in confusion_timeline:
        if entry["confusion_pct"] > threshold:
            slide_num = entry["slide"]
            description = ""
            if slide_num and slide_num in slide_context_map:
                # Use first 100 chars of slide context as description
                ctx = slide_context_map[slide_num]
                description = ctx[:100] + ("..." if len(ctx) > 100 else "")
            confusion_spikes.append({
                "slide": slide_num,
                "confusion_pct": entry["confusion_pct"],
                "description": description,
            })

    # Flagged for next session: clusters with status "flagged" or not addressed
    flagged_for_next = [
        c["label"]
        for c in clusters
        if c.get("status") in ("flagged", "pending") and c.get("on_topic", True)
    ]

    cluster_labels = [c["label"] for c in clusters]

    # Generate summary
    summary = await _generate_gemini_summary(
        session_title=session.get("title", "Untitled Session"),
        confusion_timeline=confusion_timeline,
        confusion_spikes=confusion_spikes,
        cluster_labels=cluster_labels,
        total_questions=total_questions,
        total_participants=total_participants,
        clusters_addressed=clusters_addressed,
        clusters_total=clusters_total,
        flagged_for_next=flagged_for_next,
    )

    if summary is None:
        summary = _generate_template_summary(
            session_title=session.get("title", "Untitled Session"),
            total_participants=total_participants,
            total_questions=total_questions,
            clusters_addressed=clusters_addressed,
            clusters_total=clusters_total,
            confusion_spikes=confusion_spikes,
            flagged_for_next=flagged_for_next,
        )

    # Build report document
    report = {
        "session_id": sid,
        "total_participants": total_participants,
        "total_questions": total_questions,
        "clusters_addressed": clusters_addressed,
        "clusters_total": clusters_total,
        "confusion_timeline": confusion_timeline,
        "confusion_spikes": confusion_spikes,
        "flagged_for_next_lecture": flagged_for_next,
        "summary": summary,
        "generated_at": now,
    }

    # Upsert report (replace if already exists for this session)
    await db.reports.update_one(
        {"session_id": sid},
        {"$set": report},
        upsert=True,
    )

    # Emit session_ended event
    if session.get("code"):
        await sio.emit("session_ended", {
            "session_id": session_id,
            "report_available": True,
        }, room=session["code"])

    # Return report with string id
    report["id"] = session_id
    report.pop("session_id", None)
    report["generated_at"] = now.isoformat()

    return report


@router.get("/{session_id}")
async def get_report(session_id: str):
    """Retrieve a stored report for a session."""
    db = get_db()
    report = await db.reports.find_one({"session_id": ObjectId(session_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": str(report["session_id"]),
        "total_participants": report["total_participants"],
        "total_questions": report["total_questions"],
        "clusters_addressed": report["clusters_addressed"],
        "clusters_total": report["clusters_total"],
        "confusion_timeline": report["confusion_timeline"],
        "confusion_spikes": report["confusion_spikes"],
        "flagged_for_next_lecture": report["flagged_for_next_lecture"],
        "summary": report["summary"],
        "generated_at": report["generated_at"].isoformat() if hasattr(report["generated_at"], "isoformat") else report["generated_at"],
    }
