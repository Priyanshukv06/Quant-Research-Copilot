from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import json

from agents.orchestrator import orchestrator_agent
from agents.screener import screener_agent
from agents.news import news_agent
from llm.provider import llm

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Quant Research Copilot API")

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    action: str
    data: dict

@app.post("/api/copilot/query", response_model=QueryResponse)
async def process_query(req: QueryRequest):
    logger.info(f"Received query: {req.query}")
    
    # 1. Orchestrator parses intent
    try:
        intent = await orchestrator_agent.parse_intent(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse intent: {e}")

    action = intent.get("action")
    data = {"intent": intent}

    # 2. Route based on action
    if action in ["SCREEN", "SCREEN_AND_NEWS"]:
        try:
            # Extract detailed indicator parameters
            indicators = await screener_agent.extract_parameters(req.query)
            data["indicators_extracted"] = indicators
            
            # Synchronous BigQuery call for now
            screen_result = screener_agent.execute_screen(indicators)
            data["screened_symbols"] = screen_result["symbols"]
            data["bq_query"] = screen_result["query"]
            if "error" in screen_result:
                data["error"] = screen_result["error"]
            if action == "SCREEN_AND_NEWS":
                sym_list = [s["nse_symbol"] for s in screen_result.get("symbols", [])]
                sector_filter = next((ind.get("params", {}).get("value") for ind in indicators if ind["id"] == "sector_filter"), None)
                data["news"] = await news_agent.get_intelligence(symbols=sym_list, sector=sector_filter)
                
        except Exception as e:
            logger.error(f"Screening failed: {e}")
            data["screened_symbols"] = []
            data["error"] = str(e)
            
    elif action == "NEWS":
        symbols = intent.get("symbols", [])
        sector = intent.get("sector_filter")
        try:
            data["news"] = await news_agent.get_intelligence(symbols=symbols, sector=sector)
        except Exception as e:
            logger.error(f"News fetching failed: {e}")
            data["error"] = str(e)

    return QueryResponse(action=action, data=data)

@app.get("/health")
def health_check():
    return {"status": "ok", "provider": llm.primary_model}

if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    # Ensure backend is in path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run(app, host="0.0.0.0", port=8000)
