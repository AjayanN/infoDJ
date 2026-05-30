"""Business-history query generation for source discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


NETFLIX_QUERY_TOPICS = (
    "DVD rental business model",
    "streaming launch",
    "subscription pricing change",
    "original content strategy",
    "international expansion",
    "advertising tier launch",
    "password sharing crackdown",
    "subscriber growth decline response",
    "partnership strategy",
    "acquisition strategy",
)

NETFLIX_STRATEGIC_TURN_QUERIES = (
    "Netflix DVD rental business model Reed Hastings",
    "Netflix streaming launch 2007 strategy",
    "Netflix Qwikster backlash pricing 2011",
    "Netflix House of Cards original content strategy 2013",
    "Netflix international expansion 2016 strategy",
    "Netflix subscriber loss 2022 strategy response",
    "Netflix advertising tier launch 2022 strategy",
    "Netflix password sharing crackdown 2023 strategy",
    "Netflix gaming expansion strategy",
    "Netflix live sports entertainment strategy",
    "Netflix partnership Microsoft advertising tier",
    "Netflix content spending strategy originals",
)

DEFAULT_BUSINESS_TOPICS = (
    "business model",
    "pricing change",
    "product strategy",
    "international expansion",
    "partnership strategy",
    "acquisition strategy",
    "leadership change",
    "competitive response",
    "revenue model expansion",
)

NETFLIX_SEC_RELEVANT_FORMS = ("10-K", "10-Q", "8-K")


@dataclass(frozen=True)
class QueryDefinition:
    company_name: str
    topic: str
    query: str


def generate_company_queries(
    company_name: str,
    *,
    aliases: Iterable[str] | None = None,
    topics: Iterable[str] | None = None,
    include_aliases: bool = True,
) -> list[QueryDefinition]:
    """Generate deterministic business-history queries for a company."""

    names = _company_names(company_name, aliases if include_aliases else None)
    topic_list = tuple(topics or _default_topics_for(company_name))

    definitions: list[QueryDefinition] = []
    seen: set[str] = set()
    for name in names:
        for topic in topic_list:
            query = f"{name} {topic}".strip()
            key = query.lower()
            if key in seen:
                continue
            seen.add(key)
            definitions.append(QueryDefinition(company_name=name, topic=topic, query=query))
    return definitions


def generate_query_strings(
    company_name: str,
    *,
    aliases: Iterable[str] | None = None,
    topics: Iterable[str] | None = None,
    include_aliases: bool = True,
) -> list[str]:
    return [
        definition.query
        for definition in generate_company_queries(
            company_name,
            aliases=aliases,
            topics=topics,
            include_aliases=include_aliases,
        )
    ]


def generate_netflix_queries(*, aliases: Iterable[str] | None = None) -> list[str]:
    """Return the Phase 7 predictable Netflix query list."""

    return generate_query_strings(
        "Netflix",
        aliases=aliases,
        topics=NETFLIX_QUERY_TOPICS,
        include_aliases=False,
    )


def generate_netflix_strategic_turn_queries() -> list[str]:
    """Return focused Netflix queries for strategic-turn discovery."""

    return list(NETFLIX_STRATEGIC_TURN_QUERIES)


def _default_topics_for(company_name: str) -> tuple[str, ...]:
    if company_name.strip().lower() == "netflix":
        return NETFLIX_QUERY_TOPICS
    return DEFAULT_BUSINESS_TOPICS


def _company_names(company_name: str, aliases: Iterable[str] | None) -> list[str]:
    names = [company_name.strip()]
    for alias in aliases or ():
        clean_alias = alias.strip()
        if clean_alias:
            names.append(clean_alias)

    seen: set[str] = set()
    unique_names: list[str] = []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            unique_names.append(name)
    return unique_names
