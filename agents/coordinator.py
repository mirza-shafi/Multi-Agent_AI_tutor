"""
coordinator.py — Leo's Coordinator Agent (Powered by Groq Llama-3.3-70B)

Role: Master orchestrator of the multi-agent tutoring pipeline.
      - Receives the student's topic request
      - Validates and clarifies the request if needed
      - Delegates to Explainer → Quiz Master → Evaluator (sequential)
      - Triggers re-teaching if Evaluator flags it (feedback loop)
      - Handles errors gracefully
"""

import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

from memory.session_store import SessionMemory
from agents.explainer import run_explainer
from agents.quiz_master import run_quiz_master
from agents.evaluator import run_evaluator

load_dotenv()

# ── Prompt template ──────────────────────────────────────────────────────────
COORDINATOR_IDENTITY = """\
You are Leo — a warm, encouraging multi-agent AI tutor coordinator.
Your role is to:
1. Welcome the student and confirm what they want to learn.
2. Validate that the topic is suitable for tutoring (educational, not harmful).
3. Introduce each specialist agent as they take over.
4. Keep the session focused and on-track.
5. Handle any confusion gracefully — if a request is unclear, ask for clarification.

You speak in a friendly, motivating tone. Always address the student by name.
"""


class TutoringCoordinator:
    """
    The central orchestrator that manages the full Leo tutoring pipeline.
    """

    def __init__(self, student_name: str, topic: str):
        self.session = SessionMemory(
            student_name=student_name,
            topic=topic,
        )

    def _get_client(self) -> AsyncOpenAI:
        api_key = os.getenv("GROQ_API_KEY")
        return AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    async def validate_topic(self) -> tuple[bool, str]:
        """
        Use the Coordinator LLM to validate and optionally clarify the topic.
        Returns (is_valid, coordinator_message).
        """
        client = self._get_client()
        prompt = (
            f"A student named {self.session.student_name} wants to learn about: "
            f"'{self.session.topic}'. "
            f"Is this a valid educational topic? If yes, give a one-sentence "
            f"welcome message confirming the topic. If no or unclear, explain "
            f"what clarification is needed."
        )

        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": COORDINATOR_IDENTITY},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        message = response.choices[0].message.content
        is_valid = "clarification" not in message.lower()
        return is_valid, message

    async def run_teaching_phase(
        self, status_callback=None
    ) -> tuple[SessionMemory, str]:
        """
        Phase 1: Coordinator → Explainer.
        Returns updated session and coordinator intro message.
        """
        client = self._get_client()
        intro_response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": COORDINATOR_IDENTITY},
                {
                    "role": "user",
                    "content": f"Introduce the start of a tutoring session for {self.session.student_name} on '{self.session.topic}'. Be brief and enthusiastic.",
                },
            ],
            temperature=0.6,
        )
        intro_msg = intro_response.choices[0].message.content

        if status_callback:
            status_callback("🧭 Coordinator: Starting teaching phase...")

        explanation = await run_explainer(
            topic=self.session.topic,
            status_callback=status_callback,
        )
        self.session.explanation = explanation
        return self.session, intro_msg

    async def run_quiz_phase(self, status_callback=None) -> SessionMemory:
        """
        Phase 2: Quiz Master generates questions from Explainer's output.
        Returns updated session with quiz_questions populated.
        """
        if not self.session.explanation:
            raise ValueError("Teaching phase must run before quiz phase.")

        if status_callback:
            status_callback("🧭 Coordinator: Handing off to Quiz Master...")

        questions = await run_quiz_master(
            topic=self.session.topic,
            explanation=self.session.explanation,
            status_callback=status_callback,
        )

        self.session.quiz_questions = questions
        return self.session

    async def run_evaluation_phase(
        self,
        student_answers: list[str],
        status_callback=None,
    ) -> SessionMemory:
        """
        Phase 3: Evaluator grades answers. Triggers re-teaching if needed (bonus loop).
        Returns fully evaluated session.
        """
        if not self.session.quiz_questions:
            raise ValueError("Quiz phase must run before evaluation phase.")

        self.session.student_answers = student_answers

        if status_callback:
            status_callback("🧭 Coordinator: Sending answers to Evaluator...")

        # Hand off to Evaluator
        self.session = await run_evaluator(
            session=self.session,
            status_callback=status_callback,
        )

        # ── BONUS: Feedback loop — re-teach if score <= 1 ─────────────────
        if self.session.needs_reteach:
            if status_callback:
                status_callback(
                    "🔄 Coordinator: Score is low. Triggering re-teach with Explainer..."
                )
            reteach_focus = self.session.reteach_explanation
            reteach = await run_explainer(
                topic=self.session.topic,
                reteach_focus=reteach_focus,
                status_callback=status_callback,
            )
            self.session.reteach_explanation = reteach

        return self.session

    async def get_closing_message(self) -> str:
        """Coordinator generates a closing/encouragement message."""
        client = self._get_client()
        score = self.session.score
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": COORDINATOR_IDENTITY},
                {
                    "role": "user",
                    "content": f"{self.session.student_name} just completed their tutoring session on '{self.session.topic}' and scored {score}/3. Give an encouraging closing message.",
                },
            ],
            temperature=0.6,
        )
        return response.choices[0].message.content
