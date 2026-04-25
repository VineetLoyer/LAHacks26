from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    active = "active"
    ended = "ended"


class ClusterStatus(str, Enum):
    pending = "pending"
    addressed = "addressed"
    flagged = "flagged"
    hidden = "hidden"


class ResponseType(str, Enum):
    explained_now = "explained_now"
    flagged_next_class = "flagged_next_class"
    text_response = "text_response"


# --- Request Models ---

class CreateSessionRequest(BaseModel):
    title: str = ""
    anonymous_mode: bool = True
    confusion_threshold: int = Field(default=60, ge=0, le=100)
    demo_mode: bool = False


class JoinSessionRequest(BaseModel):
    code: str
    display_name: Optional[str] = None


class SubmitCheckinRequest(BaseModel):
    session_id: str
    confusion_rating: int = Field(ge=1, le=5)
    slide: Optional[int] = None


class SubmitQuestionRequest(BaseModel):
    session_id: str
    text: str
    slide: Optional[int] = None


class AddressClusterRequest(BaseModel):
    cluster_id: str
    response_type: ResponseType
    custom_response: Optional[str] = None


class VerifyWorldIdRequest(BaseModel):
    session_code: str
    proof: dict  # IDKit proof payload (merkle_root, nullifier_hash, proof, verification_level)


class OptInEmailRequest(BaseModel):
    email: str
