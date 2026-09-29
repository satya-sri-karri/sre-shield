"""
Script to generate the SRE-Shield Word document.
Run from the project root: python generate_doc.py
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def set_cell_bg(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def set_cell_border(cell, border_color="2563EB"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side in ('top', 'left', 'bottom', 'right'):
        border = OxmlElement(f'w:{side}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '6')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), border_color)
        tcBorders.append(border)
    tcPr.append(tcBorders)

def heading(doc, text, level=1, color="1E3A5F"):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor.from_string(color)
        run.font.bold = True
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)
    return h

def body(doc, text, bold=False, italic=False, size=10.5, color="1F2937", space_after=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    p.paragraph_format.space_after = Pt(space_after)
    return p

def bullet(doc, text, bold_prefix=None, size=10.5):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        r1 = p.add_run(bold_prefix + " ")
        r1.font.bold = True
        r1.font.size = Pt(size)
        r1.font.color.rgb = RGBColor.from_string("1F2937")
    r2 = p.add_run(text)
    r2.font.size = Pt(size)
    r2.font.color.rgb = RGBColor.from_string("374151")
    p.paragraph_format.space_after = Pt(3)
    return p

def add_code_block(doc, code_text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(code_text)
    run.font.name = 'Courier New'
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor.from_string("1E40AF")
    # Add shading to paragraph
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'EFF6FF')
    pPr.append(shd)
    return p

def add_info_box(doc, title, content_lines, bg_color="EFF6FF", border_color="2563EB", title_color="1E40AF"):
    """Renders a styled info box using a borderless 1-column table"""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.rows[0].cells[0]
    set_cell_bg(cell, bg_color)
    set_cell_border(cell, border_color)
    cell.add_paragraph()
    p_title = cell.add_paragraph()
    r = p_title.add_run(title)
    r.font.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string(title_color)
    p_title.paragraph_format.space_after = Pt(4)
    for line in content_lines:
        p = cell.add_paragraph()
        run = p.add_run(line)
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor.from_string("1F2937")
        p.paragraph_format.space_after = Pt(2)
    cell.add_paragraph()
    doc.add_paragraph()
    return tbl

def add_flow_step(doc, steps):
    """Renders a horizontal flow diagram as a table"""
    cols = len(steps)
    tbl = doc.add_table(rows=1, cols=cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (label, desc, color) in enumerate(steps):
        cell = tbl.rows[0].cells[i]
        set_cell_bg(cell, color)
        set_cell_border(cell, "94A3B8")
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(label)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        if desc:
            p2 = cell.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r2 = p2.add_run(desc)
            r2.font.size = Pt(7.5)
            r2.font.color.rgb = RGBColor.from_string("E2E8F0")
    doc.add_paragraph()
    return tbl


# ─────────────────────────────────────────────
# Build Document
# ─────────────────────────────────────────────

def build_document():
    doc = Document()

    # Page Margins
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # Normal style base font
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10.5)

    # ══════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph()

    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_run = title_para.add_run("SRE-Shield")
    t_run.font.size = Pt(36)
    t_run.font.bold = True
    t_run.font.color.rgb = RGBColor.from_string("1E3A5F")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s_run = subtitle.add_run("AI-Powered Self-Learning Incident Response Agent")
    s_run.font.size = Pt(18)
    s_run.font.bold = False
    s_run.font.color.rgb = RGBColor.from_string("2563EB")

    doc.add_paragraph()
    tagline = doc.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tl_run = tagline.add_run(
        '"The system learns from every incident and uses previous\n'
        'experience to solve future incidents faster."'
    )
    tl_run.font.size = Pt(12)
    tl_run.font.italic = True
    tl_run.font.color.rgb = RGBColor.from_string("475569")

    doc.add_paragraph()
    doc.add_paragraph()

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    m_run = meta.add_run(
        "Hackathon Project  |  Category: AI / DevOps / SRE\n"
        "Stack: Python 3.10  •  FastAPI  •  Streamlit  •  Groq LLM  •  Hindsight Agent Memory  •  SQLite\n"
        "September 2026"
    )
    m_run.font.size = Pt(10)
    m_run.font.color.rgb = RGBColor.from_string("6B7280")

    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 1 — PROBLEM STATEMENT
    # ══════════════════════════════════════════════
    heading(doc, "1.  Problem Statement", level=1)

    body(doc,
         "Modern software organisations run hundreds of microservices in production. When an outage occurs — "
         "a database crashes, a Kubernetes pod is OOMKilled, an API starts returning HTTP 500 errors — the "
         "on-call Site Reliability Engineer (SRE) is paged and must identify, diagnose, and resolve the "
         "problem before revenue is lost and customers churn.",
         size=10.5)

    heading(doc, "1.1  The Core Challenge", level=2, color="2563EB")
    body(doc,
         "The real cost of a production incident is not just the downtime — it is the repeated cost of "
         "rediscovering the same root causes again and again. Post-mortems are written, shelved, and forgotten. "
         "The next on-call engineer pages in at 2 AM with no memory of the fix that resolved an identical "
         "incident three weeks ago.",
         size=10.5)

    heading(doc, "1.2  Specific Pain Points", level=2, color="2563EB")

    pain_data = [
        ("Tribal Knowledge Vanishes",
         "40–70% of Mean Time to Recovery (MTTR) is spent rediscovering root causes that "
         "were already diagnosed and solved by a different engineer in a previous shift."),
        ("Stateless AI Chatbots Fail in SRE Context",
         "General-purpose LLMs (ChatGPT, Copilot) provide generic textbook advice — "
         '"Check your logs", "Restart the service", "Check the gateway" — with no memory of '
         "the specific cluster topology, connection pool limits, or what command actually resolved "
         "the same failure last Tuesday."),
        ("Secrets Leaking into Vector Databases",
         "Engineers paste raw stack traces containing database passwords, API tokens, and JWTs "
         "directly into LLM prompts and vector databases, creating catastrophic security exposure."),
        ("Destructive Command Automation Risk",
         "Autonomous AI agents that blindly run recommended shell commands risk corrupting "
         "production databases, terminating live namespaces, or triggering cascading failures."),
        ("No Continuous Learning",
         "Traditional on-call workflows do not feed resolution outcomes back into a persistent "
         "memory bank. Every incident starts from zero — the same triage, the same Google searches, "
         "the same escalations."),
    ]

    for title, desc in pain_data:
        bullet(doc, desc, bold_prefix=title + ":")

    doc.add_paragraph()
    add_info_box(doc,
        "The Core Question",
        [
            "How can an AI-powered system behave like a Principal SRE who has personally",
            "resolved every production incident the organisation has ever experienced,",
            "recalls the exact fix that worked, and safely guides the on-call engineer to resolution",
            "in minutes rather than hours — without ever blindly executing destructive commands?",
        ],
        bg_color="EFF6FF", border_color="2563EB", title_color="1E40AF"
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 2 — BUILT SOLUTION
    # ══════════════════════════════════════════════
    heading(doc, "2.  The Built Solution: SRE-Shield", level=1)

    body(doc,
         "SRE-Shield is a closed-loop, self-learning incident response platform that combines "
         "Groq LLM inference, Hindsight Agent Memory (a structured 4-network memory architecture), "
         "a Memory Defense sanitization layer, and a Human-in-the-Loop safety gate into a single "
         "cohesive production-grade SRE tool.")

    body(doc,
         "The fundamental innovation is the separation between a stateless AI (which simply answers "
         "from training data) and a memory-augmented SRE agent (which reasons over verified past "
         "resolutions, calibrated beliefs, and service-specific entity profiles). SRE-Shield "
         "demonstrates this contrast side-by-side on every incident.", italic=True)

    heading(doc, "2.1  Key Features at a Glance", level=2, color="2563EB")

    features = [
        ("Hindsight 4-Network Agent Memory",
         "Persistent structured incident knowledge split into World Facts, Experience Trajectories, "
         "Entity Summaries, and Evolving Beliefs — far richer than flat vector embeddings."),
        ("Memory Defense Sanitization",
         "Automatic detection and masking of passwords, JWTs, Bearer tokens, AWS keys, and PII "
         "before any data is stored in persistent memory."),
        ("Dual Diagnosis Engine",
         "Every incident produces two independent analyses: With Hindsight Memory (96% confidence, "
         "grounded in verified fixes) vs Without Memory (generic, stateless, 45% confidence). "
         "Displayed side-by-side to prove the memory advantage."),
        ("Human-in-the-Loop Safety Gate",
         "No production command is ever executed autonomously. The engineer reviews the risk level, "
         "can modify the command, then clicks Approve. All actions run in SIMULATION MODE with "
         "realistic cluster output."),
        ("Automated Verification",
         "After execution, SRE-Shield automatically probes the service health endpoint, "
         "checks error rate telemetry, and marks the incident RESOLVED only when verified."),
        ("Closed-Loop Post-Mortem & Learning",
         "Auto-generated blameless post-mortems are reviewed, approved, and fed back into "
         "Hindsight memory — completing the learning loop so future incidents benefit immediately."),
        ("SRE AI Copilot",
         "Natural-language chat assistant grounded in incident history, answering questions like "
         "What happened last time Redis timed out? with exact citations."),
        ("SRE Analytics Dashboard",
         "MTTR reduction curves, service reliability heatmaps, runbook success rates, and "
         "severity distribution charts proving organisational learning over time."),
    ]

    for title, desc in features:
        bullet(doc, desc, bold_prefix=title + ":")

    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 3 — TECHNOLOGY STACK
    # ══════════════════════════════════════════════
    heading(doc, "3.  Technology Stack", level=1)

    stack_table = doc.add_table(rows=1, cols=3)
    stack_table.style = 'Table Grid'
    stack_table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Layer", "Technology", "Purpose"]
    hdr_cells = stack_table.rows[0].cells
    for i, h in enumerate(headers):
        set_cell_bg(hdr_cells[i], "1E3A5F")
        p = hdr_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        r.font.size = Pt(10)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    rows_data = [
        ("Backend Framework", "Python 3.10 + FastAPI + Uvicorn", "Async REST API server handling incident ingestion, AI calls, memory operations, and execution endpoints"),
        ("AI Inference", "Groq API (llama-3.3-70b-versatile)", "Ultra-low-latency LLM inference for root cause diagnosis and post-mortem generation; falls back to a local SRE heuristic engine when offline"),
        ("Agent Memory", "Hindsight 4-Network Architecture", "Persistent structured memory: World Network, Experience Network, Entity Summaries, Evolving Beliefs — with Retain, Recall, Reflect operations"),
        ("Vector Search", "scikit-learn TF-IDF + Cosine Similarity + SRE Keyword Boosting", "Hybrid semantic recall combining vector cosine distance with exact SRE error pattern boosting (HTTP 500, OOMKilled, pool exhausted, etc.)"),
        ("Database / ORM", "SQLAlchemy 2.0 + aiosqlite (async SQLite)", "Zero-friction local persistence; pluggable to PostgreSQL + pgvector via DATABASE_URL environment variable"),
        ("Security", "Memory Defense Sanitizer (custom regex engine)", "Detects and masks passwords, Bearer tokens, JWTs, AWS keys, private key blocks, credit cards, and PII before persistence"),
        ("Frontend", "Streamlit 1.32+ with Plotly + Custom Dark CSS", "Professional enterprise SRE dashboard with live telemetry cards, charts, incident timelines, and approval controls"),
        ("Containerisation", "Docker + Docker Compose", "Single docker-compose up --build launches the entire platform"),
    ]

    for row_data in rows_data:
        row = stack_table.add_row()
        for i, val in enumerate(row_data):
            p = row.cells[i].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9.5)
            if i == 0:
                r.font.bold = True
                r.font.color.rgb = RGBColor.from_string("1E3A5F")

    doc.add_paragraph()
    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 4 — HINDSIGHT AGENT MEMORY ARCHITECTURE
    # ══════════════════════════════════════════════
    heading(doc, "4.  Hindsight Agent Memory Architecture", level=1)

    body(doc,
         "The most important differentiator of SRE-Shield is its memory layer. Unlike standard "
         "RAG architectures that store flat text chunks in a vector database, SRE-Shield implements "
         "the Hindsight Agent Memory model — organising knowledge into four distinct cognitive "
         "networks that mirror how a seasoned SRE actually thinks and reasons.")

    heading(doc, "4.1  Why Hindsight Is Different from Standard RAG", level=2, color="2563EB")

    comparison_tbl = doc.add_table(rows=1, cols=3)
    comparison_tbl.style = 'Table Grid'
    comparison_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    comp_headers = ["Capability", "Standard RAG System", "Hindsight Agent Memory (SRE-Shield)"]
    ch_cells = comparison_tbl.rows[0].cells
    bg_colors = ["1E3A5F", "7F1D1D", "064E3B"]
    for i, (h, bg) in enumerate(zip(comp_headers, bg_colors)):
        set_cell_bg(ch_cells[i], bg)
        p = ch_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor.from_string("FFFFFF")

    comp_data = [
        ("Memory Structure", "Flat chunks of text in a vector index", "4 specialised cognitive networks with typed, structured records"),
        ("Recall Quality", "Cosine similarity on raw text", "Hybrid: vector similarity + SRE keyword boosting + service-name weighting"),
        ("Self-Learning", "Static; requires manual re-indexing", "Closed-loop: every approved post-mortem automatically teaches the system"),
        ("Entity Profiles", "Not supported", "Rolling synthesized profile per microservice with failure modes and MTTR"),
        ("Calibrated Beliefs", "Not supported", "Confidence-rated operational invariants that grow stronger with each incident"),
        ("Secret Safety", "Secrets embedded in raw chunks", "Memory Defense sanitization before any data enters storage"),
        ("Recall Transparency", "Black-box similarity score", "Explicit citation: Incident ID, root cause, runbook, outcome, recall count"),
    ]

    for row_data in comp_data:
        row = comparison_tbl.add_row()
        for i, val in enumerate(row_data):
            p = row.cells[i].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9)
            if i == 0:
                r.font.bold = True
                r.font.color.rgb = RGBColor.from_string("1E3A5F")
            elif i == 1:
                r.font.color.rgb = RGBColor.from_string("7F1D1D")
            else:
                r.font.color.rgb = RGBColor.from_string("064E3B")

    doc.add_paragraph()

    heading(doc, "4.2  The 4 Hindsight Networks", level=2, color="2563EB")

    networks = [
        ("Network 1 — World Network (Objective Architecture & Constraints)",
         "Stores immutable facts about system topology, operational limits, and SLAs that never change between incidents.",
         [
             "Checkout API PostgreSQL connection pool maximum: 50 connections across 4 pods",
             "Checkout API 99.9% availability SLO: error rate must stay below 0.1% over a 30-day window",
             "Payment Gateway communicates with Stripe via mTLS over egress NAT gateway",
             "User Auth Service depends strictly on Redis Cluster for OAuth2 token validation",
         ],
         "E0F2FE", "0284C7"),

        ("Network 2 — Experience Network (First-Person SRE Action History)",
         "Stores complete incident resolution trajectories — the core memory bank. Each record captures the full problem-solving arc.",
         [
             "Error Signature: the exact alert text or exception that fired",
             "Root Cause: the confirmed failure mode",
             "Resolution Strategy: the approved remediation plan",
             "Successful Commands: the specific CLI commands that worked",
             "Runbook Code: the standard operating procedure applied",
             "Outcome: SUCCESS or FAILED",
             "Post-Mortem Summary: the distilled lessons",
             "Recall Count: how many times this memory has been retrieved",
         ],
         "F0FDF4", "16A34A"),

        ("Network 3 — Entity Summaries (Rolling Service Profiles)",
         "A continuous synthesis of each microservice's incident history — updated automatically via Reflection after every post-mortem approval.",
         [
             "Checkout API: Prone to database connection pool starvation when traffic > 15,000 rps. Requires pool size >= 50 and a rollout restart after patching. 3 incidents, avg MTTR 12 minutes.",
             "Inventory Service: JVM heap OOMKilled by unpaginated bulk queries during warehouse sync. Memory limit must maintain 30% headroom. 2 incidents, avg MTTR 8 minutes.",
             "Redis Cache: OOM lockup triggered by noeviction policy. Must maintain allkeys-lru and 8 GB maxmemory. 1 incident, avg MTTR 6 minutes.",
         ],
         "FFFBEB", "D97706"),

        ("Network 4 — Evolving Beliefs (Calibrated Wisdom & Heuristics)",
         "High-level operational invariants that the system develops over time — analogous to the mental models a 10-year SRE accumulates from repeated firefighting.",
         [
             'Domain: Database | Confidence 96% | "When Checkout API reports connection pool exhausted, patching the ConfigMap without a rollout restart leaves dangling sessions — always execute patch and rollout restart together."',
             'Domain: Kubernetes | Confidence 94% | "Container Exit Code 137 is invariably OOMKilled. Bumping memory limit by 2.5x immediately stops CrashLoopBackOff before deep heap analysis is needed."',
             'Domain: Deployments | Confidence 98% | "Startup crashes within 5 minutes of a CI/CD deploy indicate a missing environment secret — fast rollback has 100% MTTR superiority over live debugging."',
         ],
         "F5F3FF", "7C3AED"),
    ]

    for net_title, net_desc, net_bullets, bg, border in networks:
        heading(doc, net_title, level=3, color="374151")
        body(doc, net_desc, size=10)
        add_info_box(doc, "Examples stored in this network:", net_bullets, bg_color=bg, border_color=border, title_color="1F2937")

    heading(doc, "4.3  The 3 Core Memory Operations", level=2, color="2563EB")

    ops = [
        ("retain()",
         "Triggered after every resolved incident and approved post-mortem. Runs the Memory Defense "
         "sanitization pass first (masking secrets), then stores the experience into the Experience "
         "Network, updates the embedding index, and writes an audit log entry. Optionally syncs to "
         "the remote Hindsight cloud API if an API key is configured.",
         "Returns: experience_id, sanitization_report, reflection result, remote_synced flag"),
        ("recall()",
         "Triggered on every new incoming alert. Executes a hybrid search across the Experience "
         "Network using TF-IDF cosine similarity combined with SRE keyword boosting (HTTP 500, "
         "connection pool, OOMKilled, etc.) and service-name weighting. Simultaneously retrieves "
         "the Entity Summary, Evolving Beliefs, and World Facts for the affected service.",
         "Returns: match_count, similarity_pct per match, top_match, entity_summary, beliefs, world_facts"),
        ("reflect()",
         "Triggered after every post-mortem approval. Scans all experiences for the affected "
         "service and synthesises an updated Entity Summary (failure modes, preferred runbooks, "
         "MTTR statistics). Also checks for recurring patterns and strengthens the confidence "
         "score of relevant Evolving Beliefs.",
         "Returns: updated entity profile, updated belief confidence scores"),
    ]

    for op_name, op_desc, op_return in ops:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.2)
        r1 = p.add_run(op_name + "  ")
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = RGBColor.from_string("1E40AF")
        r1.font.name = "Courier New"
        p2 = doc.add_paragraph()
        p2.paragraph_format.left_indent = Inches(0.4)
        r2 = p2.add_run(op_desc)
        r2.font.size = Pt(10)
        r2.font.color.rgb = RGBColor.from_string("1F2937")
        p3 = doc.add_paragraph()
        p3.paragraph_format.left_indent = Inches(0.4)
        r3 = p3.add_run(op_return)
        r3.font.size = Pt(9.5)
        r3.font.italic = True
        r3.font.color.rgb = RGBColor.from_string("4B5563")
        p3.paragraph_format.space_after = Pt(10)

    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 5 — SYSTEM ARCHITECTURE
    # ══════════════════════════════════════════════
    heading(doc, "5.  System Architecture", level=1)

    heading(doc, "5.1  High-Level Component Map", level=2, color="2563EB")

    body(doc,
         "SRE-Shield is structured as a clean, layered architecture with clear separation of "
         "concerns between the Ingestion layer, Security layer, AI Reasoning layer, "
         "Memory layer, Execution layer, and Presentation layer.")

    # Architecture Table
    arch_tbl = doc.add_table(rows=1, cols=2)
    arch_tbl.style = 'Table Grid'
    arch_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    arch_headers = ["Layer", "Components & Responsibilities"]
    arch_hdr_cells = arch_tbl.rows[0].cells
    for i, h in enumerate(arch_headers):
        set_cell_bg(arch_hdr_cells[i], "1E3A5F")
        p = arch_hdr_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        r.font.size = Pt(10)

    arch_rows = [
        ("Alert Ingestion Layer", "FastAPI REST endpoint (/api/incidents) receives alerts from monitoring systems or manual entry. Normalises and timestamps the alert payload."),
        ("Memory Defense Layer", "Regex-based sanitizer scans error messages, logs, and deployment info for passwords, API keys, JWTs, AWS credentials, private keys, and PII. Replaces with [REDACTED_*] tokens before any downstream processing."),
        ("Hindsight Memory Layer (recall)", "Executes hybrid search across the 4-network memory bank. Returns ranked similar past experiences, the entity profile, relevant beliefs, and architecture facts for the affected service."),
        ("AI Reasoning Layer", "Groq LLM (llama-3.3-70b-versatile) receives the sanitized alert plus the full Hindsight memory context and generates a structured JSON diagnosis: root cause, confidence score, reasoning explanation, recommended runbook, suggested command, and risk level. A resilient local SRE Heuristic Engine provides identical output when offline."),
        ("Dual Diagnosis Engine", "Simultaneously generates a second stateless diagnosis (no memory context) to produce the side-by-side with/without memory comparison shown in the dashboard."),
        ("Runbook Recommendation Engine", "Maps AI diagnosis to the closest matching Standard Operating Procedure from the runbook catalog. Enriches recommendation with investigation steps, resolution steps, CLI commands, and historical success rates."),
        ("Human-in-the-Loop Gate", "Engineer reviews: risk level (LOW / MEDIUM / HIGH), AI reasoning explanation, proposed CLI command (editable), and runbook reference. Must explicitly click Approve, Modify, or Reject. No command executes without approval."),
        ("Safe Execution Engine", "Runs approved command in SIMULATION MODE, generating realistic cluster output (kubectl rollout status, Redis CONFIG SET responses, AWS volume resize). Logs the approved action to the immutable audit trail."),
        ("Automated Verification Engine", "After execution, probes the service /healthz endpoint, checks error rate telemetry, and evaluates whether PASS or FAIL criteria are met. Updates incident status to RESOLVED or returns to INVESTIGATING."),
        ("Post-Mortem Agent", "Generates a structured blameless post-mortem from incident data using Groq LLM. Engineer reviews and edits the draft. On approval, calls hindsight.retain() to persist the new resolution into the Experience Network."),
        ("Hindsight Reflect Trigger", "Post-mortem approval triggers hindsight.reflect() which synthesises the new experience into updated Entity Summaries and reinforces relevant Evolving Beliefs — completing the learning loop."),
        ("Streamlit Frontend", "Professional dark-themed enterprise SRE dashboard rendering all 9 pages: Executive Dashboard, Incident Center, Human Approval, Post-Mortem, Hindsight Memory Inspector, Runbook Catalog, Incident History, SRE Copilot, and Analytics."),
    ]

    for row_data in arch_rows:
        row = arch_tbl.add_row()
        for i, val in enumerate(row_data):
            p = row.cells[i].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9.5)
            if i == 0:
                r.font.bold = True
                r.font.color.rgb = RGBColor.from_string("1E3A5F")

    doc.add_paragraph()
    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 6 — END-TO-END SYSTEM FLOW
    # ══════════════════════════════════════════════
    heading(doc, "6.  End-to-End Incident Resolution Flow", level=1)

    body(doc,
         "The following describes the complete lifecycle of a production incident through SRE-Shield "
         "from the moment an alert fires to the moment the learning is stored for future incidents.")

    flow_steps = [
        ("Step 1\nAlert Ingestion", "POST /api/incidents", "1E3A5F"),
        ("Step 2\nMemory Defense", "Secrets Redacted", "7C2D12"),
        ("Step 3\nHindsight Recall", "4-Network Query", "064E3B"),
        ("Step 4\nAI Diagnosis", "Groq LLM + Heuristic", "1E40AF"),
        ("Step 5\nRunbook Match", "Ranked by history", "4338CA"),
        ("Step 6\nHuman Approval", "Review & Authorize", "92400E"),
        ("Step 7\nSafe Execution", "SIMULATION MODE", "134E4A"),
        ("Step 8\nVerification", "Health Probe", "1A2E05"),
        ("Step 9\nPost-Mortem", "AI Draft", "3B0764"),
        ("Step 10\nRetain & Reflect", "Hindsight Update", "1C1917"),
    ]
    add_flow_step(doc, flow_steps)

    # Detailed Step-by-Step Descriptions
    steps_detail = [
        ("Step 1: Alert Ingestion",
         "A production monitoring system (PagerDuty, Prometheus AlertManager, or manual entry) "
         "sends an HTTP POST request to /api/incidents containing: service name, severity, "
         "error message, raw log lines, and recent deployment information. FastAPI validates the "
         "payload via Pydantic models and assigns a unique incident ID (e.g. INC-A3F7B1)."),

        ("Step 2: Memory Defense Sanitization",
         "Before any data is processed, the Memory Defense Sanitizer scans all text fields for:\n"
         "  •  Passwords and secrets in key=value format (password=..., api_secret=...)\n"
         "  •  Bearer tokens and JWT strings\n"
         "  •  Groq, OpenAI, and GitHub API key prefixes (gsk_..., sk-..., ghp_...)\n"
         "  •  AWS Access Key IDs (AKIA...)\n"
         "  •  PEM private key blocks\n"
         "  •  Database connection strings with embedded credentials\n"
         "  •  Email addresses (PII)\n"
         "All matches are replaced with [REDACTED_SECRET], [REDACTED_JWT_TOKEN], etc. "
         "A sanitization report is returned and displayed in the dashboard. The engineer is "
         "informed exactly how many sensitive tokens were intercepted."),

        ("Step 3: Hindsight Memory Recall",
         "The sanitized alert triggers hindsight.recall() across all 4 networks:\n"
         "  •  Experience Network: Hybrid TF-IDF vector similarity + SRE keyword boost retrieves "
         "the top 3 most similar past incidents, ranked by similarity score.\n"
         "  •  Entity Summary: The rolling profile for the affected service is retrieved "
         "(known failure modes, preferred runbooks, average MTTR).\n"
         "  •  Evolving Beliefs: The top confidence-rated operational beliefs are retrieved.\n"
         "  •  World Network: Architecture constraints for the service are retrieved.\n"
         "Recall counts are incremented on matching experiences, providing usage analytics."),

        ("Step 4: Dual AI Diagnosis",
         "Two independent diagnoses are generated in parallel:\n\n"
         "  Memory-Augmented Diagnosis (With Hindsight):\n"
         "  The Groq LLM receives the sanitized alert plus the full Hindsight context (top matches, "
         "entity profile, beliefs, world facts). The model is prompted as a Principal SRE with "
         "long-term memory and produces a structured JSON diagnosis with confidence score, "
         "root cause, recommended runbook, CLI command, and risk rating.\n\n"
         "  Stateless Baseline Diagnosis (Without Memory):\n"
         "  The same alert is sent to a separate prompt with no context — simulating a generic "
         "AI chatbot. The model produces a low-confidence generic response. Both outputs are "
         "displayed side-by-side in the dashboard to demonstrate the memory advantage.\n\n"
         "  Resilient Fallback:\n"
         "  If the Groq API is unavailable, an intelligent SRE Heuristic Engine provides "
         "equivalent structured output based on pattern matching — ensuring 100% uptime."),

        ("Step 5: Runbook Recommendation",
         "The AI diagnosis includes a recommended_runbook_id (e.g. DB-CONNECTION-001). "
         "SRE-Shield retrieves the full runbook from the catalog including investigation "
         "steps, resolution procedures, CLI command snippets with risk ratings, and "
         "historical success/failure statistics. The recommendation is displayed alongside "
         "the reasoning explanation from Hindsight memory."),

        ("Step 6: Human-in-the-Loop Approval",
         "The engineer reviews:\n"
         "  •  The diagnosed root cause and confidence score\n"
         "  •  The referenced historical incident(s) that grounded the diagnosis\n"
         "  •  The proposed CLI command (fully editable in a text area)\n"
         "  •  The risk level badge (LOW / MEDIUM / HIGH)\n"
         "  •  The reasoning explanation from Hindsight Recall\n\n"
         "The engineer then chooses:\n"
         "  •  Approve & Execute — runs the command exactly as proposed\n"
         "  •  Modify & Execute — runs the edited command\n"
         "  •  Reject — marks the action rejected and keeps the incident in INVESTIGATING state\n\n"
         "The approval event, engineer name, and timestamp are recorded in the immutable audit log."),

        ("Step 7: Safe Execution in SIMULATION MODE",
         "The approved command is passed to the SafeExecutionEngine. SRE-Shield does NOT "
         "connect to a real Kubernetes cluster during the hackathon demo. Instead, the engine "
         "pattern-matches the command type and generates realistic, authentic-looking execution "
         "output:\n"
         "  •  kubectl rollout restart → pod rolling update progress with replica counts\n"
         "  •  kubectl scale → deployment scaling confirmation\n"
         "  •  redis-cli CONFIG SET → Redis OK responses with memory stats\n"
         "  •  kubectl rollout undo → rollback success confirmation\n"
         "All output is labelled [SIMULATION MODE] to maintain clear transparency. "
         "The execution result and engineer approval are permanently stored in the audit trail."),

        ("Step 8: Automated Verification",
         "After execution, SRE-Shield runs automated verification checks:\n"
         "  •  Health Probe: Simulates GET /healthz → checks for 200 OK response\n"
         "  •  Telemetry Check: Verifies error rate has dropped below SLO threshold (0.1%)\n"
         "  •  Metric Validation: Confirms resource utilisation is within healthy bounds\n\n"
         "If all checks pass, the incident is marked VERIFIED / RESOLVED and the MTTR "
         "is calculated. The runbook's success_count is incremented. If checks fail, "
         "the incident remains INVESTIGATING for further triage."),

        ("Step 9: Automated Post-Mortem Generation",
         "The PostMortemAgent generates a structured blameless post-mortem from the incident "
         "record using the Groq LLM. The draft includes:\n"
         "  •  Executive Summary\n"
         "  •  Customer & Business Impact\n"
         "  •  Chronological Timeline of Events\n"
         "  •  Confirmed Root Cause\n"
         "  •  Resolution Steps Taken\n"
         "  •  Commands Used\n"
         "  •  What Worked Well\n"
         "  •  What Failed or Was Delayed\n"
         "  •  Prevention Strategies\n"
         "  •  Recommended Monitoring & Alerting Improvements\n"
         "  •  Key Lessons Learned\n\n"
         "The engineer reviews and edits the post-mortem in the dashboard. The Approve button "
         "is the gateway to the learning loop."),

        ("Step 10: Hindsight Retain & Reflect (Learning Loop Closes)",
         "On post-mortem approval, SRE-Shield executes the full learning closure:\n\n"
         "  retain():\n"
         "  The sanitized incident data and post-mortem are stored as a new MemoryExperience "
         "record. The TF-IDF index is rebuilt to include the new corpus. An audit entry is "
         "written with the experience ID and sanitization report.\n\n"
         "  reflect():\n"
         "  The system re-analyses all experiences for the affected service and produces an "
         "updated Entity Summary with refreshed failure mode lists, preferred runbooks, and "
         "MTTR statistics. If a recurring pattern is detected (e.g. connection pool exhaustion "
         "appearing for the 3rd time), the confidence score of the related Evolving Belief is "
         "raised by 5 percentage points.\n\n"
         "  Impact:\n"
         "  The next time any incident with a similar signature arrives — even from a different "
         "service or a new engineer — SRE-Shield will immediately recall this resolution with "
         "high confidence and recommend the exact command that was verified to work."),
    ]

    for step_title, step_body in steps_detail:
        heading(doc, step_title, level=2, color="1E3A5F")
        body(doc, step_body, size=10)

    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 7 — PROJECT STRUCTURE
    # ══════════════════════════════════════════════
    heading(doc, "7.  Project Structure", level=1)

    structure = """sre-shield/
├── backend/
│   ├── config.py                 Settings, env vars, DB URL, Groq model, ports
│   ├── api/
│   │   ├── main.py               FastAPI app with lifespan startup (DB init, seed, memory warm)
│   │   └── routes.py             REST endpoints for incidents, memory, runbooks, execution, chat
│   ├── memory/
│   │   ├── base.py               Abstract BaseMemoryEngine interface
│   │   ├── hindsight_engine.py   Hindsight 4-Network impl + retain/recall/reflect
│   │   └── embeddings.py         Hybrid TF-IDF + SRE keyword search engine
│   ├── security/
│   │   └── sanitizer.py          Memory Defense regex redaction engine
│   ├── agents/
│   │   ├── groq_client.py        Groq API client with heuristic fallback
│   │   ├── analyzer.py           Dual incident analyzer (with/without memory)
│   │   ├── postmortem_agent.py   Post-mortem generator and memory closer
│   │   └── assistant.py          SRE AI Copilot grounded in Hindsight memory
│   ├── execution/
│   │   └── executor.py           Safe simulated execution + automated verification
│   ├── runbooks/
│   │   └── runbook_manager.py    5 standard SRE runbooks with steps and CLI commands
│   └── database/
│       ├── connection.py         Async (FastAPI) and sync (Streamlit) DB sessions
│       ├── models.py             8 SQLAlchemy models (Incident, Runbook, PostMortem,
│       │                         MemoryExperience, EntitySummary, EvolvingBelief,
│       │                         WorldFact, AuditLog)
│       └── seed_data.py          10 realistic historical SRE incidents + Hindsight pre-load
├── frontend/
│   ├── app.py                    Streamlit entrypoint, dark theme, sidebar router
│   ├── components.py             CSS theme, KPI cards, severity badges, timeline widgets
│   ├── pages_dashboard.py        Executive dashboard: KPIs, MTTR chart, service breakdown
│   ├── pages_incident_center.py  Incident ingestion, 1-click scenarios, dual diagnosis view
│   ├── pages_approval.py         Human-in-the-loop approval and safe execution timeline
│   ├── pages_postmortem.py       Post-mortem editor and learning loop retention
│   ├── pages_hindsight.py        4-network memory inspector + live recall sandbox
│   ├── pages_runbooks.py         Runbook catalog with steps, commands, success rates
│   ├── pages_history.py          Searchable incident history with post-mortem drilldown
│   ├── pages_assistant.py        SRE AI Copilot chat with memory citations
│   └── pages_analytics.py        MTTR trends, root cause frequency, severity distribution
├── data/
│   └── sre_shield.db             Auto-seeded SQLite database (10 incidents, 5 runbooks)
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── seed.py                       Standalone DB + memory seeding utility
├── run.py                        One-command launcher: Backend + Frontend
└── tests/
    ├── test_sanitizer.py         Unit tests: Memory Defense (4 test cases)
    ├── test_hindsight.py         Unit tests: Recall and Reflect operations
    └── test_analyzer_and_execution.py  Unit tests: Dual diagnosis and safe execution"""

    add_code_block(doc, structure)
    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 8 — DEMO DATA & SCENARIO
    # ══════════════════════════════════════════════
    heading(doc, "8.  Pre-loaded Demo Data & Hackathon Scenario", level=1)

    body(doc,
         "SRE-Shield is pre-seeded with 10 realistic production incidents so the hackathon "
         "demo can begin immediately without any manual data entry. Each incident includes "
         "full logs, root cause, CLI commands, verification output, post-mortem, and Hindsight "
         "memory records.")

    heading(doc, "8.1  Pre-loaded Incidents", level=2, color="2563EB")

    incidents_data = [
        ("INC-1001", "Checkout API", "CRITICAL",
         "PostgreSQL connection pool exhausted under flash sale traffic",
         "Increase pool size to 50 in ConfigMap + rollout restart",
         "DB-CONNECTION-001", "12m"),
        ("INC-1002", "Inventory Service", "HIGH",
         "JVM heap OOMKilled — unpaginated catalog sync query",
         "kubectl set resources --limits=memory=2560Mi",
         "K8S-POD-OOM-002", "8m"),
        ("INC-1003", "Redis Cache", "HIGH",
         "maxmemory-policy=noeviction blocked all writes on memory cap",
         "redis-cli CONFIG SET maxmemory-policy allkeys-lru + 8gb",
         "REDIS-TIMEOUT-003", "6m"),
        ("INC-1004", "User Auth Service", "HIGH",
         "3-pod replica insufficient for end-of-month login surge — 503",
         "kubectl scale deployment --replicas=8",
         "HTTP-503-INGRESS-004", "5m"),
        ("INC-1005", "Payment Gateway", "CRITICAL",
         "Missing STRIPE_WEBHOOK_SECRET caused 100% pod CrashLoopBackOff",
         "kubectl rollout undo deployment/payment-gateway",
         "DEPLOY-ROLLBACK-005", "4m"),
        ("INC-1006", "Order Processing", "HIGH",
         "Kafka consumer rebalance storm — max.poll.interval exceeded",
         "Patch KAFKA_MAX_POLL_INTERVAL_MS=900000 + restart",
         "DB-CONNECTION-001", "10m"),
        ("INC-1007", "Database Cluster", "CRITICAL",
         "WAL log disk exhaustion — S3 archive IAM role expired",
         "AWS EBS volume resize + pg_archivecleanup",
         "DB-CONNECTION-001", "15m"),
        ("INC-1008", "API Gateway", "CRITICAL",
         "TLS certificate expired — cert-manager DNS challenge failed",
         "kubectl cert-manager renew api-tls-cert",
         "DEPLOY-ROLLBACK-005", "6m"),
    ]

    inc_tbl = doc.add_table(rows=1, cols=7)
    inc_tbl.style = 'Table Grid'
    inc_headers = ["Incident ID", "Service", "Sev", "Root Cause", "Resolution", "Runbook", "MTTR"]
    inc_hdr_cells = inc_tbl.rows[0].cells
    for i, h in enumerate(inc_headers):
        set_cell_bg(inc_hdr_cells[i], "1E3A5F")
        p = inc_hdr_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        r.font.size = Pt(8.5)

    for row_data in incidents_data:
        row = inc_tbl.add_row()
        for i, val in enumerate(row_data):
            p = row.cells[i].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if i == 2:  # Severity column
                if val == "CRITICAL":
                    r.font.color.rgb = RGBColor.from_string("B91C1C")
                    r.font.bold = True
                elif val == "HIGH":
                    r.font.color.rgb = RGBColor.from_string("D97706")
                    r.font.bold = True

    doc.add_paragraph()

    heading(doc, "8.2  The Core Hackathon Demo Scenario", level=2, color="2563EB")

    body(doc,
         "The primary demonstration uses INC-1001 as the historical anchor. The engineer then "
         "triggers a new incident with the same root cause pattern:", bold=False)

    add_info_box(doc,
        "Historical Incident (Pre-loaded in Memory — INC-1001)",
        [
            "Service: Checkout API",
            "Error: HTTP 500 — PostgreSQL FATAL: remaining connection slots are reserved",
            "Root Cause: Connection pool exhausted (20 connections, 4 pods) under flash sale traffic",
            "Resolution: Patched ConfigMap DB_POOL_MAX=50, rolling restart applied",
            "Outcome: VERIFIED — error rate dropped from 48.2% to 0.00%. MTTR: 12 minutes.",
        ],
        bg_color="F0FDF4", border_color="16A34A", title_color="064E3B"
    )

    add_info_box(doc,
        "New Demo Incident (Triggered via 1-Click Scenario Button)",
        [
            "Service: Checkout API",
            "Error: HTTP 500 — org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved",
            "Logs: [FATAL] Connection pool exhausted! Max pool size 20 reached. (contains simulated password + API key)",
            "Deployment Info: Traffic surged to 24,000 rps after holiday coupon push notification.",
        ],
        bg_color="EFF6FF", border_color="2563EB", title_color="1E40AF"
    )

    body(doc,
         "What happens next demonstrates the core SRE-Shield value proposition:",
         bold=True)

    memory_demo_steps = [
        "Memory Defense sanitizes password=prodSecretPassword123 and the Groq API key from logs before storage.",
        "Hindsight Recall identifies INC-1001 with 92% similarity. Root cause, verified command, and runbook are surfaced instantly.",
        "AI Diagnosis generates a 96% confidence answer citing the historical incident — compared to the stateless AI producing a 45% confidence generic guess.",
        "Engineer reviews and approves the recommended kubectl patch command.",
        "Safe execution runs in SIMULATION MODE. Health probe returns 200 OK. Error rate drops to 0.00%.",
        "Post-mortem is generated, approved, and retained. Hindsight memory is updated. The learning loop closes.",
    ]

    for step in memory_demo_steps:
        bullet(doc, step)

    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 9 — SECURITY
    # ══════════════════════════════════════════════
    heading(doc, "9.  Security: Memory Defense Layer", level=1)

    body(doc,
         "SRE-Shield includes a production-grade secret interception layer that operates "
         "on every data ingestion path before any information reaches the LLM, the vector "
         "index, or the persistent database.")

    security_table = doc.add_table(rows=1, cols=3)
    security_table.style = 'Table Grid'
    sec_headers = ["Threat", "Detection Pattern", "Replacement"]
    sec_hdr_cells = security_table.rows[0].cells
    for i, h in enumerate(sec_headers):
        set_cell_bg(sec_hdr_cells[i], "7F1D1D")
        p = sec_hdr_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        r.font.size = Pt(9.5)

    sec_data = [
        ("Passwords in key=value", "password=..., passwd=..., db_pass=...", "[REDACTED_SECRET]"),
        ("Basic Auth URLs", "http://user:password@host", "http://user:[REDACTED_AUTH]@host"),
        ("Bearer Tokens", "Bearer [token string 15+ chars]", "Bearer [REDACTED_BEARER_TOKEN]"),
        ("JWT Strings", "eyJ[...].eyJ[...].sig pattern", "[REDACTED_JWT_TOKEN]"),
        ("Groq / OpenAI API Keys", "gsk_..., sk-... prefixes", "[REDACTED_API_KEY]"),
        ("AWS Access Key IDs", "AKIA[A-Z0-9]{16}", "[REDACTED_AWS_KEY_ID]"),
        ("PEM Private Keys", "-----BEGIN PRIVATE KEY----- block", "[REDACTED_PRIVATE_KEY_BLOCK]"),
        ("Credit Card Numbers", "16-digit card number pattern", "[REDACTED_CREDIT_CARD]"),
        ("Email Addresses (PII)", "user@domain.com format", "[REDACTED_EMAIL]"),
        ("DB Connection Strings", "postgres://user:pass@host", "postgres://user:[REDACTED_PASSWORD]@host"),
    ]

    for row_data in sec_data:
        row = security_table.add_row()
        for i, val in enumerate(row_data):
            p = row.cells[i].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9)
            if i == 0:
                r.font.bold = True
            if i == 2:
                r.font.color.rgb = RGBColor.from_string("065F46")
                r.font.name = "Courier New"

    doc.add_paragraph()

    body(doc,
         "Additionally, every action — incident ingestion, AI diagnosis, human approval, "
         "command execution, post-mortem approval, and memory retention — is written to an "
         "immutable audit log with actor identity, timestamp, and action details.", italic=True)

    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 10 — HOW TO RUN
    # ══════════════════════════════════════════════
    heading(doc, "10.  How to Run the Application", level=1)

    heading(doc, "10.1  Prerequisites", level=2, color="2563EB")
    bullet(doc, "Python 3.10 or higher")
    bullet(doc, "pip (included with Python)")
    bullet(doc, "Internet access for pip install (offline packages can be bundled separately)")

    heading(doc, "10.2  Installation", level=2, color="2563EB")
    body(doc, "Step 1 — Install dependencies:", bold=True)
    add_code_block(doc, "pip install -r requirements.txt")

    body(doc, "Step 2 — Configure environment variables:", bold=True)
    body(doc, "Copy .env.example to .env. Only GROQ_API_KEY is optional. The app works fully offline without it.")
    add_code_block(doc,
        "GROQ_API_KEY=               # Optional: Groq cloud inference (fallback heuristic engine runs offline)\n"
        "GROQ_MODEL=llama-3.3-70b-versatile\n"
        "DATABASE_URL=sqlite+aiosqlite:///./data/sre_shield.db\n"
        "HINDSIGHT_API_KEY=          # Optional: remote Hindsight cloud sync (local 4-network memory works without it)\n"
        "SIMULATION_MODE=true        # Ensures no real cluster commands are executed"
    )

    body(doc, "Step 3 — Launch (single command):", bold=True)
    add_code_block(doc, "python run.py")

    body(doc,
         "This command automatically initialises the database, seeds 10 historical incidents and 5 runbooks, "
         "pre-warms the Hindsight memory index, launches the FastAPI backend on port 8000, and "
         "opens the Streamlit dashboard on port 8501.")

    heading(doc, "10.3  Access URLs", level=2, color="2563EB")
    url_tbl = doc.add_table(rows=1, cols=2)
    url_tbl.style = 'Table Grid'
    url_headers = ["Service", "URL"]
    url_hdr_cells = url_tbl.rows[0].cells
    for i, h in enumerate(url_headers):
        set_cell_bg(url_hdr_cells[i], "1E3A5F")
        p = url_hdr_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string("FFFFFF")

    url_data = [
        ("SRE-Shield Dashboard (Frontend)", "http://localhost:8501"),
        ("FastAPI REST API", "http://127.0.0.1:8000"),
        ("Interactive API Documentation", "http://127.0.0.1:8000/docs"),
        ("Health Check Endpoint", "http://127.0.0.1:8000/api/health"),
    ]
    for row_data in url_data:
        row = url_tbl.add_row()
        for i, val in enumerate(row_data):
            p = row.cells[i].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(10)
            if i == 1:
                r.font.name = "Courier New"
                r.font.color.rgb = RGBColor.from_string("1E40AF")

    doc.add_paragraph()
    doc.add_page_break()

    # ══════════════════════════════════════════════
    # SECTION 11 — DIFFERENTIATORS
    # ══════════════════════════════════════════════
    heading(doc, "11.  Key Differentiators", level=1)

    body(doc,
         "The following table summarises why SRE-Shield is fundamentally different from "
         "every other AI-powered DevOps tool built on standard LLM or RAG architectures.")

    diff_tbl = doc.add_table(rows=1, cols=4)
    diff_tbl.style = 'Table Grid'
    diff_headers = ["Dimension", "Generic Chatbot", "Standard RAG", "SRE-Shield (Hindsight)"]
    diff_hdr_cells = diff_tbl.rows[0].cells
    diff_bg = ["1E3A5F", "7F1D1D", "7F1D1D", "064E3B"]
    for i, (h, bg) in enumerate(zip(diff_headers, diff_bg)):
        set_cell_bg(diff_hdr_cells[i], bg)
        p = diff_hdr_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        r.font.size = Pt(9)

    diff_rows = [
        ("Root Cause Accuracy", "40% – Hallucination-prone", "60% – Uncertain relevance", "94–98% – Grounded in verified outcomes"),
        ("Memory Model", "None – stateless per session", "Flat vector chunks – static", "4 structured cognitive networks – live"),
        ("Self-Learning", "Zero – no retention", "Manual re-indexing required", "Closed-loop on every resolved incident"),
        ("Secret Protection", "Raw secrets sent to LLM API", "Secrets embedded in vector store", "Memory Defense sanitization before retention"),
        ("Production Safety", "No guardrails", "No execution layer", "Human-in-the-loop approval + SIMULATION MODE"),
        ("Service Knowledge", "No topology awareness", "Generic documentation retrieval", "Rolling entity profiles with failure mode library"),
        ("Transparency", "Opaque similarity score", "Ranked chunks – no audit trail", "Cited incident IDs, recall count, confidence score"),
    ]

    for row_data in diff_rows:
        row = diff_tbl.add_row()
        for i, val in enumerate(row_data):
            p = row.cells[i].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9)
            if i == 0:
                r.font.bold = True
            if i in (1, 2):
                r.font.color.rgb = RGBColor.from_string("7F1D1D")
            if i == 3:
                r.font.color.rgb = RGBColor.from_string("064E3B")
                r.font.bold = True

    doc.add_paragraph()

    # ══════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════
    doc.add_page_break()
    heading(doc, "12.  Summary", level=1)

    body(doc,
         "SRE-Shield demonstrates that production incident response does not have to start from "
         "zero every time an alert fires. By combining the Hindsight Agent Memory architecture with "
         "Groq LLM inference, Memory Defense security, and a Human-in-the-Loop approval gate, "
         "the platform achieves something no stateless chatbot or standard RAG pipeline can match: "
         "a system that genuinely learns from every resolved incident and applies that learning "
         "automatically to the next one.")

    body(doc,
         "The result is a measurable, demonstrable reduction in MTTR — from hours of manual "
         "triage and tribal knowledge recovery to minutes of AI-guided, memory-augmented diagnosis "
         "and approved, verified remediation.")

    add_info_box(doc,
        "The SRE-Shield Promise",
        [
            "Every incident resolved today makes the next incident faster to resolve.",
            "Every post-mortem approved adds a permanent, searchable, structured lesson to the memory bank.",
            "Every engineer who responds to an alert stands on the shoulders of every SRE who came before them.",
            "No secret ever leaks into the memory layer.",
            "No destructive command ever runs without a human authorising it.",
        ],
        bg_color="F0FDF4", border_color="059669", title_color="064E3B"
    )

    # Save document
    output_path = r"c:\Users\MADHAVI\OneDrive\Desktop\SRE-Shield\SRE-Shield_Project_Document.docx"
    doc.save(output_path)
    print(f"Document saved successfully: {output_path}")
    return output_path


if __name__ == "__main__":
    build_document()
