"""
Screener Agent
Translates parsed indicators into BigQuery execution.
"""
import logging
from typing import Dict, Any, List

from google.cloud import bigquery
from google.oauth2 import service_account

from config import settings
from templates.indicators import build_query
from agents.refiner import refiner_agent

logger = logging.getLogger(__name__)

class ScreenerAgent:
    def __init__(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GCP_SERVICE_ACCOUNT_PATH
            )
            self.client = bigquery.Client(
                credentials=credentials, 
                project=settings.GCP_PROJECT_ID,
                location="asia-south1"
            )
            logger.info("BigQuery client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            self.client = None

    async def extract_parameters(self, query: str) -> List[Dict[str, Any]]:
        """
        Uses the LLM to extract indicator IDs and their exact parameters from the query.
        """
        from llm.provider import llm
        from llm.prompts import SCREENER_SLOT_FILL_SYSTEM, SCREENER_SLOT_FILL_USER

        messages = [
            {"role": "system", "content": SCREENER_SLOT_FILL_SYSTEM},
            {"role": "user", "content": SCREENER_SLOT_FILL_USER.format(query=query)}
        ]
        
        try:
            indicators = await llm.generate_json(messages, temperature=0.1)
            logger.info(f"Screener extracted indicators: {indicators}")
            if not isinstance(indicators, list):
                logger.error("LLM did not return a list for indicators")
                return []
            return indicators
        except Exception as e:
            logger.error(f"Screener failed to extract parameters: {e}")
            return []

    async def execute_screen(self, indicators: List[Dict[str, Any]], user_query: str) -> Dict[str, Any]:
        """
        Takes a list of indicators, generates BQ SQL, and intersects results.
        Returns a dictionary with 'symbols' and the 'query' executed.
        """
        if not self.client:
            raise RuntimeError("BigQuery client not available")
            
        config_vars = {
            "project_id": settings.GCP_PROJECT_ID,
            "dataset_fundamentals": settings.BQ_DATASET_FUNDAMENTALS,
            "dataset_technicals": settings.BQ_DATASET_TECHNICALS,
        }

        cte_aliases = []
        select_cols = ["t0.nse_symbol"]
        join_clauses = []
        
        for ind in indicators:
            try:
                sql = build_query(ind["id"], ind.get("params", {}), config_vars)
                idx = len(cte_aliases)
                alias = f"t{idx}"
                cte_aliases.append(f"({sql}) {alias}")
                
                select_cols.append(f"{alias}.{ind['id']}")
                
                if idx > 0:
                    join_clauses.append(f"INNER JOIN {cte_aliases[idx]} ON t0.nse_symbol = {alias}.nse_symbol")
                
            except Exception as e:
                logger.error(f"Failed to build query for {ind['id']}: {e}")
                continue

        if not cte_aliases:
            return {"symbols": [], "query": ""}

        # Build dynamic INNER JOIN query
        select_str = ", ".join(select_cols)
        from_clause = cte_aliases[0]
        join_str = " ".join(join_clauses)
        
        final_query = f"SELECT {select_str} FROM {from_clause} {join_str}"
        
        # Clean up newlines and extra spaces for cleaner JSON output
        final_query = " ".join(final_query.split())
        
        # --- SQL REFINER ---
        refined_query = await refiner_agent.refine_query(user_query, final_query)
        
        logger.info(f"Executing BigQuery (Refined): {refined_query}")

        try:
            # Try to execute the LLM refined query first
            query_job = self.client.query(refined_query)
            results = query_job.result()
            executed_query = refined_query
        except Exception as e:
            logger.warning(f"Refined query execution failed: {e}. Falling back to base template query.")
            try:
                # Fallback to the safe, rigid template query
                query_job = self.client.query(final_query)
                results = query_job.result()
                executed_query = final_query
            except Exception as inner_e:
                logger.error(f"Base BigQuery execution also failed: {inner_e}")
                return {"symbols": [], "query": final_query, "error": str(inner_e)}

        # Return fully parsed dictionary rows with all requested metrics
        symbols_data = []
        for row in results:
            row_dict = dict(row)
            if "near_52_week_high" in row_dict:
                row_dict["price% from 52 week high"] = row_dict.pop("near_52_week_high")
            symbols_data.append(row_dict)
            
        logger.info(f"Screening returned {len(symbols_data)} symbols")
        return {"symbols": symbols_data, "query": executed_query}

screener_agent = ScreenerAgent()
