"""Clinical Codes Finder - Agentic RAG for medical coding systems"""
__version__ = "1.0.0"
__author__ = "Your Name"

# Package-level imports for convenience
from .agent import create_clinical_codes_graph
from .api import ClinicalTablesAPI

__all__ = ["create_clinical_codes_graph", "ClinicalTablesAPI", "__version__"]
