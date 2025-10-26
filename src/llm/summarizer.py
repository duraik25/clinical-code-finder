# src/llm/summarizer.py
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Any
from .base import get_llm_provider


class ResultSummarizer:
    def __init__(self):
        # Use the provider pattern instead of direct import
        self.llm = get_llm_provider().get_llm()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """For each code found, explain in  why it matches the query.  
            Generate a clear, minimal explanation with traceable reasoning."""),
            ("human", """Query: {query}

            Results:
            {results_detail}""")
        ])

    async def summarize(self, query: str, results: Dict[str, List[Dict]], intent: Any,
                        confidence_scores: Dict[str, float]) -> str:
        # Create detailed results summary
        results_detail = []
        for system, items in results.items():
            if items:
                results_detail.append(f"\n{system.upper()} ({len(items)} codes):")
                for item in items[:5]:  # Top 5 per system
                    results_detail.append(f"  • {item['code']}: {item['display']}")

        results_text = "\n".join(results_detail) if results_detail else "No codes found"

        chain = self.prompt | self.llm
        response = await chain.ainvoke({
            "query": query,
            "intent_type": intent.concept_type,
            "primary_system": intent.primary_system.value,
            "results_detail": results_text
        })

        return response.content if hasattr(response, 'content') else str(response)

