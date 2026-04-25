"""
Agentverse Agent Client — calls the three AskSafe agents deployed on Agentverse.

Integration points:
1. Confusion Monitor Agent — called after check-in batches for spike detection
2. Question Clustering Agent — called when professor generates clusters
3. Insight Report Agent — called when professor ends session

Each function has a fallback to return None if the agent is unreachable,
so the backend can fall back to direct Gemini calls.
"""
import os
import json
import httpx
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

# Agentverse agent addresses
CONFUSION_MONITOR_ADDRESS = os.getenv(
    "AGENT_CONFUSION_MONITOR",
    "agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt",
)
QUESTION_CLUSTERING_ADDRESS = os.getenv(
    "AGENT_QUESTION_CLUSTERING",
    "agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd",
)
INSIGHT_REPORT_ADDRESS = os.getenv(
    "AGENT_INSIGHT_REPORT",
    "agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy",
)

# Agentverse Almanac API base URL for sending messages to agents
AGENTVERSE_API = "https://agentverse.ai/v1/almanac/agents"

# Timeout for agent calls (seconds)
AGENT_TIMEOUT = 30


async def _send_chat_message(agent_address: str, message: str) -> Optional[str]:
    """Send a chat message to an Agentverse agent and return the response.

    Uses the Agentverse REST API to send a message to the agent's chat endpoint.
    Returns the agent's response text, or None if the call fails.
    """
    try:
        # Use the Agentverse chat API endpoint
        url = f"https://agentverse.ai/v1beta1/engine/chat/completions"

        payload = {
            "model": agent_address,
            "messages": [
                {"role": "user", "content": message}
            ],
        }

        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                # Extract the agent's response text
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            else:
                print(
                    f"[AgentClient] Agent {agent_address} returned "
                    f"status {response.status_code}: {response.text[:200]}"
                )
                return None

    except Exception as e:
        print(f"[AgentClient] Failed to reach agent {agent_address}: {e}")
        return None


async def call_confusion_monitor(
    session_code: str,
    ratings: List[int],
    slide: Optional[int] = None,
    threshold: int = 60,
) -> Optional[dict]:
    """Call the Confusion Monitor Agent with check-in data.

    Returns a dict with confusion analytics, or None if agent is unreachable.
    The agent queries MongoDB directly, so we just need to send the session code.
    """
    message = (
        f"Analyze confusion for session {session_code}. "
        f"Latest batch: {len(ratings)} check-ins on slide {slide or 'unknown'}, "
        f"threshold {threshold}%."
    )

    response = await _send_chat_message(CONFUSION_MONITOR_ADDRESS, message)
    if response:
        return {"agent_response": response, "source": "agentverse"}
    return None


async def call_question_clustering(
    session_code: str,
    title: str,
    question_count: int,
) -> Optional[dict]:
    """Call the Question Clustering Agent to cluster session questions.

    Returns a dict with clustering results, or None if agent is unreachable.
    The agent queries MongoDB directly for questions and slide contexts.
    """
    message = (
        f"Cluster the questions for session {session_code}. "
        f"Lecture title: \"{title}\". "
        f"There are {question_count} questions to analyze."
    )

    response = await _send_chat_message(QUESTION_CLUSTERING_ADDRESS, message)
    if response:
        return {"agent_response": response, "source": "agentverse"}
    return None


async def call_insight_report(
    session_code: str,
    title: str,
) -> Optional[dict]:
    """Call the Insight Report Agent to generate a session report.

    Returns a dict with the report, or None if agent is unreachable.
    The agent queries MongoDB directly for all session data.
    """
    message = (
        f"Generate a comprehensive report for session {session_code}. "
        f"Lecture title: \"{title}\"."
    )

    response = await _send_chat_message(INSIGHT_REPORT_ADDRESS, message)
    if response:
        return {"agent_response": response, "source": "agentverse"}
    return None
