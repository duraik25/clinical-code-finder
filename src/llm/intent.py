from typing import List, Dict
from langchain_core.prompts import ChatPromptTemplate
import json
import logging
from .base import get_llm_provider
from ..agent.state import SearchIntent, CodingSystem

logger = logging.getLogger(__name__)


class IntentClassifier:
    def __init__(self):
        self.llm = get_llm_provider().get_llm()
        logger.warning(f"resolved llm provider: {self.llm}")

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyze medical queries and return strict JSON with:
            - primary_system: one of [icd10cm, loinc, rxnorm, hcpcs, ucum, hpo]
            - secondary_systems: list of other relevant systems
            - refined_query: search term
            - concept_type: one of [diagnosis, lab, drug, equipment, unit, phenotype]

            Examples:
            "diabetes" -> primary: icd10cm, type: diagnosis
            "glucose test" -> primary: loinc, type: lab
            "wheelchair" -> primary: hcpcs, type: equipment
            "mg/dL" -> primary: ucum, type: unit
            "ataxia" -> primary: hpo, type: phenotype
            "metformin" -> primary: rxnorm, type: drug

            Never interpret equipment/supply queries as diagnoses.
            Other type queries can be refined as appropriate to get better coverage.
            Identify secondary systems as applicable as well.
            if type is diagnosis or lab, do not map to type drug.
            Consider the conversation context when resolving references like 'it', 'that', or 'those'.
            When refining queries about lab tests for conditions, use the most specific common test:
            - high cholesterol → lipid profile
            - kidney disease → creatinine, eGFR
            - liver disease → liver function panel, ALT/AST
            - thyroid → TSH, T3/T4
            - anemia → CBC, hemoglobin
            Return only the JSON, no explanations."""),
            ("human", "{context}\n\nCurrent query: {query}")
        ])

    def classify(self, query: str, conversation_history: List[Dict] = None) -> SearchIntent:
        try:
            # Build richer context from last 3 conversations
            context_parts = []
            if conversation_history:
                for entry in conversation_history[-3:]:  # Last 3 queries
                    if entry.get("intent"):
                        context_parts.append(
                            f"Query: '{entry['query']}' → Found {entry['intent'].concept_type} ({entry['intent'].refined_query})"
                        )

            context = "\n".join(context_parts) if context_parts else "No previous context"

            # Update prompt to handle references
            prompt_input = {
                "query": query,
                "context": context
            }


            chain = self.prompt | self.llm
            response = chain.invoke(prompt_input)
            logger.info(f"llm classification response: {response}")

            content = response.content if hasattr(response, 'content') else str(response)

            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning("Failed to extract JSON, using fallback")
                data = self._fallback_parse(query)

            return SearchIntent(
                primary_system=CodingSystem(data["primary_system"]),
                secondary_systems=[CodingSystem(s) for s in data.get("secondary_systems", [])],
                refined_query=data.get("refined_query", query),
                concept_type=data.get("concept_type", "unknown")
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return self._keyword_fallback(query)

    def _keyword_fallback(self, query: str) -> SearchIntent:
        """Fallback classification using keywords"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["diabetes", "hypertension", "infection"]):
            return SearchIntent(
                primary_system=CodingSystem.ICD10,
                secondary_systems=[],
                refined_query=query,
                concept_type="diagnosis"
            )
        elif any(word in query_lower for word in ["test", "lab", "glucose", "hemoglobin"]):
            return SearchIntent(
                primary_system=CodingSystem.LOINC,
                secondary_systems=[],
                refined_query=query,
                concept_type="lab"
            )
        elif any(word in query_lower for word in ["mg", "tablet", "medication", "drug"]):
            return SearchIntent(
                primary_system=CodingSystem.RXTERMS,
                secondary_systems=[],
                refined_query=query,
                concept_type="drug"
            )
        else:
            return SearchIntent(
                primary_system=CodingSystem.ICD10,
                secondary_systems=[CodingSystem.LOINC],
                refined_query=query,
                concept_type="unknown"
            )
