# FitNova - Sales Call Intelligence System

FitNova is an enterprise conversational intelligence and compliance auditing platform designed for high-performance sales teams. It automates speech transcription, speaker diarization (separating sales advisors vs. prospective clients), Gemini-driven quality evaluations, structured script compliance audits, and advisor feedback appeal workflows.

---

## 🚀 Quick Start

Follow these steps to clone, configure, and launch the application:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/fitnova-sales-call-intelligence.git
cd fitnova-sales-call-intelligence

# 2. Set up virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
copy .env.example .env
# Note: Open .env and configure your GEMINI_API_KEY and Hugging Face PYANNOTE_AUTH_TOKEN

# 5. Initialize the database and seed demo data
python backend/app/database/init_db.py

# 6. Start the FastAPI backend
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# 7. Start the Streamlit frontend (in a separate terminal)
streamlit run frontend/Home.py
```

---

## ⚡ System Architecture

The workflow moves sequentially from speech upload to multi-stage pipeline processing, database persistence, and filesystem caching.

```text
                                 [ Web Client Dashboard ]
                                    (Streamlit Front)
                                           │
                                           ▼ (REST API HTTP)
                                     [ FastAPI App ]
                                           │
                         ┌─────────────────┴─────────────────┐
                         ▼                                   ▼
                 [ PostgreSQL DB ]                 [ BackgroundTasks ]
              (Metadata & Relations)            (Pipeline Orchestration)
                                                             │
                                                             ▼
                                                      [ CallProcessor ]
                                                             │
       ┌─────────────────────┬───────────────────────┼───────────────────┐
       ▼                     ▼                       ▼                   ▼
[ Transcription ]     [ Diarization ]         [ PII Redaction ]   [ AI Analytics ]
(Whisper Speech)      (Advisor/Customer)      (Sensitive Masking) (Gemini Multi-Agent)
       │                     │                       │                   │
       └─────────────────────┼───────────────────────┴───────────────────┘
                             ▼
                 [ Storage Manager (Disk) ]
             (transcript, conversation, analysis,
               and timeline JSON files)
```

For a detailed visual description, see the [Architecture Flowchart](docs/architecture.png).

---

## 📋 Features

*   **Audio Ingestion**: Drag-and-drop file upload supporting `.wav`, `.mp3`, and `.m4a` files with Mutagen metadata duration parsing.
*   **Background Pipeline**: Async FastAPI background tasks status tracker mapping states: `Uploaded` ➔ `Queued` ➔ `Processing` ➔ `Completed`/`Failed`.
*   **Speech-to-Text**: High-speed, local transcription using optimized **Faster Whisper**.
*   **Speaker Diarization**: Multi-speaker alignment separating `Advisor` and `Customer` turns using **Pyannote.audio**.
*   **Compliance Audits**: Multi-agent LLM framework (Google Gemini) rating calls and highlighting compliance issue tags.
*   **Dispute Appeals**: Formal lifecycle workflow for advisors to appeal issue flags, routed to manager review queues.
*   **Dynamic Visualizations**: Manager leaderboards, performance histograms, and pie charts built with **Plotly Express**.

---

## 🛠️ Technology Stack

*   **Backend API**: FastAPI, Uvicorn
*   **Frontend UI**: Streamlit
*   **Database & ORM**: PostgreSQL / SQLite, SQLAlchemy 2.0, Alembic migrations
*   **Audio Processing**: Mutagen
*   **Machine Learning Models**: Faster Whisper (speech-to-text), Pyannote.audio (speaker diarization)
*   **LLM Orchestrations**: Google Gemini (1.5-flash)
*   **Visualizations**: Plotly Express
*   **Testing**: Pytest

---

## 📂 Project Structure

```text
fitnova/
├── backend/
│   ├── alembic/              # Database migration version files
│   ├── app/                  # Application source package
│   │   ├── api/              # API router and endpoints
│   │   ├── core/             # Base settings & logging configs
│   │   ├── database/         # Session local and initialization seeder scripts
│   │   ├── models/           # SQLAlchemy ORM models definitions
│   │   ├── schemas/          # Validation Pydantic schemas
│   │   ├── services/         # Business layer services (Upload, Dashboard, Appeals)
│   │   ├── pipeline/         # Orchestrator and background tasks trigger
│   │   ├── ai/               # AI models (Whisper, Pyannote, Gemini)
│   │   └── utils/            # Storage and json helpers
│   └── tests/                # Automated pytest suite (37 tests)
├── docs/                     # Visual assets folder
│   └── architecture.png      # System architecture flow diagram
├── frontend/
│   ├── Home.py               # Streamlit homepage portal
│   ├── sidebar.py            # Central navigation and authentication switches
│   └── pages/                # Streamlit multi-page registries
└── storage/                  # Decoupled filesystem cache (.gitkeep inside)
    ├── audio/
    ├── transcripts/
    ├── conversations/
    ├── analysis/
    └── processed/
```

---

## 🔧 Environment Variables

Configure the following parameters in your `.env` file (copied from `.env.example`):

*   `DATABASE_URL`: PostgreSQL connection string (defaults to local config).
*   `GEMINI_API_KEY`: Google Gemini platform developer API key.
*   `PYANNOTE_AUTH_TOKEN`: Hugging Face read access token to download Pyannote pipelines.
*   `WHISPER_MODEL`: Local Whisper size model (`base`, `tiny`, `small`).
*   `WHISPER_DEVICE`: Local device execution mapping (`cpu` or `cuda`).

---

## 🧪 Running Tests

To run the complete automated test suite (37 tests covering DB operations, upload file limits, background pipeline state machines, transcription, diarization, Gemini scorecards, and appeals updates):

```bash
python -m pytest backend/tests/
```

---

## 📷 Screenshots
*Expects real application screenshots demonstrating manager dashboards, call scorecards, and dispute appeals tabs.*

*   **Dashboard Overview**: `docs/dashboard.png` (Placeholder)
*   **Upload Form**: `docs/upload.png` (Placeholder)
*   **AI Analysis**: `docs/analysis.png` (Placeholder)
*   **Appeals Review**: `docs/manager_dashboard.png` (Placeholder)
*   **Pipeline Status**: `docs/pipeline.png` (Placeholder)

---

## 🚀 Future Improvements
1.  **JWT Authentication**: Incorporate active security tokens and role-based permissions validation.
2.  **Appeal Notifications**: Notify advisors automatically when managers resolve disputes.
3.  **Real-Time Pipelines**: Transition uploader pipelines to streaming WebSockets for live transcript rendering.

---

## 📄 License
This project is licensed under the MIT License.
