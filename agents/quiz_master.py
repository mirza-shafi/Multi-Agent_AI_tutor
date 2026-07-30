"""
quiz_master.py — Leo's Quiz Master Agent (Powered by Groq Llama-3.3-70B)

Role: Generates 3 multiple-choice quiz questions based on the Explainer's
      lesson content using Groq Llama-3.3-70B.
"""

import os
import json
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

from memory.session_store import QuizQuestion

load_dotenv()

# ── Prompt template ──────────────────────────────────────────────────────────
QUIZ_MASTER_IDENTITY = """\
You are Leo's Quiz Master Agent — an expert at creating educational assessments.
Your job is to generate exactly 3 multiple-choice quiz questions based on the
lesson content provided.

You MUST respond ONLY with a valid JSON object with the following structure:
{
  "questions": [
    {
      "question": "Question text here?",
      "options": {
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text"
      },
      "correct_answer": "A",
      "explanation": "Why answer A is correct"
    }
  ]
}

Rules:
- Generate exactly 3 questions.
- Each question MUST have options A, B, C, D.
- correct_answer MUST be "A", "B", "C", or "D".
- Output raw valid JSON ONLY. No extra markdown, no code blocks, no text outside JSON.
"""


async def run_quiz_master(
    topic: str,
    explanation: str,
    status_callback=None,
) -> list[QuizQuestion]:
    """
    Run the Quiz Master agent to generate quiz questions using Groq Llama-3.3-70B.

    Args:
        topic: The topic being taught.
        explanation: The Explainer's lesson output (handoff input).
        status_callback: Optional callable(str) for UI status updates.

    Returns:
        List of QuizQuestion dataclass objects.
    """
    if status_callback:
        status_callback("❓ Quiz Master Agent is crafting your questions...")

    api_key = os.getenv("GROQ_API_KEY")
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    prompt = (
        f"Based on the following lesson about '{topic}', generate exactly "
        f"3 multiple-choice questions in JSON format.\n\n"
        f"=== LESSON CONTENT ===\n{explanation}\n=== END OF LESSON ==="
    )

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": QUIZ_MASTER_IDENTITY},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    raw_text = response.choices[0].message.content
    questions: list[QuizQuestion] = []

    try:
        data = json.loads(raw_text)
        q_list = data.get("questions", [])
        for q in q_list:
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
    except Exception as e:
        print(f"Error parsing quiz JSON: {e}")

    # Fallback if parsing failed
    if not questions:
        questions = [
            QuizQuestion(
                question=f"What is a core concept of {topic}?",
                options={
                    "A": "Code organization and extension",
                    "B": "Memory allocation",
                    "C": "Hardware control",
                    "D": "Network routing"
                },
                correct_answer="A",
                explanation=f"{topic} helps organize and extend behavior cleanly.",
            )
        ]

    if status_callback:
        status_callback(f"✅ Quiz Master created {len(questions)} questions.")

    return questions
