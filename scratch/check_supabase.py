import os
from dotenv import load_dotenv
from supabase import create_client

# Load .env
load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_ANON_KEY")

print(f"Checking Supabase connection...")
print(f"URL: {URL}")
print(f"Key present: {'Yes' if KEY else 'No'}")

if not URL or not KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env")
    exit(1)

try:
    supabase = create_client(URL, KEY)
    buckets = supabase.storage.list_buckets()
    print("\nSUCCESS! Connected to Supabase.")
    print("Available Buckets:")
    for b in buckets:
        print(f" - {b.name} ({'Public' if b.public else 'Private'})")
    
    expected = ['gallery', 'downloads', 'students']
    found = [b.name for b in buckets]
    for e in expected:
        if e not in found:
            print(f"WARNING: Bucket '{e}' not found. Please create it in Supabase dashboard.")
        else:
            print(f"OK: Bucket '{e}' is ready.")

except Exception as e:
    print(f"\nERROR connecting to Supabase: {e}")
