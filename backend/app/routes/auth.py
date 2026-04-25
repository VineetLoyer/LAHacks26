from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException

from app.config import WORLD_APP_ID, WORLD_ACTION
from app.database import get_db
from app.models import VerifyWorldIdRequest

router = APIRouter()


@router.post("/verify-world-id")
async def verify_world_id(req: VerifyWorldIdRequest):
    db = get_db()

    # Look up the session by code to get session_id
    session = await db.sessions.find_one({"code": req.session_code.upper()})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_id = session["_id"]

    # Extract proof fields from the IDKit payload
    proof = req.proof
    nullifier_hash = proof.get("nullifier_hash")
    merkle_root = proof.get("merkle_root")
    proof_value = proof.get("proof")
    verification_level = proof.get("verification_level")

    if not nullifier_hash:
        raise HTTPException(status_code=400, detail="Missing nullifier_hash in proof")

    # Check for duplicate verification (same nullifier for this session)
    existing = await db.verifications.find_one({
        "session_id": session_id,
        "nullifier_hash": nullifier_hash,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Already verified for this session")

    # If WORLD_APP_ID is not configured, skip external verification (dev mode)
    if not WORLD_APP_ID:
        await db.verifications.insert_one({
            "session_id": session_id,
            "nullifier_hash": nullifier_hash,
            "verified_at": datetime.utcnow(),
        })
        return {"verified": True, "simulated": True}

    # Validate proof against World Developer Portal verify API
    verify_url = f"https://developer.worldcoin.org/api/v2/verify/{WORLD_APP_ID}"
    verify_payload = {
        "merkle_root": merkle_root,
        "nullifier_hash": nullifier_hash,
        "proof": proof_value,
        "action": WORLD_ACTION,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(verify_url, json=verify_payload)
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to reach World verification service")

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="World ID verification failed")

    # Store verification record — only session_id, nullifier_hash, verified_at (no PII)
    await db.verifications.insert_one({
        "session_id": session_id,
        "nullifier_hash": nullifier_hash,
        "verified_at": datetime.utcnow(),
    })

    return {"verified": True}
