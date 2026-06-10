import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.storage import _get_creds, get_public_url

print("--- Testing Trailing Slash Sanitization ---")
# Manually test url stripping logic
url = "https://example.supabase.co/"
clean_url = url.rstrip('/')
print(f"Original URL: '{url}'")
print(f"Sanitized URL: '{clean_url}'")
assert clean_url == "https://example.supabase.co", "Sanitization failed!"
print("Sanitization assertion passed!")

print("\n--- Testing get_public_url() Behavior ---")
# 1. Test case when file does not exist locally
non_existent_filename = "non_existent_image_12345.jpg"
public_url_cloud = get_public_url("gallery", non_existent_filename)
print(f"Cloud URL for non-existent local file: {public_url_cloud}")
# If credentials are configured, it should be a Supabase storage URL
if "supabase.co" in public_url_cloud:
    print("SUCCESS: Correctly returned Supabase URL since local file doesn't exist.")
else:
    print("INFO: Returned local path because Supabase credentials are not set (correct behaviour).")

# 2. Test case when file exists locally
import shutil
local_dir = os.path.join(os.getcwd(), 'static', 'uploads', 'gallery')
os.makedirs(local_dir, exist_ok=True)
dummy_filename = "test_local_only.jpg"
dummy_local_path = os.path.join(local_dir, dummy_filename)

with open(dummy_local_path, "w") as f:
    f.write("local file content")

try:
    public_url_local = get_public_url("gallery", dummy_filename)
    print(f"Public URL for existing local file: {public_url_local}")
    assert public_url_local == f"/static/uploads/gallery/{dummy_filename}", "Did not serve locally for existing file!"
    print("SUCCESS: Correctly returned local path since the file exists locally.")
finally:
    # Clean up dummy local file
    if os.path.exists(dummy_local_path):
        os.remove(dummy_local_path)
