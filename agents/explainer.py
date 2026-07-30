"""
explainer.py — Leo's Explainer Agent (Powered by Groq Llama-3.3-70B)

Role: Teaches a topic clearly using a structured explanation format.
      Can be called twice: once for initial teaching, once for re-teaching
      weak concepts identified by the Evaluator.
"""

import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Prompt template ──────────────────────────────────────────────────────────
EXPLAINER_IDENTITY = """\
You are Leo's Explainer Agent — a world-class educator who makes complex
topics easy to understand. Your job is to teach concepts clearly and
engagingly to a student.

When teaching, always structure your response EXACTLY as follows:
1. 📖 **Overview** — A 2-3 sentence big-picture introduction.
2. 🔑 **Key Concepts** — 3–5 bullet points covering the essential ideas.
3. 🌍 **Real-World Example** — One concrete, relatable example.
4. ✅ **Quick Summary** — One sentence recap of what the student should remember.

Keep language accessible. Avoid jargon unless you define it immediately.
Be enthusiastic and encouraging.
"""


async def run_explainer(
    topic: str,
    reteach_focus: str = "",
    status_callback=None,
) -> str:
    """
    Run the Explainer agent using Groq Llama-3.3-70B.

    Args:
        topic: The subject to teach (e.g. "Python decorators").
        reteach_focus: Optional string describing weak areas to focus on during re-teach.
        status_callback: Optional callable(str) for UI status updates.

    Returns:
        The full explanation as a string.
    """
    if status_callback:
        status_callback("📚 Explainer Agent is preparing your lesson...")

    api_key = os.getenv("GROQ_API_KEY")
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    if reteach_focus:
        prompt = (
            f"The student has struggled with parts of '{topic}'. "
            f"Re-teach the topic with special focus on these weak areas:\n"
            f"{reteach_focus}\n\n"
            f"Make sure to address each weak point clearly."
        )
    else:
        prompt = f"Please teach me about: **{topic}**"

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EXPLAINER_IDENTITY},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
    )

    explanation = response.choices[0].message.content

    if status_callback:
        status_callback("✅ Explainer Agent finished.")

    return explanation
