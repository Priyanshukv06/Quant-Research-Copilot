import requests
import json

url = "http://localhost:8000/api/copilot/query"
payload = {"query": "Find me IT sector stocks with a PE ratio below 30, and cross reference them with the latest news to give me a deep dive report."}

print("Sending query...")
response = requests.post(url, json=payload)
print(json.dumps(response.json(), indent=2))
