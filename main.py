"""
main.py — Leo CLI Entry Point

A rich terminal-based demo of the full multi-agent tutoring pipeline.
Shows each agent's turn with clear prefixes and coloured headers.

Usage:
    python main.py
    python main.py --topic "Python decorators" --student "Alice"
"""

import asyncio
import argparse
import sys

# ANSI colours for terminal output
RESET   = "\033[0m"
BOLD    = "\033[1m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
MAGENTA = "\033[95m"
RED     = "\033[91m"
BLUE    = "\033[94m"
DIM     = "\033[2m"


def header(agent_name: str, color: str) -> str:
    bar = "─" * 60
    return f"\n{color}{BOLD}{bar}\n  🤖 {agent_name}\n{bar}{RESET}\n"


def status(msg: str):
    print(f"  {DIM}{msg}{RESET}")


async def run_cli(student_name: str, topic: str):
    from agents.coordinator import TutoringCoordinator

    print(f"\n{BOLD}{CYAN}{'═'*60}")
    print(f"   🎓  Welcome to Leo — Your Multi-Agent AI Tutor")
    print(f"{'═'*60}{RESET}\n")

    coordinator = TutoringCoordinator(
        student_name=student_name,
        topic=topic,
    )

    # ── Step 0: Validate topic ────────────────────────────────────────────────
    print(header("🧭 COORDINATOR — Validating Topic", BLUE))
    is_valid, welcome_msg = await coordinator.validate_topic()
    print(f"  {welcome_msg}\n")

    if not is_valid:
        print(f"  {RED}Please clarify your topic and try again.{RESET}")
        return

    # ── Step 1: Teaching phase ────────────────────────────────────────────────
    print(header("🧭 COORDINATOR → 📚 EXPLAINER", BLUE))
    session, intro = await coordinator.run_teaching_phase(status_callback=status)
    print(f"\n  {CYAN}Coordinator says:{RESET} {intro}\n")
    print(header("📚 EXPLAINER — Lesson", CYAN))
    print(session.explanation)

    input(f"\n  {DIM}(Press Enter when you're ready for the quiz...){RESET}")

    # ── Step 2: Quiz phase ────────────────────────────────────────────────────
    print(header("🧭 COORDINATOR → ❓ QUIZ MASTER", BLUE))
    session = await coordinator.run_quiz_phase(status_callback=status)

    print(header("❓ QUIZ MASTER — Your Quiz", YELLOW))
    student_answers: list[str] = []

    for i, q in enumerate(session.quiz_questions, 1):
        print(f"\n  {BOLD}Q{i}: {q.question}{RESET}")
        for letter, text in q.options.items():
            print(f"       {letter}) {text}")

        while True:
            ans = input(f"\n  Your answer (A/B/C/D): ").strip().upper()
            if ans in ("A", "B", "C", "D"):
                student_answers.append(ans)
                break
            print(f"  {RED}Please enter A, B, C, or D.{RESET}")

    # ── Step 3: Evaluation phase ──────────────────────────────────────────────
    print(header("🧭 COORDINATOR → ✅ EVALUATOR", BLUE))
    session = await coordinator.run_evaluation_phase(
        student_answers=student_answers,
        status_callback=status,
    )

    print(header("✅ EVALUATOR — Results", GREEN))
    print(f"\n  {BOLD}Score: {session.score}/3{RESET}\n")

    for fb in session.question_feedback:
        q = session.quiz_questions[fb.question_index]
        mark = f"{GREEN}✅{RESET}" if fb.is_correct else f"{RED}❌{RESET}"
        print(f"  {mark} Q{fb.question_index+1}: {q.question}")
        print(f"     {fb.feedback}\n")

    # ── Step 4 (Bonus): Re-teach if needed ───────────────────────────────────
    if session.needs_reteach:
        print(header("🔄 FEEDBACK LOOP — EXPLAINER Re-Teaching", MAGENTA))
        print(f"  {MAGENTA}Your score was low. Leo is re-teaching the weak concepts...{RESET}\n")
        print(session.reteach_explanation)

    # ── Closing ───────────────────────────────────────────────────────────────
    print(header("🧭 COORDINATOR — Session Complete", BLUE))
    closing = await coordinator.get_closing_message()
    print(f"  {closing}\n")
    print(f"  {DIM}Session summary: {session.summary()}{RESET}")
    print(f"\n{CYAN}{'═'*60}{RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Leo — Multi-Agent AI Tutor (CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python main.py --topic 'Python decorators' --student 'Alice'",
    )
    parser.add_argument("--topic",   type=str, default="", help="Topic to study")
    parser.add_argument("--student", type=str, default="", help="Student name")
    args = parser.parse_args()

    student_name = args.student or input("Enter your name: ").strip() or "Student"
    topic = args.topic or input("What topic would you like to learn? ").strip()

    if not topic:
        print("❌ No topic provided. Exiting.")
        sys.exit(1)

    asyncio.run(run_cli(student_name=student_name, topic=topic))


if __name__ == "__main__":
    main()
