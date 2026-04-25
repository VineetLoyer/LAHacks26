from datetime import datetime
from fastapi import APIRouter
from bson import ObjectId

from app.database import get_db
from app.sio_instance import sio
from app.models import SubmitCheckinRequest
from app import agent_client

router = APIRouter()


@router.post("/submit")
async def submit_checkin(req: SubmitCheckinRequest):
    db = get_db()
    checkin = {
        "session_id": ObjectId(req.session_id),
        "confusion_rating": req.confusion_rating,
        "slide": req.slide,
        "timestamp": datetime.utcnow(),
    }
    await db.checkins.insert_one(checkin)

    # Calculate current confusion index for this session
    pipeline = [
        {"$match": {"session_id": ObjectId(req.session_id)}},
        {"$group": {
            "_id": None,
            "avg_confusion": {"$avg": "$confusion_rating"},
            "total": {"$sum": 1},
            "confused_count": {
                "$sum": {"$cond": [{"$gte": ["$confusion_rating", 4]}, 1, 0]}
            },
        }},
    ]
    cursor = db.checkins.aggregate(pipeline)
    stats = await cursor.to_list(length=1)

    if stats:
        s = stats[0]
        confusion_pct = round((s["confused_count"] / s["total"]) * 100)
    else:
        confusion_pct = 0

    total_checkins = stats[0]["total"] if stats else 0

    # Look up session code and emit confusion_update to the session room
    session = await db.sessions.find_one({"_id": ObjectId(req.session_id)})
    if session:
        await sio.emit("confusion_update", {
            "confusion_index": confusion_pct,
            "total_checkins": total_checkins,
            "slide": req.slide,
        }, room=session["code"])

        # Call the Confusion Monitor Agent on Agentverse (async, non-blocking)
        # Demonstrates agent integration — agent does correlation analysis
        try:
            # Gather recent ratings for this slide to send as a batch
            recent_cursor = db.checkins.find(
                {"session_id": ObjectId(req.session_id), "slide": req.slide}
            ).sort("timestamp", -1).limit(20)
            recent = await recent_cursor.to_list(length=20)
            ratings = [c.get("confusion_rating", 3) for c in recent]

            agent_result = await agent_client.call_confusion_monitor(
                session_code=session.get("code", ""),
                ratings=ratings,
                slide=req.slide,
                threshold=session.get("confusion_threshold", 60),
            )
            if agent_result:
                print(f"[Agentverse] Confusion Monitor Agent responded for session {session.get('code')}")
        except Exception as e:
            print(f"[Agentverse] Confusion Monitor Agent call failed (non-critical): {e}")

    return {
        "confusion_index": confusion_pct,
        "total_checkins": total_checkins,
    }


@router.get("/stats/{session_id}")
async def get_confusion_stats(session_id: str):
    db = get_db()
    pipeline = [
        {"$match": {"session_id": ObjectId(session_id)}},
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

    return {"timeline": timeline}
