from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company, CustomerSupplierDependencySnapshot
from apps.ingestion.api import customer_supplier_dependency_source_gaps, persist_customer_supplier_dependency_gaps


class Command(BaseCommand):
    help = "Persist current customer and supplier dependency gaps for scheduler-driven source collection."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company slug. Omit with --all.")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        if bool(options["company"]) == bool(options["all"]):
            raise CommandError("Pass exactly one of --company or --all.")
        companies = Company.objects.filter(is_active=True).order_by("name") if options["all"] else Company.objects.filter(slug=options["company"])
        if not companies.exists():
            raise CommandError(f"Company not found: {options['company']}")
        gaps_persisted = 0
        for company in companies:
            snapshot = (
                CustomerSupplierDependencySnapshot.objects.filter(company=company, status__in=["PUBLISHED", "REVIEWED"])
                .prefetch_related("dependencies__contract_terms")
                .order_by("-effective_date", "-updated_at")
                .first()
            )
            dependencies = list(snapshot.dependencies.all()) if snapshot else []
            gaps = customer_supplier_dependency_source_gaps(company, snapshot, dependencies) if snapshot else [{
                "key": "dependency_snapshot",
                "label": "Dependency map unavailable",
                "reason": f"No reviewed customer and supplier dependency snapshot is available for {company.name}.",
                "source": "customer-supplier-dependency",
                "next_action": "Refresh reviewed Company 360 profiles, business-model maps, and run build_customer_supplier_dependencies.",
            }]
            persist_customer_supplier_dependency_gaps(company, gaps)
            gaps_persisted += len(gaps)
        self.stdout.write(self.style.SUCCESS(f"Dependency source gaps persisted: companies={companies.count()}, gaps={gaps_persisted}"))
