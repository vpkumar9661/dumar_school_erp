"""
Supabase Storage Utility — Uses service_role key + REST API for reliable uploads.

The service_role key bypasses all RLS policies, ensuring uploads always succeed
as long as the Supabase project is reachable. Buckets are auto-created as public
if they don't exist.
"""
import os, mimetypes, requests

def _log(message, level="info"):
    """Helper to log messages using Flask's logger or print as fallback."""
    try:
        from flask import current_app
        if level == "error":
            current_app.logger.error(message)
        elif level == "warning":
            current_app.logger.warning(message)
        else:
            current_app.logger.info(message)
    except RuntimeError:
        # Fallback to standard print with flush=True
        print(message, flush=True)

# ── Credentials ──────────────────────────────────────────────────────────────

def _get_creds():
    """Get Supabase URL and service_role key from env/config."""
    try:
        from flask import current_app
        url = current_app.config.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
        key = (current_app.config.get("SUPABASE_SERVICE_ROLE_KEY")
               or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))
    except RuntimeError:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    # Fallback to anon key if service_role key is not set
    if not key:
        _log("DEBUG: [STORAGE] WARNING: SUPABASE_SERVICE_ROLE_KEY is not set! Falling back to SUPABASE_ANON_KEY. Cloud uploads will fail if RLS policies are enabled.", "warning")
        try:
            from flask import current_app
            key = current_app.config.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
        except RuntimeError:
            key = os.environ.get("SUPABASE_ANON_KEY", "")
    else:
        _log(f"DEBUG: [STORAGE] Using SUPABASE_SERVICE_ROLE_KEY (key length: {len(key)})")

    if url:
        url = url.rstrip('/')

    return url, key


def _headers(content_type=None):
    """Build auth headers for Supabase Storage REST API."""
    _, key = _get_creds()
    h = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


# ── Bucket Management ────────────────────────────────────────────────────────

_buckets_ensured = set()  # Cache: only check once per process lifetime

def _ensure_bucket(bucket):
    """Create the storage bucket if it doesn't exist (public, no file size limit)."""
    if bucket in _buckets_ensured:
        return
    url, key = _get_creds()
    if not url or not key:
        return

    try:
        # List existing buckets
        resp = requests.get(
            f"{url}/storage/v1/bucket",
            headers=_headers(),
            timeout=10
        )
        if resp.status_code == 200:
            existing = {b["id"] for b in resp.json()}
            if bucket not in existing:
                # Create bucket as public
                create_resp = requests.post(
                    f"{url}/storage/v1/bucket",
                    headers={**_headers(), "Content-Type": "application/json"},
                    json={"id": bucket, "name": bucket, "public": True},
                    timeout=10
                )
                if create_resp.status_code in (200, 201):
                    _log(f"DEBUG: [STORAGE] Created bucket '{bucket}' (public)")
                else:
                    _log(f"DEBUG: [STORAGE] Bucket create response: {create_resp.status_code} {create_resp.text[:200]}", "error")
            else:
                _log(f"DEBUG: [STORAGE] Bucket '{bucket}' already exists")
        _buckets_ensured.add(bucket)
    except Exception as e:
        _log(f"DEBUG: [STORAGE] Bucket check error: {e}", "error")


# ── Upload ───────────────────────────────────────────────────────────────────

def upload_to_supabase(file_path, bucket, filename):
    """
    Uploads a local file to Supabase Storage using service_role key + REST API.
    Auto-creates the bucket if it doesn't exist.
    Returns True on success, False on failure.
    """
    url, key = _get_creds()
    if not url or not key:
        _log("DEBUG: [STORAGE] No Supabase credentials found.", "error")
        return False

    _ensure_bucket(bucket)

    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        content_type = mime_type or "application/octet-stream"

        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Upload via REST API (upsert mode to overwrite if exists)
        upload_url = f"{url}/storage/v1/object/{bucket}/{filename}"
        headers = {
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": content_type,
            "x-upsert": "true",   # Overwrite if file already exists
        }

        resp = requests.post(upload_url, headers=headers, data=file_data, timeout=30)

        if resp.status_code in (200, 201):
            _log(f"DEBUG: [STORAGE] SUCCESS: Uploaded {filename} to '{bucket}' ({content_type}, {len(file_data)} bytes)")
            return True
        else:
            _log(f"DEBUG: [STORAGE] FAILED: Upload failed: {resp.status_code} — {resp.text[:300]}", "error")
            return False

    except Exception as e:
        _log(f"DEBUG: [STORAGE] FAILED: Upload exception for {filename}: {e}", "error")
        return False


# ── Delete ───────────────────────────────────────────────────────────────────

def delete_from_supabase(bucket, filename):
    """Deletes a file from Supabase Storage."""
    url, key = _get_creds()
    if not url or not key:
        return False
    try:
        resp = requests.delete(
            f"{url}/storage/v1/object/{bucket}/{filename}",
            headers=_headers(),
            timeout=10
        )
        if resp.status_code in (200, 204):
            _log(f"DEBUG: [STORAGE] Deleted {filename} from '{bucket}'")
            return True
        else:
            _log(f"DEBUG: [STORAGE] Delete failed: {resp.status_code}", "error")
            return False
    except Exception as e:
        _log(f"DEBUG: [STORAGE] Delete error: {e}", "error")
        return False


# ── Public URL ───────────────────────────────────────────────────────────────

def get_public_url(bucket, filename):
    """
    Gets the public URL for a file in Supabase Storage.
    Falls back to local path if credentials are missing or if the file exists locally.
    """
    if not filename or filename == 'default_student.jpg':
        return "/static/images/default_student.jpg"

    # If the file exists locally, serve it locally
    try:
        from flask import current_app
        local_path = os.path.join(current_app.root_path, 'static', 'uploads', bucket, filename)
        if os.path.exists(local_path):
            return f"/static/uploads/{bucket}/{filename}"
    except Exception:
        # Fallback if outside Flask context
        local_path = os.path.join(os.getcwd(), 'static', 'uploads', bucket, filename)
        if os.path.exists(local_path):
            return f"/static/uploads/{bucket}/{filename}"

    url, key = _get_creds()
    if not url or not key:
        return f"/static/uploads/{bucket}/{filename}"

    # Supabase public URL format (works for public buckets)
    return f"{url}/storage/v1/object/public/{bucket}/{filename}"
