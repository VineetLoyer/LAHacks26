import json
from datetime import datetime

from typing import Optional

from fastapi import APIRouter, HTTPException
from bson import ObjectId
from google import genai

from app.database import get_db
from app.sio_instance import sio
from app.config import GEMINI_API_KEY
from app import agent_client

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
            model="gemma-3-27b-it",
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


async def _generate_student_email_body(
    session_title: str,
    report: Optional[dict],
    db,
    session_id,
) -> str:
    """Generate a student-friendly email summary for post-session delivery.

    Different from the professor report — more encouraging, focused on what was
    covered and what to review next.
    """
    # Gather data from report or raw session data
    if report:
        summary = report.get("summary", "")
        confusion_spikes = report.get("confusion_spikes", [])
        flagged = report.get("flagged_for_next_lecture", [])
        total_questions = report.get("total_questions", 0)
        clusters_addressed = report.get("clusters_addressed", 0)
        clusters_total = report.get("clusters_total", 0)
    else:
        # Fallback: compute from raw data
        summary = ""
        total_questions = await db.questions.count_documents({"session_id": session_id})
        clusters_cursor = db.clusters.find({"session_id": session_id})
        clusters = await clusters_cursor.to_list(length=200)
        clusters_total = len(clusters)
        clusters_addressed = sum(1 for c in clusters if c.get("status") == "addressed")
        flagged = [
            c["label"] for c in clusters
            if c.get("status") in ("flagged", "pending") and c.get("on_topic", True)
        ]
        confusion_spikes = []

    # Gather addressed cluster labels and explanations for the email
    addressed_clusters = []
    clusters_cursor = db.clusters.find({
        "session_id": session_id,
        "status": "addressed",
    })
    async for c in clusters_cursor:
        addressed_clusters.append({
            "label": c.get("label", ""),
            "explanation": c.get("ai_explanation", "") or "",
        })

    # Try Gemini for a student-friendly email
    if gemini_client:
        addressed_text = "\n".join(
            f"- {ac['label']}: {ac['explanation'][:200]}"
            for ac in addressed_clusters
        ) or "No clusters were addressed during this session."

        spike_text = ", ".join(
            f"Slide {s['slide']} ({s['confusion_pct']}%)"
            for s in confusion_spikes
        ) or "None"

        flagged_text = ", ".join(flagged) if flagged else "None"

        prompt = f"""You are a friendly teaching assistant writing a post-session email to students.
Write a warm, encouraging email summary for students who attended this lecture session.

Session: {session_title}
Total questions asked: {total_questions}
Topics addressed by the professor ({clusters_addressed} of {clusters_total}):
{addressed_text}

Confusion areas (slides where students struggled): {spike_text}
Topics flagged for next class: {flagged_text}

The email should:
1. Start with a friendly greeting and acknowledge their participation
2. Summarize the key topics that were covered
3. List the questions that were answered (from addressed clusters)
4. Mention confusion areas that were resolved
5. Suggest what to review before the next class (flagged topics)
6. End with an encouraging note

Keep it concise (under 300 words), warm, and student-friendly. Use simple language.
Do NOT include a subject line — just the body text."""

        try:
            response = gemini_client.models.generate_content(
                model="gemma-3-27b-it",
                contents=prompt,
            )
            if response.text:
                return response.text
        except Exception as e:
            print(f"Gemini student email generation failed: {e}")

    # Fallback: template-based email
    addressed_list = ""
    if addressed_clusters:
        items = [f"  - {ac['label']}" for ac in addressed_clusters]
        addressed_list = "\n".join(items)
    else:
        addressed_list = "  (No topics were formally addressed)"

    flagged_list = ""
    if flagged:
        flagged_list = "\n".join(f"  - {f}" for f in flagged)
    else:
        flagged_list = "  Nothing specific — great job keeping up!"

    return (
        f"Hi there!\n\n"
        f"Thanks for participating in today's session: \"{session_title}\"!\n\n"
        f"Here's a quick recap of what was covered:\n\n"
        f"Questions Answered ({clusters_addressed} of {clusters_total} topics):\n"
        f"{addressed_list}\n\n"
        f"Topics to Review Before Next Class:\n"
        f"{flagged_list}\n\n"
        f"A total of {total_questions} questions were submitted during the session. "
        f"Keep asking questions — that's how you learn best!\n\n"
        f"Good luck with your studies! 📚"
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

    # Attach feedback summary if feedback exists
    try:
        feedback_cursor = db.session_feedback.find({"session_id": sid})
        feedback_docs = await feedback_cursor.to_list(length=1000)
        if feedback_docs:
            fb_total = len(feedback_docs)
            fb_avg = round(sum(f["rating"] for f in feedback_docs) / fb_total, 1)
            report["feedback_summary"] = {
                "average_rating": fb_avg,
                "total_count": fb_total,
            }
    except Exception as e:
        print(f"[Feedback] Failed to attach feedback to report (non-critical): {e}")

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

    # Auto-send email summaries to opted-in students (non-blocking)
    try:
        email_cursor = db.session_emails.find({"session_id": sid})
        email_docs = await email_cursor.to_list(length=500)

        if email_docs:
            emails = [doc["email"] for doc in email_docs]

            summary_text = await _generate_student_email_body(
                session_title=session.get("title", "Untitled Session"),
                report=report,
                db=db,
                session_id=sid,
            )

            # Log the emails that would be sent (actual Resend integration comes later)
            print(f"\n{'='*60}")
            print(f"POST-SESSION EMAIL SUMMARY - {session.get('title', 'Session')}")
            print(f"{'='*60}")
            print(f"Recipients ({len(emails)}): {', '.join(emails)}")
            print(f"{'-'*60}")
            print(summary_text)
            print(f"{'='*60}\n")

            # Delete email records after "sending" (privacy: store only for delivery)
            await db.session_emails.delete_many({"session_id": sid})
            print(f"[Email] Summary sent to {len(emails)} student(s), email records deleted.")
    except Exception as e:
        print(f"[Email] Auto-send summary failed (non-critical): {e}")

    # Call the Insight Report Agent on Agentverse (enrichment)
    # Demonstrates agent integration — agent generates its own narrative analysis
    agent_analysis = None
    try:
        agent_result = await agent_client.call_insight_report(
            session_code=session.get("code", ""),
            title=session.get("title", ""),
        )
        if agent_result:
            agent_analysis = agent_result.get("agent_response")
            # Store agent analysis alongside the report
            await db.reports.update_one(
                {"session_id": sid},
                {"$set": {"agent_analysis": agent_analysis}},
            )
            print(f"[Agentverse] Insight Report Agent responded for session {session.get('code')}")
    except Exception as e:
        print(f"[Agentverse] Insight Report Agent call failed (non-critical): {e}")

    # Return report with string id
    report["id"] = session_id
    report.pop("session_id", None)
    report["generated_at"] = now.isoformat()
    if agent_analysis:
        report["agent_analysis"] = agent_analysis

    return report


@router.get("/{session_id}")
async def get_report(session_id: str):
    """Retrieve a stored report for a session."""
    db = get_db()
    report = await db.reports.find_one({"session_id": ObjectId(session_id)})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    result = {
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
    if "feedback_summary" in report:
        result["feedback_summary"] = report["feedback_summary"]
    return result
