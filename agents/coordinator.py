"""
coordinator.py — Leo's Coordinator Agent

Role: Master orchestrator of the multi-agent tutoring pipeline.
      - Receives the student's topic request
      - Validates and clarifies the request if needed
      - Delegates to Explainer → Quiz Master → Evaluator (sequential)
      - Triggers re-teaching if Evaluator flags it (feedback loop)
      - Handles errors gracefully

Orchestration Pattern: Sequential / Hierarchical
  Coordinator controls the flow; each agent is a specialist sub-unit.
"""

import os
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.types import TemplatedSystemInstructions
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
    
    Usage:
        coordinator = TutoringCoordinator(student_name="Alice", topic="Python decorators")
        session = await coordinator.run_teaching_phase(status_callback=my_cb)
        # (student answers quiz)
        session = await coordinator.run_evaluation_phase(student_answers=["A","B","C"], ...)
    """

    def __init__(self, student_name: str, topic: str):
        self.session = SessionMemory(
            student_name=student_name,
            topic=topic,
        )
        self._coordinator_config = LocalAgentConfig(
            system_instructions=TemplatedSystemInstructions(
                identity=COORDINATOR_IDENTITY
            ),
        )

    async def validate_topic(self) -> tuple[bool, str]:
        """
        Use the Coordinator LLM to validate and optionally clarify the topic.
        Returns (is_valid, coordinator_message).
        """
        prompt = (
            f"A student named {self.session.student_name} wants to learn about: "
            f"'{self.session.topic}'. "
            f"Is this a valid educational topic? If yes, give a one-sentence "
            f"welcome message confirming the topic. If no or unclear, explain "
            f"what clarification is needed."
        )
        async with Agent(self._coordinator_config) as agent:
            response = await agent.chat(prompt)
            message = await response.text()

        # Simple heuristic: if the response contains "clarification" assume invalid
        is_valid = "clarification" not in message.lower()
        return is_valid, message

    async def run_teaching_phase(
        self, status_callback=None
    ) -> tuple[SessionMemory, str]:
        """
        Phase 1: Coordinator → Explainer.
        Returns updated session and coordinator intro message.
        """
        # Coordinator introduces the session
        async with Agent(self._coordinator_config) as agent:
            intro_response = await agent.chat(
                f"Introduce the start of a tutoring session for "
                f"{self.session.student_name} on the topic: '{self.session.topic}'. "
                f"Be brief and enthusiastic (2-3 sentences)."
            )
            intro_msg = await intro_response.text()

        if status_callback:
            status_callback("🧭 Coordinator: Starting teaching phase...")

        # Hand off to Explainer
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

        if not questions:
            # Graceful fallback: Coordinator generates a simple question
            if status_callback:
                status_callback(
                    "⚠️ Coordinator: Quiz Master encountered an issue. "
                    "Using fallback questions..."
                )
            from memory.session_store import QuizQuestion
            questions = [
                QuizQuestion(
                    question=f"What is the main purpose of {self.session.topic}?",
                    options={"A": "Processing data", "B": "Managing memory",
                             "C": "Core concept of the topic", "D": "Networking"},
                    correct_answer="C",
                    explanation="This is a fallback question. Please retry.",
                )
            ]

        self.session.quiz_questions = questions
        return self.session

    async def run_evaluation_phase(
        self,
        student_answers: list[str],
        status_callback=None,
    ) -> SessionMemory:
        """
        Phase 3: Evaluator grades answers. Triggers re-teach if needed (bonus loop).
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
        score = self.session.score
        async with Agent(self._coordinator_config) as agent:
            response = await agent.chat(
                f"{self.session.student_name} just completed their Leo tutoring "
                f"session on '{self.session.topic}' and scored {score}/3. "
                f"Give them an encouraging closing message (2-3 sentences). "
                f"If they scored 3/3, celebrate! If lower, motivate them to keep going."
            )
            return await response.text()
