from urllib.parse import urlparse


def extract_source_summary(source_url: str) -> str:
    parsed = urlparse(source_url)
    host = parsed.netloc or "unknown-source"
    return f"Source host: {host}. Use core IT admin concepts from this source URL: {source_url}."
