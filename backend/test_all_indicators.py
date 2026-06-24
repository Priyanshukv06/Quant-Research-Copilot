import asyncio
import logging
from agents.screener import screener_agent
from templates.indicators import INDICATOR_TEMPLATES

logging.basicConfig(level=logging.INFO)

async def test_all_indicators():
    indicators_to_test = [
        {"id": "live_pe", "params": {"operator": "<", "value": 20}},
        {"id": "pe_below_sector_median", "params": {}},
        {"id": "revenue_growth_yoy", "params": {"min_pct": 10}},
        {"id": "margin_improving", "params": {"quarters": 3, "metric": "operating"}},
        {"id": "smart_money_inflow", "params": {"quarters": 1}},
        {"id": "cfo_positive", "params": {}},
        {"id": "near_52_week_high", "params": {"threshold_pct": 5}},
        {"id": "supertrend_bullish", "params": {}},
        {"id": "volume_spike", "params": {"multiplier": 3}},
        {"id": "npa_decreasing", "params": {"quarters": 2}}
    ]

    print("=== TESTING ALL KNOWLEDGE BASE INDICATORS ===")
    
    for ind in indicators_to_test:
        print(f"\nTesting Indicator: {ind['id']} ...")
        # We pass a fake user query just to satisfy the new async signature
        result = await screener_agent.execute_screen([ind], f"Test {ind['id']}")
        
        if result.get("error"):
            print(f"FAIL in {ind['id']}: {result['error']}")
        else:
            print(f"SUCCESS: {ind['id']} returned {len(result.get('symbols', []))} symbols.")

if __name__ == "__main__":
    asyncio.run(test_all_indicators())
