"""Deterministic business-event extraction for SEC filing text.

This is a first-pass rules engine. It creates reviewable candidate rows; it is
not intended to replace an LLM extractor later.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any, Iterable


@dataclass(frozen=True)
class EventSignal:
    decision_theme: str
    event_type: str
    lifecycle_stage: str
    decision: str
    trigger: str
    before_state: str
    after_state: str
    outcome: str
    founder_lesson: str
    keywords: tuple[str, ...]
    sectors: tuple[str, ...] = ()


GENERIC_SEC_EVENT_SIGNALS = (
    EventSignal(
        decision_theme="COMPETITIVE_PRESSURE",
        event_type="COMPETITIVE_RESPONSE",
        lifecycle_stage="MATURITY",
        decision="Respond to intensifying competition.",
        trigger="Market competition, pricing pressure, product substitution, or changing customer behavior.",
        before_state="The company operated with existing competitive assumptions.",
        after_state="Competitive pressure becomes an explicit strategic and operating constraint.",
        outcome="Competition shapes pricing, product, investment, and retention decisions.",
        founder_lesson="Durable companies keep adapting after competitors copy or attack the model.",
        keywords=("intense competition", "highly competitive", "competitive pressures", "competition for", "compete with"),
    ),
    EventSignal(
        decision_theme="REGULATORY_LEGAL_RISK",
        event_type="REGULATORY_RESPONSE",
        lifecycle_stage="MATURITY",
        decision="Adapt to legal, regulatory, and compliance pressure.",
        trigger="Regulation, litigation, investigations, privacy rules, tax rules, or market-specific compliance.",
        before_state="Operations could scale with fewer explicit compliance constraints.",
        after_state="Regulatory and legal obligations become material operating requirements.",
        outcome="Compliance, risk management, and market-entry decisions become part of strategy.",
        founder_lesson="Scale turns many product and market choices into regulatory choices.",
        keywords=("regulatory", "regulation", "litigation", "legal proceedings", "compliance", "governmental"),
    ),
    EventSignal(
        decision_theme="INTERNATIONAL_OPERATIONS",
        event_type="GEOGRAPHIC_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Scale operations across international markets.",
        trigger="Growth opportunities and operating exposure outside the home market.",
        before_state="The business had a more concentrated market footprint.",
        after_state="International operations become a material growth and risk area.",
        outcome="Foreign exchange, localization, local regulation, and regional demand affect strategy.",
        founder_lesson="International scale adds growth, but also currency, regulatory, and operating complexity.",
        keywords=("international operations", "foreign operations", "outside the united states", "foreign exchange", "global operations"),
    ),
    EventSignal(
        decision_theme="ACQUISITION_ACTIVITY",
        event_type="ACQUISITION",
        lifecycle_stage="SCALE",
        decision="Use acquisitions or divestitures to reshape the business portfolio.",
        trigger="Need for capabilities, market access, consolidation, or portfolio simplification.",
        before_state="The company relied more on its existing asset and capability base.",
        after_state="M&A becomes a lever for growth, capability building, or restructuring.",
        outcome="Acquired or divested assets change the company portfolio.",
        founder_lesson="M&A is useful only when it changes capability, distribution, or focus.",
        keywords=("acquisition of", "acquired company", "acquired business", "business combination", "merger", "divestiture", "divested"),
    ),
    EventSignal(
        decision_theme="PARTNERSHIP_ACTIVITY",
        event_type="PARTNERSHIP",
        lifecycle_stage="SCALE",
        decision="Use partnerships, alliances, or customer agreements to extend the business.",
        trigger="Need for distribution, supply, capabilities, customer access, or ecosystem leverage.",
        before_state="The company relied more heavily on direct internal execution.",
        after_state="External relationships become part of operating and growth strategy.",
        outcome="Partnerships or commercial agreements support distribution, supply, or capability expansion.",
        founder_lesson="Partnerships matter when they unlock a constraint the company cannot solve alone.",
        keywords=("strategic partnership", "partnership with", "alliance", "joint venture", "collaboration agreement"),
    ),
    EventSignal(
        decision_theme="PRODUCT_SERVICE_EXPANSION",
        event_type="PRODUCT_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Expand products, services, or capabilities.",
        trigger="Need for growth, differentiation, customer retention, or adjacent revenue.",
        before_state="The company offered a narrower product or service set.",
        after_state="The company expands the scope of what it sells or operates.",
        outcome="Product or service expansion becomes a growth and differentiation lever.",
        founder_lesson="Expansion works best when it builds from existing customer trust or operating strengths.",
        keywords=("new products", "new services", "expanded our", "launched", "introduced", "product portfolio"),
    ),
    EventSignal(
        decision_theme="PRICING_PACKAGING",
        event_type="PRICING_CHANGE",
        lifecycle_stage="MATURITY",
        decision="Adjust pricing, packaging, or monetization.",
        trigger="Cost inflation, competitive pressure, demand changes, or monetization opportunity.",
        before_state="The company used its existing pricing and packaging structure.",
        after_state="Pricing or packaging becomes an active strategic lever.",
        outcome="Pricing changes affect revenue quality, demand, and customer behavior.",
        founder_lesson="Pricing is strategy once the company understands customer willingness to pay.",
        keywords=("pricing", "price increases", "price changes", "subscription plan", "fees charged"),
    ),
    EventSignal(
        decision_theme="COST_RESTRUCTURING",
        event_type="COST_RESTRUCTURING",
        lifecycle_stage="MATURITY",
        decision="Restructure costs, operations, or investment commitments.",
        trigger="Margin pressure, operating complexity, cost inflation, or demand shifts.",
        before_state="Growth or existing operations carried the prior cost structure.",
        after_state="Cost discipline and restructuring become part of the operating model.",
        outcome="The company adjusts spending, footprint, workforce, assets, or commitments.",
        founder_lesson="Operating discipline becomes strategic when growth gets harder or costs compound.",
        keywords=("restructuring", "cost reduction", "cost savings", "impairment", "charges", "operating expenses"),
    ),
    EventSignal(
        decision_theme="PERFORMANCE_DECLINE",
        event_type="PERFORMANCE_DECLINE",
        lifecycle_stage="MATURITY",
        decision="Respond to declining or pressured performance.",
        trigger="Revenue decline, margin pressure, demand weakness, churn, losses, or lower volume.",
        before_state="The company expected stronger performance from existing operations.",
        after_state="Management must respond to weaker performance or demand conditions.",
        outcome="Performance pressure forces operating, pricing, portfolio, or investment changes.",
        founder_lesson="Declines are early warnings that the strategy or operating model needs attention.",
        keywords=("decline in", "decrease in", "lower demand", "reduced demand", "net loss", "margin pressure"),
    ),
    EventSignal(
        decision_theme="CAPITAL_ALLOCATION",
        event_type="FUNDING_EVENT",
        lifecycle_stage="MATURITY",
        decision="Change capital allocation through financing, repurchases, dividends, or debt.",
        trigger="Liquidity needs, shareholder returns, investment requirements, or balance-sheet management.",
        before_state="Capital allocation followed the prior investment and financing pattern.",
        after_state="Financing or shareholder-return decisions become visible strategic levers.",
        outcome="Debt, cash flow, dividends, repurchases, or financing capacity shape strategic flexibility.",
        founder_lesson="Capital allocation determines how much room a company has to adapt.",
        keywords=("share repurchase", "dividends", "debt financing", "liquidity", "capital allocation", "free cash flow"),
    ),
)


MEDIA_SEC_EVENT_SIGNALS = (
    EventSignal(
        decision_theme="ADS_TIER",
        event_type="REVENUE_MODEL_EXPANSION",
        lifecycle_stage="MATURITY",
        decision="Expand monetization through advertising-supported plans.",
        trigger="Streaming market maturity and need for additional revenue streams.",
        before_state="Subscription-led streaming revenue model.",
        after_state="Subscription model complemented by advertising revenue.",
        outcome="Advertising becomes a tracked business lever in company filings.",
        founder_lesson="Add adjacent revenue streams when the core model matures.",
        keywords=("ad-supported", "ads plan", "ad tier", "advertising-supported"),
    ),
    EventSignal(
        decision_theme="PAID_SHARING",
        event_type="PRICING_CHANGE",
        lifecycle_stage="MATURITY",
        decision="Monetize account sharing and refine subscription packaging.",
        trigger="Password sharing and pricing pressure in mature streaming markets.",
        before_state="Broad account sharing reduced monetization per household.",
        after_state="Paid sharing and plan changes increase monetization discipline.",
        outcome="Paid sharing becomes part of subscriber and revenue strategy.",
        founder_lesson="Pricing architecture matters once usage patterns mature.",
        keywords=("paid sharing", "password sharing", "account sharing", "extra member"),
    ),
    EventSignal(
        decision_theme="GAMING",
        event_type="PRODUCT_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Expand the product surface beyond on-demand video into games.",
        trigger="Need to deepen engagement and broaden entertainment use cases.",
        before_state="Streaming video was the primary product experience.",
        after_state="Games become part of the entertainment bundle.",
        outcome="Gaming is positioned as a product expansion path.",
        founder_lesson="Use the existing customer relationship to test adjacent engagement loops.",
        keywords=("films and games", "include games", "mobile games", "game studio", "gaming"),
    ),
    EventSignal(
        decision_theme="LIVE_EVENTS",
        event_type="PRODUCT_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Expand into live programming and event-based entertainment.",
        trigger="Competition for attention and demand for differentiated programming.",
        before_state="Primarily on-demand entertainment catalog.",
        after_state="On-demand catalog supplemented by live events and programming.",
        outcome="Live entertainment becomes a visible strategic programming category.",
        founder_lesson="A scaled platform can create new appointment-viewing habits.",
        keywords=("live", "live events", "sports", "wwe", "nfl", "boxing"),
    ),
    EventSignal(
        decision_theme="ORIGINAL_CONTENT",
        event_type="PRODUCT_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Invest in original and exclusive content to differentiate the service.",
        trigger="Need for durable differentiation and control over content supply.",
        before_state="Reliance on licensed third-party content.",
        after_state="Original and exclusive content becomes a strategic asset.",
        outcome="Content investment is central to acquisition, retention, and brand positioning.",
        founder_lesson="Owning differentiated supply can protect distribution advantage.",
        keywords=("original content", "originals", "exclusive content", "content slate", "content spending"),
    ),
    EventSignal(
        decision_theme="INTERNATIONAL_EXPANSION",
        event_type="GEOGRAPHIC_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Scale the service internationally across markets.",
        trigger="Growth opportunity outside the domestic streaming market.",
        before_state="Business concentrated in fewer markets.",
        after_state="Global member base and international content operations.",
        outcome="International scale becomes a core growth and localization lever.",
        founder_lesson="Global expansion requires local content and pricing adaptation.",
        keywords=(
            "over 190 countries",
            "international streaming",
            "international operations",
            "international segment",
            "outside the united states",
            "local language",
            "global business",
        ),
    ),
    EventSignal(
        decision_theme="SUBSCRIBER_DECLINE",
        event_type="PERFORMANCE_DECLINE",
        lifecycle_stage="MATURITY",
        decision="Respond to slowing or declining membership growth.",
        trigger="Subscriber losses, churn, saturation, or slower paid net additions.",
        before_state="Growth expectations relied on continued subscriber expansion.",
        after_state="Management must improve monetization, retention, and operating discipline.",
        outcome="Subscriber performance becomes a strategic pressure point.",
        founder_lesson="Watch for growth saturation before it forces reactive monetization changes.",
        keywords=("subscriber loss", "decline in paid memberships", "paid net additions", "churn", "member churn"),
    ),
    EventSignal(
        decision_theme="COMPETITIVE_PRESSURE",
        event_type="COMPETITIVE_RESPONSE",
        lifecycle_stage="MATURITY",
        decision="Respond to intensifying competition for entertainment attention.",
        trigger="Competition from streaming services, linear TV, social video, gaming, and other entertainment options.",
        before_state="Earlier market leadership provided stronger differentiation.",
        after_state="The company must compete through content, pricing, product, and engagement.",
        outcome="Competition becomes an explicit strategic risk and operating constraint.",
        founder_lesson="Category creation eventually attracts competition; strategy must evolve before differentiation erodes.",
        keywords=("intense competition", "compete", "competitors", "competitive", "competition for"),
    ),
    EventSignal(
        decision_theme="CONTENT_COST_PRESSURE",
        event_type="COST_RESTRUCTURING",
        lifecycle_stage="MATURITY",
        decision="Manage rising content costs and investment commitments.",
        trigger="Increasing content obligations, amortization, impairment, or production cost pressure.",
        before_state="Content investment was primarily a growth lever.",
        after_state="Content spend requires tighter portfolio discipline and return analysis.",
        outcome="Cost discipline becomes part of the content strategy.",
        founder_lesson="Strategic assets can become liabilities if investment discipline weakens.",
        keywords=("content obligations", "content assets", "impairment", "amortization", "production costs"),
    ),
    EventSignal(
        decision_theme="REGULATORY_LEGAL_RISK",
        event_type="REGULATORY_RESPONSE",
        lifecycle_stage="MATURITY",
        decision="Adapt to legal, regulatory, privacy, and content compliance risk.",
        trigger="Regulation, litigation, privacy rules, censorship, tax rules, or local content requirements.",
        before_state="Expansion can proceed with fewer local constraints.",
        after_state="Compliance and regulation become operating requirements in scaled markets.",
        outcome="Regulatory risk shapes market entry, content, data, and operating decisions.",
        founder_lesson="Global scale changes the company from product operator to regulated institution.",
        keywords=("regulation", "regulatory", "litigation", "legal proceedings", "privacy", "censorship", "local content"),
    ),
)


SECTOR_SEC_EVENT_SIGNALS = (
    EventSignal(
        decision_theme="R_AND_D_PIPELINE",
        event_type="PRODUCT_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Invest in research, development, and product pipeline expansion.",
        trigger="Need for new products, clinical progress, intellectual property, or technical differentiation.",
        before_state="Growth depended more on existing products or capabilities.",
        after_state="Pipeline investment becomes central to future growth.",
        outcome="Research and development shape product timing, risk, and capital needs.",
        founder_lesson="Pipeline businesses need disciplined investment before revenue arrives.",
        keywords=("research and development", "clinical trials", "pipeline", "product candidates", "fda approval"),
        sectors=("Health Care",),
    ),
    EventSignal(
        decision_theme="CREDIT_MARKET_RISK",
        event_type="CRISIS_RESPONSE",
        lifecycle_stage="MATURITY",
        decision="Manage credit, liquidity, market, and financial-system risk.",
        trigger="Credit cycles, interest rates, market volatility, liquidity risk, or counterparty exposure.",
        before_state="Financial performance relied on normal market and credit conditions.",
        after_state="Risk management and capital strength become central operating constraints.",
        outcome="Credit, liquidity, and capital controls shape growth and resilience.",
        founder_lesson="Financial businesses scale only as far as their risk controls can hold.",
        keywords=("credit risk", "liquidity risk", "interest rate risk", "market risk", "capital requirements"),
        sectors=("Financials",),
    ),
    EventSignal(
        decision_theme="ENERGY_TRANSITION_AND_COMMODITY_EXPOSURE",
        event_type="COMPETITIVE_RESPONSE",
        lifecycle_stage="MATURITY",
        decision="Adapt to commodity cycles, energy transition, and resource-market pressure.",
        trigger="Commodity price volatility, climate policy, supply constraints, or energy transition.",
        before_state="The company operated under prior commodity, energy, or resource assumptions.",
        after_state="Commodity exposure and transition risk become strategic planning constraints.",
        outcome="Capital spending, reserves, production, and portfolio decisions respond to market and policy shifts.",
        founder_lesson="Asset-heavy companies must plan for cycles that are outside their control.",
        keywords=("commodity prices", "energy transition", "climate change", "reserves", "production volumes"),
        sectors=("Energy", "Utilities", "Materials"),
    ),
    EventSignal(
        decision_theme="PLATFORM_AND_TECHNOLOGY_SHIFT",
        event_type="PRODUCT_EXPANSION",
        lifecycle_stage="SCALE",
        decision="Invest in platform, software, cloud, data, or technology shifts.",
        trigger="Technology transitions, customer adoption shifts, and platform competition.",
        before_state="The company relied on its prior technology or product architecture.",
        after_state="New platforms or technical capabilities become central to growth.",
        outcome="Technology investment changes product direction and competitive position.",
        founder_lesson="Technology leaders have to disrupt their own architecture before others do.",
        keywords=("cloud", "artificial intelligence", "machine learning", "platform", "software and services"),
        sectors=("Information Technology",),
    ),
    EventSignal(
        decision_theme="SUPPLY_CHAIN_AND_CHANNEL_SHIFT",
        event_type="DISTRIBUTION_CHANNEL_SHIFT",
        lifecycle_stage="SCALE",
        decision="Adapt supply chain, fulfillment, stores, or distribution channels.",
        trigger="Customer behavior changes, logistics pressure, inventory risk, or channel migration.",
        before_state="The company relied on its prior distribution and operating footprint.",
        after_state="Supply chain and channels become active strategic levers.",
        outcome="Fulfillment, stores, inventory, and direct channels affect growth and margins.",
        founder_lesson="Channel control becomes strategic when customer behavior or supply chains shift.",
        keywords=("supply chain", "fulfillment", "inventory", "e-commerce", "direct-to-consumer", "distribution network"),
        sectors=("Consumer Discretionary", "Consumer Staples", "Industrials"),
    ),
    EventSignal(
        decision_theme="REAL_ESTATE_PORTFOLIO",
        event_type="COST_RESTRUCTURING",
        lifecycle_stage="MATURITY",
        decision="Manage real estate portfolio, occupancy, development, and financing exposure.",
        trigger="Interest rates, occupancy, development demand, tenant risk, or asset recycling.",
        before_state="Portfolio growth relied on prior demand and capital-market assumptions.",
        after_state="Portfolio allocation and financing become strategic constraints.",
        outcome="Occupancy, development, acquisitions, dispositions, and debt shape growth capacity.",
        founder_lesson="Asset portfolios require capital discipline as much as growth ambition.",
        keywords=("occupancy", "development pipeline", "tenant", "real estate", "lease", "property portfolio"),
        sectors=("Real Estate",),
    ),
)


SEC_EVENT_SIGNALS = (*GENERIC_SEC_EVENT_SIGNALS, *SECTOR_SEC_EVENT_SIGNALS, *MEDIA_SEC_EVENT_SIGNALS)


BOILERPLATE_PATTERNS = (
    "forward-looking statements",
    "not limited to",
    "future financial performance",
    "stock price volatility",
    "adequacy of existing",
    "new accounting standards",
    "actual results may differ",
    "risks and uncertainties",
    "indicate by check mark",
    "aggregate market value",
    "nasdaq global select market",
    "interactive data file",
    "commission file number",
    "table of contents",
)


def extract_business_events_from_sec_filing(
    *,
    company: Any,
    source_document: Any,
    article_extraction: Any,
    business_event_model: Any,
) -> list[Any]:
    if getattr(article_extraction, "extraction_status", "") != "SUCCEEDED":
        return []

    text = article_extraction.clean_text or ""
    text_lower = text.lower()
    created_events: list[Any] = []
    event_date = source_document.published_date.date() if source_document.published_date else None

    for signal in select_sec_event_signals(company):
        matched = [keyword for keyword in signal.keywords if keyword_matches(text_lower, keyword)]
        if not matched:
            continue
        evidence = find_evidence_sentence(text, signal, matched)
        if not evidence:
            continue
        source_claim = source_claim_from_evidence(evidence)
        actual_change = actual_change_for(signal, source_claim, company_name=company.name)
        event, created = business_event_model.objects.get_or_create(
            company=company,
            event_type=signal.event_type,
            decision_theme=signal.decision_theme,
            actual_change=actual_change,
            defaults={
                "source_document": source_document,
                "article_extraction": article_extraction,
                "decision": signal.decision,
                "event_date": event_date,
                "lifecycle_stage": signal.lifecycle_stage,
                "before_state": signal.before_state,
                "after_state": signal.after_state,
                "trigger": signal.trigger,
                "outcome": signal.outcome,
                "evidence_text": evidence,
                "source_claim": source_claim,
                "confidence_score": Decimal("0.650"),
                "review_status": "NEEDS_REVIEW",
                "raw_extraction_json": {
                    "extractor": "sec_rules_v1",
                    "matched_keywords": matched,
                    "decision_theme": signal.decision_theme,
                    "source_api": source_document.source_api,
                    "source_title": source_document.title,
                    "first_observed_source_id": source_document.id,
                    "first_observed_filing_date": event_date.isoformat() if event_date else None,
                    "additional_source_ids": [],
                },
            },
        )
        if created:
            created_events.append(event)
        else:
            append_additional_source(event, source_document, event_date)
    return created_events


def select_sec_event_signals(company: Any) -> tuple[EventSignal, ...]:
    sector = (getattr(company, "industry", "") or "").strip()
    signals = list(GENERIC_SEC_EVENT_SIGNALS)
    signals.extend(signal for signal in SECTOR_SEC_EVENT_SIGNALS if sector in signal.sectors)
    if sector == "Communication Services":
        signals.extend(MEDIA_SEC_EVENT_SIGNALS)
    return tuple(dedupe_signals(signals))


def dedupe_signals(signals: Iterable[EventSignal]) -> list[EventSignal]:
    seen: set[tuple[str, str]] = set()
    unique: list[EventSignal] = []
    for signal in signals:
        key = (signal.event_type, signal.decision_theme)
        if key in seen:
            continue
        seen.add(key)
        unique.append(signal)
    return unique


def append_additional_source(event: Any, source_document: Any, event_date: Any) -> None:
    raw = event.raw_extraction_json or {}
    additional_source_ids = list(raw.get("additional_source_ids") or [])
    if source_document.id not in additional_source_ids and source_document.id != raw.get("first_observed_source_id"):
        additional_source_ids.append(source_document.id)
        raw["additional_source_ids"] = additional_source_ids
        raw["latest_observed_filing_date"] = event_date.isoformat() if event_date else None
        event.raw_extraction_json = raw
        event.save(update_fields=["raw_extraction_json", "updated_at"])


def create_strategic_turns_from_events(
    *,
    company: Any,
    business_event_model: Any,
    strategic_turn_model: Any,
    strategic_turn_source_model: Any,
) -> list[Any]:
    turns: list[Any] = []
    approved_statuses = ("NEEDS_REVIEW", "APPROVED")
    event_types = (
        business_event_model.objects.filter(company=company, review_status__in=approved_statuses)
        .order_by()
        .values_list("event_type", "decision_theme")
        .distinct()
    )

    for event_type, decision_theme in event_types:
        decision_theme = decision_theme or "GENERAL"
        events = list(
            business_event_model.objects.filter(
                company=company,
                event_type=event_type,
                decision_theme=decision_theme,
            )
            .exclude(source_document__source_api="MANUAL")
            .order_by("event_date", "id")
        )
        if not events:
            continue
        first = events[0]
        last = events[-1]
        turn, _created = strategic_turn_model.objects.get_or_create(
            company=company,
            title=turn_title(company.name, event_type, decision_theme),
            defaults={
                "turn_type": event_type,
                "start_date": first.event_date,
                "end_date": last.event_date,
                "lifecycle_stage": first.lifecycle_stage,
                "summary": summarize_events(events),
                "before_state": first.before_state,
                "after_state": first.after_state,
                "trigger": first.trigger,
                "decision": first.decision,
                "outcome": first.outcome,
                "founder_lesson": founder_lesson_for(event_type),
                "confidence_score": Decimal("0.650"),
                "review_status": "NEEDS_REVIEW",
                "is_published": False,
            },
        )
        if not _created:
            turn.start_date = first.event_date
            turn.end_date = last.event_date
            turn.lifecycle_stage = first.lifecycle_stage
            turn.summary = summarize_events(events)
            turn.before_state = first.before_state
            turn.after_state = first.after_state
            turn.trigger = first.trigger
            turn.decision = first.decision
            turn.outcome = first.outcome
            turn.founder_lesson = founder_lesson_for(event_type)
            turn.confidence_score = Decimal("0.650")
            turn.save()
        for event in events:
            if event.source_document_id:
                strategic_turn_source_model.objects.get_or_create(
                    strategic_turn=turn,
                    source_document=event.source_document,
                    business_event=event,
                    defaults={"evidence_text": event.evidence_text},
                )
            for source_document in additional_source_documents_for(event):
                strategic_turn_source_model.objects.get_or_create(
                    strategic_turn=turn,
                    source_document=source_document,
                    business_event=event,
                    defaults={"evidence_text": event.evidence_text},
                )
        turns.append(turn)
    return turns


def additional_source_documents_for(event: Any) -> list[Any]:
    if not event.source_document_id:
        return []
    source_ids = (event.raw_extraction_json or {}).get("additional_source_ids") or []
    if not source_ids:
        return []
    source_model = event.source_document.__class__
    return list(source_model.objects.filter(id__in=source_ids))


def find_evidence_sentence(text: str, signal: EventSignal, keywords: Iterable[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    keyword_list = [keyword.lower() for keyword in keywords]
    candidates: list[tuple[int, str]] = []
    for sentence in sentences:
        sentence_clean = " ".join(sentence.split())
        sentence_lower = sentence_clean.lower()
        if is_boilerplate_sentence(sentence_lower):
            continue
        if is_signal_false_positive(signal, sentence_lower):
            continue
        if any(keyword_matches(sentence_lower, keyword) for keyword in keyword_list):
            if signal.decision_theme == "REGULATORY_LEGAL_RISK":
                candidates.append((regulatory_evidence_score(sentence_lower), sentence_clean[:700]))
                continue
            return sentence_clean[:700]
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        if candidates[0][0] > 0:
            return candidates[0][1]
    return ""


def keyword_matches(text_lower: str, keyword: str) -> bool:
    keyword_lower = keyword.lower()
    pattern = re.escape(keyword_lower).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text_lower))


def is_boilerplate_sentence(sentence_lower: str) -> bool:
    return any(pattern in sentence_lower for pattern in BOILERPLATE_PATTERNS)


def is_signal_false_positive(signal: EventSignal, sentence_lower: str) -> bool:
    generic_false_positive_patterns = (
        "could have a material adverse effect",
        "may adversely affect",
        "may not be able to",
        "events and consequences discussed in these risk factors",
    )
    if signal.decision_theme in {
        "ACQUISITION_ACTIVITY",
        "CAPITAL_ALLOCATION",
        "PARTNERSHIP_ACTIVITY",
        "PRODUCT_SERVICE_EXPANSION",
        "PRICING_PACKAGING",
    } and any(pattern in sentence_lower for pattern in generic_false_positive_patterns):
        return True

    if signal.decision_theme == "REGULATORY_LEGAL_RISK":
        if len(sentence_lower) < 55:
            return True
        if sentence_lower.count("|") >= 4:
            return True
        if re.fullmatch(r"[\w\s,/&().-]{1,80}", sentence_lower) and sentence_lower.rstrip(".") in {
            "government regulation",
            "legal proceedings",
            "supervision and regulation",
        }:
            return True
        if "table of contents" in sentence_lower:
            return True
        if "item 4" in sentence_lower and "legal proceedings" in sentence_lower:
            return True
        if "item 406" in sentence_lower or "code of ethics" in sentence_lower:
            return True
        if "internal revenue service |" in sentence_lower:
            return True
        if "general counsel" in sentence_lower:
            return True
        if re.fullmatch(r"legal proceedings\s+\d+\s+item\s+\d+\.?", sentence_lower):
            return True
        if "covid-19 pandemic" in sentence_lower and "regulatory" not in sentence_lower:
            return True

    if signal.decision_theme == "PRODUCT_SERVICE_EXPANSION":
        return any(
            pattern in sentence_lower
            for pattern in (
                "newly-launched products and services",
                "used to breach security",
                "not recognized until launched",
            )
        )

    if signal.decision_theme == "PRICING_PACKAGING":
        return "competitors" in sentence_lower and "pricing" in sentence_lower

    if signal.decision_theme == "CAPITAL_ALLOCATION":
        return "risk factors" in sentence_lower or "trade receivables" in sentence_lower

    if signal.decision_theme == "ADS_TIER":
        return any(
            pattern in sentence_lower
            for pattern in (
                "economic models underlying",
                "market is segmented",
                "ad-supported and piracy-based models",
            )
        )
    if signal.decision_theme == "GAMING":
        return "video gaming providers" in sentence_lower or "video gaming websites" in sentence_lower
    return False


def regulatory_evidence_score(sentence_lower: str) -> int:
    score = 1
    action_terms = (
        "settled",
        "settlement",
        "entered into",
        "agreed to",
        "resolved",
        "paid",
        "recorded",
        "accrued",
        "appealed",
        "responded",
        "implemented",
        "modified",
        "changed",
        "ceased",
        "suspended",
        "received",
        "filed",
        "defending",
        "cooperating",
        "remediated",
        "compliance program",
        "required us to",
        "require us to",
        "continue to make investments",
        "make investments",
    )
    risk_terms = (
        "subject to",
        "legal proceedings",
        "litigation",
        "regulatory",
        "regulation",
        "compliance",
        "governmental",
        "investigation",
        "laws and regulations",
    )
    score += sum(6 for term in action_terms if term in sentence_lower)
    score += sum(2 for term in risk_terms if term in sentence_lower)
    if "risk factors" in sentence_lower:
        score -= 2
    if "glossary" in sentence_lower or "abbreviation" in sentence_lower:
        score -= 6
    if sentence_lower.count("|"):
        score -= sentence_lower.count("|") * 3
    if len(sentence_lower) > 650:
        score -= 2
    return score


def source_claim_from_evidence(evidence: str) -> str:
    return evidence[:500]


def actual_change_for(signal: EventSignal, source_claim: str, *, company_name: str = "The company") -> str:
    if not source_claim:
        return ""
    claim_lower = source_claim.lower()

    if signal.decision_theme == "REGULATORY_LEGAL_RISK":
        return regulatory_actual_change(source_claim, company_name=company_name)

    generic_changes = {
        "COMPETITIVE_PRESSURE": f"{company_name} disclosed competitive pressure as a strategic constraint.",
        "INTERNATIONAL_OPERATIONS": f"{company_name} disclosed international operations as a material growth or risk area.",
        "ACQUISITION_ACTIVITY": f"{company_name} used acquisitions, mergers, or divestitures to reshape its business portfolio.",
        "PARTNERSHIP_ACTIVITY": f"{company_name} used partnerships, alliances, or collaborations to extend capabilities or market access.",
        "PRODUCT_SERVICE_EXPANSION": f"{company_name} expanded its product, service, or capability set.",
        "PRICING_PACKAGING": f"{company_name} adjusted pricing, packaging, or monetization as a business lever.",
        "COST_RESTRUCTURING": f"{company_name} disclosed cost, restructuring, impairment, or operating-expense pressure.",
        "PERFORMANCE_DECLINE": f"{company_name} disclosed performance pressure that may require strategic or operating response.",
        "CAPITAL_ALLOCATION": f"{company_name} disclosed capital allocation, financing, dividends, buybacks, or liquidity as a strategic lever.",
        "R_AND_D_PIPELINE": f"{company_name} invested in research, development, regulatory approvals, or product pipeline expansion.",
        "CREDIT_MARKET_RISK": f"{company_name} disclosed credit, liquidity, market, interest-rate, or capital risk as a strategic constraint.",
        "ENERGY_TRANSITION_AND_COMMODITY_EXPOSURE": f"{company_name} disclosed commodity, resource, climate, production, or energy-transition exposure.",
        "PLATFORM_AND_TECHNOLOGY_SHIFT": f"{company_name} invested in platform, cloud, software, AI, data, or technology shifts.",
        "SUPPLY_CHAIN_AND_CHANNEL_SHIFT": f"{company_name} adapted supply chain, fulfillment, inventory, or distribution channels.",
        "REAL_ESTATE_PORTFOLIO": f"{company_name} managed real estate portfolio, occupancy, leasing, development, or financing exposure.",
    }
    if signal.decision_theme in generic_changes:
        return generic_changes[signal.decision_theme]

    if signal.decision_theme == "ADS_TIER":
        if "introduced" in claim_lower or "ad-supported subscription plan" in claim_lower:
            return f"{company_name} introduced and continued offering a lower-priced ad-supported subscription plan."
        return f"{company_name} positioned ad-supported plans as part of its monetization model."

    if signal.decision_theme == "PAID_SHARING":
        if "extra member" in claim_lower:
            return f"{company_name} monetized account sharing through paid extra-member sub accounts."
        return f"{company_name} changed account-sharing and plan packaging to improve household monetization."

    if signal.decision_theme == "GAMING":
        if "offering" in claim_lower or "include games" in claim_lower or "films and games" in claim_lower:
            return f"{company_name} expanded the entertainment service beyond films and series into games."
        return f"{company_name} treated gaming as an adjacent entertainment category."

    if signal.decision_theme == "LIVE_EVENTS":
        if "expanded" in claim_lower or "offering" in claim_lower or "live programming" in claim_lower:
            return f"{company_name} expanded from on-demand programming into live programming and event-based entertainment."
        return f"{company_name} positioned live entertainment as part of its broader programming strategy."

    if signal.decision_theme == "ORIGINAL_CONTENT":
        if "original content" in claim_lower or "original content projects" in claim_lower:
            return f"{company_name} invested in original content as a differentiated content supply strategy."
        return f"{company_name} used exclusive or owned content to differentiate the service."

    if signal.decision_theme == "INTERNATIONAL_EXPANSION":
        if "over 190 countries" in claim_lower:
            return f"{company_name} operated at global scale, serving members in more than 190 countries."
        if "international operations" in claim_lower:
            return f"{company_name}'s international operations became material enough to carry dedicated operating risks."
        return f"{company_name} expanded the business across international markets."

    if signal.decision_theme == "SUBSCRIBER_DECLINE":
        if "decline" in claim_lower or "loss" in claim_lower or "churn" in claim_lower:
            return f"{company_name} disclosed subscriber or membership pressure that required a strategic response."
        return f"{company_name} reported membership-growth pressure."

    if signal.decision_theme == "COMPETITIVE_PRESSURE":
        return f"{company_name} disclosed intense competition as a strategic constraint on growth, pricing, content, and retention."

    if signal.decision_theme == "CONTENT_COST_PRESSURE":
        if "production costs" in claim_lower:
            return f"{company_name} carried production-cost risk as it became a content producer."
        if "content obligations" in claim_lower or "content assets" in claim_lower:
            return f"{company_name}'s content strategy created material content obligations and asset-management pressure."
        return f"{company_name} disclosed content-cost pressure as a strategic operating constraint."

    return signal.decision


def regulatory_actual_change(source_claim: str, *, company_name: str) -> str:
    claim = source_claim.strip()
    claim_lower = claim.lower()
    action_patterns = (
        "settled",
        "entered into",
        "agreed to",
        "resolved",
        "paid",
        "recorded",
        "accrued",
        "appealed",
        "responded",
        "implemented",
        "modified",
        "changed",
        "ceased",
        "suspended",
        "received",
        "filed",
        "is defending",
        "are defending",
        "defending",
        "cooperating",
        "remediated",
        "compliance program",
        "required us to",
        "require us to",
        "continue to make investments",
        "make investments",
    )
    if any(pattern in claim_lower for pattern in action_patterns):
        return f"{company_name}: {claim[:420]}"

    risk_patterns = (
        "subject to",
        "legal proceedings",
        "litigation",
        "regulatory",
        "regulation",
        "compliance",
        "governmental",
        "investigation",
        "laws and regulations",
    )
    if any(pattern in claim_lower for pattern in risk_patterns):
        return f"{company_name} disclosed this legal/regulatory risk; no response action was extracted: {claim[:360]}"

    return f"{company_name}: {claim[:420]}"


def summarize_events(events: list[Any]) -> str:
    decisions = []
    for event in events:
        if event.decision and event.decision not in decisions:
            decisions.append(event.decision)
    return " ".join(decisions[:3])


def founder_lesson_for(event_type: str) -> str:
    for signal in (*GENERIC_SEC_EVENT_SIGNALS, *SECTOR_SEC_EVENT_SIGNALS, *MEDIA_SEC_EVENT_SIGNALS):
        if signal.event_type == event_type:
            return signal.founder_lesson
    return "Use evidence from durable sources before treating a strategic pattern as a lesson."


def turn_title(company_name: str, event_type: str, decision_theme: str) -> str:
    theme_titles = {
        "ACQUISITION_ACTIVITY": "uses acquisitions and divestitures",
        "CAPITAL_ALLOCATION": "changes capital allocation",
        "COMPETITIVE_PRESSURE": "responds to competitive pressure",
        "COST_RESTRUCTURING": "restructures costs and operations",
        "CREDIT_MARKET_RISK": "manages credit and market risk",
        "ENERGY_TRANSITION_AND_COMMODITY_EXPOSURE": "adapts to commodity and transition exposure",
        "INTERNATIONAL_OPERATIONS": "expands international operations",
        "PARTNERSHIP_ACTIVITY": "uses partnerships and alliances",
        "PERFORMANCE_DECLINE": "responds to performance pressure",
        "PLATFORM_AND_TECHNOLOGY_SHIFT": "invests in technology shifts",
        "PRICING_PACKAGING": "adjusts pricing and packaging",
        "PRODUCT_SERVICE_EXPANSION": "expands products and services",
        "R_AND_D_PIPELINE": "invests in research and pipeline expansion",
        "REAL_ESTATE_PORTFOLIO": "manages real estate portfolio exposure",
        "REGULATORY_LEGAL_RISK": "adapts to regulatory and legal risk",
        "SUPPLY_CHAIN_AND_CHANNEL_SHIFT": "adapts supply chain and channels",
        "ADS_TIER": "launches advertising-supported monetization",
        "PAID_SHARING": "monetizes account sharing",
        "GAMING": "expands into gaming",
        "LIVE_EVENTS": "expands into live events",
        "ORIGINAL_CONTENT": "invests in original content",
        "INTERNATIONAL_EXPANSION": "expands internationally",
        "GENERAL": event_type.replace("_", " ").lower(),
    }
    title = theme_titles.get(decision_theme, decision_theme.replace("_", " ").lower())
    return f"{company_name} {title}"
