# 📚 Automated Book Generation System

A modular, scalable book generation system that uses AI to generate book content with human-in-the-loop feedback at every stage.

## 🎯 Features

- **Outline Generation**: AI-powered outline creation with editor feedback loop
- **Chapter Generation**: Context-aware chapter writing with previous chapter summaries
- **Human-in-the-Loop**: Notes and feedback at every stage for quality control
- **Multiple LLM Support**: OpenAI, Anthropic Claude, and Google Gemini
- **Flexible Database**: SQLite (default) or Supabase
- **Multiple Output Formats**: DOCX, PDF, and TXT
- **Notifications**: Email (SMTP) and MS Teams webhooks
- **Web Search Integration**: Optional research-backed content generation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                              │
│    Excel/CSV/JSON → Input Handler → Database                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW ORCHESTRATOR                         │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   STAGE 1    │───▶│   STAGE 2    │───▶│   STAGE 3    │      │
│  │   Outline    │    │   Chapters   │    │  Compilation │      │
│  │  Generation  │    │  Generation  │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         ↕                   ↕                   ↕                │
│    [Editor Notes]     [Editor Notes]     [Final Review]         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        OUTPUT LAYER                              │
│              DOCX / PDF / TXT → Storage/Export                   │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
Book Generator/
├── main.py                 # CLI entry point
├── orchestrator.py         # Main workflow controller
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── modules/
│   ├── __init__.py
│   ├── database.py         # SQLite/Supabase database layer
│   ├── llm.py              # LLM integrations (OpenAI, Anthropic, Gemini)
│   ├── notifications.py    # Email & Teams notifications
│   ├── exporter.py         # DOCX, PDF, TXT export
│   ├── input_handler.py    # Excel/CSV/JSON input reader
│   └── stages.py           # Workflow stage logic
├── input/                  # Input files (created on first run)
└── output/                 # Generated books
```

## 🛠️ Tech Stack

| Component     | Options                                   |
| ------------- | ----------------------------------------- |
| Language      | Python 3.9+                               |
| Database      | SQLite (default) / Supabase               |
| LLM           | OpenAI / Anthropic Claude / Google Gemini |
| Input         | Excel (.xlsx) / CSV / JSON                |
| Output        | DOCX / PDF / TXT                          |
| Notifications | SMTP Email / MS Teams Webhooks            |

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to the project
cd "Book Generator"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
copy .env.example .env

# Edit .env with your API keys
notepad .env
```

Required settings in `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

### 3. Initialize System

```bash
python main.py init
```

### 4. Create Your First Book

```bash
# Option A: Create directly via CLI
python main.py create "My Book Title" "Notes for outline: cover topics X, Y, Z for beginners"

# Option B: Import from file
python main.py sample  # Creates sample input file
python main.py import input/books.xlsx
```

### 5. Run the Workflow

```bash
# Step-by-step workflow:
python main.py outline 1           # Generate outline
python main.py status 1            # Check status
python main.py approve-outline 1   # Approve outline
python main.py chapter 1 1         # Generate chapter 1
python main.py approve-chapter 1 1 # Approve chapter 1
# ... repeat for all chapters
python main.py compile 1           # Generate final book

# OR: Fully automated (for testing)
python main.py auto 1 --auto-approve
```

## 📖 Workflow Stages

## 📝 Example Workflow

```bash
# 1. Initialize
python main.py init

# 2. Create book
python main.py create "Python for Beginners" "Create a comprehensive guide covering basics, data types, control flow, functions, OOP, and web development. Target: complete beginners."

# 3. Generate and review outline
python main.py outline 1
python main.py status 1
# Review the outline in database or output

# 4. Add feedback (optional)
python main.py outline-feedback 1 "Add a chapter on testing and debugging"
python main.py regen-outline 1

# 5. Approve outline
python main.py approve-outline 1

# 6. Generate chapters
python main.py chapter 1 1
python main.py approve-chapter 1 1
# ... repeat for all chapters

# 7. Compile final book
python main.py compile 1

# Output files will be in the 'output/' directory
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

Mohsin Bin Ramzan - feel free to use and modify for your projects.

