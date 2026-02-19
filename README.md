# AURA: AI Understanding, Research, and Analytics glossary for AI education

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

AURA is a self-updating glossary built upon an end-to-end data pipeline that automates the analysis of academic papers, enabling better understanding of trends in cutting-edge AI research. The system fetches the latest AI-related papers from arXiv, extracts and cleans text from PDFs, uses LLMs to identify keywords and definitions, and stores results in a SQLite database.

## Features

- **Automated Paper Collection**: Fetches latest AI research papers from arXiv daily.
- **Text Extraction**: Extracts and cleans text from PDFs using pypdf or docling.
- **Keyword and Definition Extraction**: Uses local LLMs (Gemma3, Llama3.3) or OpenAI to identify key terms and their definitions.
- **Database Integration**: SQLite database with WAL mode for concurrent access.
- **Web Frontend**: Nginx-served frontend with a searchable "river" view of AI terminology.
- **Analytics Dashboard**: Streamlit dashboard for backend metrics (daily scraping activity, category distribution).
- **Fully Containerized**: Four-service Docker Compose setup with shared data volume.

## Architecture

```
┌────────────┐     ┌──────────┐     ┌─────────────┐
│  Processor │────>│  SQLite  │<────│  Dashboard  │
│  (Python)  │     │ aura.db  │     │ (Streamlit) │
└────────────┘     └────┬─────┘     └─────────────┘
                        │               :8501
                   ┌────┴─────┐
                   │   API    │
                   │ (FastAPI)│
                   └────┬─────┘
                        │ :8000
                   ┌────┴─────┐
                   │  Nginx   │──── :80 (frontend)
                   └──────────┘
```

| Service | Description | Port |
|---------|-------------|------|
| **processor** | Daily pipeline: scrapes arXiv, downloads PDFs, extracts text, runs LLM keyword/definition extraction, writes to SQLite | internal |
| **api** | FastAPI service exposing `/terms` and `/terms/{id}` endpoints for the frontend | 8000 (internal) |
| **dashboard** | Streamlit analytics dashboard for scraping metrics and category distribution | 8501 |
| **nginx** | Serves the static frontend and reverse-proxies `/api/` requests to FastAPI | 80 |

### Main Components

| File | Purpose |
|------|---------|
| `processor/main.py` | Orchestrates the daily pipeline and scheduling |
| `processor/src/scrapers.py` | arXiv metadata retrieval |
| `processor/src/scrape_papers.py` | PDF downloading and text extraction |
| `processor/src/process_text.py` | LLM-based keyword and definition extraction |
| `processor/src/db_functions.py` | SQLite database operations |
| `processor/src/logger_config.py` | Logging configuration |
| `processor/src/metrics.py` | Pipeline metrics collection |
| `api/main.py` | FastAPI endpoints connecting SQLite to the frontend |
| `dashboard/app.py` | Streamlit analytics dashboard |
| `nginx/html/` | Static frontend (HTML, JS, CSS) |
| `nginx.conf` | Nginx reverse proxy configuration |

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- [Ollama](https://ollama.com/) (for local LLM inference) or an OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mkPuzon/Self-Updating-Research-Analytics-Tool.git
   cd Self-Updating-Research-Analytics-Tool
   ```

2. Create a `.env` file in the project root with the following variables:
   ```env
   OLLAMA_API=http://host.docker.internal:11434/api/generate
   OPENAI_KEY=your-key-here
   KEYWORD_PROMPT_1=your-keyword-extraction-prompt
   DEFINTION_PROMPT_1=your-definition-extraction-prompt
   ```

3. Start all services:
   ```bash
   docker compose up -d --build
   ```

### Usage

Once running, the services are available at:

- **Frontend**: [http://localhost](http://localhost) — searchable glossary of AI terms
- **Dashboard**: [http://localhost:8501](http://localhost:8501) — backend analytics
- **API**: [http://localhost/api/terms](http://localhost/api/terms) — JSON endpoint (proxied through Nginx)

The processor runs daily at 2:00 AM, scraping new papers and updating the database. Old PDFs are only stored for debugging/quality checks and are automatically cleaned up after 7 days.

### Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate

# Run processor
pip install -r processor/requirements.txt
cd processor && python main.py

# Run dashboard
pip install -r dashboard/requirements.txt
cd dashboard && streamlit run app.py
```

## Data Storage

```
data/
├── aura.db                         # SQLite database
├── pdfs/papers_YYYY-MM-DD/         # Downloaded PDFs (auto-deleted after 7 days)
├── metadata/metadata_YYYY-MM-DD.json  # Daily paper metadata
└── logs/                           # Pipeline logs
```

## Current TODOs
This project is still in progress. Up next we are working on...

- [X] Working project MVP w/ PostgreSQL
- [X] Set up container project structure
- [X] Processor: fix imports, streamline logic, switch to SQLite, add OpenAI support
- [X] Dashboard: connect to SQLite, display scraping metrics and category distribution
- [X] Frontend: Nginx container serving web UI, connected to SQLite via FastAPI
- [X] Automated scripts: logging, PDF cleanup
- [ ] Fix search bar on river frontend page
- [ ] Add paper links to keyword page
- [ ] Create reports for model timing/cost statistics in Streamlit dashboard

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Thank you to [arXiv](https://arxiv.org/) for use of its open access interoperability.
