import asyncio
from typing import Dict, Any, List
import logging
from .state import AgentState, CodingSystem

logger = logging.getLogger(__name__)

# Lazy initialization to avoid import errors
_intent_classifier = None
_summarizer = None


def get_intent_classifier():
    global _intent_classifier
    if _intent_classifier is None:
        from ..llm.intent import IntentClassifier
        _intent_classifier = IntentClassifier()
    return _intent_classifier


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        from ..llm.summarizer import ResultSummarizer
        _summarizer = ResultSummarizer()
    return _summarizer


async def classify_intent_node(state: AgentState) -> Dict[str, Any]:
    """Classify user intent and determine which APIs to call"""
    try:
        classifier = get_intent_classifier()
        intent = classifier.classify(
            state["user_query"],
            state.get("conversation_history", [])  # Pass history
        )
        logger.info(f"Classified intent: {intent.concept_type} -> {intent.primary_system.value}")
        return {"intent": intent}
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        from .state import SearchIntent
        fallback = SearchIntent(
            primary_system=CodingSystem.ICD10,
            secondary_systems=[],
            refined_query=state["user_query"],
            concept_type="unknown"
        )
        return {"intent": fallback}


async def search_primary_node(state: AgentState) -> Dict[str, Any]:
    """Search the primary coding system"""
    intent = state["intent"]
    api_calls = state.get("api_calls_made", [])
    raw_results = state.get("raw_results", {})

    results = await _search_system(intent.primary_system, intent.refined_query, limit=10)

    api_calls.append({
        "system": intent.primary_system.value,
        "query": intent.refined_query,
        "result_count": len(results)
    })

    raw_results[intent.primary_system.value] = results

    return {
        "api_calls_made": api_calls,
        "raw_results": raw_results
    }


async def search_secondary_node(state: AgentState) -> Dict[str, Any]:
    """Search secondary coding systems"""
    intent = state["intent"]
    api_calls = state.get("api_calls_made", [])
    raw_results = state.get("raw_results", {})

    for system in intent.secondary_systems[:3]:
        results = await _search_system(system, intent.refined_query, limit=5)

        api_calls.append({
            "system": system.value,
            "query": intent.refined_query,
            "result_count": len(results)
        })

        if results:
            raw_results[system.value] = results

    return {
        "api_calls_made": api_calls,
        "raw_results": raw_results
    }


async def aggregate_results_node1(state: AgentState) -> Dict[str, Any]:
    """Filter and rank results based on relevance"""
    raw_results = state.get("raw_results", {})
    filtered_results = {}
    confidence_scores = {}

    for system, results in raw_results.items():
        logger.info(f"Processing {system}: {len(results)} raw results")
        filtered = []
        for result in results[:5]:
            score = calculate_relevance_score(result, state["intent"].refined_query)
            logger.info(f"Score for '{result['display']}': {score}")
            if score > 0.3:
                result["relevance_score"] = score
                filtered.append(result)
        logger.info(f"{system}: {len(filtered)} results after filtering")
        if filtered:
            filtered_results[system] = sorted(filtered, key=lambda x: x["relevance_score"], reverse=True)
            confidence_scores[system] = max([r["relevance_score"] for r in filtered])
        else:
            confidence_scores[system] = 0.0
    logger.info(f"Final filtered_results: {list(filtered_results.keys())}")
    return {
        "filtered_results": filtered_results,
        "confidence_scores": confidence_scores
    }


def aggregate_results_node(state: AgentState) -> Dict[str, Any]:
    raw_results = state.get("raw_results", {})
    filtered_results = {}
    confidence_scores = {}

    for system, results in raw_results.items():
        if results:
            # Just take top 5 - API already ranked them
            filtered_results[system] = results[:5]
            # Simple confidence based on result count
            confidence_scores[system] = min(len(results) / 10, 1.0)

    return {
        "filtered_results": filtered_results,
        "confidence_scores": confidence_scores
    }


async def summarize_results_node(state: AgentState) -> Dict[str, Any]:
    """Generate plain English summary"""
    summarizer = get_summarizer()
    summary = await summarizer.summarize(
        query=state["user_query"],
        results=state["filtered_results"],
        intent=state["intent"],
        confidence_scores=state["confidence_scores"]
    )

    return {"summary": summary}


async def _search_system(system: CodingSystem, query: str, limit: int) -> List[Dict]:
    """Helper to search a specific coding system"""
    endpoint_map = {
        CodingSystem.ICD10: "icd10cm",
        CodingSystem.LOINC: "loinc_items",
        CodingSystem.RXNORM: "rxterms",
        CodingSystem.HCPCS: "hcpcs",
        CodingSystem.UCUM: "ucum",
        CodingSystem.HPO: "hpo"
    }

    endpoint = endpoint_map.get(system)
    if not endpoint:
        logger.warning(f"No endpoint mapping for system: {system}")
        return []

    try:
        from ..api.clinical_tables import ClinicalTablesAPI
        async with ClinicalTablesAPI() as api:
            results = await api.search(
                endpoint=endpoint,
                query=query,
                limit=limit
            )
            return results
    except Exception as e:
        logger.error(f"Search failed for {system}: {e}")
        return []


def calculate_relevance_score(result: Dict, query: str) -> float:
    """Calculate relevance score based on string matching"""
    query_lower = query.lower()
    text = f"{result.get('display', '')} {result.get('code', '')}".lower()

    if query_lower in text:
        return 1.0

    query_words = set(query_lower.split())
    text_words = set(text.split())

    if not query_words:
        return 0.0

    intersection = query_words.intersection(text_words)
    union = query_words.union(text_words)

    return len(intersection) / len(union) if union else 0.0
