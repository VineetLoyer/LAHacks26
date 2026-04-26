"""
OmegaClaw skill — AskSafe Agentverse Agent Caller

Uses send_sync_message to call AskSafe agents with synchronous Model handlers.
This follows the OmegaClaw integration guide (Section 4) for proper agent communication.

The agents expose both:
- Chat Protocol (for ASI:One conversational chat)
- Synchronous AskSafeRequest/AskSafeResponse Models (for OmegaClaw skills)
"""
import asyncio
import os

from uagents import Model
from uagents.query import send_sync_message

# Agent addresses on Agentverse
CONFUSION_MONITOR = os.environ.get(
    "ASKSAFE_CONFUSION_AGENT",
    "agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt",
)
QUESTION_CLUSTERING = os.environ.get(
    "ASKSAFE_CLUSTERING_AGENT",
    "agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd",
)
INSIGHT_REPORT = os.environ.get(
    "ASKSAFE_REPORT_AGENT",
    "agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy",
)


# Must match the Model defined in the Agentverse agents
class AskSafeRequest(Model):
    session_code: str


async def _ask_agent(destination: str, session_code: str, timeout: int = 60) -> str:
    """Send a sync message to an AskSafe agent and return the response."""
    try:
        request = AskSafeRequest(session_code=session_code)
        envelope_or_status = await send_sync_message(
            destination=destination,
            message=request,
            timeout=timeout,
        )
        # Parse the response — send_sync_message returns the response Model as a string
        result = str(envelope_or_status)
        # Try to extract the 'response' field if it's JSON
        try:
            import json
            data = json.loads(result)
            if isinstance(data, dict) and "response" in data:
                return data["response"]
        except (json.JSONDecodeError, TypeError):
            pass
        return result
    except Exception as e:
        return f"Error calling agent: {e}"


def check_confusion(session_code: str, timeout: int = 60) -> str:
    """Check confusion levels for a session via the AskSafe Confusion Monitor Agent."""
    try:
        return asyncio.run(_ask_agent(CONFUSION_MONITOR, session_code, int(timeout)))
    except Exception as e:
        return f"Error: {e}"


def cluster_questions(session_code: str, timeout: int = 60) -> str:
    """Cluster questions for a session via the AskSafe Question Clustering Agent."""
    try:
        return asyncio.run(_ask_agent(QUESTION_CLUSTERING, session_code, int(timeout)))
    except Exception as e:
        return f"Error: {e}"


def generate_report(session_code: str, timeout: int = 60) -> str:
    """Generate a session report via the AskSafe Insight Report Agent."""
    try:
        return asyncio.run(_ask_agent(INSIGHT_REPORT, session_code, int(timeout)))
    except Exception as e:
        return f"Error: {e}"
