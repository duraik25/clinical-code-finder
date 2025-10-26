from langgraph.graph import StateGraph, END
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


def create_clinical_codes_graph():
    """Create the agentic RAG graph for clinical code finding"""
    from .state import AgentState
    from .nodes import (
        classify_intent_node,
        search_primary_node,
        search_secondary_node,
        aggregate_results_node,
        summarize_results_node
    )

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("search_primary", search_primary_node)
    graph.add_node("search_secondary", search_secondary_node)
    graph.add_node("aggregate_results", aggregate_results_node)
    graph.add_node("summarize", summarize_results_node)

    # Define edges
    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "search_primary")

    # Conditional edge
    def should_search_secondary(state):
        return "search_secondary" if state["intent"].secondary_systems else "aggregate_results"

    graph.add_conditional_edges(
        "search_primary",
        should_search_secondary,
        {
            "search_secondary": "search_secondary",
            "aggregate_results": "aggregate_results"
        }
    )

    graph.add_edge("search_secondary", "aggregate_results")
    graph.add_edge("aggregate_results", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()


async def run_agent(query: str, conversation_history: List[Dict] = None):
    """Run the clinical codes agent with conversation context"""
    from .state import AgentState

    history = conversation_history or []
    app = create_clinical_codes_graph()

    # Build initial state with conversation context
    initial_state: AgentState = {
        "user_query": query,
        "conversation_history": history,  # Pass to intent classifier
        "intent": None,
        "api_calls_made": [],
        "raw_results": {},
        "filtered_results": {},
        "confidence_scores": {},
        "summary": ""
    }

    # Run the graph
    result = await app.ainvoke(initial_state)

    # Update history with this interaction
    history.append({
        "query": query,
        "intent": result["intent"],
        "results_summary": f"{len(result['filtered_results'])} systems with results"
    })

    return result, history

