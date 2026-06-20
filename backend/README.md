# Quant Research Copilot Backend API

This is the FastAPI backend for the Quant Research Copilot. It currently features the Orchestrator and Screener agents (Phase 1).

## Setup & Running

The Python virtual environment (`venv`) is already created and dependencies are installed.

To run the server manually, open a terminal in this directory and run:
```powershell
.\venv\Scripts\activate
python main.py
```

The server will start on `http://localhost:8000`.

## How to Test

FastAPI comes with an auto-generated interactive API documentation (Swagger UI). This is the easiest way to test the API yourself!

1. Open your browser and go to: **http://localhost:8000/docs**
2. Click on the `POST /api/copilot/query` endpoint to expand it.
3. Click the **"Try it out"** button.
4. Modify the Request body to enter your natural language query. For example:
   ```json
   {
     "query": "Find IT stocks with P/E below 30 and positive cash flow"
   }
   ```
5. Click **Execute**.
6. Scroll down to see the JSON response, which will show:
   - The parsed intent and parameters (Orchestrator output)
   - The list of screened stock symbols (Screener output from BigQuery)

### Available Indicators You Can Test
The LLM is currently trained to extract these indicators:
- `live_pe` (e.g. "P/E below 20")
- `margin_improving` (e.g. "improving operating margins")
- `revenue_growth_yoy` (e.g. "revenue growing by at least 10%")
- `eps_growth_yoy`
- `net_profit_margin`
- `promoter_holding_increasing`
- `fii_buying`
- `dii_buying`
- `smart_money_inflow`
- `debt_to_equity`
- `reserves_growing`
- `cfo_positive` (e.g. "positive cash flow")
- `free_cash_flow_positive`
- `roce_above`
- `roe_above`
- `above_200_sma` (e.g. "trading above 200 day moving average")
- `near_52_week_high`
- `volume_spike`
- `momentum_positive`
- `supertrend_bullish` (e.g. "bullish supertrend")
- `sector_filter` (e.g. "IT stocks", "Banking stocks")
- `market_cap_range`
- `earnings_within_days`
- `npa_decreasing` (Banks only)
- `deposit_growth` (Banks only)
