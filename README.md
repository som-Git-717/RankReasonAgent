# Spike AI Builder Hackathon - AI Backend

## Overview
This project is an AI-powered backend designed to answer natural language questions about Web Analytics (GA4) and SEO Audits (Screaming Frog). It exposes a single HTTP POST API endpoint and utilizes a multi-agent architecture to orchestrate tasks between specialized agents.

## Architecture
The system follows a modular architecture:
1.  **API Layer (`src/main.py`)**: A FastAPI application serving the `/query` endpoint.
2.  **Orchestrator**: Determines the intent of the user's query and routes it to the appropriate agent.
3.  **Agents**:
    *   **Analytics Agent (Tier 1)**: Interfaces with the Google Analytics 4 Data API to retrieve live traffic and user data. It uses LLMs to translate natural language into structured API requests.
    *   **SEO Agent (Tier 2)**: Interfaces with the **Google Sheets API**. It fetches live data from Screaming Frog exports  and performs filtering, aggregation, and analysis using Python code execution.
    *   **Multi-Agent System (Tier 3)**: Combines insights from both GA4 and SEO data for complex reasoning.

## Setup Instructions

### Prerequisites
*   **Python 3.10+** (or use the provided `deploy.sh` which handles environments).
*   A valid `credentials.json` file for Google Analytics/Sheets API access in the project root.
*   A `propertyId` for GA4 queries.
*   A `.env` file containing the `LITELLM_API_KEY`.

### Installation & Running
The project includes a `deploy.sh` script for automated setup and execution.

```bash
./deploy.sh
```

This script will:
1.  Check for `uv` or `python3-venv`.
2.  Create a virtual environment (`.venv`).
3.  Install dependencies from `requirements.txt`.
4.  Start the server on port 8080.

### API Usage
**Tip:** Add `-w "\n"` to your curl commands to ensure the output ends with a newline for better readability.

**Example Command:**
```bash
curl -X POST http://localhost:8080/query \
-H "Content-Type: application/json" \
-d '{"query": "Which URLs do not use HTTPS and have title tags longer than 60 characters?"}' \
-w "\n"
```

**Endpoint:** `POST http://localhost:8080/query`

**Request Body (GA4):**
```json
{
  "propertyId": "YOUR_GA4_PROPERTY_ID",
  "query": "How many users visited the site in the last 7 days?"
}
```

**Request Body (General/SEO):**
```json
{
  "query": "Which URLs do not use HTTPS and have title tags longer than 60 characters?"
}
```

## Configuration (Important)

### Changing the Google Sheet Source
The SEO Agent is configured to fetch data from the specific Google Sheet provided in the problem statement. 

If needed to evaluate against a **different Google Sheet**:

1.  Open `src/agents/seo_agent.py`.
2.  Update the `self.spreadsheet_id` variable with the ID of your new sheet (around line 10).

```python
# src/agents/seo_agent.py

class SEOAgent:
    def __init__(self):
        # REPLACE THIS ID with the new Spreadsheet ID
        self.spreadsheet_id = "1zzf4ax_H2WiTBVrJigGjF2Q3Yz-qy2qMCbAMKvl6VEE" 
        ...
```

**Note:** The new sheet must follow standard Screaming Frog export conventions for the agent to function correctly.

### Credentials
This repository does NOT include any real credentials.
Users must provide their own credentials and API keys.

#### Required Files (User-Provided)
1. credentials.json
  - A **Google Cloud Service Account JSON key**
  - **Must have permissions for:**
    - Google Analytics Admin API
    - Google Analytics Data API
    - Google Analytics API
    - Google Sheets API
  - **Update this file in the project root**
2. .env **file**
  - Update the placeholder with your api key 

## Data Source Integrations
*   **Google Analytics 4**: Accessed via the `google-analytics-data` Python client. Requires a service account JSON key (`credentials.json`).
*   **Screaming Frog**: Data is ingested from Google Sheets using the **Google Sheets API** (authenticated).
*   **LiteLLM**: Used for natural language understanding and reasoning, proxying requests to Google's Gemini models.

## Key Design Decisions
*   **Google Sheets API:** Used instead of raw CSV exports to ensure robust, authenticated access to all tabs (fixing missing metadata issues in the provided link).
*   **Safe Code Execution:** SEO analysis runs in a restricted Python `exec()` scope with explicit type conversion for numeric stability.
*   **Portable Deployment:** `deploy.sh` auto-installs `uv` for fast, dependency-free environment setup.

## Assumptions and Limitations
*   The system assumes `credentials.json` is valid and has necessary permissions for both GA4 and the target Google Sheet.
*   The system assumes the provided Sheet link (`gid=1438203274`) was intended to share the entire workbook.
*   The server binds to port 8080 as strictly required.

