import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.companies.models import Company, PriceObservation, ProductOffering, RegulatoryLitigationMatter
from apps.curation.models import BusinessEvent, LifecycleEpisode
from apps.ingestion.models import ArticleExtraction, EvidenceRecord, SourceDocument


class Command(BaseCommand):
    help = "Write a read-only, per-company historical coverage report."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        output = Path(options["output"])
        if not output.is_absolute():
            output = Path.cwd() / output
        output.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for company in Company.objects.order_by("id"):
            sources = SourceDocument.objects.filter(company=company)
            events = BusinessEvent.objects.filter(company=company)
            episodes = LifecycleEpisode.objects.filter(company=company)
            offerings = ProductOffering.objects.filter(snapshot__company=company)
            prices = PriceObservation.objects.filter(offering__snapshot__company=company)
            matters = RegulatoryLitigationMatter.objects.filter(snapshot__company=company)
            rows.append({
                "company_id": company.id, "company_slug": company.slug, "company_name": company.name,
                "is_active": company.is_active,
                "identifiers": {"sec_cik": company.sec_cik or None, "wikidata_id": company.wikidata_id or None},
                "founding_anchor": {"date": company.founded_date.isoformat() if company.founded_date else None, "precision": company.founded_date_precision or None, "status": company.founding_anchor_status, "has_evidence": bool(company.founded_date_evidence and company.founded_date_source_url)},
                "counts": {"source_documents": sources.count(), "successful_text_extractions": sources.filter(article_extraction__extraction_status="SUCCEEDED").count(), "failed_extractions": sources.filter(article_extraction__extraction_status="FAILED").count(), "evidence_records": EvidenceRecord.objects.filter(company=company).count(), "business_events": events.count(), "lifecycle_episodes": episodes.count(), "product_offerings": offerings.count(), "price_observations": prices.count(), "regulatory_matters": matters.count()},
                "review_states": {"evidence_records": dict(EvidenceRecord.objects.filter(company=company).values_list("review_status").annotate(count=Count("id"))), "business_events": dict(events.values_list("review_status").annotate(count=Count("id"))), "lifecycle_episodes": dict(episodes.values_list("verification_status").annotate(count=Count("id")))},
                "date_precision": {"business_events": dict(events.values_list("action_date_precision").annotate(count=Count("id"))), "lifecycle_episodes": dict(episodes.values_list("start_date_precision").annotate(count=Count("id")))},
                "provenance_loss": {"sources_without_successful_text": sources.exclude(article_extraction__extraction_status="SUCCEEDED").count(), "events_without_source_document": events.filter(source_document__isnull=True).count(), "episodes_without_source_document": episodes.filter(source_document__isnull=True).count(), "prices_without_source_document": prices.filter(source_document__isnull=True).count(), "regulatory_matters_without_source_document": matters.filter(source_document__isnull=True).count()},
                "conflicts": {"evidence_records_needing_review": EvidenceRecord.objects.filter(company=company, review_status="NEEDS_REVIEW").count(), "events_needing_review": events.filter(review_status="NEEDS_REVIEW").count()},
            })
        report = {"report_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "read_only": True, "company_count": len(rows), "company_ids": [row["company_id"] for row in rows], "companies": rows, "global_counts": {"companies": len(rows), "source_documents": SourceDocument.objects.count(), "article_extractions": ArticleExtraction.objects.count(), "evidence_records": EvidenceRecord.objects.count(), "lifecycle_episodes": LifecycleEpisode.objects.count(), "product_offerings": ProductOffering.objects.count(), "price_observations": PriceObservation.objects.count(), "regulatory_matters": RegulatoryLitigationMatter.objects.count()}, "limitations": ["Counts and review states are coverage signals, not proof of historical facts.", "A missing count means not researched or unavailable in this database; it does not prove no historical activity.", "Legacy evidence models do not retain immutable source revisions or multi-source claim conflicts; those are reported as provenance limitations until the history pipeline is implemented."]}
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote read-only coverage report for {len(rows)} companies to {output}"))
