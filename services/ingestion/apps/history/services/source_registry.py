"""Reviewed importer/exporter for the human-maintained historical source registry."""
from __future__ import annotations
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from django.db import transaction
from apps.history.models import SourceConnectorConfig, SubjectSource

SEC_PATTERN = re.compile(r"https://data\.sec\.gov/submissions/CIK(\d+)\.json")

@transaction.atomic
def import_reviewed_registry(*, registry_path: str | Path, subjects_by_slug: dict[str, object], reviewer: str, approved: bool) -> dict:
    if not approved or not reviewer.strip():
        raise ValueError("Registry import requires an identified reviewer and explicit approval.")
    text = Path(registry_path).read_text(encoding="utf-8")
    sec = SourceConnectorConfig.objects.get_or_create(connector_key="sec_edgar", defaults={"schema_version":"1.0", "endpoint":"https://data.sec.gov/submissions/", "allowed_domain":"sec.gov", "enabled":True, "owner":reviewer, "coverage_tracks":["operations_finance", "legal_regulatory"], "requests_per_minute":8})[0]
    created = []
    for line in text.splitlines():
        if not line.startswith("|") or "https://data.sec.gov/submissions/" not in line: continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        slug = columns[0].lower().replace(" ", "-")
        subject = subjects_by_slug.get(slug)
        match = SEC_PATTERN.search(line)
        if not subject or not match: continue
        ref = match.group(1).zfill(10)
        _, made = SubjectSource.objects.get_or_create(subject=subject, connector=sec, external_reference=ref, defaults={"coverage_tracks": sec.coverage_tracks, "enabled": True})
        if made: created.append(slug)
    return {"reviewer": reviewer, "created_subject_sources": created, "registry_sha256": __import__("hashlib").sha256(text.encode()).hexdigest()}

def export_registry_json() -> str:
    rows = []
    for item in SubjectSource.objects.select_related("subject", "connector").order_by("subject__canonical_name", "connector__connector_key"):
        rows.append({"subject": item.subject.canonical_name, "connector_key": item.connector.connector_key, "external_reference": item.external_reference, "enabled": item.enabled, "coverage_tracks": item.coverage_tracks})
    return json.dumps(rows, indent=2, sort_keys=True)