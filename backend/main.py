from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import json

from agents.orchestrator import orchestrator_agent
from agents.screener import screener_agent
from agents.news import news_agent
from agents.synthesis import synthesis_agent
from agents.report import report_agent
from utils.visualizer import visualizer
from llm.provider import llm

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Quant Research Copilot API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            
            # Await the async BigQuery execution (which now includes SQL Refiner)
            screen_result = await screener_agent.execute_screen(indicators, req.query)
            data["screened_symbols"] = screen_result["symbols"]
            data["bq_query"] = screen_result["query"]
            if "error" in screen_result:
                data["error"] = screen_result["error"]
            if action == "SCREEN_AND_NEWS":
                sym_list = [s["nse_symbol"] for s in screen_result.get("symbols", [])]
                sector_filter = next((ind.get("params", {}).get("value") for ind in indicators if ind["id"] == "sector_filter"), None)
                data["news"] = await news_agent.get_intelligence(symbols=sym_list, sector=sector_filter)
                
                # 3. Synthesis and Report Generation
                data["synthesis"] = await synthesis_agent.synthesize(
                    screened_data=screen_result.get("symbols", []), 
                    news_data=data["news"]
                )
                data["report_markdown"] = await report_agent.generate_report(
                    query=req.query, 
                    synthesis_data=data["synthesis"]
                )
            
            # 4. Generate Visualization Charts for any screen action
            data["charts"] = visualizer.generate_comparison_charts(screen_result.get("symbols", []))
            
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

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/health")
def health_check():
    return {"status": "ok", "provider": llm.primary_model}

# Mount Next.js frontend static files
frontend_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend/out")
if os.path.exists(frontend_out):
    logger.info(f"Serving frontend from {frontend_out}")
    
    # Serve Next.js static assets (_next/*, images, etc.)
    app.mount("/_next", StaticFiles(directory=os.path.join(frontend_out, "_next")), name="next-assets")
    
    # Catch-all: serve the matching HTML file or fall back to index.html
    # This ensures page refreshes on /screener, /news, /report all work
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Try the exact path as a directory with index.html (trailingSlash: true)
        index_path = os.path.join(frontend_out, full_path, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        
        # Try as a direct file (e.g. favicon.ico, manifest.json)
        file_path = os.path.join(frontend_out, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Fallback: serve root index.html and let Next.js client router handle it
        return FileResponse(os.path.join(frontend_out, "index.html"), media_type="text/html")
else:
    logger.warning("Frontend build directory not found. API only mode.")

if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    # Ensure backend is in path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run(app, host="0.0.0.0", port=8000)
