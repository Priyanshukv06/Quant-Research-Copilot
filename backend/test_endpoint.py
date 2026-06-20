import asyncio
import httpx
import json

async def test_endpoint():
    url = "http://localhost:8000/api/copilot/query"
    payload = {
        "query": "Find IT stocks with P/E below 30 and positive cash flow"
    }
    
    print(f"Sending request to {url}...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            print("\nResponse:")
            print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoint())
