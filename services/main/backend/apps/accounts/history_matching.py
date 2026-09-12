"""Deterministic founder-to-history matching gates and transparent explanations."""
from __future__ import annotations
from collections import Counter
from typing import Any

REQUIRED_TYPES={"documented_action","source_reported_outcome","measurement"}

def rank_history_cases(context: dict[str, Any], episodes: list[dict[str, Any]]) -> dict[str, Any]:
    ranked=[]; rejected=[]
    for episode in episodes:
        reasons=[]; score=0
        if episode.get("claim_type") not in REQUIRED_TYPES: reasons.append("decision_irrelevant_claim_type")
        if not episode.get("source_families"): reasons.append("missing_source_family")
        if context.get("scope") == "product" and episode.get("scope") != "product": reasons.append("company_event_not_product_anchor")
        if context.get("business_type") and episode.get("business_type") and context["business_type"] != episode["business_type"]: reasons.append("business_model_mismatch")
        if context.get("objective") and context["objective"] == episode.get("objective"): score += 5
        elif context.get("objective"): reasons.append("objective_mismatch")
        if context.get("sector") == episode.get("sector"): score += 2
        if context.get("scope") == episode.get("scope"): score += 2
        if reasons: rejected.append({"id":episode.get("id"),"reasons":reasons}); continue
        ranked.append((score, episode))
    ranked.sort(key=lambda row:(-row[0],str(row[1].get("id"))))
    families=Counter(f for _, e in ranked for f in e.get("source_families",[]))
    semantics="insufficient" if not ranked else "case_study" if len(ranked)==1 or len(families)<2 else "supported_pattern"
    return {"semantics":semantics,"cases":[{**e,"match_score":s} for s,e in ranked],"rejected":rejected,"known_differences":["No repeated pattern is claimed without multiple cases and independent source families."] if semantics!="supported_pattern" else []}