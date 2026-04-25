"""Socket.IO event handlers for real-time communication."""
from app.sio_instance import sio
from app.database import get_db
from bson import ObjectId

# Track connected users per session: {session_code: set(sid)}
session_rooms: dict[str, set] = {}


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    db = get_db()
    # Remove from all rooms and update MongoDB counts
    for code, members in session_rooms.items():
        if sid in members:
            members.discard(sid)
            live_count = len(members)
            # Update MongoDB and compute emitted count
            if db is not None:
                session = await db.sessions.find_one({"code": code})
                if session:
                    demo_count = session.get("demo_participant_count", 0)
                    is_demo = session.get("demo_mode", False)
                    # For demo sessions, never decrement below demo_participant_count
                    stored_count = max(demo_count, live_count) if is_demo else live_count
                    await db.sessions.update_one(
                        {"_id": session["_id"]},
                        {"$set": {"live_participant_count": live_count}},
                    )
                    await sio.emit("participant_count", {"count": stored_count}, room=code)
                else:
                    await sio.emit("participant_count", {"count": live_count}, room=code)


@sio.event
async def join_room(sid, data):
    """Student or professor joins a session room."""
    code = data.get("code")
    role = data.get("role", "student")  # "student" or "professor"
    if code:
        await sio.enter_room(sid, code)
        session_rooms.setdefault(code, set()).add(sid)
        live_count = len(session_rooms[code])

        db = get_db()
        emitted_count = live_count
        if db is not None:
            session = await db.sessions.find_one({"code": code})
            if session:
                demo_count = session.get("demo_participant_count", 0)
                is_demo = session.get("demo_mode", False)
                # Persist live_participant_count in MongoDB
                await db.sessions.update_one(
                    {"_id": session["_id"]},
                    {"$set": {"live_participant_count": live_count}},
                )
                # For demo sessions, emit max(demo_participant_count, live_participant_count)
                emitted_count = max(demo_count, live_count) if is_demo else live_count

        await sio.emit("participant_count", {"count": emitted_count}, room=code)
        print(f"{role} {sid} joined room {code} ({emitted_count} participants)")


@sio.event
async def leave_room(sid, data):
    """Leave a session room."""
    code = data.get("code")
    if code:
        await sio.leave_room(sid, code)
        if code in session_rooms:
            session_rooms[code].discard(sid)
            live_count = len(session_rooms[code])

            db = get_db()
            emitted_count = live_count
            if db is not None:
                session = await db.sessions.find_one({"code": code})
                if session:
                    demo_count = session.get("demo_participant_count", 0)
                    is_demo = session.get("demo_mode", False)
                    await db.sessions.update_one(
                        {"_id": session["_id"]},
                        {"$set": {"live_participant_count": live_count}},
                    )
                    emitted_count = max(demo_count, live_count) if is_demo else live_count

            await sio.emit("participant_count", {"count": emitted_count}, room=code)


@sio.event
async def trigger_checkin(sid, data):
    """Professor triggers a confusion check-in for all students."""
    code = data.get("code")
    slide = data.get("slide", 1)
    if code:
        await sio.emit(
            "checkin_requested",
            {"slide": slide},
            room=code,
            skip_sid=sid,
        )
        print(f"Check-in triggered for room {code}, slide {slide}")
