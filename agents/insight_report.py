"""
Insight Report Agent — Registered on Agentverse
Generates post-session analytics: confusion timeline, participation stats,
flagged items for next lecture, and student email summary.
"""
import os
import json
from uagents import Agent, Context, Model
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


class SlideStats(Model):
    slide: int
    confusion_pct: int
    responses: int


class ClusterSummary(Model):
    label: str
    question_count: int
    status: str
    upvotes: int


class ReportRequest(Model):
    session_id: str
    title: str
    total_participants: int
    timeline: List[SlideStats]
    clusters: List[ClusterSummary]


class ReportResponse(Model):
    session_id: str
    summary: str
    confusion_spikes: List[str]
    flagged_for_next: List[str]
    student_email_body: str


agent = Agent(
    name="insight_report",
    seed="asksafe-insight-report-seed-2026",
    port=8003,
    endpoint=["http://localhost:8003/submit"],
)

print(f"Insight Report Agent address: {agent.address}")


@agent.on_message(model=ReportRequest)
async def handle_report(ctx: Context, sender: str, msg: ReportRequest):
    ctx.logger.info(f"Generating report for session '{msg.title}'")

    timeline_str = json.dumps(
        [{"slide": t.slide, "confusion": t.confusion_pct} for t in msg.timeline]
    )
    clusters_str = json.dumps(
        [
            {"label": c.label, "questions": c.question_count, "status": c.status}
            for c in msg.clusters
        ]
    )

    prompt = f"""You are an educational analytics AI. Generate a post-lecture report.

Lecture: "{msg.title}"
Participants: {msg.total_participants}
Confusion Timeline (per slide): {timeline_str}
Question Clusters: {clusters_str}

Return ONLY valid JSON (no markdown fences):
{{
  "summary": "2-3 sentence overview of the session",
  "confusion_spikes": ["Slide X: description of spike"],
  "flagged_for_next": ["Topics that need revisiting next class"],
  "student_email_body": "Friendly email summary for students covering key topics discussed and questions answered"
}}"""

    try:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY", "")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(raw)
    except Exception as e:
        ctx.logger.error(f"Report generation failed: {e}")
        data = {
            "summary": f"Session '{msg.title}' had {msg.total_participants} participants.",
            "confusion_spikes": [],
            "flagged_for_next": [],
            "student_email_body": f"Thank you for attending {msg.title}!",
        }

    result = ReportResponse(
        session_id=msg.session_id,
        summary=data.get("summary", ""),
        confusion_spikes=data.get("confusion_spikes", []),
        flagged_for_next=data.get("flagged_for_next", []),
        student_email_body=data.get("student_email_body", ""),
    )

    await ctx.send(sender, result)


if __name__ == "__main__":
    agent.run()
