"""
explainer.py — Leo's Explainer Agent

Role: Teaches a topic clearly using a structured explanation format.
      Can be called twice: once for initial teaching, once for re-teaching
      weak concepts identified by the Evaluator.
"""

import os
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.types import TemplatedSystemInstructions
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
    Run the Explainer agent.

    Args:
        topic: The subject to teach (e.g. "Python decorators").
        reteach_focus: Optional string describing weak areas to focus on
                       during a re-teach pass.
        status_callback: Optional callable(str) for UI status updates.

    Returns:
        The full explanation as a string.
    """
    if status_callback:
        status_callback("📚 Explainer Agent is preparing your lesson...")

    config = LocalAgentConfig(
        system_instructions=TemplatedSystemInstructions(
            identity=EXPLAINER_IDENTITY
        ),
    )

    if reteach_focus:
        prompt = (
            f"The student has struggled with parts of '{topic}'. "
            f"Re-teach the topic with special focus on these weak areas:\n"
            f"{reteach_focus}\n\n"
            f"Make sure to address each weak point clearly."
        )
    else:
        prompt = f"Please teach me about: **{topic}**"

    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        explanation = await response.text()

    if status_callback:
        status_callback("✅ Explainer Agent finished.")

    return explanation
