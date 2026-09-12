"""Safe, content-addressed acquisition for authorized source documents."""

from __future__ import annotations

import hashlib
import ipaddress
import mimetypes
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urljoin, urlparse

import requests
from django.utils import timezone


class AcquisitionError(ValueError):
    """A source could not be fetched safely or within the configured budget."""


@dataclass(frozen=True)
class AcquiredDocument:
    url: str
    content: bytes
    media_type: str
    filename: str
    etag: str
    last_modified: str


class FilesystemBlobStore:
    """Persistent local blob storage with content-addressed immutable objects."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or os.getenv("REVISION_BLOB_ROOT", "/var/lib/infodj/revisions"))

    def put_bytes(self, content: bytes, *, prefix: str, suffix: str = "") -> str:
        digest = hashlib.sha256(content).hexdigest()
        relative = Path(prefix) / digest[:2] / f"{digest}{suffix}"
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
                temporary.write(content)
                temp_name = temporary.name
            os.replace(temp_name, destination)
        return str(relative)

    def read_bytes(self, storage_key: str) -> bytes:
        return (self.root / storage_key).read_bytes()


def _is_public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved or address.is_unspecified)


def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise AcquisitionError("Only absolute HTTP(S) URLs are allowed.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise AcquisitionError(f"Could not resolve source host: {exc}") from exc
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise AcquisitionError("Source host resolves to a non-public address.")
    return url


def fetch_authorized_document(
    url: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 30.0,
    max_bytes: int = 20 * 1024 * 1024,
    max_redirects: int = 3,
) -> AcquiredDocument:
    """Fetch bounded bytes, validating every redirect target before requesting it."""
    current_url = validate_public_http_url(url)
    session = session or requests.Session()
    for _redirect in range(max_redirects + 1):
        response = session.get(current_url, timeout=timeout, stream=True, allow_redirects=False)
        if response.is_redirect:
            location = response.headers.get("Location")
            if not location:
                raise AcquisitionError("Redirect response had no Location header.")
            current_url = validate_public_http_url(urljoin(current_url, location))
            continue
        response.raise_for_status()
        declared_length = response.headers.get("Content-Length")
        if declared_length and int(declared_length) > max_bytes:
            raise AcquisitionError("Source document exceeds the configured size budget.")
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise AcquisitionError("Source document exceeds the configured size budget.")
            chunks.append(chunk)
        content = b"".join(chunks)
        media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if not media_type:
            media_type = mimetypes.guess_type(urlparse(current_url).path)[0] or "application/octet-stream"
        filename = Path(urlparse(current_url).path).name or "document"
        return AcquiredDocument(current_url, content, media_type, filename, response.headers.get("ETag", ""), response.headers.get("Last-Modified", ""))
    raise AcquisitionError("Source exceeded the redirect limit.")


def persist_source_revision(source_document, acquired: AcquiredDocument, *, blob_store: FilesystemBlobStore, revision_model, parser_version: str = "p02"):
    digest = hashlib.sha256(acquired.content).hexdigest()
    revision, created = revision_model.objects.get_or_create(
        source_document=source_document,
        content_sha256=digest,
        defaults={
            "retrieved_at": timezone.now(),
            "published_at": source_document.published_date,
            "media_type": acquired.media_type,
            "storage_key": blob_store.put_bytes(acquired.content, prefix="original"),
            "original_filename": acquired.filename,
            "content_length": len(acquired.content),
            "etag": acquired.etag,
            "last_modified": acquired.last_modified,
            "parser_version": parser_version,
        },
    )
    return revision, created
