from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.curation.models import BusinessEvent
from apps.ingestion.services.event_extractor import (
    SEC_EVENT_SIGNALS,
    actual_change_for,
    find_evidence_sentence,
    source_claim_from_evidence,
)


class Command(BaseCommand):
    help = "Rebuild source_claim and actual_change text for extracted business events."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="")
        parser.add_argument("--decision-theme", default="")

    def handle(self, *args, **options):
        signal_by_theme = {signal.decision_theme: signal for signal in SEC_EVENT_SIGNALS}
        queryset = BusinessEvent.objects.select_related("company").order_by("company__name", "id")

        company_slug = (options["company"] or "").strip()
        if company_slug:
            company = Company.objects.get(slug=company_slug)
            queryset = queryset.filter(company=company)

        decision_theme = (options["decision_theme"] or "").strip()
        if decision_theme:
            queryset = queryset.filter(decision_theme=decision_theme)

        updated = 0
        skipped = 0
        for event in queryset:
            signal = signal_by_theme.get(event.decision_theme)
            if not signal:
                skipped += 1
                continue

            evidence = event.evidence_text or event.source_claim
            article_text = ""
            if event.article_extraction_id:
                article_text = event.article_extraction.clean_text or ""
            if article_text:
                matched_keywords = (event.raw_extraction_json or {}).get("matched_keywords") or signal.keywords
                improved_evidence = find_evidence_sentence(article_text, signal, matched_keywords)
                if improved_evidence:
                    evidence = improved_evidence
            source_claim = source_claim_from_evidence(evidence)
            actual_change = actual_change_for(signal, source_claim, company_name=event.company.name)
            if not actual_change:
                skipped += 1
                continue

            raw = event.raw_extraction_json or {}
            raw["source_claim"] = source_claim
            raw["actual_change_rebuilt"] = True
            event.source_claim = source_claim
            event.actual_change = actual_change
            event.evidence_text = evidence
            event.raw_extraction_json = raw
            event.save(update_fields=["source_claim", "actual_change", "evidence_text", "raw_extraction_json", "updated_at"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Rebuilt {updated} event claims. Skipped {skipped}."))
