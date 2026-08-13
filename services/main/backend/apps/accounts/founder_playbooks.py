from __future__ import annotations

from dataclasses import dataclass


FOUNDER_STAGES = ("validate", "build", "launch", "grow", "scale")
FOUNDER_OBJECTIVES = ("find_demand", "build_product", "win_customers", "improve_retention", "scale_operations")

STAGE_QUESTIONS = {
    "validate": "Is this a painful problem for a specific customer?",
    "build": "What is the smallest workflow customers will repeatedly use?",
    "launch": "Can we turn first value into a repeatable customer journey?",
    "grow": "What makes customers stay and recommend us?",
    "scale": "Which advantage can we compound without losing focus?",
}

DEFAULT_PLAYBOOK = {
    "label": "General business",
    "questions": ["Who has the problem now?", "What proves demand?", "What changes the next decision?"],
    "metrics": ["Customer evidence", "Activation", "Retention", "Revenue quality"],
    "risks": ["Unclear customer need", "Weak repeat usage", "Unproven economics"],
    "monetisation_models": ["Subscription", "Usage-based pricing", "Transaction fee", "Services"],
    "source_requirements": ["Official filings", "Company product pages", "Earnings materials", "Regulatory disclosures"],
}

SECTOR_PLAYBOOKS = {
    "Information Technology": {
        "label": "Technology",
        "questions": ["Which workflow is indispensable?", "What drives adoption and retention?", "Which pricing model matches delivered value?"],
        "metrics": ["Activation", "Retention", "Usage depth", "Gross margin", "Acquisition payback"],
        "risks": ["Weak product adoption", "Commoditisation", "Cloud or AI cost pressure", "Platform dependency"],
        "monetisation_models": ["Subscription", "Usage-based pricing", "Seat-based pricing", "Transaction fee", "Enterprise contract"],
        "source_requirements": ["Product pages", "Pricing pages", "Earnings materials", "Customer case studies"],
    },
    "Communication Services": {
        "label": "Communication",
        "questions": ["Which audience will return?", "How do content, distribution, and monetisation reinforce each other?", "What makes the audience valuable to customers or advertisers?"],
        "metrics": ["Audience reach", "Engagement", "Subscriber retention", "Advertising yield", "Content efficiency"],
        "risks": ["Audience churn", "Rising content cost", "Distribution dependence", "Advertising cyclicality"],
        "monetisation_models": ["Subscription", "Advertising", "Licensing", "Affiliate fee", "Marketplace fee"],
        "source_requirements": ["Earnings releases", "Subscriber disclosures", "Advertising materials", "Content and distribution announcements"],
    },
    "Energy": {
        "label": "Energy",
        "questions": ["Which asset or project creates durable cash flow?", "What regulatory, commodity, and capex risks can change the plan?", "Where is the economics strongest by geography?"],
        "metrics": ["Production or capacity", "Unit cost", "Realised price", "Capital intensity", "Project milestones"],
        "risks": ["Commodity exposure", "Permitting", "Capital overruns", "Operational reliability", "Geopolitical exposure"],
        "monetisation_models": ["Commodity sales", "Long-term contracts", "Capacity or service fee", "Asset leasing", "Value-added products"],
        "source_requirements": ["Annual filings", "Investor presentations", "Regulatory permits", "Project updates"],
    },
}


def normalize_sector(value: str) -> str:
    return (value or "").strip()


def playbook_for(sector: str, stage: str) -> dict:
    normalized_stage = stage if stage in FOUNDER_STAGES else ""
    base = dict(DEFAULT_PLAYBOOK)
    sector_playbook = SECTOR_PLAYBOOKS.get(normalize_sector(sector), {})
    base.update(sector_playbook)
    return {
        "sector": normalize_sector(sector),
        "sector_label": base["label"],
        "stage": normalized_stage,
        "stage_question": STAGE_QUESTIONS.get(normalized_stage, "Which decision matters most right now?"),
        "questions": base["questions"],
        "metrics": base["metrics"],
        "risks": base["risks"],
        "monetisation_models": base["monetisation_models"],
        "source_requirements": base["source_requirements"],
        "evidence_policy": {
            "reported_fact": "Directly supported by a dated source.",
            "observed_pattern": "A repeated pattern across source-backed comparable-company evidence.",
            "founder_hypothesis": "A proposal to test; not represented as a fact.",
            "unavailable": "Evidence is insufficient or conflicting.",
        },
    }
