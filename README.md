# Clinical Code Finder

An intelligent agent that finds medical codes across multiple coding systems using LangGraph and OpenAI and Ollama

## Overview

This application uses LLMs and graph-based agents to intelligently search medical coding systems. It understands natural language queries and maintains conversation context to provide accurate medical codes.

## Features

- 🔍 Multi-system search (ICD-10, LOINC, RxNorm, HCPCS, UCUM, HPO)
- 🧠 Intelligent intent classification
- 💬 Conversation memory for contextual queries
- 📊 Confidence scoring and result ranking
- 🚀 Support for both Ollama and OpenAI models

## Installation

### Prerequisites
- Python 3.11+
- pip

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/duraik25/clinical-codes-finder.git
cd clinical_code_finder
```

2. **Create and activate virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```
2(a). **If using IDE like pyCharm**
    Folder can be directly opened in ide and following steps can be executed in IDE environment itself.
3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Create .env file:**
```bash
cp .env.example .env
```

5. **Configure your LLM provider in .env:**
Follow Ollama documentation to install and run Ollama server and host models locally
```bash
# For Ollama (default)
LLM_PROVIDER=ollama
OLLAMA_MODEL=gpt-oss:120b-cloud  # or mistral, codellama, llama2 etc.
OLLAMA_BASE_URL=http://localhost:11434

# For OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o # or gpt4 or other models as applicable 

# Optional
LLM_TEMPERATURE=0.1
```

### Verify Installation

Run this verification script:
```bash
python -c "from langchain_openai import ChatOpenAI; from src.agent.graph import create_clinical_codes_graph; print('✅ All imports successful!')"
```

## Running the Application

### Start Ollama (if using Ollama)
```bash
ollama serve
ollama pull llama2  # or your preferred model
```

### Start the Streamlit UI
```bash
streamlit run src/ui/app.py
```

The app will open at http://localhost:8501

## Usage Examples

### Basic Searches

#### Diagnosis Codes (ICD-10)
- Query: "diabetes type 2"
- Returns: E11.9, E11.65, etc.

#### Lab Tests (LOINC)
- Query: "hemoglobin A1c"
- Returns: 4548-4, 4549-2, etc.

#### Medications (RxNorm)
- Query: "metformin 500mg"
- Returns: 860974, 860975, etc.

#### Medical Equipment (HCPCS)
- Query: "wheelchair"
- Returns: K0001, K0002, etc.

### Conversation Memory Examples

The app maintains context across queries:

```
User: "diabetes"
Agent: [Returns ICD-10 codes for diabetes]

User: "what is the lab test for it?"
Agent: [Understands "it" = diabetes, returns glucose/HbA1c tests]

```

### More Phrase Queries

- Multiple concepts: "diabetes with neuropathy"
- Specific tests: "fasting glucose blood test"

## API Systems

The app searches these medical coding systems:

- **ICD-10**: International Classification of Diseases
- **LOINC**: Logical Observation Identifiers
- **RxNorm/RxTerms**: Medication terminology
- **HCPCS**: Healthcare Common Procedure Coding
- **UCUM**: Unified Code for Units of Measure
- **HPO**: Human Phenotype Ontology

## Project Structure

```
clinical_code_finder_cp/
├── src/
│   ├── agent/          # LangGraph agents
│   │   ├── graph.py    # Main workflow
│   │   ├── nodes.py    # Processing nodes
│   │   └── state.py    # State definitions
│   ├── api/            # API integrations
│   │   └── clinical_tables.py
│   ├── llm/            # LLM providers
│   │   ├── base.py     # Provider interface
│   │   ├── intent.py   # Intent classifier
│   │   └── summarizer.py
│   └── ui/             # Streamlit interface
│       └── app.py
├── requirements.txt
├── .env
└── README.md
```

## Troubleshooting

### Import Errors
```bash
pip uninstall langchain langgraph langchain-openai openai -y
pip cache purge
pip install -r requirements.txt
```

### OpenAI Proxy Error
If you see "unexpected keyword argument 'proxies'", ensure you're using:
- langchain-openai==1.0.1
- openai==2.6.1

### Ollama Connection Issues
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check OLLAMA_BASE_URL in .env

### Memory Not Working
- Click "🔄 Reset Conversation" in sidebar
- Ensure conversation_history is in AgentState


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Clinical Tables API by NIH/NLM
- LangChain and LangGraph frameworks
- Streamlit for the UI
