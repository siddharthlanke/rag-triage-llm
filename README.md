# RAG Triage LLM

An open, reproducible **Retrieval-Augmented Generation (RAG)** prototype for support-ticket triage.  
It provides instant, evidence-grounded suggestions and a human-in-the-loop triage flow (classification, priority, and team-facing solution), with **local inference for privacy**.

> **To view the prototype in action:** [link]

---

<details>
<summary><strong>Table of Contents</strong></summary>

- [Features](#features)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
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

- Retrieval-augmented instant suggestions with hallucination checks for reliability  
- Triage pipeline: category classification, priority assessment, internal solution synthesis, and storage for closed-loop learning  
- Local models via **Ollama** for both generation and embeddings to keep data on device  
- Deterministic control-flow graphs for observability and auditability  

---

## Architecture

- **Embeddings:** MiniLM class (`all-minilm:latest`)  
- **Vector store:** Astra DB (serverless, vector-enabled)  
- **Web app:** Flask backend with two JSON endpoints and a lightweight HTML/JS/CSS frontend  

**Pipelines:**  
- Suggestion graph: expand → retrieve (k=5) → relevance gate → generate → hallucination check  
- Triage graph: classify → prioritise → generate team solution → store ticket  

---

## Repository Layout

```
app.py                # web server and pipelines
ingest_data.py        # one-shot ingestion: assemble → split (500/50) → embed → upsert
templates/index.html  # UI
static/script.js, static/style.css  # client logic and styles
requirements.txt      # Python dependencies
.env                  # user-supplied secrets (not committed)
```

---

## Prerequisites

- Python **3.10+** and Git  
- Astra DB serverless (Vector enabled) with API endpoint and token  
- Ollama installed and running; pull models:  

```
ollama pull qwen3:4b
ollama pull all-minilm:latest
```

---

## Quick Start

### Clone and create a virtual environment

```
git clone https://github.com/siddharthlanke/rag-triage-llm
cd rag-triage-llm
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate
```

### Install dependencies

```
pip install -r requirements.txt
```

### Configure environment

Create `.env` in the repo root with the following content:  

```
ASTRA_DB_API_ENDPOINT=<your_endpoint>
ASTRA_DB_TOKEN=<your_token>
```

### Prepare data and ingest

Place `combined.csv` (your data file in csv format) in the repo root and run:  

```
python ingest_data.py
```

### Run the app

```
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in a browser.  

---

## How to Use

- **Instant Suggestion:** Enter Subject and Description, then click **Get Instant Suggestion** for a concise, grounded answer.  
- **Raise Ticket:** If the suggestion is insufficient, click **This Didn’t Help, Raise A Support Ticket** to classify, prioritise, and persist the case with an internal solution summary.  

---

## Configuration

- Retrieval top-k is fixed at **5** (adjust in `app.py` if desired)  
- Chunking is **500 characters** with **50 overlap** (adjust in `ingest_data.py`)  
- Models are referenced by name — ensure the same versions are pulled with Ollama for reproducibility  

---

## Security and Governance

- All inference and embeddings run locally via Ollama — no ticket content sent to external LLM APIs  
- The triage collection stores metadata (including email if provided) — configure role-based access and retention policies in the database  
- Add redaction for sensitive content if required  

---

## Troubleshooting

- **Ollama not found or models missing:** Ensure the service is running and the models are pulled  
- **Vector store errors:** Verify `ASTRA_DB_API_ENDPOINT` and `ASTRA_DB_TOKEN` in `.env`  
- **Empty retrievals:** Confirm `combined.csv` was ingested without errors and that chunking parameters match the defaults  

---

## Citation

If this repository informs academic work, please cite relevant RAG and governance references that inspired the design:

- Retrieval-Augmented Generation (Lewis et al., 2020)  
- Grounding/verification (Izacard & Grave, 2021; Ji et al., 2023)  
- Data quality, chunking, and query expansion (Guo et al., 2021; Khattab & Zaharia, 2020; Shuster et al., 2022)  
- Governance and ethics (European Commission, 2021; Leslie, 2020)  
