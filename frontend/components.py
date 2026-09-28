import streamlit as st

def apply_sre_theme():
    """Injects high-grade dark enterprise SRE dashboard CSS"""
    st.markdown("""
    <style>
    /* Dark SRE Theme */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre, .stCode, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main background */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #070a12 !important;
        border-right: 1px solid #1e293b;
    }

    /* Metric cards */
    .sre-metric-card {
        background: linear-gradient(135deg, #131b2e 0%, #0f172a 100%);
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .sre-metric-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }
    .sre-metric-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .sre-metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.2;
    }
    .sre-metric-subtitle {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 4px;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .badge-critical {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid #ef4444;
    }
    .badge-high {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid #f59e0b;
    }
    .badge-medium {
        background-color: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid #3b82f6;
    }
    .badge-low {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #10b981;
    }
    .badge-sim {
        background-color: rgba(168, 85, 247, 0.2);
        color: #c084fc;
        border: 1px solid #a855f7;
    }

    /* Incident card */
    .incident-panel {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }

    /* Comparison box */
    .comparison-card-mem {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 78, 59, 0.2) 100%);
        border: 1px solid #059669;
        border-radius: 8px;
        padding: 16px;
    }
    .comparison-card-nomem {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(127, 29, 29, 0.2) 100%);
        border: 1px solid #dc2626;
        border-radius: 8px;
        padding: 16px;
    }

    /* Pulse dot */
    .pulse-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
        margin-right: 6px;
    }

    /* Execution timeline step */
    .timeline-step {
        border-left: 2px solid #3b82f6;
        padding-left: 14px;
        margin-left: 6px;
        margin-bottom: 12px;
        position: relative;
    }
    .timeline-step::before {
        content: "";
        position: absolute;
        left: -6px;
        top: 4px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #3b82f6;
    }
    </style>
    """, unsafe_allow_html=True)

def render_metric_card(label: str, value: str, subtitle: str = "", delta_color: str = "#10b981"):
    st.markdown(f"""
    <div class="sre-metric-card">
        <div class="sre-metric-label">{label}</div>
        <div class="sre-metric-value">{value}</div>
        <div class="sre-metric-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_severity_badge(severity: str):
    sev = severity.upper()
    cls_map = {
        "CRITICAL": "badge-critical",
        "HIGH": "badge-high",
        "MEDIUM": "badge-medium",
        "LOW": "badge-low"
    }
    cls = cls_map.get(sev, "badge-medium")
    return f'<span class="badge {cls}">{sev}</span>'

def render_status_badge(status: str):
    st_upper = status.upper()
    if st_upper in ("RESOLVED", "VERIFIED"):
        return f'<span class="badge badge-low">● {st_upper}</span>'
    elif st_upper in ("NEW", "INVESTIGATING", "AWAITING_APPROVAL"):
        return f'<span class="badge badge-critical">⚡ {st_upper}</span>'
    elif st_upper == "EXECUTING":
        return f'<span class="badge badge-high">⚙ {st_upper}</span>'
    else:
        return f'<span class="badge badge-medium">{st_upper}</span>'
