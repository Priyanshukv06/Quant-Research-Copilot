# Quant Research Copilot

**An agentic, multi-agent stock screening terminal that translates natural language queries into BigQuery SQL, aggregates real-time news from 5+ sources, synthesizes cross-referenced trading signals, and generates professional research reports — powered by a 5-provider LLM router with automatic failover.**

🔗 [**Live Demo**](https://stock-screener-private.onrender.com/)

---

## System Architecture

```
User Query (Natural Language)
        │
        ▼
┌──────────────────────┐
│   ORCHESTRATOR       │   Parses intent → SCREEN / NEWS / SCREEN_AND_NEWS
│   (Intent Router)    │
└──────────┬───────────┘
           │
    ┌──────┴──────────────────────────────┐
    │                                      │
    ▼                                      ▼
┌──────────────┐                  ┌─────────────────┐
│   SCREENER   │                  │   NEWS AGENT    │
│   Agent      │                  │   (v2 Pipeline) │
│              │                  │                 │
│ NL → Params  │                  │ 5 Sources:      │
│ → SQL Build  │                  │  Google News    │
│ → SQL Refine │                  │  ET Markets     │
│ → BQ Execute │                  │  Moneycontrol   │
└──────┬───────┘                  │  GNews API      │
       │                          │  NewsData.io    │
       │   ┌──────────────┐       │                 │
       │   │ SQL REFINER  │       │ Parallel Fetch  │
       │   │ (LLM-based)  │       │ → Dedup         │
       │   │              │       │ → Batch Classify │
       │   │ Adds ORDER   │       │ → Cache (15min) │
       │   │ BY / LIMIT   │       └────────┬────────┘
       │   └──────────────┘                │
       │                                   │
       └──────────┬────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │   SYNTHESIS    │   Cross-references screening metrics
         │   Agent        │   with news sentiment → STRONG / WATCH / CAUTION
         └───────┬────────┘
                 │
                 ▼
         ┌────────────────┐
         │   REPORT       │   Generates polished markdown report
         │   Agent        │   with signal table, analysis, disclaimers
         └───────┬────────┘
                 │
                 ▼
         ┌────────────────┐
         │  VISUALIZER    │   Plotly.js comparison charts
         └───────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │   Next.js UI    │   4 pages: Knowledge Base, Query Agent,
        │   (React 19)    │   News Agent, Report Agent
        └─────────────────┘
```

---

## Agent Pipeline

### 1. Orchestrator Agent

Parses every user query into a structured JSON intent using the LLM:

```json
{
  "action": "SCREEN_AND_NEWS",
  "indicators": [{"id": "live_pe", "params": {"operator": "<", "value": 25}}],
  "sector_filter": "Information Technology",
  "symbols": ["TCS", "INFY"],
  "news_query": "IT sector outlook"
}
```

**Supported actions:** `SCREEN` · `NEWS` · `SCREEN_AND_NEWS`

---

### 2. Screener Agent

Translates parsed indicators into BigQuery SQL using a **template engine** with 20+ indicator templates. Each template maps to a validated CTE that queries fundamentals, technicals, or earnings datasets.

**Pipeline:** Natural language → LLM slot-fill → Template SQL → SQL Refiner → BigQuery execution

---

### 3. SQL Refiner Agent

An LLM-based post-processor that enhances the rigid template-generated SQL with user-specific constraints:

- `"Top 3 stocks"` → Adds `ORDER BY ... LIMIT 3`
- `"Lowest PE"` → Adds `ORDER BY live_pe ASC`
- `"Sort by market cap"` → Adds `ORDER BY ...`

Falls back to the base template query if the refined SQL fails execution.

---

### 4. News Agent (v2 — Multi-Source Intelligence Pipeline)

A complete multi-source news aggregation system that replaced the original single-source RSS scraper:

| Feature | Details |
|---------|---------|
| **Sources** | Google News RSS, ET Markets RSS, Moneycontrol RSS, GNews API, NewsData.io API |
| **Fetching** | Parallel via `asyncio.gather` across all sources |
| **Deduplication** | Fuzzy title matching using `difflib` (stdlib) |
| **Classification** | Single batch LLM call classifies all articles (was 1 call per article) |
| **Caching** | 15-minute TTL, configurable via `NEWS_CACHE_TTL_SECONDS` |
| **News Levels** | Entity (per-stock), Sector, Macro (always-on baseline) |

RSS sources work without any API keys. GNews and NewsData.io are optional bonus layers.

---

### 5. Synthesis Agent

Cross-references screening metrics with news intelligence to assign trading signals:

| Signal | Meaning |
|--------|---------|
| 🟢 **STRONG** | Good fundamentals + positive/neutral news |
| 🟡 **WATCH** | Good fundamentals + mixed signals or limited news |
| 🔴 **CAUTION** | Good fundamentals + negative news or risk flags |

**Features:**
- Input truncation — caps at 10 stocks, summarizes news to counts + top headlines
- Output schema validation — fills missing fields with sensible defaults
- Adds `overall_market_stance` (BULLISH / NEUTRAL / BEARISH)

---

### 6. Report Agent

Generates a professional markdown research report with a prescribed structure:

```
📊 Quant Research Report
├── Query / Date / Stocks Analyzed (metadata header)
├── Executive Summary
├── Signal Overview (emoji table: 🟢🟡🔴)
├── Detailed Analysis (per-stock with actual numbers)
├── Market Context (sector + macro observations)
└── Risk Flags & Disclaimers
```

**Features:**
- Accepts raw screening metrics alongside synthesis for actual numbers
- Smart truncation of synthesis data to prevent context overflow
- Returns structured metadata: timestamp, signal distribution, market stance

---

## LLM Router — 5-Provider Failover

The system uses a **priority-ordered, multi-provider LLM router** that automatically handles rate limits, auth failures, and server errors across 5 providers:

```
Gemini → Groq → Mistral → NVIDIA NIM → OpenRouter
```

| Feature | Details |
|---------|---------|
| **Providers** | Gemini, Groq, Mistral, NVIDIA NIM, OpenRouter |
| **Keys per provider** | Multiple (comma-separated), round-robin load balanced |
| **Failover** | On rate-limit (429), retries same model on next key before falling to next provider |
| **Cooldowns** | Rate-limit: 45s · Server error: 20s · Auth failure: 1hr |
| **Model chain** | 15+ models ranked by capability, strongest first |
| **Cost** | 100% free tier — all providers offer free API keys |

---

## Supported Screening Indicators

### Fundamental
`live_pe` · `pe_below_sector_median` · `margin_improving` · `revenue_growth_yoy` · `eps_growth_yoy` · `net_profit_margin`

### Ownership
`promoter_holding_increasing` · `fii_buying` · `dii_buying` · `smart_money_inflow`

### Financial Health
`debt_to_equity` · `reserves_growing` · `cfo_positive` · `free_cash_flow_positive` · `roce_above` · `roe_above`

### Technical
`above_200_sma` · `near_52_week_high` · `volume_spike` · `momentum_positive` · `supertrend_bullish`

### Filters
`sector_filter` (23 NIFTY sectors) · `market_cap_range` · `earnings_within_days`

### Banking-Specific
`npa_decreasing` · `deposit_growth`

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.11) |
| Database | Google BigQuery (fundamentals, technicals, earnings datasets) |
| LLM | OpenAI-compatible API via multi-provider router |
| News | feedparser (RSS) + aiohttp (API sources) |
| Visualization | Plotly (server-side chart generation) |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | Next.js 16 (React 19, App Router) |
| Charts | react-plotly.js |
| Markdown | react-markdown + remark-gfm |
| PDF Export | html2pdf.js |
| Icons | lucide-react |
| HTTP | axios |

### Deployment
| Component | Technology |
|-----------|-----------|
| Container | Docker (multi-stage: Node.js build → Python runtime) |
| Hosting | Render (free tier, auto-deploy from GitHub) |
| Architecture | Unified — FastAPI serves both API + static frontend |

---

## Project Structure

```
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py    # Intent parsing + action routing
│   │   ├── screener.py        # NL → SQL → BigQuery execution
│   │   ├── refiner.py         # LLM-based SQL post-processing
│   │   ├── news.py            # Multi-source news pipeline (v2)
│   │   ├── sources.py         # Pluggable news source adapters
│   │   ├── synthesis.py       # Cross-reference screening + news
│   │   └── report.py          # Markdown report generation
│   ├── llm/
│   │   ├── router.py          # 5-provider failover router
│   │   ├── models.py          # Model registry (15+ models)
│   │   ├── providers.py       # Provider endpoints + key handling
│   │   ├── provider.py        # Unified LLM interface
│   │   └── prompts.py         # All LLM prompts (structured)
│   ├── templates/
│   │   └── indicators.py      # 20+ BigQuery SQL templates
│   ├── utils/
│   │   └── visualizer.py      # Plotly chart generation
│   ├── config.py              # Centralized settings from .env
│   ├── main.py                # FastAPI app + routing
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Knowledge Base (home)
│   │   │   ├── screener/page.tsx  # Query Agent
│   │   │   ├── news/page.tsx      # News Agent
│   │   │   └── report/page.tsx    # Report Agent
│   │   ├── components/
│   │   │   ├── Sidebar.tsx        # Navigation sidebar
│   │   │   └── ChatInput.tsx      # Reusable search input
│   │   └── lib/
│   │       └── api.ts             # API client
│   ├── package.json
│   └── next.config.ts         # Static export config
├── Dockerfile                 # Multi-stage build
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud service account with BigQuery access
- At least one LLM API key (Gemini recommended — free, 1M context)

### 1. Clone the Repository

```bash
git clone https://github.com/Priyanshukv06/STOCK_SCREENER_PRIVATE.git
cd STOCK_SCREENER_PRIVATE
```

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create `backend/.env` by copying the structure below and filling in your API keys:

```env
# LLM API Keys (comma-separated for multiple keys per provider)
GEMINI_API_KEYS=your_gemini_key_1,your_gemini_key_2
GROQ_API_KEYS=your_groq_key
MISTRAL_API_KEYS=your_mistral_key
NVIDIA_API_KEYS=your_nvidia_key
OPENROUTER_API_KEYS=your_openrouter_key

# BigQuery
GCP_PROJECT_ID=your-gcp-project
GCP_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
BQ_DATASET_FUNDAMENTALS=fundamentals
BQ_DATASET_TECHNICALS=technicals
BQ_DATASET_EARNINGS=earnings
BQ_DATASET_STOCKS=stocks

# News API Keys (optional — RSS works without these)
GNEWS_API_KEY=your_gnews_key
NEWSDATA_API_KEY=your_newsdata_key
NEWS_CACHE_TTL_SECONDS=900

# Server
HOST=0.0.0.0
PORT=8000
```

**Where to get API keys:**

| Provider | Free Tier | Link |
|----------|-----------|------|
| Gemini | 1M context, generous RPM | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Groq | ~14,400 req/day | [console.groq.com/keys](https://console.groq.com/keys) |
| Mistral | ~1B tokens/month | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys) |
| NVIDIA NIM | Credit-based | [build.nvidia.com](https://build.nvidia.com) |
| OpenRouter | ~20 RPM free | [openrouter.ai/keys](https://openrouter.ai/keys) |
| GNews | 100 req/day | [gnews.io](https://gnews.io) |
| NewsData.io | 200 credits/day | [newsdata.io](https://newsdata.io) |

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Run Locally

**Terminal 1 — Backend:**
```bash
cd backend
python main.py
# Runs at http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
# Runs at http://localhost:3000
```

Open **http://localhost:3000** in your browser.

---

## Deployment (Docker + Render)

### Build & Run with Docker

```bash
docker build -t quant-copilot .
docker run -p 8000:8000 --env-file backend/.env quant-copilot
```

The Docker image uses a multi-stage build:
1. **Stage 1:** Node.js builds the Next.js frontend as a static export
2. **Stage 2:** Python serves both the FastAPI API and the static frontend

### Deploy to Render

1. Push to GitHub
2. Create a **Web Service** on [Render](https://render.com)
3. Connect your GitHub repository
4. Set **Build Command:** `docker` (auto-detected from Dockerfile)
5. Add all environment variables from `.env` in Render's dashboard
6. Deploy — Render auto-deploys on every push to `main`

---

## Example Queries

| Query | Action | What Happens |
|-------|--------|-------------|
| *"Find top 5 IT stocks with PE below 30"* | `SCREEN` | Screens BigQuery, returns table + charts |
| *"Latest news for TCS and Infosys"* | `NEWS` | Aggregates from 5 sources, classifies, displays by stock |
| *"Find IT stocks with low PE and check their news"* | `SCREEN_AND_NEWS` | Full pipeline: screen → news → synthesis → report |
| *"What's happening in the banking sector?"* | `NEWS` | Sector-level + macro news intelligence |

---

## License

This project is built for educational and portfolio purposes. Not intended for production trading decisions.
