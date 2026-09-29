# 🛡️ SRE-Shield – AI-Powered Self-Learning Incident Response Agent
> **"The system learns from every incident and uses previous experience to solve future incidents faster."**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io)
[![Groq LLM](https://img.shields.io/badge/LLM-Groq%20Llama--3.3--70b-orange.svg)](https://groq.com)
[![Hindsight Memory](https://img.shields.io/badge/Memory-Hindsight%204--Network-purple.svg)](https://github.com/vectorize-io/hindsight)
[![Security](https://img.shields.io/badge/Security-Memory%20Defense%20Active-emerald.svg)](#memory-defense-layer)

---

## 1. Project Overview

**SRE-Shield** is an autonomous, self-learning Incident Response platform designed for DevOps and Site Reliability Engineering (SRE) teams. Instead of treating outages as isolated emergencies or answering queries like a stateless chatbot, SRE-Shield acts like a **Principal SRE with persistent long-term memory**. 

When a production incident strikes, SRE-Shield ingests telemetry, sanitizes sensitive secrets, recalls matching historical incident trajectories from **Hindsight Agent Memory**, diagnoses the root cause with high confidence, recommends peer-reviewed runbooks and precise CLI commands, requires **Human-in-the-Loop** authorization, executes safe simulated remediation, verifies cluster health, generates a blameless post-mortem, and **feeds the verified learning back into persistent memory** to immunize the infrastructure against future recurrences.

---

## 2. Problem Statement & The "Stateless AI" Trap

During high-severity production outages (Sev-1 / Sev-0):
1. **Tribal Knowledge Vanishes:** On-call engineers spend 40–70% of MTTR (Mean Time to Recovery) rediscovering root causes that were already diagnosed and solved weeks ago by another engineer.
2. **Stateless AI Chatbots Fail in SRE:** Generic LLMs (ChatGPT, raw RAG) provide generic textbook advice ("Check your logs, restart your server, ping the gateway"). They have no memory of cluster topology, historical failure modes, or what exact command actually solved the problem last Tuesday.
3. **Destructive Command Risk:** Autonomous agents that blindly run shell scripts risk corrupting production databases or deleting active namespaces.
4. **Leaked Secrets in Vector Stores:** Engineers frequently paste raw stack traces containing database passwords, API tokens, and JWTs directly into prompts and vector databases, creating catastrophic security vulnerabilities.

---

## 3. The Solution: Closed-Loop SRE-Shield Architecture

SRE-Shield solves this with a **closed-loop self-learning architecture** anchored by **Hindsight Agent Memory** and **Memory Defense**:

```text
               Production Alerts / Telemetry
                             │
                             ▼
                 [ Memory Defense Sanitizer ]
              (Masks passwords, tokens, API keys)
                             │
                             ▼
                 [ SRE Incident Analyzer ]
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
  [ Hindsight Memory ]                   [ Stateless LLM ]
 (Recalls 4 Networks:                   (Generic textbook
  Past Fixes, Beliefs)                   guesses for comparison)
         │                                       │
         ▼                                       ▼
  [ Grounded Diagnosis ]                  [ Low-Confidence Guess ]
  (Confidence: 96% | INC-1001)           (Confidence: 45%)
         │
         ▼
  [ Runbook Recommendation ] (e.g. DB-CONNECTION-001)
         │
         ▼
  [ Human-in-the-Loop Gate ] (Review, Modify, Reject, Approve)
         │ [Approved]
         ▼
  [ Safe Execution Sandbox ] (SIMULATION MODE: k8s/redis/aws)
         │
         ▼
  [ Automated Verification ] (Health probe 200 OK, Error rate 0.00%)
         │
         ▼
  [ Blameless Post-Mortem ] (Drafted by AI, edited & approved by SRE)
         │
         ▼
  [ Hindsight Retain & Reflect ] ───► Updates Entity Summaries & Beliefs
                                  └──► Future Incidents Solved in Seconds!
```

---

## 4. Key Features

- **Hindsight 4-Network Agent Memory:**
  - 🧠 **Experience Network:** First-person action history (alerts, root causes, verified CLI commands, recall counters).
  - 🏢 **Entity Summaries:** Rolling synthesized profiles for microservices (known failure modes, preferred runbooks, average MTTR).
  - ⚡ **Evolving Beliefs:** Calibrated operational invariants and heuristics developed over time.
  - 🌐 **World Network:** Architecture constraints, PostgreSQL connection quotas, and availability SLOs.
- **Memory Defense Sanitization Layer:** Automatically detects and replaces passwords, JWTs, Bearer tokens, private keys, and cloud secrets with `[REDACTED_*]` before saving to persistent storage.
- **Dual Diagnosis (With vs Without Memory):** Side-by-side contrast demonstrating the radical superiority of persistent incident memory over stateless AI.
- **Human-in-the-Loop Production Safety:** Dangerous commands are NEVER executed autonomously. Features `[Approve & Execute]`, `[Modify & Execute]`, and `[Reject]` controls clearly marked with `[SIMULATION MODE]`.
- **Automated Health Verification:** Probes cluster endpoints (`/healthz` 200 OK) and monitors telemetry to verify that the remediation succeeded.
- **Automated Post-Mortem Generator:** Generates comprehensive post-mortems (Summary, Impact, Timeline, Root Cause, What Worked, What Failed, Prevention, Lessons Learned) and stores approved findings back into memory.
- **Interactive SRE AI Copilot:** Natural-language chat grounded in past post-mortems and cluster history.
- **Runbook Catalog:** Standard operating procedures with investigation checklists, CLI snippets, and historical success rates.
- **SRE Analytics & MTTR Dashboards:** Visualizes MTTR reduction curves, service reliability distributions, and runbook efficacy.

---

## 5. Technology Stack

- **Backend:** Python 3.10+, FastAPI (Async REST architecture), Uvicorn.
- **Database / ORM:** SQLAlchemy 2.0 + aiosqlite (async SQLite zero-friction local storage, pluggable to PostgreSQL + pgvector via `DATABASE_URL`).
- **Memory Engine:** Hindsight Agent Memory architecture with Hybrid Vector + BM25 keyword matching (`scikit-learn` TF-IDF cosine distance + token boosting). Remote sync support via `HINDSIGHT_API_KEY`.
- **AI Inference:** Groq API (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`) with automatic fallback to an Intelligent SRE Heuristic Expert Engine for 100% offline resiliency.
- **Frontend Dashboard:** Streamlit with custom Dark Enterprise SRE styling, Plotly interactive charts, and live operational status indicators.
- **Containerization:** Docker, Docker Compose.

---

## 6. Project Structure

```text
sre-shield/
│
├── backend/
│   ├── config.py                 # Configuration and environment settings
│   ├── api/
│   │   ├── main.py               # FastAPI application & lifespan management
│   │   └── routes.py             # REST API endpoints (Incidents, Memory, Runbooks, Execution)
│   ├── memory/
│   │   ├── base.py               # BaseMemoryEngine abstract interface
│   │   ├── hindsight_engine.py   # Hindsight 4 Networks (World, Experience, Entities, Beliefs)
│   │   └── embeddings.py         # Hybrid Vector & SRE keyword search engine
│   ├── security/
│   │   └── sanitizer.py          # Memory Defense secret redaction layer
│   ├── agents/
│   │   ├── groq_client.py        # Groq client with resilient heuristic fallback
│   │   ├── analyzer.py           # Dual Incident Analyzer (Memory vs Stateless)
│   │   ├── postmortem_agent.py   # Post-Mortem generator & memory closer
│   │   └── assistant.py          # SRE AI Assistant grounded in Hindsight
│   ├── execution/
│   │   └── executor.py           # Safe simulated execution & verification engine
│   ├── runbooks/
│   │   └── runbook_manager.py    # Catalog of standard SRE runbooks
│   └── database/
│       ├── connection.py         # Async and Sync database sessions
│       ├── models.py             # SQLAlchemy models for incidents, memory, runbooks
│       └── seed_data.py          # 10 realistic historical SRE incidents & runbooks
│
├── frontend/
│   ├── app.py                    # Streamlit entrypoint & router
│   ├── components.py             # Dark SRE theme CSS, metric cards, badges
│   ├── pages_dashboard.py        # 1. Executive SRE Dashboard & Live Telemetry
│   ├── pages_incident_center.py  # 2. Incident Ingestion, 1-Click Scenarios, Dual Diagnosis
│   ├── pages_approval.py         # 3. Human-in-the-Loop Safe Execution & Verification
│   ├── pages_postmortem.py       # 4. Post-Mortem Generator & Learning Loop Retention
│   ├── pages_hindsight.py        # 5. Hindsight 4-Network Memory Inspector
│   ├── pages_runbooks.py         # 6. Standard Operating Runbooks Library
│   ├── pages_history.py          # 7. Searchable Incident History & Audit Log
│   ├── pages_assistant.py        # 8. SRE AI Copilot Chat
│   └── pages_analytics.py        # 9. SRE Analytics & MTTR Trends
│
├── data/                         # SQLite database file and local vector indices
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .env
├── seed.py                       # Standalone database and memory seeding utility
├── run.py                        # Single-command launcher for both Backend & Frontend
├── tests/
│   ├── test_sanitizer.py         # Unit tests for Memory Defense
│   ├── test_hindsight.py         # Unit tests for Hindsight Recall and Reflection
│   └── test_analyzer_and_execution.py # Tests for diagnosis and simulated execution
└── README.md
```

---

## 7. Installation & Quickstart

### Prerequisites
- Python 3.10 or higher
- Git

### Step 1: Clone the repository
```bash
git clone https://github.com/your-org/sre-shield.git
cd SRE-Shield
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional)* Add your free Groq API key in `.env`:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```
> **Note:** If no Groq API key is provided, SRE-Shield automatically uses its **Intelligent SRE Heuristic Expert Engine**, so the entire application functions flawlessly offline with zero API keys required!

### Step 4: Launch SRE-Shield (Single Command)
```bash
python run.py
```
This automatically initializes the database, pre-warms Hindsight Agent Memory with 10 realistic historical incidents, starts the FastAPI backend on `http://127.0.0.1:8000`, and opens the Streamlit Dashboard on `http://localhost:8501`.

---

## 8. Step-by-Step 3–5 Minute Hackathon Demo Script

Here is the exact sequence to present to hackathon judges:

1. **Open Executive Dashboard (`http://localhost:8501`):**
   - Highlight the **MTTR Trend Curve** showing how recovery times dropped from 25 minutes down to 4 minutes as historical memory accumulated.
   - Point out the **Hindsight Experience Bank** (8+ pre-loaded production outages across PostgreSQL, Redis, Kubernetes, Kafka, and Ingress).

2. **Trigger the Main Demo Outage (Incident Center):**
   - Navigate to **"Incident Center & AI Diagnosis"**.
   - Click the 1-click scenario button: **"🔥 Checkout API: DB Pool Starvation"**.
   - Notice the raw logs contain a deliberate database password and Bearer token.
   - Click **"⚡ Analyze Incident with SRE-Shield"**.

3. **Showcase Memory Defense & Hindsight Memory Recall:**
   - **Memory Defense Alert:** SRE-Shield instantly flags: *"Safely redacted 2 sensitive token(s) (SECRET, API_KEY) before storing into memory."*
   - **Hindsight Recall Banner:** Identified past incident `INC-1001` with **92% similarity**. Found root cause: *"Database connection pool exhaustion"*.
   - **Side-by-Side Comparison:** 
     - **Stateless AI (Without Memory):** 45% confidence, generic trial-and-error advice ("check logs, restart host").
     - **SRE-Shield (With Hindsight Memory):** 96% confidence, exact diagnosis, recommended runbook `DB-CONNECTION-001`, and precise Kubernetes patch command.

4. **Human-in-the-Loop Approval & Safe Execution:**
   - Click **"👉 Review & Approve Remediation Now"** (routes to Human Approval page).
   - Point out that **autonomous destruction is blocked**; human engineer approval is required.
   - Show the `[SIMULATION MODE]` label and risk rating (`MEDIUM`).
   - Click **"✅ Approve & Execute Command"**.
   - Watch the live execution timeline: Command dispatched -> `/healthz` probe returns 200 OK -> Error rate drops from 48.2% to **0.00%** -> Incident marked **RESOLVED**!

5. **Closing the Learning Loop (Post-Mortem & Retention):**
   - Click **"🚀 Draft Post-Mortem"**.
   - Review the auto-generated post-mortem (Timeline, Root Cause, Lessons Learned).
   - Click **"💾 Approve & Retain into Hindsight Persistent Memory"**.
   - SRE-Shield retains the new experience, triggers **Reflection**, and updates Checkout API's rolling entity profile and domain beliefs.

6. **Verify the Learning (SRE AI Copilot):**
   - Go to **"SRE AI Copilot / Assistant"**.
   - Click: *"What happened the last time Checkout API failed with 500?"*
   - The Copilot answers with exact citations to `INC-1001`, the newly resolved incident, and runbook `DB-CONNECTION-001`!

---

## 9. How Hindsight Agent Memory Works in SRE-Shield

Unlike standard RAG architectures that dump flat document chunks into a vector database, SRE-Shield implements **Hindsight Agent Memory** across **4 distinct cognitive networks**:

1. **World Network (Objective Architecture & Limits):**
   Stores system topology and hard constraints (e.g., *"Checkout API PostgreSQL connection pool maximum is 50 connections across 4 pods"*).
2. **Experience Network (First-Person SRE Trajectories):**
   Stores complete problem-solving trajectories: Alert signature -> Hypotheses -> Commands Tried -> Outcome -> Post-Mortem summary.
3. **Entity Summaries (Synthesized Operational Profiles):**
   Continuous rolling profile per microservice (e.g., *"Checkout API: Prone to DB pool starvation when traffic >15k rps; requires pool size >= 50"*).
4. **Evolving Beliefs (Calibrated Wisdom & Heuristics):**
   Operational invariants learned through trial and error (e.g., *"Belief (96% confidence): Bumping DB pool without a rollout restart leaves dangling sessions; always execute patch and rollout restart together"*).

### Core Memory Operations:
- **`retain()`**: Ingests new incident resolution, runs Memory Defense sanitization, indexes embeddings, and saves to persistent storage.
- **`recall()`**: Executes hybrid semantic cosine vector similarity combined with exact SRE keyword boosting across all 4 networks.
- **`reflect()`**: Triggered after post-mortems to reconcile new outcomes with existing entity profiles and evolve confidence ratings.

---

## 10. Running with Docker Compose

To deploy SRE-Shield in a containerized environment:

```bash
docker-compose up --build
```
- Dashboard: `http://localhost:8501`
- Backend API: `http://localhost:8000`

---

## 11. Running Unit Tests

Run the full automated test suite verifying Memory Defense, Hindsight Memory Recall, Dual Diagnosis, and Safe Execution:

```bash
python -m unittest discover tests
```
---

## 12. Security & Compliance

SRE-Shield includes built-in enterprise compliance:
- **Zero Raw Secrets in Memory:** Passwords, API keys, AWS credentials, Bearer tokens, and credit cards are intercepted and masked.
- **Immutable Audit Trail:** Every alert ingestion, command approval, and memory update is recorded in the `audit_logs` table with actor, timestamp, and action description.
- **Simulation Sandbox:** All production execution is isolated behind a safe simulation layer to prevent accidental outages during triage.

---

## 13. License

Distributed under the Apache 2.0 License.
Built for the Hackathon with ❤️ by the SRE-Shield Team.
