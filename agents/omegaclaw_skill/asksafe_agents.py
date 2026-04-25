"""
OmegaClaw skill — AskSafe Agentverse Agent Caller

Calls the AskSafe agents registered on Agentverse to get:
- Confusion analytics (asksafe-confmtr)
- Question clusters (asksafe-qclstr)
- Session reports (asksafe-report)

This module is called from MeTTa via py-call.
"""
import asyncio
import os
import time
import json
from typing import Optional

# Agent addresses on Agentverse
CONFUSION_MONITOR = "agent1qw57pw9a0ky2tlhh0ll7rt7ne6g3sarqxtr7hnlkc05cpen056kty7dwxyt"
QUESTION_CLUSTERING = "agent1q2lm9wvrstlj4vcyf2069s299ag9d8566kll3xp7vwz62dzws3vxy2ejkhd"
INSIGHT_REPORT = "agent1qfpyr023l6jy3t0e7qd4crc8flcdeuytvxgzx4fezej4ked2lfqfjgpz6hy"


async def _ask_agent(agent_address: str, message: str, timeout: int = 90) -> str:
    """Send a chat message to an Agentverse agent and wait for reply."""
    try:
        from uagents import Agent, Context, Model
        from uagents.setup import fund_agent_if_low
        import uuid

        class ChatMessage(Model):
            message: str

        class ChatResponse(Model):
            message: str

        # Create a temporary caller agent
        seed = f"asksafe-omegaclaw-caller-{uuid.uuid4().hex[:8]}"
        caller = Agent(name="asksafe_caller", seed=seed, port=0)

        result_holder = {"response": None, "done": False}

        @caller.on_message(model=ChatResponse)
        async def handle_response(ctx: Context, sender: str, msg: ChatResponse):
            result_holder["response"] = msg.message
            result_holder["done"] = True

        # Send the message
        @caller.on_event("startup")
        async def on_startup(ctx: Context):
            await ctx.send(agent_address, ChatMessage(message=message))

        # Run with timeout
        import threading
        thread = threading.Thread(target=caller.run, daemon=True)
        thread.start()

        start = time.time()
        while not result_holder["done"] and (time.time() - start) < timeout:
            await asyncio.sleep(1)

        if result_holder["response"]:
            return result_holder["response"]
        return f"Timeout: agent did not respond within {timeout}s"

    except Exception as e:
        return f"Error calling agent: {e}"


def check_confusion(session_code: str, timeout: int = 90) -> str:
    """Check confusion levels for a lecture session via the AskSafe Confusion Monitor Agent."""
    try:
        message = f"What's the confusion level for session {session_code}?"
        response = asyncio.run(_ask_agent(CONFUSION_MONITOR, message, int(timeout)))
        return response
    except Exception as e:
        return f"Error: {e}"


def cluster_questions(session_code: str, timeout: int = 90) -> str:
    """Cluster student questions for a lecture session via the AskSafe Question Clustering Agent."""
    try:
        message = f"Cluster the questions for session {session_code}"
        response = asyncio.run(_ask_agent(QUESTION_CLUSTERING, message, int(timeout)))
        return response
    except Exception as e:
        return f"Error: {e}"


def generate_report(session_code: str, timeout: int = 90) -> str:
    """Generate a session report via the AskSafe Insight Report Agent."""
    try:
        message = f"Generate a report for session {session_code}"
        response = asyncio.run(_ask_agent(INSIGHT_REPORT, message, int(timeout)))
        return response
    except Exception as e:
        return f"Error: {e}"
