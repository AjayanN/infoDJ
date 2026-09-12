"""Wayback CDX connector; archive capture is retrieval metadata, never an effective date."""
from __future__ import annotations
from datetime import datetime, timezone
import requests
from .base import ConnectorItem, ConnectorResult

class WaybackConnector:
    key = "wayback"
    def __init__(self, config, session=None, timeout=20): self.config, self.session, self.timeout = config, session or requests.Session(), timeout
    def discover(self, subject_source, *, cursor):
        params = {"url": subject_source.external_reference, "output": "json", "filter": "statuscode:200", "fl": "timestamp,original,statuscode,digest", "collapse": "digest"}
        if cursor.get("timestamp"): params["from"] = cursor["timestamp"]
        response = self.session.get(self.config.endpoint, params=params, timeout=self.timeout); response.raise_for_status()
        rows = response.json(); rows = rows[1:] if rows else []
        items = tuple(ConnectorItem(row[3], row[1], row[1], None, {"archive_timestamp": row[0], "capture_url": f"https://web.archive.org/web/{row[0]}/{row[1]}"}) for row in rows)
        next_cursor = {"timestamp": rows[-1][0]} if rows else dict(cursor)
        return ConnectorResult(items, next_cursor)
    def fetch(self, item):
        response = self.session.get(item.metadata["capture_url"], timeout=self.timeout); response.raise_for_status(); return response.content
    def normalize(self, item): return {"url": item.url, "title": item.title, "published_at": None, "raw": item.metadata}