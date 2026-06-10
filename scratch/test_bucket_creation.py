import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import _ensure_bucket, upload_to_supabase, _get_creds, _headers
import requests

print("Getting credentials...")
url, key = _get_creds()
print(f"URL: {url}")
print(f"Key length: {len(key)}")

print("\nTesting listing buckets via REST API...")
resp = requests.get(f"{url}/storage/v1/bucket", headers=_headers())
print(f"Status Code: {resp.status_code}")
print(f"Response: {resp.text}")

print("\nRunning _ensure_bucket('gallery')...")
_ensure_bucket('gallery')

print("\nChecking buckets list again...")
resp = requests.get(f"{url}/storage/v1/bucket", headers=_headers())
print(f"Status Code: {resp.status_code}")
print(f"Response: {resp.text}")
