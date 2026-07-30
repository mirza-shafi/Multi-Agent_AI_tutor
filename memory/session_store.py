"""
session_store.py — In-memory session state for Leo's multi-agent tutoring pipeline.

Stores all data exchanged between agents during a single tutoring session:
  - Student name & topic
  - Explainer's output
  - Quiz Master's questions
  - Student's answers
  - Evaluator's feedback & score
  - Re-teach flag
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuizQuestion:
    """A single multiple-choice question produced by the Quiz Master."""
    question: str
    options: dict[str, str]        # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer: str            # "A" | "B" | "C" | "D"
    explanation: str               # Why that answer is correct


@dataclass
class QuestionFeedback:
    """Per-question feedback from the Evaluator."""
    question_index: int
    student_answer: str
    correct_answer: str
    is_correct: bool
    feedback: str


@dataclass
class SessionMemory:
    """
    Central memory object passed between all agents.
    Acts as the shared 'handoff' payload.
    """
    # Identity
    student_name: str = ""
    topic: str = ""

    # Stage outputs
    explanation: str = ""                          # From Explainer
    quiz_questions: list[QuizQuestion] = field(default_factory=list)  # From Quiz Master
    student_answers: list[str] = field(default_factory=list)          # From human input
    question_feedback: list[QuestionFeedback] = field(default_factory=list)  # From Evaluator
    score: int = 0                                 # 0–3
    needs_reteach: bool = False                    # Feedback loop trigger
    reteach_explanation: str = ""                  # From Explainer (second pass)

    # Conversation IDs for persistence across agent calls
    coordinator_conv_id: Optional[str] = None
    explainer_conv_id: Optional[str] = None

    def summary(self) -> str:
        """Returns a compact string summary of the session for logging."""
        return (
            f"Student: {self.student_name} | Topic: {self.topic} | "
            f"Score: {self.score}/3 | Re-teach: {self.needs_reteach}"
        )

    def to_quiz_context(self) -> str:
        """Formats quiz questions for passing to the Evaluator."""
        lines = []
        for i, q in enumerate(self.quiz_questions, 1):
            lines.append(f"Q{i}: {q.question}")
            for letter, text in q.options.items():
                lines.append(f"  {letter}) {text}")
            lines.append(f"  Correct: {q.correct_answer}")
            lines.append(f"  Explanation: {q.explanation}")
        return "\n".join(lines)

    def to_answers_context(self) -> str:
        """Formats student answers as a string for the Evaluator."""
        return ", ".join(
            f"Q{i+1}: {ans}"
            for i, ans in enumerate(self.student_answers)
        )
