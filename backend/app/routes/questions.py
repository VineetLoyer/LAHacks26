from datetime import datetime
from fastapi import APIRouter
from bson import ObjectId

from app.database import get_db
from app.sio_instance import sio
from app.models import SubmitQuestionRequest

router = APIRouter()


@router.post("/submit")
async def submit_question(req: SubmitQuestionRequest):
    db = get_db()
    question = {
        "session_id": ObjectId(req.session_id),
        "text": req.text,
        "slide": req.slide,
        "cluster_id": None,
        "timestamp": datetime.utcnow(),
    }
    result = await db.questions.insert_one(question)

    # Count total questions for this session and emit event
    total_questions = await db.questions.count_documents(
        {"session_id": ObjectId(req.session_id)}
    )
    session = await db.sessions.find_one({"_id": ObjectId(req.session_id)})
    if session:
        await sio.emit("question_submitted", {
            "total_questions": total_questions,
            "question_id": str(result.inserted_id),
        }, room=session["code"])

    return {"id": str(result.inserted_id), "status": "submitted"}


@router.get("/list/{session_id}")
async def list_questions(session_id: str):
    db = get_db()
    cursor = db.questions.find(
        {"session_id": ObjectId(session_id)}
    ).sort("timestamp", -1)
    questions = await cursor.to_list(length=500)

    return {
        "questions": [
            {
                "id": str(q["_id"]),
                "text": q["text"],
                "slide": q.get("slide"),
                "cluster_id": str(q["cluster_id"]) if q.get("cluster_id") else None,
                "timestamp": q["timestamp"].isoformat(),
            }
            for q in questions
        ]
    }
