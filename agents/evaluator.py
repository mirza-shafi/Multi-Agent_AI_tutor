"""
evaluator.py — Leo's Evaluator Agent (Powered by Groq Llama-3.3-70B)

Role: Receives the Quiz Master's questions and the student's answers,
      grades each answer, provides constructive per-question feedback,
      calculates a total score (0–3), and determines if re-teaching is needed.
"""

import os
import json
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

from memory.session_store import QuizQuestion, QuestionFeedback, SessionMemory

load_dotenv()

# ── Prompt template ──────────────────────────────────────────────────────────
EVALUATOR_IDENTITY = """\
You are Leo's Evaluator Agent — a fair, constructive, and encouraging tutor.
Your job is to grade a student's quiz answers and provide helpful feedback.

When evaluating, for each question you MUST:
1. State whether the student's answer is CORRECT or INCORRECT.
2. If incorrect, explain what the correct answer is and why.
3. Give one encouraging sentence regardless of the result.

At the end, provide:
- Total Score: X/3
- A brief overall performance comment (1-2 sentences).
- If score is 0 or 1, list the KEY CONCEPTS the student should revisit.

Be kind, specific, and educational. Never be discouraging.
"""


async def run_evaluator(
    session: SessionMemory,
    status_callback=None,
) -> SessionMemory:
    """
    Run the Evaluator agent to grade student answers using Groq Llama-3.3-70B.

    Args:
        session: The shared SessionMemory with quiz_questions and student_answers.
        status_callback: Optional callable(str) for UI status updates.

    Returns:
        Updated SessionMemory with score, question_feedback, needs_reteach.
    """
    if status_callback:
        status_callback("✅ Evaluator Agent is grading your answers...")

    # First: grade locally (deterministic — 100% accurate scoring)
    feedback_list: list[QuestionFeedback] = []
    wrong_topics: list[str] = []
    score = 0

    for i, (q, student_ans) in enumerate(
        zip(session.quiz_questions, session.student_answers)
    ):
        is_correct = student_ans.strip().upper() == q.correct_answer.strip().upper()
        if is_correct:
            score += 1
            fb_text = f"✅ Correct! {q.explanation}"
        else:
            wrong_topics.append(q.question)
            fb_text = (
                f"❌ You answered **{student_ans}**, but the correct answer is "
                f"**{q.correct_answer}**. {q.explanation}"
            )

        feedback_list.append(QuestionFeedback(
            question_index=i,
            student_answer=student_ans,
            correct_answer=q.correct_answer,
            is_correct=is_correct,
            feedback=fb_text,
        ))

    # Then: get rich narrative feedback from Groq Llama-3.3-70B
    api_key = os.getenv("GROQ_API_KEY")
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    questions_context = session.to_quiz_context()
    answers_context = session.to_answers_context()

    prompt = (
        f"Student: {session.student_name}\n"
        f"Topic: {session.topic}\n\n"
        f"=== QUIZ QUESTIONS ===\n{questions_context}\n\n"
        f"=== STUDENT ANSWERS ===\n{answers_context}\n\n"
        f"Please evaluate the student's performance and provide detailed feedback."
    )

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EVALUATOR_IDENTITY},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
    )

    narrative_feedback = response.choices[0].message.content

    # Update session memory
    session.score = score
    session.question_feedback = feedback_list
    session.needs_reteach = score <= 1

    if feedback_list and narrative_feedback:
        feedback_list[-1].feedback += f"\n\n---\n**Overall Feedback from Evaluator:**\n{narrative_feedback}"

    if session.needs_reteach and wrong_topics:
        session.reteach_explanation = (
            "The student needs to revisit these concepts:\n"
            + "\n".join(f"- {t}" for t in wrong_topics)
        )

    if status_callback:
        status_callback(
            f"✅ Evaluator done. Score: {score}/3. "
            f"{'Re-teach triggered! 🔄' if session.needs_reteach else 'Great job! 🎉'}"
        )

    return session
