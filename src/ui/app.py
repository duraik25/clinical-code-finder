from dotenv import load_dotenv
load_dotenv()  # This loads the .env file
import streamlit as st
import asyncio
from pathlib import Path
import sys
import os
import logging
from datetime import datetime



# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agent.graph import create_clinical_codes_graph
from src.api.clinical_tables import ClinicalTablesAPI
import json

st.set_page_config(
    page_title="Clinical Codes Finder",
    page_icon="🏥",
    layout="wide"
)


async def run_agent(query: str, status_container):
    logger.info(f"=== STARTING NEW GRAPH RUN for query: '{query}' ===")
    """Execute the agent graph with user query"""
    graph = create_clinical_codes_graph()

    initial_state = {
        "user_query": query,
        "conversation_history": st.session_state.conversation_history,
        "api_calls_made": [],
        "raw_results": {},
        "filtered_results": {},
        "summary": "",
        "confidence_scores": {}
    }

    # Custom progress tracking
    with status_container:
        with st.status("Processing query...", expanded=True) as status:
            st.write(f"🔍 Analyzing: '{query}'")

            # Run the graph with logging
            start_time = datetime.now()
            async with ClinicalTablesAPI() as api:
                result = await graph.ainvoke(initial_state)

            # Show intent classification
            if "intent" in result and result["intent"]:
                st.write(f"✅ Intent identified: **{result['intent'].concept_type}**")
                st.write(f"📊 Primary system: **{result['intent'].primary_system.value.upper()}**")
                if result['intent'].secondary_systems:
                    secondary_names = [s.value.upper() for s in result['intent'].secondary_systems]
                    st.write(f"🔗 Secondary systems: {', '.join(secondary_names)}")
                st.write(f"🔧 Refined query: '{result['intent'].refined_query}'")

            # Show API calls as they complete
            st.write("---")
            for call in result.get("api_calls_made", []):
                emoji = "✅" if call['result_count'] > 0 else "⚠️"
                st.write(f"{emoji} **{call['system'].upper()}**: {call['result_count']} results")

            # Show timing
            elapsed = (datetime.now() - start_time).total_seconds()
            st.write("---")
            st.write(f"⏱️ Completed in {elapsed:.1f} seconds")

            status.update(label="✅ Search complete!", state="complete")
    st.session_state.conversation_history.append({
        "query": query,
        "intent": result.get("intent"),
        "results_summary": f"{sum(len(codes) for codes in result.get('filtered_results', {}).values())} codes found"
    })
    return result


def display_results(results: dict):
    """Display results with clear attribution"""
    tab1, tab2, tab3 = st.tabs(["📋 Summary & Results", "📊 Statistics", "🔧 Debug"])

    with tab1:
        # Summary with reasoning
        st.subheader("🔍 Analysis & Reasoning")
        st.info(results.get("summary", "No summary available"))

        # Structured results with attribution
        st.subheader("📑 Found Codes by System")
        filtered_results = results.get("filtered_results", {})

        if not filtered_results:
            st.warning("No codes found matching your query")
        else:
            for system, codes in filtered_results.items():
                if codes:
                    st.write(f"### {system.upper()} System")

                    # Create a structured table
                    for i, code in enumerate(codes[:5], 1):
                        col1, col2, col3 = st.columns([1, 1, 4])
                        with col1:
                            st.metric("System", system.upper(), label_visibility="collapsed")
                        with col2:
                            st.code(code['code'])
                        with col3:
                            st.write(f"**{code['display']}**")

                        if i < len(codes[:5]):
                            st.divider()
    with tab2:  # Statistics
        st.metric("Total Codes Found", sum(len(codes) for codes in filtered_results.values()))
        st.metric("Systems Searched", len(results.get("api_calls_made", [])))

        # Confidence scores
        for system, score in results.get("confidence_scores", {}).items():
            st.metric(f"{system} Confidence", f"{score:.0%}")

    with tab3:  # Debug
        st.json({
            "intent": results.get("intent", {}),
            "api_calls": results.get("api_calls_made", []),
            "raw_results_count": {k: len(v) for k, v in results.get("raw_results", {}).items()}
        })


def display_results_1(results: dict):
    """Display results in organized format"""
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Summary", "🔍 Detailed Results", "🔧 Debug Info"])

    with tab1:
        # Summary section
        st.info(results.get("summary", "No summary available"))

        # Quick stats
        col1, col2, col3 = st.columns(3)
        with col1:
            total_codes = sum(len(codes) for codes in results.get("filtered_results", {}).values())
            st.metric("Total Codes Found", total_codes)
        with col2:
            systems_searched = len(results.get("api_calls_made", []))
            st.metric("Systems Searched", systems_searched)
        with col3:
            avg_confidence = sum(results.get("confidence_scores", {}).values()) / max(
                len(results.get("confidence_scores", {})), 1)
            st.metric("Avg Confidence", f"{avg_confidence:.0%}")


    with tab2:
        filtered_results = results.get("filtered_results", {})

        if not filtered_results:
            st.warning("No codes found matching your query")
        else:
            for system, codes in filtered_results.items():
                if codes:
                    with st.expander(f"**{system.upper()}** ({len(codes)} results)", expanded=True):
                        for i, code in enumerate(codes):
                            col1, col2, col3 = st.columns([1, 3, 1])
                            with col1:
                                st.code(code['code'])
                            with col2:
                                st.write(code['display'])
                            with col3:
                                if 'relevance_score' in code:
                                    st.progress(code['relevance_score'], text=f"{code['relevance_score']:.0%}")

                            if i < len(codes) - 1:
                                st.divider()

    with tab3:
        # Debug information
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Intent Analysis")
            if "intent" in results and results["intent"]:
                st.json({
                    "concept_type": results["intent"].concept_type,
                    "primary_system": results["intent"].primary_system.value,
                    "secondary_systems": [s.value for s in results["intent"].secondary_systems],
                    "refined_query": results["intent"].refined_query
                })

        with col2:
            st.subheader("API Calls")
            st.json(results.get("api_calls_made", []))

        st.subheader("Confidence Scores")
        scores = results.get("confidence_scores", {})
        if scores:
            score_df = {
                "System": list(scores.keys()),
                "Confidence": [f"{v:.2%}" for v in scores.values()]
            }
            st.dataframe(score_df, hide_index=True)


def main():
    st.title("🏥 Clinical Codes Finder")
    st.markdown("AI-powered medical code search across ICD-10, LOINC, RxTerms, and more")
    # Add conversation history to session state (at the top of main())
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

    # Sidebar
    with st.sidebar:
        st.header("💡 Example Queries")
        examples = {
            "🩺 Diagnosis": "diabetes type 2",
            "🧪 Lab Test": "hemoglobin A1c",
            "💊 Medication": "metformin 500 mg",
            "🦽 Equipment": "wheelchair",
            "📏 Unit": "mg/dL",
            "🧬 Phenotype": "ataxia"
        }

        for label, query in examples.items():
            if st.button(label, use_container_width=True):
                st.session_state.query = query

        if st.session_state.conversation_history:
            st.divider()
            st.subheader("📜 Recent Searches")
            for hist in st.session_state.conversation_history[-3:]:
                st.write(f"• {hist['query']}")
        st.divider()

        # System info
        st.subheader("⚙️ System Info")
        provider = os.getenv("LLM_PROVIDER", "ollama")
        model = os.getenv("OLLAMA_MODEL" if provider == "ollama" else "OPENAI_MODEL", "unknown")
        st.info(f"**Provider:** {provider.upper()}\n**Model:** {model}")

        # In the sidebar, after System Info section:
        st.divider()

        # Reset button
        if st.button("🔄 Reset Conversation", use_container_width=True):
            st.session_state.conversation_history = []
            st.session_state.query = ""  # Clear the query too
            st.success("Conversation history cleared!")
            st.rerun()

        # About section
        st.divider()
        st.subheader("ℹ️ About")
        st.markdown("""
        This tool uses AI to understand your clinical query and search across:
        - **ICD-10**: Diagnoses
        - **LOINC**: Lab tests
        - **RxTerms**: Medications
        - **HCPCS**: Procedures
        - **UCUM**: Units
        - **HPO**: Phenotypes
        """)
        # Main query interface
    query = st.text_input(
        "Enter clinical term:",
        value=st.session_state.get("query", ""),
        placeholder="e.g., diabetes, glucose test, metformin..."
    )

    # Search button and results
    if st.button("🔍 Search", type="primary") or query:
        if query:
            # Status container for progress updates
            status_container = st.container()

            # Run the async agent
            with st.spinner("Searching medical coding systems..."):
                results = asyncio.run(run_agent(query, status_container))

            # Display results
            display_results(results)
        else:
            st.warning("Please enter a clinical term to search")

if __name__ == "__main__":
    main()
