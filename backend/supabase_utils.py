"""
İsteğe bağlı Supabase Storage desteği (bulut kurulumları için).

SUPABASE_URL ve SUPABASE_KEY tanımlı değilse veya 'supabase' paketi kurulu
değilse hiçbir şey yapmaz; görseller backend/uploads klasörüne kaydedilir.
"""
import os

import database  # noqa: F401  (.env dosyasını yükler)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "product-images")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not (SUPABASE_URL and SUPABASE_KEY) or "[" in SUPABASE_URL:
        return None
    try:
        from supabase import create_client
    except ImportError:
        return None
    _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


async def upload_file_to_supabase(file_data: bytes, filename: str, content_type: str):
    client = _get_client()
    if client is None:
        return None
    path = f"uploads/{filename}"
    response = client.storage.from_(SUPABASE_BUCKET).upload(
        path=path, file=file_data, file_options={"content-type": content_type}
    )
    if getattr(response, "error", None):
        raise Exception(f"Supabase upload error: {response.error}")
    return client.storage.from_(SUPABASE_BUCKET).get_public_url(path)
