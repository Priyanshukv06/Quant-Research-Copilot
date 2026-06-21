"""
Indicator template library for BigQuery SQL generation.
Maps natural language filters to actual BigQuery schemas.
Handles bank vs non-bank schema variations.
"""
from typing import Dict, Any, List

# Dictionary of all supported indicators
INDICATOR_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ═══════════════════════════════════════════
    # VALUATION (computed from daily + quarterly)
    # ═══════════════════════════════════════════
    
    "live_pe": {
        "description": "Live P/E ratio (current price / TTM EPS)",
        "params": {"operator": ["<", ">", "between"], "value": "float"},
        "tables": ["daily_stock_price", "quarterly_results"],
        "bq_template": """
            WITH ttm_eps AS (
                SELECT nse_symbol,
                    SUM(SAFE_CAST(REGEXP_REPLACE(CAST(EPS_in_Rs AS STRING), r'[^\\d.-]', '') AS FLOAT64)) AS ttm_eps
                FROM `{project_id}.{dataset_fundamentals}.quarterly_results`
                WHERE PARSE_DATE('%b %Y', Period) >= DATE_SUB(CURRENT_DATE(), INTERVAL 15 MONTH)
                GROUP BY nse_symbol
                HAVING COUNT(*) = 4
            ),
            latest_price AS (
                SELECT symbol AS nse_symbol, close AS latest_close
                FROM `{project_id}.{dataset_technicals}.daily_stock_price`
                WHERE date = (SELECT MAX(date) FROM `{project_id}.{dataset_technicals}.daily_stock_price`)
            )
            SELECT p.nse_symbol, (p.latest_close / e.ttm_eps) AS live_pe
            FROM latest_price p JOIN ttm_eps e USING(nse_symbol)
            WHERE e.ttm_eps > 0 AND p.latest_close / e.ttm_eps {operator} {value}
        """,
        "bank_compatible": True
    },
    
    "pe_below_sector_median": {
        "description": "P/E ratio below the median P/E of its sector",
        "params": {},
        "tables": ["daily_stock_price", "quarterly_results", "company_info"],
        "bq_template": """
            WITH ttm_eps AS (
                SELECT nse_symbol,
                    SUM(SAFE_CAST(REGEXP_REPLACE(CAST(EPS_in_Rs AS STRING), r'[^\\d.-]', '') AS FLOAT64)) AS ttm_eps
                FROM `{project_id}.{dataset_fundamentals}.quarterly_results`
                WHERE PARSE_DATE('%b %Y', Period) >= DATE_SUB(CURRENT_DATE(), INTERVAL 15 MONTH)
                GROUP BY nse_symbol
                HAVING COUNT(*) = 4
            ),
            latest_price AS (
                SELECT symbol AS nse_symbol, close AS latest_close
                FROM `{project_id}.{dataset_technicals}.daily_stock_price`
                WHERE date = (SELECT MAX(date) FROM `{project_id}.{dataset_technicals}.daily_stock_price`)
            ),
            pe_data AS (
                SELECT p.nse_symbol, c.sector_classification, (p.latest_close / e.ttm_eps) AS live_pe
                FROM latest_price p 
                JOIN ttm_eps e USING(nse_symbol)
                JOIN `{project_id}.{dataset_fundamentals}.company_info` c USING(nse_symbol)
                WHERE e.ttm_eps > 0
            )
            SELECT nse_symbol, live_pe AS pe_below_sector_median FROM (
                SELECT nse_symbol, live_pe, 
                       PERCENTILE_CONT(live_pe, 0.5) OVER(PARTITION BY sector_classification) AS median_pe
                FROM pe_data
            )
            WHERE live_pe < median_pe
        """,
        "bank_compatible": True
    },

    
    "cfo_positive": {
        "description": "Cash from operations positive for recent years",
        "params": {},
        "tables": ["cash_flows"],
        "bq_template": """
            WITH recent_cfo AS (
                SELECT nse_symbol, 
                       SAFE_CAST(REGEXP_REPLACE(CAST(Cash_from_Operating_Activity AS STRING), r'[^\\d.-]', '') AS FLOAT64) AS cfo,
                       ROW_NUMBER() OVER (PARTITION BY nse_symbol ORDER BY PARSE_DATE('%b %Y', Period) DESC) as rn
                FROM `{project_id}.{dataset_fundamentals}.cash_flows`
            )
            SELECT nse_symbol, cfo AS cfo_positive
            FROM recent_cfo
            WHERE rn = 1 AND cfo > 0
        """,
        "bank_compatible": True
    },
    
    # ═══════════════════════════════════════════
    # PROFITABILITY (quarterly — bank-aware)
    # ═══════════════════════════════════════════
    
    "margin_improving": {
        "description": "Operating margin improving over N quarters",
        "params": {"quarters": "int (default: 3)", "metric": "operating | net"},
        "tables": ["quarterly_results", "company_info"],
        "bq_template": """
            WITH margins AS (
                SELECT q.nse_symbol, q.Period,
                    PARSE_DATE('%b %Y', q.Period) AS parsed_period,
                    CASE 
                        WHEN c.sector_classification LIKE '%Banks%' 
                        THEN SAFE_CAST(REGEXP_REPLACE(CAST(q.Financing_Margin AS STRING), r'[^\\d.-]', '') AS FLOAT64)
                        ELSE SAFE_CAST(REGEXP_REPLACE(CAST(q.OPM AS STRING), r'[^\\d.-]', '') AS FLOAT64)
                    END AS margin_pct
                FROM `{project_id}.{dataset_fundamentals}.quarterly_results` q
                JOIN `{project_id}.{dataset_fundamentals}.company_info` c USING(nse_symbol)
            )
            SELECT nse_symbol, margin_pct AS margin_improving FROM (
                SELECT nse_symbol, parsed_period, margin_pct,
                    LAG(margin_pct) OVER (PARTITION BY nse_symbol ORDER BY parsed_period) AS prev_margin
                FROM margins
                WHERE parsed_period >= DATE_SUB(CURRENT_DATE(), INTERVAL {quarters}*3+3 MONTH)
            )
            GROUP BY nse_symbol
            HAVING COUNTIF(margin_pct > prev_margin) >= {quarters}
        """,
        "bank_compatible": True
    },

    "revenue_growth_yoy": {
        "description": "Year-over-year revenue growth above threshold",
        "params": {"min_pct": "float (default: 10)"},
        "tables": ["quarterly_results", "company_info"],
        "bq_template": """
            WITH revs AS (
                SELECT q.nse_symbol, q.Period,
                    PARSE_DATE('%b %Y', q.Period) AS parsed_period,
                    CASE 
                        WHEN c.sector_classification LIKE '%Banks%' 
                        THEN SAFE_CAST(REGEXP_REPLACE(CAST(q.Revenue AS STRING), r'[^\\d.-]', '') AS FLOAT64)
                        ELSE SAFE_CAST(REGEXP_REPLACE(CAST(q.Sales AS STRING), r'[^\\d.-]', '') AS FLOAT64)
                    END AS revenue
                FROM `{project_id}.{dataset_fundamentals}.quarterly_results` q
                JOIN `{project_id}.{dataset_fundamentals}.company_info` c USING(nse_symbol)
            )
            SELECT nse_symbol, ((revenue - prev_year_revenue) / prev_year_revenue) * 100 AS revenue_growth_yoy FROM (
                SELECT nse_symbol, parsed_period, revenue,
                    LAG(revenue, 4) OVER (PARTITION BY nse_symbol ORDER BY parsed_period) AS prev_year_revenue
                FROM revs
            )
            WHERE prev_year_revenue > 0 
            AND parsed_period = (SELECT MAX(parsed_period) FROM revs)
            AND ((revenue - prev_year_revenue) / prev_year_revenue) * 100 > {min_pct}
        """,
        "bank_compatible": True
    },
    
    # ═══════════════════════════════════════════
    # SHAREHOLDING (quarterly)
    # ═══════════════════════════════════════════

    "smart_money_inflow": {
        "description": "Both FII + DII holding increasing (institutional confidence)",
        "params": {"quarters": "int (default: 1)"},
        "tables": ["shareholding_quarterly"],
        "bq_template": """
            WITH holding AS (
                SELECT nse_symbol,
                    PARSE_DATE('%b %Y', Period) AS parsed_period,
                    SAFE_CAST(REGEXP_REPLACE(FIIs, r'[^\\d.-]', '') AS FLOAT64) AS fii,
                    SAFE_CAST(REGEXP_REPLACE(DIIs, r'[^\\d.-]', '') AS FLOAT64) AS dii
                FROM `{project_id}.{dataset_fundamentals}.shareholding_quarterly`
            )
            SELECT nse_symbol, CONCAT('FII:', CAST(fii AS STRING), '%, DII:', CAST(dii AS STRING), '%') AS smart_money_inflow FROM (
                SELECT nse_symbol, parsed_period, fii, dii,
                    LAG(fii) OVER (PARTITION BY nse_symbol ORDER BY parsed_period) AS prev_fii,
                    LAG(dii) OVER (PARTITION BY nse_symbol ORDER BY parsed_period) AS prev_dii
                FROM holding
            )
            WHERE parsed_period = (SELECT MAX(parsed_period) FROM holding)
            AND fii > prev_fii AND dii > prev_dii
        """,
        "bank_compatible": True
    },
    
    # ═══════════════════════════════════════════
    # TECHNICALS (daily — from daily_stock_price)
    # ═══════════════════════════════════════════

    "near_52_week_high": {
        "description": "Price within X% of 52-week high",
        "params": {"within_pct": "float (default: 5)"},
        "tables": ["daily_stock_price"],
        "bq_template": """
            WITH yearly_high AS (
                SELECT symbol AS nse_symbol, MAX(high) AS high_52w
                FROM `{project_id}.{dataset_technicals}.daily_stock_price`
                WHERE date >= DATE_SUB((SELECT MAX(date) FROM `{project_id}.{dataset_technicals}.daily_stock_price`), INTERVAL 365 DAY)
                GROUP BY symbol
            ),
            latest_price AS (
                SELECT symbol AS nse_symbol, close AS latest_close
                FROM `{project_id}.{dataset_technicals}.daily_stock_price`
                WHERE date = (SELECT MAX(date) FROM `{project_id}.{dataset_technicals}.daily_stock_price`)
            )
            SELECT p.nse_symbol, (h.high_52w - p.latest_close) / h.high_52w * 100 AS near_52_week_high
            FROM latest_price p JOIN yearly_high h USING(nse_symbol)
            WHERE h.high_52w > 0 AND (h.high_52w - p.latest_close) / h.high_52w * 100 <= {within_pct}
        """,
        "bank_compatible": True
    },

    "above_200_sma": {
        "description": "Price trading above 200-day SMA",
        "params": {},
        "tables": ["daily_stock_price"],
        "bq_template": """
            WITH moving_avg AS (
                SELECT symbol AS nse_symbol, date, close,
                    AVG(close) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS sma_200
                FROM `{project_id}.{dataset_technicals}.daily_stock_price`
            )
            SELECT nse_symbol, close AS above_200_sma
            FROM moving_avg
            WHERE date = (SELECT MAX(date) FROM `{project_id}.{dataset_technicals}.daily_stock_price`)
            AND close > sma_200
        """,
        "bank_compatible": True
    },
    
    "supertrend_bullish": {
        "description": "Supertrend indicator is bullish",
        "params": {"period": "int (default: 10)", "multiplier": "float (default: 3)"},
        "tables": ["daily_stock_price"],
        "bq_template": """
            -- Simplified Supertrend approximation for BigQuery
            -- Calculates ATR and compares Close to Upper/Lower Bands
            WITH ohlcv AS (
                SELECT symbol AS nse_symbol, date, high, low, close,
                    LAG(close) OVER (PARTITION BY symbol ORDER BY date) as prev_close
                FROM `{project_id}.{dataset_technicals}.daily_stock_price`
            ),
            tr AS (
                SELECT nse_symbol, date, close, high, low,
                    GREATEST(
                        high - low,
                        ABS(high - COALESCE(prev_close, high)),
                        ABS(low - COALESCE(prev_close, low))
                    ) as tr_val
                FROM ohlcv
            ),
            atr AS (
                SELECT nse_symbol, date, close,
                    AVG(tr_val) OVER (PARTITION BY nse_symbol ORDER BY date ROWS BETWEEN {period}-1 PRECEDING AND CURRENT ROW) as atr_val,
                    (high + low) / 2 as hl2
                FROM tr
            )
            SELECT nse_symbol, close AS supertrend_bullish
            FROM atr
            WHERE date = (SELECT MAX(date) FROM atr)
            AND close > (hl2 - ({multiplier} * atr_val))
        """,
        "bank_compatible": True
    },

    # ═══════════════════════════════════════════
    # SECTOR / COMPANY FILTERS
    # ═══════════════════════════════════════════
    
    "sector_filter": {
        "description": "Filter by sector classification",
        "params": {"value": "string"},
        "tables": ["company_info"],
        "bq_template": """
            SELECT nse_symbol, sector_classification AS sector_filter
            FROM `{project_id}.{dataset_fundamentals}.company_info`
            WHERE LOWER(sector_classification) LIKE LOWER(CONCAT('%', '{value}', '%'))
        """,
        "bank_compatible": True
    }
}


def build_query(indicator_id: str, params: Dict[str, Any], config_vars: Dict[str, str]) -> str:
    """
    Build a BigQuery SQL statement for a specific indicator.
    """
    if indicator_id not in INDICATOR_TEMPLATES:
        raise ValueError(f"Unknown indicator ID: {indicator_id}")
        
    template = INDICATOR_TEMPLATES[indicator_id]["bq_template"]
    
    # --- RESILIENCE: Fix LLM parameter hallucinations ---
    if indicator_id == "live_pe":
        if "max" in params:
            params["operator"] = "<"
            params["value"] = params["max"]
        elif "min" in params:
            params["operator"] = ">"
            params["value"] = params["min"]
        
        if "operator" not in params:
            params["operator"] = "<" # Default to finding under a certain P/E
            
        if "value" not in params:
             raise ValueError("live_pe requires a 'value' parameter")
    # ----------------------------------------------------
    
    # Merge config vars and LLM params
    format_kwargs = {**config_vars, **params}
    
    # Handle optional values
    if "value2" not in format_kwargs:
        format_kwargs["value2"] = ""
        
    try:
        return template.format(**format_kwargs).strip()
    except KeyError as e:
        raise ValueError(f"Missing required parameter for {indicator_id}: {e}")
