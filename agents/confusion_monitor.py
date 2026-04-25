"""
Confusion Monitor Agent — Registered on Agentverse
Receives real-time check-in data, calculates confusion index,
and fires spike alerts when threshold is exceeded.
"""
from uagents import Agent, Context, Model
from typing import List, Optional


class CheckinBatch(Model):
    session_id: str
    ratings: List[int]  # list of 1-5 ratings
    slide: Optional[int] = None
    threshold: int = 60  # confusion threshold percentage


class ConfusionResult(Model):
    session_id: str
    slide: Optional[int]
    confusion_index: int  # 0-100 percentage
    avg_rating: float
    total_responses: int
    spike_detected: bool


agent = Agent(
    name="confusion_monitor",
    seed="asksafe-confusion-monitor-seed-2026",
    port=8001,
    endpoint=["http://localhost:8001/submit"],
)

print(f"Confusion Monitor Agent address: {agent.address}")


@agent.on_message(model=CheckinBatch)
async def handle_checkin(ctx: Context, sender: str, msg: CheckinBatch):
    ctx.logger.info(
        f"Received {len(msg.ratings)} check-ins for session {msg.session_id}"
    )

    if not msg.ratings:
        return

    total = len(msg.ratings)
    confused_count = sum(1 for r in msg.ratings if r >= 4)
    confusion_pct = round((confused_count / total) * 100)
    avg_rating = round(sum(msg.ratings) / total, 2)
    spike = confusion_pct >= msg.threshold

    result = ConfusionResult(
        session_id=msg.session_id,
        slide=msg.slide,
        confusion_index=confusion_pct,
        avg_rating=avg_rating,
        total_responses=total,
        spike_detected=spike,
    )

    if spike:
        ctx.logger.warning(
            f"SPIKE DETECTED! Confusion at {confusion_pct}% "
            f"(threshold: {msg.threshold}%) on slide {msg.slide}"
        )

    await ctx.send(sender, result)


if __name__ == "__main__":
    agent.run()
