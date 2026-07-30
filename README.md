# 🎓 Leo — Multi-Agent AI Tutor

> **Assignment: Exam Week 4 — Multi-Agent AI Tutor**
> A collaborative multi-agent system where AI specialists work together to teach, quiz, and evaluate students on any topic.

---

## 🤖 Agents & Their Roles

| Agent | Role | Prompt Template |
|-------|------|-----------------|
| 🧭 **Coordinator** | Orchestrates the full pipeline, validates topics, delegates tasks, handles errors gracefully | `"You are Leo — a warm, encouraging multi-agent AI tutor coordinator..."` |
| 📚 **Explainer** | Teaches the concept using a structured format: Overview → Key Concepts → Real-World Example → Quick Summary | `"You are Leo's Explainer Agent — a world-class educator..."` |
| ❓ **Quiz Master** | Generates exactly 3 MCQ questions (A/B/C/D) from the lesson using Pydantic structured output | `"You are Leo's Quiz Master Agent — an expert at creating educational assessments..."` |
| ✅ **Evaluator** | Grades student answers, provides per-question feedback, computes score (0–3), flags weak areas | `"You are Leo's Evaluator Agent — a fair, constructive, and encouraging tutor..."` |

---

## 🏗️ Architecture Diagram

```
                     ┌─────────────────────────────┐
                     │        STUDENT INPUT         │
                     │   (name + topic selection)   │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │    🧭 COORDINATOR AGENT      │
                     │  • Validates topic           │
                     │  • Manages session memory    │
                     │  • Orchestrates pipeline     │
                     │  • Handles errors/fallbacks  │
                     └──────────────┬──────────────┘
                                    │ delegates
                          ┌─────────▼─────────┐
                          │  📚 EXPLAINER AGENT │
                          │  • Teaches topic    │
                          │  • Structured format│
                          └─────────┬──────────┘
                                    │ explanation (handoff)
                          ┌─────────▼─────────┐
                          │ ❓ QUIZ MASTER AGENT│
                          │ • 3 MCQ questions  │
                          │ • Pydantic output  │
                          └─────────┬──────────┘
                                    │ questions (handoff)
                                    │
                          ┌─────────▼──────────────┐
                          │  👤 HUMAN-IN-THE-LOOP   │
                          │  Student answers A/B/C/D │
                          └─────────┬──────────────┘
                                    │ answers (handoff)
                          ┌─────────▼─────────┐
                          │  ✅ EVALUATOR AGENT │
                          │  • Grades answers  │
                          │  • Score 0–3       │
                          │  • Per-Q feedback  │
                          └─────────┬──────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
       score > 1                                    score ≤ 1
              │                                           │
     ┌────────▼────────┐                    ┌────────────▼────────────┐
     │  Session Done!  │                    │  🔄 FEEDBACK LOOP       │
     │  Coordinator    │                    │  Coordinator triggers   │
     │  closes session │                    │  Explainer to RE-TEACH  │
     └─────────────────┘                    │  weak concepts          │
                                            └─────────────────────────┘
```

### Orchestration Pattern

**Sequential / Hierarchical** — The Coordinator is the single point of control. It calls each specialist agent in sequence and passes the output of each agent as the input context (handoff) to the next:

```
Coordinator → Explainer → [Quiz Master] → [Student] → Evaluator → (optionally) Explainer
```

---

## 📁 Project Structure

```
Multi-Agent_AI_tutor/
├── agents/
│   ├── __init__.py
│   ├── coordinator.py      # Master orchestrator (TutoringCoordinator class)
│   ├── explainer.py        # Teaching agent (run_explainer function)
│   ├── quiz_master.py      # MCQ generator with Pydantic structured output
│   └── evaluator.py        # Answer grader + feedback generator
├── memory/
│   ├── __init__.py
│   └── session_store.py    # SessionMemory dataclass — shared state/handoff
├── app.py                  # Gradio web interface (recommended)
├── main.py                 # CLI interface
├── requirements.txt        # Python dependencies
├── .env.example            # API key template (never commit .env)
└── README.md               # This file
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd Multi-Agent_AI_tutor
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
# OR
venv\Scripts\activate         # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up your API key
```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```
> Get your free API key at: https://aistudio.google.com/app/api-keys

---

## 🚀 How to Run

### Option A: Gradio Web Interface (Recommended)
```bash
python app.py
```
Then open [http://localhost:7860](http://localhost:7860) in your browser.

**Steps in the UI:**
1. Enter your name and topic
2. Click **Start Learning** — Coordinator validates
3. Click **Teach Me!** — Explainer teaches, Quiz Master creates questions
4. Answer all 3 MCQ questions
5. Click **Submit My Answers** — Evaluator grades and gives feedback
6. If score ≤ 1/3, the **re-teach panel** automatically appears 🔄

### Option B: CLI
```bash
python main.py
# OR with flags:
python main.py --student "Alice" --topic "Python decorators"
```

---

## 🔑 Key Features

| Feature | Implementation |
|---------|----------------|
| **4 distinct agents** | Separate `LocalAgentConfig` + `system_instructions` per agent |
| **Real handoffs** | `SessionMemory` dataclass passed between agents; output of one = input of next |
| **Sequential orchestration** | `TutoringCoordinator` class manages the pipeline order |
| **Memory** | `SessionMemory` stores student name, topic, explanation, quiz, answers, score across all stages |
| **Prompt templates** | Each agent uses `TemplatedSystemInstructions(identity=...)` |
| **Structured output** | Quiz Master uses `response_schema=QuizOutput` (Pydantic) for guaranteed MCQ format |
| **Error handling** | Coordinator has fallback questions if Quiz Master fails; topic validation step |
| **Bonus: Feedback loop** | Evaluator → Coordinator → Explainer re-teach when score ≤ 1/3 |
| **Bonus: Human-in-the-loop** | Student answers quiz interactively (Gradio radio buttons / CLI input) |
| **Interface** | Gradio (dark theme, animated agent status pills) + CLI (coloured ANSI output) |

---

## 🛡️ Security

- **No API keys committed** — use `.env` file (listed in `.gitignore`)
- See `.env.example` for the required variables

---

## 📦 Dependencies

```
google-antigravity    # Multi-agent SDK
gradio>=4.0           # Web UI
pydantic>=2.0         # Structured output schema
python-dotenv         # .env file loading
```

---

## 🎯 Assignment Requirements Checklist

- [x] **4 distinct agent roles** — Coordinator, Explainer, Quiz Master, Evaluator
- [x] **CrewAI or AutoGen** → using **Google Antigravity SDK** (equivalent multi-agent framework per Module 23)
- [x] **Real handoffs** — `SessionMemory` carries outputs between agents
- [x] **Clear orchestration pattern** — Sequential/Hierarchical via `TutoringCoordinator`
- [x] **Memory** — `SessionMemory` remembers student, topic, and all stage outputs
- [x] **Prompt template per role** — `TemplatedSystemInstructions(identity=...)` per agent
- [x] **Structured output** — Quiz Master uses Pydantic `QuizOutput` schema
- [x] **Error handling** — topic validation, fallback questions, graceful coordinator
- [x] **Interface showing agent turns** — agent status pills in Gradio; coloured prefixes in CLI
- [x] **Bonus: Feedback loop** — low score triggers Explainer re-teach
- [x] **Bonus: Human-in-the-loop** — student answers quiz mid-pipeline

---

*Built for: AI Engineering Course — Ostad | Assignment Week 4*
