"""Approved-domain official web connector; discovery never expands beyond config domain."""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from .base import ConnectorItem, ConnectorResult

class OfficialWebConnector:
    key = "official_web"
    def __init__(self, config, session=None, timeout=20):
        self.config, self.session, self.timeout = config, session or requests.Session(), timeout
    def discover(self, subject_source, *, cursor):
        url = subject_source.external_reference or self.config.endpoint
        host = (urlparse(url).hostname or "").lower()
        allowed = self.config.allowed_domain.lower().lstrip(".")
        if host != allowed and not host.endswith("." + allowed):
            raise ValueError("Official-web reference is outside approved domain")
        response = self.session.get(url, timeout=self.timeout, headers={"If-None-Match": cursor.get("etag", "")})
        if response.status_code == 304:
            return ConnectorResult((), dict(cursor), not_modified=True)
        response.raise_for_status()
        item = ConnectorItem(url, url, response.url, datetime.now(timezone.utc), {"etag": response.headers.get("ETag", ""), "retrieved_url": response.url})
        return ConnectorResult((item,), {"etag": response.headers.get("ETag", "")})
    def fetch(self, item):
        response = self.session.get(item.url, timeout=self.timeout); response.raise_for_status(); return response.content
    def normalize(self, item):
        return {"url": item.url, "title": item.title, "published_at": item.published_at, "raw": item.metadata}