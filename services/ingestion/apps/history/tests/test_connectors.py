from types import SimpleNamespace
from django.test import SimpleTestCase
from apps.ingestion.services.source_router import build_company_source_plan
from apps.history.connectors.official_web import OfficialWebConnector
from apps.history.connectors.wayback import WaybackConnector
from apps.ingestion.services.sec_edgar_client import SecEdgarClient

class Response:
    def __init__(self, status=200, data=None, headers=None, url="https://news.example.com/releases"):
        self.status_code, self._data, self.headers, self.url = status, data or [], headers or {}, url
        self.content = b"document"
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(self.status_code)
    def json(self): return self._data

class Session:
    def __init__(self, responses): self.responses = list(responses); self.calls = []; self.headers = {}
    def get(self, *args, **kwargs): self.calls.append((args, kwargs)); return self.responses.pop(0)

class ConnectorAndRoutingTests(SimpleTestCase):
    def test_unknown_ipo_keeps_pre_public_research_and_clock_is_injected(self):
        company = SimpleNamespace(founded_date=None, sec_cik="0000123456")
        routes = build_company_source_plan(company, founded_year=2001, public_listing_year=None, current_year=2031)
        self.assertEqual(routes[0].stage, "PUBLIC_COMPANY")
        private = build_company_source_plan(SimpleNamespace(founded_date=None, sec_cik=""), founded_year=2020, current_year=2031)
        self.assertEqual(private[0].year_end, 2031)
        self.assertIn("ARCHIVED_WEB", private[0].primary_sources)

    def test_official_domain_304_and_disallowed_reference(self):
        config = SimpleNamespace(endpoint="https://news.example.com/releases", allowed_domain="example.com")
        connector = OfficialWebConnector(config, session=Session([Response(304)]))
        result = connector.discover(SimpleNamespace(external_reference="https://news.example.com/releases"), cursor={"etag":"old"})
        self.assertTrue(result.not_modified)
        with self.assertRaises(ValueError):
            connector.discover(SimpleNamespace(external_reference="https://evil.example.net/"), cursor={})

    def test_wayback_capture_does_not_supply_published_date_or_effective_date(self):
        config = SimpleNamespace(endpoint="https://web.archive.org/cdx/search/cdx")
        connector = WaybackConnector(config, session=Session([Response(data=[["timestamp","original","statuscode","digest"],["20000101120000","https://example.com/a","200","hash"]])]))
        result = connector.discover(SimpleNamespace(external_reference="https://example.com/a"), cursor={})
        self.assertIsNone(result.items[0].published_at)
        self.assertEqual(connector.normalize(result.items[0])["published_at"], None)

    def test_credential_failure_is_exposed_not_rewritten_as_public_content(self):
        config = SimpleNamespace(endpoint="https://news.example.com/releases", allowed_domain="example.com")
        connector = OfficialWebConnector(config, session=Session([Response(401)]))
        with self.assertRaises(RuntimeError): connector.discover(SimpleNamespace(external_reference="https://news.example.com/releases"), cursor={})
    def test_sec_client_honors_retry_after_and_304(self):
        waits = []
        client = SecEdgarClient(session=Session([Response(429, headers={"Retry-After": "2"}), Response(200, data={"ok": True})]), request_delay=0, sleep_fn=waits.append)
        self.assertEqual(client._get_json("https://data.sec.gov/x"), {"ok": True})
        self.assertEqual(waits, [0, 2.0, 0])
        cached = SecEdgarClient(session=Session([Response(304)]), request_delay=0, sleep_fn=lambda _: None)
        self.assertEqual(cached._get_json("https://data.sec.gov/x"), {"not_modified": True})
