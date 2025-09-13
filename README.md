# RAG Triage LLM

An open, reproducible **Retrieval-Augmented Generation (RAG)** prototype for support-ticket triage.  
It provides instant, evidence-grounded suggestions (classification, priority, and team-facing solution), with **local inference for privacy**.

---

<details>
<summary><strong>Table of Contents</strong></summary>

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [How to Use](#how-to-use)
- [Configuration](#configuration)
- [Security and Governance](#security-and-governance)
- [Troubleshooting](#troubleshooting)
- [Citation](#citation)

</details>

---

## Features

- Retrieval-augmented instant suggestions with hallucination checks  
- Triage pipeline: category classification, priority assessment, internal solution generation, and storage  
- Local models via **Ollama** for both generation and embeddings to keep data on device  
- Deterministic control-flow graphs for observability and auditability  

---

## Architecture

- **Embeddings:** MiniLM class (`all-minilm:latest`)  
- **Vector store:** Astra DB (serverless, vector-enabled)  
- **Web app:** Flask backend with two JSON endpoints and a lightweight HTML/JS/CSS frontend  

**Pipelines:**  
- Suggestion graph: expand → retrieve → relevance gate → generate → hallucination check  
- Triage graph: classify → prioritise → generate team solution → store ticket  

---

## Prerequisites

- **Python 3.10+** installed ([download here](https://www.python.org/downloads/))  
- **Git** for cloning the repository and version control ([download here](https://git-scm.com/downloads))  
- **Astra DB** serverless (Vector-enabled) instance with API endpoint and token ([sign up here](https://astra.datastax.com/signup))  
- **Ollama** installed and running locally to support both the LLM and embedding model ([download here](https://ollama.com/download))  
- **Anaconda** or **Miniconda** to create and activate a conda virtual environment for isolating dependencies ([download here](https://www.anaconda.com/download/success))  

> **Note:** Docker is *not* required for this project.

---

## Quick Start

All commands below should be run **inside the conda virtual environment** (except Ollama, which is recommended to be installed and run globally).  

### 1. Clone this repo and create a virtual environment

```bash
git clone https://github.com/siddharthlanke/rag-triage-llm
cd rag-triage-llm

conda create -n rag-triage-llm python=3.10 -y
conda activate rag-triage-llm
conda install pip
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Alternatively, you can install packages individually:

```bash
pip install langchain langchain-text-splitters langchain-community langgraph langchain-openai langchain-google-genai langchain-ollama langchain-astradb python-dotenv pandas Flask Flask-Cors
```

### 3. Configure environment

Create a `.env` file (plain text, no extension) in the repo root with the following content:

```
ASTRA_DB_API_ENDPOINT=<your_astra_db_api_endpoint>
ASTRA_DB_TOKEN=<your_astra_db_token>
LANGSMITH_ENDPOINT=<optional>
LANGSMITH_API_KEY=<optional>
LANGSMITH_PROJECT=<optional>
```

- `ASTRA_DB_API_ENDPOINT` and `ASTRA_DB_TOKEN` are **required**  
- LangSmith keys are **optional** (only for latency profiling)

### 4. Install Ollama globally and pull models

> Ollama should be installed **globally outside the virtual environment**.  
> You may open another terminal window to handle installation and model downloads.  

In that separate terminal, run:

```bash
ollama serve
ollama pull qwen3:4b
ollama pull all-minilm:latest
```

Keep Ollama running while using the app so that:  
- `ChatOllama(model="qwen3:4b")` (LLM)  
- `OllamaEmbeddings(model="all-minilm:latest")` (embeddings)  

remain accessible.

### 5. Ingest your data

Place your dataset (CSV format) in the repo root and run inside the virtual environment:

```bash
python ingest_data.py
```

This will:  
- Load the CSV  
- Split text into 500-character chunks (50 overlap)  
- Compute embeddings with **all-minilm:latest**  
- Upload vectors into Astra DB collection  

On completion, the script reports processed documents and chunks.

### 6. Launch the app

Inside the virtual environment:

```bash
python app.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.  

---

## How to Use

- **Instant Suggestion:** Enter Subject and Description, then click **Get Instant Suggestion** for a concise, grounded answer.  
- **Raise Ticket:** If the suggestion is insufficient, click **This Didn’t Help, Raise A Support Ticket** to classify, prioritise, and persist the ticket with an internal solution summary.  

---

## Configuration

- Retrieval top-k is fixed at **5** (adjust in `app.py` if required)  
- Chunking is **500 characters** with **50 overlap** (adjust in `ingest_data.py`)  
- Models are referenced by name - ensure the same versions are pulled with Ollama for reproducibility  

---

## Security and Governance

- All inference and embeddings run locally via Ollama — no ticket content sent to external LLM APIs  
- The triage collection stores metadata (including email if provided) - configure role-based access and retention policies in the database  

---

## Troubleshooting

- If the Flask server fails on localhost:5000, check that another process isn’t already using that port.
- **Ollama not found or models missing:** Ensure the service is running and the models are pulled  
- **Vector store errors:** Verify `ASTRA_DB_API_ENDPOINT` and `ASTRA_DB_TOKEN` in `.env`  
- **Empty retrievals:** Confirm `data.csv` file was ingested without errors and that chunking parameters match the defaults  

---

## Citation

If this repository informs academic work, please cite relevant RAG and governance references that inspired the design:

- Retrieval-Augmented Generation (Lewis et al., 2020)  
- Grounding/verification (Izacard & Grave, 2021; Ji et al., 2023)  
- Data quality, chunking, and query expansion (Guo et al., 2021; Khattab & Zaharia, 2020; Shuster et al., 2022)  
- Governance and ethics (European Commission, 2021; Leslie, 2020)  
