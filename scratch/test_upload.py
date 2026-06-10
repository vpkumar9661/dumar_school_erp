import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import upload_to_supabase, get_public_url
import requests

# Create a dummy small image file
dummy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dummy.jpg")
with open(dummy_path, "wb") as f:
    f.write(b"this is a dummy image content")

print("Uploading to Supabase...")
success = upload_to_supabase(dummy_path, "gallery", "test_dummy.jpg")
print(f"Upload success: {success}")

if success:
    url = get_public_url("gallery", "test_dummy.jpg")
    print(f"Public URL: {url}")
    
    print("\nVerifying URL accessibility...")
    resp = requests.get(url)
    print(f"Response status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type')}")
    print(f"Content Length: {len(resp.content)} bytes")
    print(f"First 100 bytes of response: {resp.content[:100]}")
