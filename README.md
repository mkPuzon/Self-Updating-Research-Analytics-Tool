# AURA: AI Understanding, Research, and Analytics glossary for AI education

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

AURA is a self-updating glossary built upon an end-to-end data pipeline that automates the analysis of academic papers, enabling better understand of trends in cutting-edge AI research. The system fetches the latest AI-related papers from arXiv, extracts and cleans data, formats data in machine readable formats, and prepares data for further analysis and display.

This project features a Streamlit dashboard for developer metrics as well as an Nginx container for a full web frontend to display data.

## Features

- **Automated Paper Collection**: Fetches latest AI research papers from arXiv.
- **Text Extraction**: Extracts and cleans text from pdf in a structured manner for easy analysis with LLMs.
- **Keyword and Definition Extraction**: Uses Gemma3 and Llama3.3 to identify key terms, ideas, and their definitions.
- **Database Integration**: Uses SQLite to store data for analysis and retrieval.
- **Modular Design**: Easy to extend with new processing modules and data sources.

## Components

1. **`update_db.sh`**: Main script that orchestrates the entire pipeline; designed to be run daily.
2. **`full_scraper.py`**: Handles paper retrieval from arXiv and PDF downloading.
3. **`process_text.py`**: Processes paper text to extract keywords and definitions using locally run LLMs.
4. **`scrapers.py`**: Contains web scraping utilities and API interactions.
5. **`db_functions.py`**: Manages database operations.
## Getting Started

### Prerequisites
- Python 3.11.4+
- PostgreSQL (for database functionality)
- Ollama (for local LLM inference)
- Required Python packages (install via `pip install -r requirements.txt`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mkPuzon/AURA.git
   cd AURA
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Create a `.env` file in the project root
   - Add required API keys and configurations (see `.env.example` if available)

### Usage

Run the main pipeline:
```bash
./update_db.sh
```

This will:
1. Fetch new papers from arXiv
2. Download and process PDFs
3. Extract text and analyze content
4. Update the database with new findings

## Current TODOs
This project is currently being containerized and we are migrating from PostgreSQL to SQLite.

- [X] Working project MVP w/ PostgreSQL
- [X] Set up container project structure
   - [X] Confirm docker compose runs base project

- [ ] processor
   - [X] Fix imports and streamline logic
   - [X] Set up option to query OpenAI models
   - [ ] Switch db logic to SQLite

- [ ] dashboard
   - [ ] Connect to new db and display basic stats

- [ ] front end
   - [ ] Get front end up and running in Docker container
   - [ ] Connect to SQLite db

- [ ] Write Python-native automated scripts
   - [ ] General logging for volume and quality of extracted text
   - [X] Delete locally stored files

- [ ] Create reports for model timing/cost statistics 

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thank you to [arXiv](https://arxiv.org/) for use of its open access interoperability.
