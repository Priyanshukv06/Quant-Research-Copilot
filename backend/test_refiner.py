import requests
import json

url = "http://localhost:8000/api/copilot/query"
# Testing both top 3 lowest PE, and pe_below_sector_median extraction
payload = {"query": "Find me the top 3 IT sector stocks with the lowest PE ratio that are also trading below their sector median PE."}

print("Sending query...")
response = requests.post(url, json=payload)
data = response.json()

print('\n--- SCREENED SYMBOLS ---')
print(json.dumps(data.get('data', {}).get('screened_symbols', []), indent=2))

print('\n--- REFINED BQ QUERY ---')
print(data.get('data', {}).get('bq_query', ''))
