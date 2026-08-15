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


SECTOR_PLAYBOOKS.update({
    "Financials": {"label": "Financial services", "questions": ["Which customer problem justifies trust?", "How do unit economics change with risk and capital?", "Which regulation shapes distribution?"], "metrics": ["Customer acquisition cost", "Retention", "Loss or default rate", "Assets or payment volume", "Contribution margin"], "risks": ["Credit or underwriting loss", "Regulatory compliance", "Fraud", "Funding concentration", "Trust erosion"], "monetisation_models": ["Net interest margin", "Transaction fee", "Assets-under-management fee", "Subscription", "Interchange or referral fee"], "source_requirements": ["Annual filings", "Regulatory disclosures", "Investor presentations", "Pricing and fee schedules"]},
    "Health Care": {"label": "Health care", "questions": ["Which clinical or operational outcome improves?", "Who adopts and who pays?", "What evidence and approvals are required?"], "metrics": ["Adoption by care setting", "Clinical or workflow outcome", "Reimbursement", "Retention", "Cost to serve"], "risks": ["Regulatory approval", "Reimbursement dependence", "Clinical evidence gaps", "Privacy and security", "Procurement cycles"], "monetisation_models": ["Reimbursement", "Per-member fee", "Enterprise subscription", "Procedure or usage fee", "Services"], "source_requirements": ["Regulator filings", "Clinical evidence", "Payer materials", "Provider contracts and announcements"]},
    "Consumer Discretionary": {"label": "Consumer", "questions": ["Which customer moment drives repeat purchase?", "How do brand, assortment, and channel improve conversion?", "What protects margin?"], "metrics": ["Traffic", "Conversion", "Repeat purchase", "Average order value", "Gross margin"], "risks": ["Demand volatility", "Inventory exposure", "Channel dependence", "Promotion pressure", "Brand dilution"], "monetisation_models": ["Product sale", "Subscription", "Marketplace take rate", "Loyalty membership", "Licensing"], "source_requirements": ["Product and pricing pages", "Earnings materials", "Retail and channel announcements", "Customer disclosures"]},
    "Consumer Staples": {"label": "Consumer staples", "questions": ["Which repeat-use need anchors demand?", "How do price, pack, and channel protect volume?", "Where does distribution create an advantage?"], "metrics": ["Volume", "Price and mix", "Household penetration", "Distribution", "Gross margin"], "risks": ["Input cost inflation", "Private-label pressure", "Retail concentration", "Regulatory labelling", "Demand shifts"], "monetisation_models": ["Product sale", "Distributor margin", "Subscription replenishment", "Licensing"], "source_requirements": ["Earnings materials", "Product pages", "Retail disclosures", "Commodity and regulatory data"]},
    "Industrials": {"label": "Industrials", "questions": ["Which workflow or asset has measurable downtime or cost?", "How does backlog convert into durable revenue?", "Where are service economics strongest?"], "metrics": ["Order intake", "Backlog", "Utilisation", "Service attachment", "Operating margin"], "risks": ["Project execution", "Supply chain concentration", "Cyclicality", "Safety", "Working capital"], "monetisation_models": ["Equipment sale", "Service contract", "Lease", "Consumables", "Outcome-based fee"], "source_requirements": ["Annual filings", "Order and backlog disclosures", "Product catalogues", "Customer project announcements"]},
    "Materials": {"label": "Materials", "questions": ["Which material specification earns a premium?", "How do capacity, energy, and feedstock drive economics?", "Which customer qualification creates stickiness?"], "metrics": ["Capacity utilisation", "Realised price", "Unit cost", "Yield", "Customer qualification"], "risks": ["Commodity and energy exposure", "Environmental permits", "Capacity oversupply", "Safety", "Customer concentration"], "monetisation_models": ["Material sale", "Long-term supply contract", "Specialty premium", "Recycling or recovery fee"], "source_requirements": ["Annual filings", "Plant and capacity updates", "Environmental permits", "Customer and product specifications"]},
    "Real Estate": {"label": "Real estate", "questions": ["Which location and tenant need create durable occupancy?", "What improves yield after financing and operating costs?", "Where is supply or regulation changing the risk?"], "metrics": ["Occupancy", "Rent growth", "Net operating income", "Lease duration", "Debt coverage"], "risks": ["Interest rates", "Tenant concentration", "Vacancy", "Refinancing", "Zoning and regulation"], "monetisation_models": ["Rent", "Management fee", "Development sale", "Transaction fee", "Ancillary services"], "source_requirements": ["Property filings", "Lease and occupancy disclosures", "Local planning data", "Investor presentations"]},
    "Utilities": {"label": "Utilities", "questions": ["Which regulated asset or service improves reliability?", "How do rate design and capex affect customer value?", "What approvals and grid constraints set the pace?"], "metrics": ["Rate base", "Reliability", "Customer growth", "Capital deployment", "Allowed return"], "risks": ["Regulatory outcome", "Grid reliability", "Fuel or power cost", "Capital overruns", "Weather exposure"], "monetisation_models": ["Regulated tariff", "Connection fee", "Capacity payment", "Service contract", "Energy sale"], "source_requirements": ["Regulator decisions", "Annual filings", "Grid plans", "Capital and reliability disclosures"]},
})


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
