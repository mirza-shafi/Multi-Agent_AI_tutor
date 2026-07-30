"""
app.py — Leo: Multi-Agent AI Tutor — Gradio Web Interface

Displays a rich step-by-step UI that shows which agent is currently active,
presents the lesson, quiz questions as interactive radio buttons, and evaluation
results with a bonus re-teach panel.

Run with: python app.py
"""

import asyncio
import os
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

# ── Server-side Session Memory ────────────────────────────────────────────────
_sessions: dict[str, object] = {}   # "active" -> TutoringCoordinator instance


# ── CSS ───────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
/* ─ Global ─ */
:root {
    --leo-primary:   #6c63ff;
    --leo-secondary: #f5a623;
    --leo-success:   #27ae60;
    --leo-danger:    #e74c3c;
    --leo-bg:        #0f0f1a;
    --leo-card:      #1a1a2e;
    --leo-border:    #2d2d4e;
    --leo-text:      #e0e0f0;
    --leo-muted:     #8888aa;
}

body, .gradio-container {
    background: var(--leo-bg) !important;
    color: var(--leo-text) !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}

/* ─ Header ─ */
#leo-header {
    background: linear-gradient(135deg, #1a1a3e 0%, #0f0f2a 100%);
    border: 1px solid var(--leo-border);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 8px;
    text-align: center;
}

#leo-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #6c63ff, #f5a623, #6c63ff);
    background-size: 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 3s linear infinite;
}

@keyframes shimmer {
    0%   { background-position: 0% }
    100% { background-position: 200% }
}

/* ─ Agent Status Panel ─ */
.agent-pill {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    margin: 4px;
    transition: all 0.3s ease;
    border: 2px solid transparent;
}

.agent-inactive { background: #1e1e3a; color: #666; }
.agent-active   {
    background: linear-gradient(135deg, #6c63ff22, #6c63ff44);
    border-color: #6c63ff;
    color: #a0a0ff;
    box-shadow: 0 0 16px #6c63ff55;
    animation: pulse 1.5s ease-in-out infinite;
}
.agent-done { background: #1a3a2a; color: #4ade80; border-color: #27ae60; }

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 8px #6c63ff55; }
    50%       { box-shadow: 0 0 24px #6c63ffaa; }
}

/* ─ Cards ─ */
.leo-card {
    background: var(--leo-card);
    border: 1px solid var(--leo-border);
    border-radius: 12px;
    padding: 20px 24px;
}

/* ─ Score bar ─ */
.score-chip {
    font-size: 1.8rem;
    font-weight: 800;
    padding: 8px 24px;
    border-radius: 12px;
    display: inline-block;
}
.score-high { background: #1a3a2a; color: #4ade80; border: 2px solid #27ae60; }
.score-mid  { background: #3a2a1a; color: #fbbf24; border: 2px solid #f59e0b; }
.score-low  { background: #3a1a1a; color: #f87171; border: 2px solid #e74c3c; }

/* ─ Gradio overrides ─ */
.gr-button-primary {
    background: linear-gradient(135deg, #6c63ff, #9c5fff) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
.gr-button-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px #6c63ff44 !important;
}

.gr-textbox textarea, .gr-textbox input {
    background: #12122a !important;
    border: 1px solid #2d2d4e !important;
    color: #e0e0f0 !important;
    border-radius: 8px !important;
}

label.svelte-1b6s6un { color: #a0a0cc !important; }

.gr-radio label { color: #c0c0e0 !important; }

/* ─ Feedback correct/wrong ─ */
.fb-correct { color: #4ade80; }
.fb-wrong   { color: #f87171; }
"""


# ── Render Helpers ────────────────────────────────────────────────────────────

def build_agent_status_html(active: str) -> str:
    """Renders the agent status pills."""
    agents = [
        ("🧭", "Coordinator"),
        ("📚", "Explainer"),
        ("❓", "Quiz Master"),
        ("✅", "Evaluator"),
    ]
    pills = []
    for emoji, name in agents:
        if name == active:
            cls = "agent-pill agent-active"
        elif active == "Done":
            cls = "agent-pill agent-done"
        else:
            cls = "agent-pill agent-inactive"
        pills.append(f'<span class="{cls}">{emoji} {name}</span>')
    return (
        '<div style="text-align:center;padding:12px 0;">'
        + "".join(pills)
        + "</div>"
    )


def build_results_html(session) -> str:
    """Renders evaluation results."""
    score = session.score
    if score == 3:
        score_cls, score_label = "score-high", "🏆 Perfect Score!"
    elif score == 2:
        score_cls, score_label = "score-mid", "👍 Good Job!"
    else:
        score_cls, score_label = "score-low", "📖 Keep Studying!"

    html = f"""
    <div style="text-align:center;margin-bottom:20px;">
        <span class="score-chip {score_cls}">{score}/3 — {score_label}</span>
    </div>"""

    for fb in session.question_feedback:
        q = session.quiz_questions[fb.question_index]
        mark = "✅" if fb.is_correct else "❌"
        cls  = "fb-correct" if fb.is_correct else "fb-wrong"
        html += f"""
        <div class="leo-card" style="margin:10px 0;">
            <p class="{cls}" style="font-weight:700;margin:0 0 6px;">
                {mark} Q{fb.question_index+1}: {q.question}
            </p>
            <p style="margin:0;color:#c0c0d8;">{fb.feedback.replace(chr(10), '<br>')}</p>
        </div>"""

    return html


# ── Step handlers ─────────────────────────────────────────────────────────────

async def step_start(student_name: str, topic: str):
    """Called when student clicks 'Start Learning'. Validates topic."""
    from agents.coordinator import TutoringCoordinator

    if not student_name.strip():
        return (
            build_agent_status_html("Coordinator"),
            "⚠️ Please enter your name.",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )
    if not topic.strip():
        return (
            build_agent_status_html("Coordinator"),
            "⚠️ Please enter a topic to study.",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    coordinator = TutoringCoordinator(student_name=student_name.strip(), topic=topic.strip())
    _sessions["active"] = coordinator

    is_valid, welcome = await coordinator.validate_topic()
    if not is_valid:
        return (
            build_agent_status_html("Coordinator"),
            f"⚠️ {welcome}\n\nPlease clarify your topic.",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    return (
        build_agent_status_html("Coordinator"),
        f"✅ {welcome}",
        gr.update(visible=True),   # show "Start Teaching" button
        gr.update(visible=False),
        gr.update(visible=False),
    )


async def step_teach(status_box):
    """Runs Explainer and Quiz Master. Yields progressive UI updates."""
    coordinator = _sessions.get("active")
    if coordinator is None:
        yield (
            build_agent_status_html("Explainer"),
            "❌ Session not started. Please go back.",
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )
        return

    logs = ["📚 Explainer Agent is preparing your lesson..."]
    yield (
        build_agent_status_html("Explainer"),
        "\n".join(logs),
        "",
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )

    def cb(msg):
        logs.append(msg)

    # Teaching phase
    session, intro = await coordinator.run_teaching_phase(status_callback=cb)

    yield (
        build_agent_status_html("Quiz Master"),
        "\n".join(logs),
        session.explanation,
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )

    # Quiz phase
    session = await coordinator.run_quiz_phase(status_callback=cb)
    questions = session.quiz_questions

    # Build radio choices for each question
    radio_updates = []
    for i in range(3):
        if i < len(questions):
            q = questions[i]
            choices = [f"{k}: {v}" for k, v in q.options.items()]
            radio_updates.append(
                gr.update(
                    label=f"Q{i+1}: {q.question}",
                    choices=choices,
                    value=None,
                    visible=True,
                )
            )
        else:
            radio_updates.append(gr.update(visible=False))

    yield (
        build_agent_status_html("Quiz Master"),
        "\n".join(logs),
        session.explanation,
        gr.update(visible=True),     # explanation panel
        radio_updates[0],            # q1
        radio_updates[1],            # q2
        radio_updates[2],            # q3
        gr.update(visible=True),     # submit button
    )


async def step_evaluate(q1_ans, q2_ans, q3_ans):
    """Collects answers and runs Evaluator. Yields progressive UI updates."""
    coordinator = _sessions.get("active")
    if coordinator is None or not getattr(coordinator.session, "quiz_questions", None):
        yield (
            build_agent_status_html("Evaluator"),
            "❌ No active session.",
            "",
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            "",
        )
        return

    questions = coordinator.session.quiz_questions
    logs = ["✅ Evaluator Agent is grading your answers..."]
    yield (
        build_agent_status_html("Evaluator"),
        "\n".join(logs),
        '<div style="text-align:center;padding:24px;color:#a0a0ff;font-size:1.1rem;">⏳ Evaluator is checking your answers...</div>',
        gr.update(visible=True),
        "",
        gr.update(visible=False),
        "",
    )

    # Parse answers from "A: option text" → "A"
    raw_answers = [q1_ans, q2_ans, q3_ans]
    answers = []
    for i, raw in enumerate(raw_answers[:len(questions)]):
        if raw and isinstance(raw, str) and len(raw) > 0:
            answers.append(raw[0])  # first char is "A"/"B"/"C"/"D"
        else:
            answers.append("A")     # fallback

    def cb(msg):
        logs.append(msg)

    # Run evaluation phase
    session = await coordinator.run_evaluation_phase(
        student_answers=answers,
        status_callback=cb,
    )

    results_html = build_results_html(session)
    reteach_visible = session.needs_reteach
    reteach_content = session.reteach_explanation if session.needs_reteach else ""

    yield (
        build_agent_status_html("Evaluator"),
        "\n".join(logs),
        results_html,
        gr.update(visible=True),
        reteach_content,
        gr.update(visible=reteach_visible),
        "⏳ Coordinator is summarizing your performance...",
    )

    closing = await coordinator.get_closing_message()

    yield (
        build_agent_status_html("Done"),
        "\n".join(logs),
        results_html,
        gr.update(visible=True),
        reteach_content,
        gr.update(visible=reteach_visible),
        f"### 🧭 Coordinator's Closing Message\n\n{closing}",
    )


# ── Build Gradio app ──────────────────────────────────────────────────────────

def create_app():
    with gr.Blocks(
        title="Leo — Multi-Agent AI Tutor",
    ) as demo:

        # ── Header ──
        gr.HTML("""
        <div id="leo-header">
            <div id="leo-title">🎓 Leo — Multi-Agent AI Tutor</div>
            <p style="color:#8888aa;margin:8px 0 0;font-size:0.95rem;">
                Powered by 4 AI agents working together: Coordinator · Explainer · Quiz Master · Evaluator
            </p>
        </div>
        """)

        # ── Agent status bar ──
        agent_status = gr.HTML(build_agent_status_html("Coordinator"))

        with gr.Row():
            # ── Left column: Input + controls ──
            with gr.Column(scale=1):
                gr.Markdown("### 👤 Student Info", elem_classes=["leo-card"])
                student_name = gr.Textbox(
                    label="Your Name",
                    placeholder="e.g. Alice",
                    max_lines=1,
                )
                topic_input = gr.Textbox(
                    label="Topic to Learn",
                    placeholder="e.g. Python decorators, Neural networks, SQL joins...",
                    max_lines=1,
                )
                start_btn = gr.Button("🚀 Start Learning", variant="primary")
                coordinator_msg = gr.Textbox(
                    label="🧭 Coordinator",
                    interactive=False,
                    lines=3,
                )
                teach_btn = gr.Button(
                    "📚 Teach Me!", variant="primary", visible=False
                )

                # Agent log (status messages)
                agent_log = gr.Textbox(
                    label="⚙️ Agent Activity Log",
                    interactive=False,
                    lines=6,
                    placeholder="Agent activity will appear here...",
                )

            # ── Right column: Content panels ──
            with gr.Column(scale=2):
                # Explanation panel
                with gr.Group(visible=False) as explanation_group:
                    gr.Markdown("### 📚 Explainer's Lesson")
                    explanation_box = gr.Markdown(value="")

                # Quiz panel
                gr.Markdown("### ❓ Quiz — Answer All Questions")
                q1 = gr.Radio(label="", choices=[], visible=False)
                q2 = gr.Radio(label="", choices=[], visible=False)
                q3 = gr.Radio(label="", choices=[], visible=False)
                submit_btn = gr.Button(
                    "✅ Submit My Answers", variant="primary", visible=False
                )

                # Results panel
                with gr.Group(visible=False) as results_group:
                    gr.Markdown("### 📊 Your Results")
                    results_html = gr.HTML("")

                # Re-teach panel (bonus feedback loop)
                with gr.Group(visible=False) as reteach_group:
                    gr.Markdown(
                        "### 🔄 Re-Teaching — Feedback Loop Active",
                        elem_id="reteach-header",
                    )
                    gr.Markdown(
                        "_Your score was low. The Explainer is revisiting the weak areas._",
                        elem_classes=["leo-muted"],
                    )
                    reteach_box = gr.Markdown(value="")

                # Closing message
                closing_box = gr.Markdown(value="")

        # ── Event wiring ─────────────────────────────────────────────────────

        # Step 1: Start → validate topic
        start_btn.click(
            fn=step_start,
            inputs=[student_name, topic_input],
            outputs=[
                agent_status,
                coordinator_msg,
                teach_btn,
                results_group,
                reteach_group,
            ],
        )

        # Step 2: Teach → explanation + quiz
        teach_btn.click(
            fn=step_teach,
            inputs=[agent_log],
            outputs=[
                agent_status,
                agent_log,
                explanation_box,
                explanation_group,
                q1,
                q2,
                q3,
                submit_btn,
            ],
        )

        # Step 3: Submit → evaluate + optional re-teach
        submit_btn.click(
            fn=step_evaluate,
            inputs=[q1, q2, q3],
            outputs=[
                agent_status,
                agent_log,
                results_html,
                results_group,
                reteach_box,
                reteach_group,
                closing_box,
            ],
        )

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.queue()   # Enable queue so long-running agent calls don't freeze the browser
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            primary_hue="violet",
            secondary_hue="orange",
            neutral_hue="slate",
        ),
    )
