"""
quiz_master.py — Leo's Quiz Master Agent

Role: Generates 3 multiple-choice quiz questions based on the Explainer's
      lesson content. Uses Pydantic structured output to guarantee a
      machine-readable, consistent quiz format.
"""

import os
import json
from typing import Optional
import pydantic
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.types import TemplatedSystemInstructions
from dotenv import load_dotenv

from memory.session_store import QuizQuestion

load_dotenv()

# ── Structured Output Schema ─────────────────────────────────────────────────

class QuizOption(pydantic.BaseModel):
    A: str
    B: str
    C: str
    D: str


class QuizQuestionSchema(pydantic.BaseModel):
    question: str
    options: QuizOption
    correct_answer: str   # Must be "A", "B", "C", or "D"
    explanation: str      # Why the correct answer is right


class QuizOutput(pydantic.BaseModel):
    questions: list[QuizQuestionSchema]


# ── Prompt template ──────────────────────────────────────────────────────────
QUIZ_MASTER_IDENTITY = """\
You are Leo's Quiz Master Agent — an expert at creating educational assessments.
Your job is to generate exactly 3 multiple-choice quiz questions based on the
lesson content provided. Each question must:

- Test genuine understanding, NOT just memorisation.
- Have exactly 4 options: A, B, C, D.
- Have exactly ONE correct answer (A, B, C, or D).
- Include a clear explanation of why the correct answer is right.
- Be fair and unambiguous.

You MUST return your response as structured JSON data matching the schema.
Do NOT add any text outside the JSON.
"""


async def run_quiz_master(
    topic: str,
    explanation: str,
    status_callback=None,
) -> list[QuizQuestion]:
    """
    Run the Quiz Master agent to generate quiz questions.

    Args:
        topic: The topic being taught.
        explanation: The Explainer's lesson output (handoff input).
        status_callback: Optional callable(str) for UI status updates.

    Returns:
        List of QuizQuestion dataclass objects.
    """
    if status_callback:
        status_callback("❓ Quiz Master Agent is crafting your questions...")

    config = LocalAgentConfig(
        system_instructions=TemplatedSystemInstructions(
            identity=QUIZ_MASTER_IDENTITY
        ),
        response_schema=QuizOutput,
    )

    prompt = (
        f"Based on the following lesson about '{topic}', generate exactly "
        f"3 multiple-choice questions.\n\n"
        f"=== LESSON CONTENT ===\n{explanation}\n=== END OF LESSON ==="
    )

    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        raw = await response.structured_output()

    # Parse structured output into our internal dataclass
    questions: list[QuizQuestion] = []
    if raw and "questions" in raw:
        for q in raw["questions"]:
            opts = q.get("options", {})
            questions.append(QuizQuestion(
                question=q.get("question", ""),
                options={
                    "A": opts.get("A", ""),
                    "B": opts.get("B", ""),
                    "C": opts.get("C", ""),
                    "D": opts.get("D", ""),
                },
                correct_answer=q.get("correct_answer", "A"),
                explanation=q.get("explanation", ""),
            ))

    # Fallback: if structured output failed, try parsing text as JSON
    if not questions:
        try:
            text = await response.text()
            data = json.loads(text)
            for q in data.get("questions", []):
                opts = q.get("options", {})
                questions.append(QuizQuestion(
                    question=q.get("question", ""),
                    options={k: opts.get(k, "") for k in ["A", "B", "C", "D"]},
                    correct_answer=q.get("correct_answer", "A"),
                    explanation=q.get("explanation", ""),
                ))
        except Exception:
            pass  # Coordinator will handle the fallback

    if status_callback:
        status_callback(f"✅ Quiz Master created {len(questions)} questions.")

    return questions
