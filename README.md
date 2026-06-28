# Quant Research Copilot — Multi-Agent Stock Screening Terminal

A production-grade, multi-agent stock screening system that translates natural language queries into BigQuery SQL, fetches real-time news, synthesizes cross-referenced signals, and generates professional research reports — all powered by NVIDIA NIM LLMs with Groq fallback.

🔗 [**Live Demo**](https://stock-screener-private.onrender.com/)

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Agent Pipeline](#agent-pipeline)
  - [Orchestrator Agent](#1-orchestrator-agent)
  - [Screener Agent](#2-screener-agent)
  - [SQL Refiner Agent](#3-sql-refiner-agent)
  - [News Agent](#4-news-agent)
  - [Synthesis Agent](#5-synthesis-agent)
  - [Report Agent](#6-report-agent)
- [Supported Indicators](#supported-indicators)
- [Frontend](#frontend)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Deployment](#deployment)

---

## System Architecture

```
User Query (Natural Language)
        │
        ▼
┌──────────────────┐
│  ORCHESTRATOR    │  Parses intent → SCREEN / NEWS / SCREEN_AND_NEWS
│  (Intent Router) │
└────────┬─────────┘
         │
    ┌────┴────────────────────────┐
    │                             │
    ▼                             ▼
┌──────────┐              ┌────────────┐
│ SCREENER │              │    NEWS    │
│  Agent   │              │   Agent    │
│          │              │            │
│ Extract  │              │ RSS Feeds  │
│ Params → │              │ (Google +  │
│ Build SQL│              │  ET Mkts)  │
│ → BQ Exec│              │ → Classify │
└────┬─────┘              └─────┬──────┘
     │                          │
     │   ┌──────────┐           │
     ├──►│ REFINER  │           │
     │   │  Agent   │           │
     │   │ (SQL Fix)│           │
     │   └──────────┘           │
     │                          │
     └──────────┬───────────────┘
                │
                ▼
        ┌──────────────┐
        │  SYNTHESIS   │  Cross-references screener + news
        │    Agent     │  → STRONG / WATCH / CAUTION signal
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │   REPORT     │  Generates professional markdown
        │    Agent     │  research report
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │  VISUALIZER  │  Plotly bar charts for all
        │   (Charts)   │  numeric metrics
        └──────────────┘
```

---

## Agent Pipeline

### 1. Orchestrator Agent

**File:** `backend/agents/orchestrator.py`

The entry point of the system. It receives the raw user query and uses the LLM to parse it into a structured JSON action.

**Responsibilities:**
- Classify the user's intent into one of: `SCREEN`, `NEWS`, `SCREEN_AND_NEWS`, `COMPARE`, `DEEP_DIVE`
- Extract relevant indicators, sector filters, and stock symbols from natural language
- Map abbreviations (e.g., "IT" → "Information Technology") to exact sector names from a curated list of 23 Indian market sectors
- Route the parsed intent to the appropriate downstream agents

**Example:**
```
Input:  "Find IT stocks with P/E below 20 and positive cash flow"

Output: {
  "action": "SCREEN",
  "indicators": [
    {"id": "sector_filter", "params": {"value": "Information Technology"}},
    {"id": "live_pe", "params": {"operator": "<", "value": 20}},
    {"id": "cfo_positive", "params": {}}
  ]
}
```

---

### 2. Screener Agent

**File:** `backend/agents/screener.py`

The core engine that translates parsed indicators into executable BigQuery SQL. It maintains a library of 15+ indicator templates, each mapping to real BigQuery table schemas.

**Responsibilities:**
- **Parameter Extraction:** Uses a separate LLM call with slot-filling prompts to extract precise indicator IDs and their parameters
- **SQL Generation:** Each indicator has a pre-built BigQuery SQL template (CTE-based) that gets parameterized at runtime
- **Dynamic JOIN Composition:** When multiple indicators are requested, the agent dynamically composes them using `INNER JOIN` on `nse_symbol`, ensuring only stocks that pass ALL filters are returned
- **Resilience Layer:** Handles common LLM hallucinations (e.g., `max` instead of `value` for P/E) and pre-calculates BigQuery-incompatible expressions (e.g., `period - 1` for window frames)
- **Bank-Aware Schema:** Automatically switches between bank and non-bank column names (e.g., `Revenue` vs `Sales`, `Financing_Margin` vs `OPM`)

**Data Sources (4 BigQuery Datasets):**
| Dataset | Tables | Description |
|---------|--------|-------------|
| `fundamentals` | `quarterly_results`, `company_info`, `cash_flows`, `shareholding_quarterly` | Financial statements, sector classification, institutional holdings |
| `technicals` | `daily_stock_price` | OHLCV price data with 200+ day history |
| `earnings` | Earnings calendar | Upcoming earnings dates |
| `stocks` | Stock metadata | NSE symbol registry |

---

### 3. SQL Refiner Agent

**File:** `backend/agents/refiner.py`

A self-healing agent that sits between the template engine and BigQuery execution. It catches nuances that rigid templates cannot handle.

**Responsibilities:**
- Takes the base template-generated SQL and the original user query
- Adds `ORDER BY`, `LIMIT`, and additional `WHERE` clauses that the template engine couldn't infer
- Ensures column references in `ORDER BY` actually exist in the `SELECT` projection
- Falls back gracefully to the base template query if the refined query fails execution

**Example:**
```
User Query:  "Top 3 IT stocks by lowest P/E"

Base SQL:    SELECT t0.nse_symbol, t1.live_pe FROM (...) t0 INNER JOIN (...) t1 ...
Refined SQL: SELECT t0.nse_symbol, t1.live_pe FROM (...) t0 INNER JOIN (...) t1 ... ORDER BY t1.live_pe ASC LIMIT 3
```

---

### 4. News Agent

**File:** `backend/agents/news.py`

Fetches and classifies real-time news from RSS feeds using a 3-tier intelligence hierarchy.

**Responsibilities:**
- **Entity-Level News:** Fetches stock-specific news from Google News RSS (limited to ≤3 symbols to prevent API burnout)
- **Sector-Level News:** Fetches sector-wide news when a sector filter is detected
- **Macro-Level News:** Falls back to ET Markets RSS for broad Indian market updates
- **LLM Classification:** Each article is individually classified by the LLM for:
  - `relevant`: Is the article actually relevant to the target?
  - `sentiment`: `POSITIVE` / `NEGATIVE` / `NEUTRAL`
  - `category`: `EARNINGS` / `REGULATORY` / `MANAGEMENT` / `PRODUCT` / `MACRO` / `OTHER`
  - `summary`: One-sentence summary

**Feed Sources:**
- Google News RSS (parameterized queries, India region)
- Economic Times Markets RSS (general market feed)

---

### 5. Synthesis Agent

**File:** `backend/agents/synthesis.py`

The intelligence fusion layer that cross-references screening results with news data to produce actionable trading signals.

**Responsibilities:**
- Takes the screener output (stocks that passed fundamental/technical filters) and the classified news data
- Assigns each stock a signal:
  - **STRONG:** Good fundamentals + positive/neutral news
  - **WATCH:** Good fundamentals + mixed or concerning news
  - **CAUTION:** Good fundamentals + negative news
- Generates per-stock summaries including fundamental reasoning, news highlights, and risk flags
- Provides sector-level and macro-level context observations

**Output Structure:**
```json
{
  "stocks": [
    {
      "symbol": "ITC",
      "signal": "STRONG",
      "fundamental_summary": "Why it passed the screen",
      "news_summary": "Key news highlights",
      "risk_flags": ["any concerns"]
    }
  ],
  "sector_context": "Sector-level observations",
  "macro_context": "Market-level observations"
}
```

---

### 6. Report Agent

**File:** `backend/agents/report.py`

The final presentation layer that transforms the structured synthesis data into a professional, human-readable markdown research report.

**Responsibilities:**
- Generates a comprehensive research note with:
  1. Executive Summary (2-3 sentences)
  2. Screened Stocks table with key metrics
  3. News Digest organized by sentiment
  4. Stock-by-stock signal breakdown
  5. Risk flags and disclaimers
- Uses `enable_thinking: True` mode for deeper reasoning
- Output is rendered as rich markdown with GFM tables in the frontend

---

## Supported Indicators

| Indicator | Description | Key Parameters |
|-----------|-------------|---------------|
| `live_pe` | Live P/E ratio (current price / TTM EPS) | `operator` (`<`, `>`, `=`), `value` |
| `pe_below_sector_median` | P/E below the median of its sector | — |
| `margin_improving` | Operating margin improving over N quarters | `quarters` |
| `revenue_growth_yoy` | Year-over-year revenue growth above threshold | `min_pct` |
| `smart_money_inflow` | Both FII + DII increasing stake | `quarters` |
| `cfo_positive` | Positive cash from operations | — |
| `near_52_week_high` | Price within X% of 52-week high | `within_pct` |
| `above_200_sma` | Price above 200-day SMA with margin buffer | `min_margin_pct` |
| `supertrend_bullish` | Supertrend indicator showing bullish signal | `period`, `multiplier` |
| `sector_filter` | Filter by sector (23 Indian market sectors) | `value` |

---

## Frontend

The frontend is a Next.js application with three dedicated agent pages:

| Page | Purpose |
|------|---------|
| **Knowledge Base** | Landing page with all supported indicators and example queries |
| **Query Agent** | Natural language stock screening with results table and Plotly charts |
| **News Agent** | Standalone news intelligence with entity/sector/macro feeds |
| **Report Agent** | Full research report generation with markdown rendering and PDF export |

**Key Features:**
- **Session Memory:** Each agent page persists its results in `sessionStorage`, so switching between tabs retains previous outputs
- **PDF Export:** Reports can be downloaded as clean, printer-friendly PDFs using `html2pdf.js` with print-optimized CSS
- **Interactive Charts:** Plotly bar charts are auto-generated for every numeric metric returned by the screener
- **GFM Tables:** Markdown tables are rendered using `remark-gfm` for proper formatting

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React, TypeScript, Plotly.js, remark-gfm, html2pdf.js |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **LLM (Primary)** | NVIDIA NIM — DiffusionGemma 26B-A4B-IT |
| **LLM (Fallback)** | Groq Cloud — LLaMA 3.3 70B Versatile |
| **Database** | Google BigQuery (4 datasets, 6+ tables) |
| **News** | Google News RSS, ET Markets RSS, feedparser |
| **Visualization** | Plotly Express (server-side chart generation) |
| **Agent Framework** | LangGraph |
| **Deployment** | Docker (multi-stage), Render |

---

## Project Structure

```
genai-project-idea/
├── Dockerfile                     # Multi-stage build (Node + Python)
├── requirements.txt               # Root-level Python dependencies
│
├── backend/
│   ├── main.py                    # FastAPI app + static file serving
│   ├── config.py                  # Centralized env configuration
│   ├── requirements.txt           # Python dependencies
│   │
│   ├── agents/
│   │   ├── orchestrator.py        # Intent parsing & routing
│   │   ├── screener.py            # BigQuery SQL execution
│   │   ├── refiner.py             # Self-healing SQL refinement
│   │   ├── news.py                # RSS fetching & classification
│   │   ├── synthesis.py           # Signal fusion (STRONG/WATCH/CAUTION)
│   │   └── report.py             # Markdown report generation
│   │
│   ├── llm/
│   │   ├── provider.py            # NVIDIA NIM + Groq fallback
│   │   └── prompts.py            # All system/user prompts
│   │
│   ├── templates/
│   │   └── indicators.py          # 10+ BigQuery SQL templates
│   │
│   └── utils/
│       └── visualizer.py          # Plotly chart generation
│
└── frontend/
    ├── next.config.ts              # Static export configuration
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx            # Knowledge Base (landing)
    │   │   ├── screener/page.tsx   # Query Agent
    │   │   ├── news/page.tsx       # News Agent
    │   │   └── report/page.tsx     # Report Agent + PDF export
    │   ├── components/
    │   │   ├── Sidebar.tsx         # Navigation sidebar
    │   │   └── ChatInput.tsx       # Reusable query input with session memory
    │   ├── data/
    │   │   └── indicators.ts       # Indicator metadata for Knowledge Base
    │   └── lib/
    │       └── api.ts              # Axios client with env-aware routing
    └── package.json
```

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Cloud service account with BigQuery access
- NVIDIA NIM API key
- Groq API key (fallback)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:
```env
NVIDIA_API_KEY=your_nvidia_api_key
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=google/diffusiongemma-26b-a4b-it

GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile

GCP_PROJECT_ID=your-project-id
GCP_SERVICE_ACCOUNT_PATH=path/to/service_account.json
BQ_DATASET_FUNDAMENTALS=fundamentals
BQ_DATASET_TECHNICALS=technicals
BQ_DATASET_EARNINGS=earnings
BQ_DATASET_STOCKS=stocks

HOST=0.0.0.0
PORT=8000
```

```bash
python main.py
# Backend runs on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

---

## Deployment

The application is deployed as a **single Docker container** on Render's free tier. The multi-stage `Dockerfile` builds the Next.js frontend into static HTML and serves it alongside the FastAPI backend on the same port.

```bash
# Build locally (optional)
docker build -t quant-copilot .
docker run -p 8000:8000 --env-file backend/.env quant-copilot
```

**Environment Variables (Render Dashboard):**
- `NVIDIA_API_KEY` — NVIDIA NIM API key
- `GROQ_API_KEY` — Groq fallback API key
- `GCP_SERVICE_ACCOUNT_PATH` — Path to service account secret file (`/etc/secrets/service-account.json`)
- BigQuery dataset names (`BQ_DATASET_FUNDAMENTALS`, etc.)

**Secret Files (Render Dashboard):**
- `service-account.json` — Google Cloud service account credentials

---

## License

This project is for educational and personal portfolio purposes.
