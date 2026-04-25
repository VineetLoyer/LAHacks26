"""
Question Clustering Agent — Registered on Agentverse
Receives raw student questions, uses Gemini to semantically cluster them,
and returns ranked clusters with labels.
"""
import os
import json
from uagents import Agent, Context, Model
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


class QuestionItem(Model):
    id: str
    text: str


class ClusterRequest(Model):
    session_id: str
    title: str
    questions: List[QuestionItem]


class ClusterItem(Model):
    label: str
    question_ids: List[str]
    representative_question: str
    on_topic: bool = True


class ClusterResponse(Model):
    session_id: str
    clusters: List[ClusterItem]


agent = Agent(
    name="question_clustering",
    seed="asksafe-question-clustering-seed-2026",
    port=8002,
    endpoint=["http://localhost:8002/submit"],
)

print(f"Question Clustering Agent address: {agent.address}")


@agent.on_message(model=ClusterRequest)
async def handle_clustering(ctx: Context, sender: str, msg: ClusterRequest):
    ctx.logger.info(
        f"Clustering {len(msg.questions)} questions for '{msg.title}'"
    )

    q_list = [{"id": q.id, "text": q.text} for q in msg.questions]

    prompt = f"""You are an educational AI. Given student questions from a lecture
titled "{msg.title}", group them into semantic clusters.

Questions:
{json.dumps(q_list, indent=2)}

Return ONLY valid JSON (no markdown) as an array:
[{{"label":"Short label","question_ids":["id1"],"representative_question":"Best question","on_topic":true}}]"""

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
        cluster_data = json.loads(raw)
    except Exception as e:
        ctx.logger.error(f"Gemini clustering failed: {e}")
        cluster_data = [
            {
                "label": "All Questions",
                "question_ids": [q.id for q in msg.questions],
                "representative_question": msg.questions[0].text
                if msg.questions
                else "",
                "on_topic": True,
            }
        ]

    clusters = [
        ClusterItem(
            label=c["label"],
            question_ids=c["question_ids"],
            representative_question=c.get("representative_question", ""),
            on_topic=c.get("on_topic", True),
        )
        for c in cluster_data
    ]

    await ctx.send(sender, ClusterResponse(session_id=msg.session_id, clusters=clusters))


if __name__ == "__main__":
    agent.run()
