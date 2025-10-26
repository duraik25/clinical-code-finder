from typing import TypedDict, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class CodingSystem(Enum):
    ICD10 = "icd10cm"
    LOINC = "loinc"
    RXNORM = "rxnorm"
    HCPCS = "hcpcs"
    UCUM = "ucum"
    HPO = "hpo"


@dataclass
class SearchIntent:
    primary_system: CodingSystem
    secondary_systems: List[CodingSystem]
    refined_query: str
    concept_type: str  # diagnosis, lab, drug, procedure, unit, phenotype


class AgentState(TypedDict):
    # Input
    user_query: str

    #Conversation History
    conversation_history: List[Dict]

    # Processing state
    intent: SearchIntent
    api_calls_made: List[Dict[str, Any]]
    raw_results: Dict[str, List[Dict]]

    # Output
    filtered_results: Dict[str, List[Dict]]
    summary: str
    confidence_scores: Dict[str, float]
