import random
import re
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from bson import ObjectId

from app.database import get_db
from app.sio_instance import sio
from app.models import CreateSessionRequest, SessionStatus, ClusterStatus, OptInEmailRequest
from app.file_parser import parse_pdf, parse_docx, parse_pptx

router = APIRouter()


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def seed_demo_data(session_id: str, db):
    """Populate a session with realistic demo data for a Data Mining - Stream Processing lecture."""
    sid = ObjectId(session_id)

    # --- Slide Contexts (12 slides) ---
    slide_contexts = [
        {"slide_number": 1, "text_content": "Introduction to Data Streams - What is a data stream? Continuous, unbounded sequence of data elements. Examples: sensor data, web clicks, financial transactions."},
        {"slide_number": 2, "text_content": "Stream Processing Model - Data arrives continuously at high speed. Cannot store everything. Must process in one pass. Limited memory constraint."},
        {"slide_number": 3, "text_content": "Sampling from a Stream - How to get a representative sample? Reservoir sampling algorithm. Maintaining a fixed-size sample as new elements arrive."},
        {"slide_number": 4, "text_content": "Filtering a Stream - Bloom Filters. Probabilistic data structure for set membership. False positives possible, false negatives impossible."},
        {"slide_number": 5, "text_content": "Counting Distinct Elements - Flajolet-Martin algorithm. Using hash functions to estimate cardinality. Bit pattern analysis for counting."},
        {"slide_number": 6, "text_content": "Sliding Windows - Processing only recent data. Fixed-size vs time-based windows. Maintaining statistics over a moving window."},
        {"slide_number": 7, "text_content": "DGIM Algorithm - Counting 1s in a sliding window. Exponential histogram approach. Buckets with timestamps and sizes."},
        {"slide_number": 8, "text_content": "DGIM Algorithm Details - Bucket merging rules. At most 2 buckets of each size. Error bound of 50% for oldest bucket."},
        {"slide_number": 9, "text_content": "Decaying Windows - Exponentially decaying weights. Recent data matters more. Smooth transition vs hard cutoff of sliding windows."},
        {"slide_number": 10, "text_content": "Counting Items - Frequent items in a stream. Misra-Gries algorithm. Space-saving algorithm for heavy hitters."},
        {"slide_number": 11, "text_content": "Moment Estimation - Computing moments of a stream. AMS algorithm. Second moment estimation using random variables."},
        {"slide_number": 12, "text_content": "Summary and Applications - Real-world stream processing: network monitoring, social media analytics, IoT sensor data, financial fraud detection."},
    ]

    await db.sessions.update_one(
        {"_id": sid},
        {"$set": {"slide_contexts": slide_contexts}},
    )

    # --- Check-ins (40-45 records) ---
    base_time = datetime.utcnow() - timedelta(minutes=60)
    checkins = []

    def _make_checkins(slide, count, low, high):
        nonlocal base_time
        for _ in range(count):
            base_time += timedelta(seconds=random.randint(15, 45))
            checkins.append({
                "session_id": sid,
                "confusion_rating": random.randint(low, high),
                "slide": slide,
                "timestamp": base_time,
            })

    # Slides 1-3: low confusion (ratings 1-2, some 3) ~10 check-ins
    for s in [1, 2, 3]:
        cnt = random.randint(3, 4)
        _make_checkins(s, cnt, 1, 3)

    # Slides 4-5: moderate confusion (ratings 2-4) ~8 check-ins
    for s in [4, 5]:
        cnt = random.randint(3, 5)
        _make_checkins(s, cnt, 2, 4)

    # Slides 6-7: high confusion spike (ratings 4-5 dominant) ~12 check-ins
    for s in [6, 7]:
        cnt = random.randint(5, 7)
        _make_checkins(s, cnt, 4, 5)

    # Slides 8-9: still elevated (ratings 3-5) ~8 check-ins
    for s in [8, 9]:
        cnt = random.randint(3, 5)
        _make_checkins(s, cnt, 3, 5)

    # Slides 10-12: recovery (ratings 1-3) ~7 check-ins
    for s in [10, 11, 12]:
        cnt = random.randint(2, 3)
        _make_checkins(s, cnt, 1, 3)

    if checkins:
        await db.checkins.insert_many(checkins)

    # --- Questions (22-25 tagged to slides) ---
    base_time = datetime.utcnow() - timedelta(minutes=55)
    question_groups = {
        3: [
            "How does reservoir sampling guarantee equal probability?",
            "What if the stream is infinite - when do we stop sampling?",
        ],
        4: [
            "Why can't Bloom filters have false negatives?",
            "How do you choose the number of hash functions?",
        ],
        5: [
            "Why does Flajolet-Martin use trailing zeros?",
            "Can we get exact distinct counts from a stream?",
        ],
        6: [
            "What's the difference between count-based and time-based windows?",
            "How much memory does a sliding window need?",
        ],
        7: [
            "I don't understand how DGIM buckets work",
            "Why are there at most 2 buckets of each size?",
            "Can someone explain the bucket merging step?",
            "What's the error bound of DGIM and why?",
        ],
        8: [
            "How does the 50% error bound relate to the oldest bucket?",
            "When exactly do buckets get merged?",
        ],
        9: [
            "Why would you use decaying windows instead of sliding windows?",
            "How do you pick the decay rate?",
        ],
        10: [
            "What's the difference between Misra-Gries and Space-Saving?",
            "How do you know if an item is truly frequent?",
        ],
        11: [
            "What is a moment of a stream intuitively?",
            "Why is the second moment useful?",
        ],
    }

    off_topic = [
        "Will this be on the final exam?",
        "Can we get the slides posted?",
        "What time is office hours?",
    ]

    # Insert on-topic questions and track IDs by slide
    question_ids_by_slide: dict[int, list[ObjectId]] = {}
    all_question_docs = []

    for slide, texts in question_groups.items():
        question_ids_by_slide[slide] = []
        for text in texts:
            base_time += timedelta(seconds=random.randint(20, 60))
            doc = {
                "session_id": sid,
                "text": text,
                "slide": slide,
                "cluster_id": None,
                "timestamp": base_time,
            }
            all_question_docs.append((slide, doc))

    # Insert off-topic questions (no specific slide, use None)
    off_topic_docs = []
    for text in off_topic:
        base_time += timedelta(seconds=random.randint(20, 60))
        doc = {
            "session_id": sid,
            "text": text,
            "slide": None,
            "cluster_id": None,
            "timestamp": base_time,
        }
        off_topic_docs.append(doc)

    # Bulk insert all questions and collect IDs
    for slide, doc in all_question_docs:
        result = await db.questions.insert_one(doc)
        question_ids_by_slide.setdefault(slide, []).append(result.inserted_id)

    off_topic_ids = []
    for doc in off_topic_docs:
        result = await db.questions.insert_one(doc)
        off_topic_ids.append(result.inserted_id)

    # --- Set demo_participant_count ---
    demo_count = random.randint(38, 47)
    await db.sessions.update_one(
        {"_id": sid},
        {"$set": {"demo_participant_count": demo_count}},
    )

    # --- Pre-insert 5 cluster documents ---
    clusters_data = [
        {
            "label": "DGIM Algorithm Mechanics",
            "slides": [7, 8],
            "representative": "I don't understand how DGIM buckets work",
            "upvotes": 14,
            "on_topic": True,
        },
        {
            "label": "Sliding Window Memory & Tradeoffs",
            "slides": [6],
            "representative": "How much memory does a sliding window need?",
            "upvotes": 9,
            "on_topic": True,
        },
        {
            "label": "Bloom Filter False Positive Behavior",
            "slides": [4],
            "representative": "Why can't Bloom filters have false negatives?",
            "upvotes": 7,
            "on_topic": True,
        },
        {
            "label": "Sampling Guarantees in Infinite Streams",
            "slides": [3],
            "representative": "How does reservoir sampling guarantee equal probability?",
            "upvotes": 5,
            "on_topic": True,
        },
        {
            "label": "Course Logistics",
            "slides": [],  # off-topic
            "representative": "Will this be on the final exam?",
            "upvotes": 2,
            "on_topic": False,
        },
    ]

    for cdata in clusters_data:
        # Gather question_ids for this cluster
        c_question_ids = []
        if cdata["on_topic"]:
            for s in cdata["slides"]:
                c_question_ids.extend(question_ids_by_slide.get(s, []))
        else:
            c_question_ids = off_topic_ids

        cluster_doc = {
            "session_id": sid,
            "label": cdata["label"],
            "question_ids": c_question_ids,
            "representative_question": cdata["representative"],
            "upvotes": cdata["upvotes"],
            "status": ClusterStatus.pending,
            "on_topic": cdata["on_topic"],
            "ai_explanation": None,
            "professor_response": None,
            "response_type": None,
        }
        cluster_result = await db.clusters.insert_one(cluster_doc)

        # Update questions with their cluster_id
        if c_question_ids:
            await db.questions.update_many(
                {"_id": {"$in": c_question_ids}},
                {"$set": {"cluster_id": cluster_result.inserted_id}},
            )

    return {"demo_participant_count": demo_count, "checkins": len(checkins)}


@router.post("/create")
async def create_session(req: CreateSessionRequest):
    db = get_db()
    code = generate_code()
    # Ensure unique code
    while await db.sessions.find_one({"code": code}):
        code = generate_code()

    title = req.title
    if req.demo_mode and not req.title:
        title = "Data Mining - Stream Processing"

    session = {
        "code": code,
        "title": title,
        "anonymous_mode": req.anonymous_mode,
        "confusion_threshold": req.confusion_threshold,
        "current_slide": 1,
        "status": SessionStatus.active,
        "demo_mode": req.demo_mode,
        "demo_participant_count": 0,
        "live_participant_count": 0,
        "created_at": datetime.utcnow(),
        "ended_at": None,
    }
    result = await db.sessions.insert_one(session)
    session_id = str(result.inserted_id)

    # Auto-seed demo data when demo_mode is true
    if req.demo_mode:
        await seed_demo_data(session_id, db)

    return {
        "id": session_id,
        "code": code,
        "title": title,
    }


@router.post("/create-with-file")
async def create_session_with_file(
    title: str = Form(""),
    anonymous_mode: str = Form("true"),
    confusion_threshold: int = Form(60),
    demo_mode: str = Form("false"),
    file: Optional[UploadFile] = File(None),
):
    """Create a session with optional lecture material file upload (multipart form)."""
    db = get_db()
    code = generate_code()
    while await db.sessions.find_one({"code": code}):
        code = generate_code()

    # Parse string booleans from form fields
    is_anonymous = anonymous_mode.lower() in ("true", "1", "yes")
    is_demo = demo_mode.lower() in ("true", "1", "yes")

    if is_demo and not title:
        title = "Data Mining - Stream Processing"

    # Parse uploaded file if present
    slide_contexts = []
    lecture_material_filename = None

    if file and file.filename:
        file_bytes = await file.read()
        if len(file_bytes) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File exceeds 50MB limit")

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        lecture_material_filename = file.filename

        if ext == "pdf":
            slide_contexts = parse_pdf(file_bytes)
        elif ext == "docx":
            slide_contexts = parse_docx(file_bytes)
        elif ext == "pptx":
            slide_contexts = parse_pptx(file_bytes)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload PDF, DOCX, or PPTX.",
            )

    session = {
        "code": code,
        "title": title,
        "anonymous_mode": is_anonymous,
        "confusion_threshold": confusion_threshold,
        "current_slide": 1,
        "status": SessionStatus.active,
        "demo_mode": is_demo,
        "demo_participant_count": 0,
        "live_participant_count": 0,
        "slide_contexts": slide_contexts,
        "lecture_material_filename": lecture_material_filename,
        "created_at": datetime.utcnow(),
        "ended_at": None,
    }
    result = await db.sessions.insert_one(session)
    session_id = str(result.inserted_id)

    # Auto-seed demo data when demo_mode is true
    if is_demo:
        await seed_demo_data(session_id, db)

    return {
        "id": session_id,
        "code": code,
        "title": title,
        "slides_extracted": len(slide_contexts),
    }


@router.get("/{session_id}/slides")
async def get_slide_contexts(session_id: str):
    """Return extracted slide contexts for a session."""
    db = get_db()
    session = await db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"slides": session.get("slide_contexts", [])}


@router.get("/join/{code}")
async def join_session(code: str):
    db = get_db()
    session = await db.sessions.find_one({"code": code.upper()})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == SessionStatus.ended:
        raise HTTPException(status_code=400, detail="Session has ended")
    return {
        "id": str(session["_id"]),
        "title": session["title"],
        "anonymous_mode": session["anonymous_mode"],
        "current_slide": session["current_slide"],
        "demo_mode": session.get("demo_mode", False),
        "confusion_threshold": session.get("confusion_threshold", 60),
    }


@router.post("/{session_id}/seed-demo")
async def seed_demo(session_id: str):
    """Populate a session with realistic demo data."""
    db = get_db()
    session = await db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await seed_demo_data(session_id, db)
    return {"status": "seeded", **result}


@router.get("/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Return all dashboard stats in a single API call."""
    db = get_db()
    sid = ObjectId(session_id)

    session = await db.sessions.find_one({"_id": sid})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Compute current confusion index from checkins
    pipeline = [
        {"$match": {"session_id": sid}},
        {"$group": {
            "_id": None,
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
        confusion_index = round((s["confused_count"] / s["total"]) * 100)
    else:
        confusion_index = 0

    # Total questions
    total_questions = await db.questions.count_documents({"session_id": sid})

    # Cluster count
    cluster_count = await db.clusters.count_documents({"session_id": sid})

    # Participant count
    demo_count = session.get("demo_participant_count", 0)
    live_count = session.get("live_participant_count", 0)
    participant_count = max(demo_count, live_count)

    return {
        "confusion_index": confusion_index,
        "total_questions": total_questions,
        "participant_count": participant_count,
        "demo_mode": session.get("demo_mode", False),
        "confusion_threshold": session.get("confusion_threshold", 60),
        "cluster_count": cluster_count,
    }


@router.post("/{session_id}/end")
async def end_session(session_id: str):
    """End a session and emit session_ended event."""
    db = get_db()
    sid = ObjectId(session_id)

    session = await db.sessions.find_one({"_id": sid})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.utcnow()
    await db.sessions.update_one(
        {"_id": sid},
        {"$set": {"status": SessionStatus.ended, "ended_at": now}},
    )

    # Emit session_ended event
    if session.get("code"):
        await sio.emit("session_ended", {
            "session_id": session_id,
            "report_available": False,
        }, room=session["code"])

    return {"status": "ended"}


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@router.post("/{session_id}/opt-in-email")
async def opt_in_email(session_id: str, req: OptInEmailRequest):
    """Store a student's email for post-session summary delivery."""
    db = get_db()
    sid = ObjectId(session_id)

    # Validate session exists
    session = await db.sessions.find_one({"_id": sid})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate email format
    if not EMAIL_REGEX.match(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Upsert so the same email for the same session doesn't create duplicates
    await db.session_emails.update_one(
        {"session_id": sid, "email": req.email},
        {"$set": {
            "session_id": sid,
            "email": req.email,
            "opted_in_at": datetime.utcnow(),
        }},
        upsert=True,
    )

    return {"status": "opted_in", "email": req.email}


@router.post("/{session_id}/send-summary")
async def send_summary(session_id: str):
    """Generate and send (log) a student-friendly email summary to opted-in students."""
    db = get_db()
    sid = ObjectId(session_id)

    session = await db.sessions.find_one({"_id": sid})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch opted-in emails
    email_cursor = db.session_emails.find({"session_id": sid})
    email_docs = await email_cursor.to_list(length=500)

    if not email_docs:
        return {"emails_sent": 0, "summary": "", "message": "No opted-in students"}

    emails = [doc["email"] for doc in email_docs]

    # Try to fetch existing report for the session
    report = await db.reports.find_one({"session_id": sid})

    # Generate student-friendly email body
    from app.routes.reports import _generate_student_email_body

    summary_text = await _generate_student_email_body(
        session_title=session.get("title", "Untitled Session"),
        report=report,
        db=db,
        session_id=sid,
    )

    # Log the emails that would be sent (hackathon demo — actual SMTP is a TODO)
    print(f"\n{'='*60}")
    print(f"POST-SESSION EMAIL SUMMARY - {session.get('title', 'Session')}")
    print(f"{'='*60}")
    print(f"Recipients ({len(emails)}): {', '.join(emails)}")
    print(f"{'-'*60}")
    print(summary_text)
    print(f"{'='*60}\n")

    # Delete email records after "sending" (privacy: store only for delivery)
    await db.session_emails.delete_many({"session_id": sid})

    return {
        "emails_sent": len(emails),
        "summary": summary_text,
        "message": f"Summary logged for {len(emails)} student(s). Email records deleted.",
    }
