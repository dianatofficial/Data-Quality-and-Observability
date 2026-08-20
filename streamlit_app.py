"""
Automated Data Quality Gatekeeper & Observability Dashboard.
Production-grade enterprise UI with multi-tier contract validation, quarantine remediation, and schema governance.
"""
import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Setup project root in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import get_settings
from src.alerts.notifier import AlertDispatcher
from src.core.engine import GatekeeperEngine
from src.core.models import ValidationSeverity, ValidationStatus
from src.core.reporter import DataDocsReporter
from src.dashboard.simulator import LiveSimulationEngine
from src.ingestion.generator import EnterpriseDataGenerator

# ==============================================================================
# UI HELPER & COMPONENT RENDERERS
# ==============================================================================

def safe_html(html_str: str) -> None:
    """Renders HTML safely without triggering markdown 4-space indentation code blocks."""
    dedented = textwrap.dedent(html_str).strip()
    st.markdown(dedented, unsafe_allow_html=True)


def render_kpi_card(
    title: str,
    value: str | int | float,
    icon: str = "📊",
    subtitle: str | None = None,
    delta: str | None = None,
    color: str = "#3b82f6",
) -> None:
    """Renders a polished glassmorphic enterprise metric card."""
    delta_html = ""
    if delta:
        is_pos = not delta.startswith("-") and not delta.startswith("✕")
        d_color = "#10b981" if is_pos else "#f43f5e"
        delta_html = f'<span style="color: {d_color}; font-size: 0.8rem; font-weight: 700; margin-left: 8px;">{delta}</span>'

    sub_html = f'<div class="obs-card-sub">{subtitle}</div>' if subtitle else ""

    card_html = f"""<div class="obs-card" style="border-left: 4px solid {color};"><div class="obs-card-label"><span>{icon}</span> {title}</div><div style="display: flex; align-items: baseline; justify-content: space-between;"><span class="obs-card-value">{value}</span>{delta_html}</div>{sub_html}</div>"""
    safe_html(card_html)


def render_sla_badge(sla_passed: bool) -> str:
    """Renders an SLA status badge."""
    if sla_passed:
        return '<span class="badge-pass"><span style="color:#10b981; margin-right:4px;">●</span> SLA COMPLIANT</span>'
    return '<span class="badge-breach"><span style="color:#f43f5e; margin-right:4px;">●</span> SLA BREACHED</span>'


def render_health_gauge(score: float) -> go.Figure:
    """Builds an enterprise gauge chart for the Composite Data Health Score."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            number={"suffix": "%", "font": {"size": 38, "color": "#f8fafc", "family": "Plus Jakarta Sans, sans-serif"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#64748b", "tickfont": {"size": 11, "color": "#94a3b8"}},
                "bar": {"color": "#3b82f6", "thickness": 0.28},
                "bgcolor": "#111827",
                "borderwidth": 1,
                "bordercolor": "#243048",
                "steps": [
                    {"range": [0, 80], "color": "rgba(244, 63, 94, 0.25)"},
                    {"range": [80, 95], "color": "rgba(245, 158, 11, 0.25)"},
                    {"range": [95, 100], "color": "rgba(16, 185, 129, 0.25)"},
                ],
                "threshold": {
                    "line": {"color": "#10b981", "width": 4},
                    "thickness": 0.75,
                    "value": 95,
                },
            },
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#94a3b8", "family": "Plus Jakarta Sans, sans-serif"},
        margin=dict(l=15, r=15, t=25, b=15),
        height=220,
    )
    return fig


def render_dimensions_radar(dimensions: Dict[str, float]) -> go.Figure:
    """Radar chart showing 5 dimensions: Completeness, Validity, Uniqueness, Timeliness, Consistency."""
    categories = list(dimensions.keys())
    values = list(dimensions.values())

    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(59, 130, 246, 0.2)",
            line=dict(color="#3b82f6", width=2.5),
            marker=dict(size=7, color="#60a5fa", symbol="circle"),
            hovertemplate="<b>%{theta}</b>: %{r:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10, color="#64748b"),
                gridcolor="#243048",
                linecolor="#243048",
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="#cbd5e1", family="Plus Jakarta Sans"),
                gridcolor="#243048",
                linecolor="#243048",
            ),
            bgcolor="rgba(17, 24, 39, 0.6)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=35, r=35, t=25, b=25),
        height=260,
        showlegend=False,
    )
    return fig


def render_trend_chart(metrics: List[Dict[str, Any]]) -> go.Figure:
    """Time-series chart showing Health Score and Quarantined Record count trend."""
    if not metrics:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text="No batch history available",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#64748b"),
                )
            ],
        )
        return fig

    df = pd.DataFrame(metrics)
    if "executed_at" in df.columns:
        df["executed_at"] = pd.to_datetime(df["executed_at"])
        df = df.sort_values("executed_at")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["batch_id"].astype(str),
            y=df["overall_health_score"],
            name="Health Score (%)",
            mode="lines+markers",
            line=dict(color="#10b981", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.08)",
            marker=dict(size=7, color="#10b981", line=dict(width=1, color="#f8fafc")),
            yaxis="y1",
            hovertemplate="Batch: <b>%{x}</b><br>Health Score: <b>%{y:.2f}%</b><extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["batch_id"].astype(str),
            y=df["quarantined_records"],
            name="Quarantined Records",
            marker=dict(color="rgba(244, 63, 94, 0.75)", line=dict(width=1, color="#f43f5e")),
            yaxis="y2",
            hovertemplate="Batch: <b>%{x}</b><br>Quarantined: <b>%{y}</b><extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#94a3b8", "family": "Plus Jakarta Sans, sans-serif"},
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1"),
        ),
        xaxis=dict(
            gridcolor="#1e293b",
            title="Batch Identifier",
            tickangle=-25,
            tickfont=dict(size=10, color="#94a3b8"),
        ),
        yaxis=dict(
            title="Health Score (%)",
            range=[0, 105],
            gridcolor="#1e293b",
            side="left",
            tickfont=dict(color="#10b981"),
        ),
        yaxis2=dict(
            title="Quarantined Count",
            side="right",
            overlaying="y",
            showgrid=False,
            tickfont=dict(color="#f43f5e"),
        ),
        margin=dict(l=35, r=35, t=30, b=40),
        height=320,
    )
    return fig


def render_violations_bar(violations: Dict[str, int]) -> go.Figure:
    """Horizontal bar chart of top rule violation categories."""
    if not violations:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text="Zero Violations Recorded (100% Compliant)",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#10b981"),
                )
            ],
        )
        return fig

    items = sorted(violations.items(), key=lambda x: x[1], reverse=True)
    df = pd.DataFrame(items, columns=["Violation Type", "Count"])

    fig = px.bar(
        df,
        x="Count",
        y="Violation Type",
        orientation="h",
        color="Count",
        color_continuous_scale="Reds",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#94a3b8", "family": "Plus Jakarta Sans, sans-serif"},
        coloraxis_showscale=False,
        yaxis=dict(autorange="reversed", gridcolor="#1e293b", tickfont=dict(color="#cbd5e1")),
        xaxis=dict(gridcolor="#1e293b", tickfont=dict(color="#94a3b8")),
        margin=dict(l=15, r=15, t=15, b=15),
        height=260,
    )
    return fig


# ==============================================================================
# MAIN STREAMLIT APPLICATION
# ==============================================================================

st.set_page_config(
    page_title="Data Quality Gatekeeper & Observability",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Dark Theme Styling Injection
CSS_PATH = BASE_DIR / "src" / "dashboard" / "styles.css"
if CSS_PATH.exists():
    st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


@st.cache_resource
def get_simulator() -> LiveSimulationEngine:
    return LiveSimulationEngine()


@st.cache_resource
def get_engine() -> GatekeeperEngine:
    return GatekeeperEngine()


settings = get_settings()
simulator = get_simulator()
engine = get_engine()

# Sidebar
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Python-Dark.svg",
        width=44,
    )
    st.markdown("### **Gatekeeper Observability**")
    st.caption("v1.0.0 • Enterprise Data Governance")

    st.markdown("---")
    mode = st.radio(
        "Storage Engine Mode",
        options=["In-Memory Simulation (Cloud Demo)", "Connected Database (PostgreSQL/SQLite)"],
        index=0,
        help="Switch between zero-dependency standalone simulation and real warehouse storage.",
    )

    st.markdown("---")
    st.markdown("#### ⚙️ **SLA & Policy Gates**")
    safe_html(f"""<div style="background: rgba(255,255,255,0.03); border: 1px solid #243048; border-radius: 8px; padding: 12px; font-size: 0.85rem;"><div>• <b>Min Health Score:</b> <span style="color:#10b981;">{settings.sla_min_health_score}%</span></div><div style="margin-top:4px;">• <b>Max Error Rate:</b> <span style="color:#f43f5e;">{settings.sla_max_error_rate * 100}%</span></div><div style="margin-top:4px;">• <b>Drift Tolerance:</b> <span style="color:#f59e0b;">{settings.drift_score_threshold}</span></div><div style="margin-top:4px;">• <b>Auto-Quarantine:</b> <span style="color:#3b82f6;">{'Active' if settings.auto_quarantine_enabled else 'Disabled'}</span></div></div>""")

    st.markdown("---")
    st.markdown("#### ⚡ **Quick Stream Trigger**")
    if st.button("🚀 Ingest Synthetic Batch (150 recs)", use_container_width=True):
        summary = simulator.run_simulation_batch(batch_type="mixed", total_records=150)
        st.toast(
            f"Ingested Batch {summary.batch_id} • Score: {summary.health_score.overall_score}%",
            icon="🛡️",
        )

# Main Application Header
col_h_left, col_h_right = st.columns([3, 1])
with col_h_left:
    safe_html("""<div style="display:flex; align-items:center; gap:12px;"><h1 style="margin:0; font-size:2rem; font-weight:800; color:#f8fafc;">🛡️ Data Quality Gatekeeper</h1></div><div style="color:#94a3b8; font-size:0.9rem; margin-top:4px;">Pre-Ingestion Contract Gate • Automated Quarantine • Schema Drift & SLA Observability</div>""")

with col_h_right:
    latest = simulator.latest_summary
    if latest:
        badge = render_sla_badge(not latest.sla_breached)
        safe_html(f"""<div style="text-align:right; padding-top:8px;"><div style="font-size:0.75rem; color:#64748b; text-transform:uppercase; font-weight:700; margin-bottom:4px;">Current Pipeline SLA</div>{badge}</div>""")

# Pulse Status Banner
safe_html("""<div class="status-banner"><div style="display:flex; align-items:center;"><span class="pulse-dot"></span><span style="font-size:0.85rem; font-weight:700; color:#34d399;">GATEKEEPER ACTIVE</span><span style="margin: 0 8px; color:#475569;">|</span><span style="font-size:0.85rem; color:#cbd5e1;">Zero Data Drift Protocol Enforced • All Ingress Feeds Intercepted</span></div><div style="font-size:0.8rem; color:#94a3b8;">Latency: <b style="color:#38bdf8;">~3.4ms/batch</b></div></div>""")

# Navigation Tabs
tabs = st.tabs([
    "📊 Executive Observability",
    "⚡ Live Ingestion & Gatekeeper",
    "🛑 Quarantine & Remediation Center",
    "🧬 Schema Drift & Contracts",
    "📜 Data Docs & Health Certificates",
    "🚨 Incident & Alert Center",
])

# ==============================================================================
# TAB 1: EXECUTIVE OBSERVABILITY
# ==============================================================================
with tabs[0]:
    latest = simulator.latest_summary
    history = simulator.batch_history

    if latest:
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            render_kpi_card(
                title="Health Score",
                value=f"{latest.health_score.overall_score}%",
                icon="🎯",
                subtitle="Weighted 5-Dim Composite",
                delta=f"{'+' if latest.health_score.overall_score >= 95 else ''}{round(latest.health_score.overall_score - 95.0, 1)}% vs SLA",
                color="#10b981" if latest.health_score.overall_score >= 95 else "#f43f5e",
            )
        with c2:
            render_kpi_card(
                title="Pass Rate",
                value=f"{latest.pass_rate}%",
                icon="✅",
                subtitle=f"{latest.passed_records} clean promoted",
                color="#3b82f6",
            )
        with c3:
            render_kpi_card(
                title="Total Evaluated",
                value=f"{latest.total_records:,}",
                icon="📦",
                subtitle=f"Batch: {latest.batch_id}",
                color="#a855f7",
            )
        with c4:
            render_kpi_card(
                title="Quarantined",
                value=f"{latest.quarantined_records:,}",
                icon="🛑",
                subtitle=f"Error rate: {latest.error_rate * 100:.1f}%",
                color="#f43f5e" if latest.quarantined_records > 0 else "#10b981",
            )
        with c5:
            render_kpi_card(
                title="Gate Latency",
                value=f"{latest.processing_duration_ms} ms",
                icon="⚡",
                subtitle="Validation throughput",
                color="#06b6d4",
            )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        col_g, col_r, col_v = st.columns([1.1, 1.4, 1.4])
        with col_g:
            st.markdown("##### 🎯 **Health Index Gauge**")
            st.plotly_chart(render_health_gauge(latest.health_score.overall_score), use_container_width=True)

        with col_r:
            st.markdown("##### 🌐 **5 Quality Dimensions Radar**")
            dims = {
                "Completeness": latest.health_score.completeness,
                "Validity": latest.health_score.validity,
                "Uniqueness": latest.health_score.uniqueness,
                "Timeliness": latest.health_score.timeliness,
                "Consistency": latest.health_score.consistency,
            }
            st.plotly_chart(render_dimensions_radar(dims), use_container_width=True)

        with col_v:
            st.markdown("##### ⚠️ **Top Rule Violations**")
            st.plotly_chart(render_violations_bar(latest.violations_by_type), use_container_width=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 📈 **Historical Data Quality Trend & Quarantine Influx**")
        st.plotly_chart(render_trend_chart(history), use_container_width=True)

# ==============================================================================
# TAB 2: LIVE INGESTION & GATEKEEPER VALIDATOR
# ==============================================================================
with tabs[1]:
    st.subheader("⚡ Real-Time Data Ingestion & Pre-Ingestion Gate")
    st.markdown("Intercept incoming payload streams before persistence. Valid records land in clean tables; corrupted records are automatically routed to quarantine.")

    col_ing_ctrl, col_ing_res = st.columns([1.1, 1.9])

    with col_ing_ctrl:
        st.markdown("#### 🛠️ **Stream Generator**")
        dataset_choice = st.selectbox("Target Dataset", options=["orders (E-Commerce Transactions)", "customers (CRM Profiles)"])
        target_name = "orders" if "orders" in dataset_choice else "customers"

        preset = st.selectbox(
            "Stream Anomaly Profile",
            options=[
                "Mixed Stream (20% Bad Records - Range, Nulls, Regex)",
                "Pristine Clean Stream (100% Valid)",
                "Schema Drifted Stream (Unplanned Structural Mutation)",
                "High Stress Stream (40% Critical Corruption)",
            ],
        )

        vol = st.slider("Record Batch Size", min_value=20, max_value=500, value=120, step=20)

        if st.button("🚀 Trigger Ingestion & Validate Gate", type="primary", use_container_width=True):
            b_type = "mixed"
            if "Clean" in preset:
                b_type = "clean"
            elif "Drifted" in preset:
                b_type = "drifted"

            summary = simulator.run_simulation_batch(batch_type=b_type, total_records=vol)
            st.success(f"Batch {summary.batch_id} processed in {summary.processing_duration_ms}ms!")
            st.rerun()

        st.markdown("---")
        st.markdown("#### 🧪 **Interactive JSON Sandbox**")
        sample_json_text = st.text_area(
            "Paste Raw Record JSON:",
            value=json.dumps({
                "order_id": "ORD-TEST9999",
                "customer_id": "CUST-1001",
                "total_amount": -45.00,
                "discount_amount": 10.00,
                "currency": "USD",
                "status": "COMPLETED",
                "order_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
            }, indent=2),
            height=160,
        )

        if st.button("🔍 Validate Sandbox Payload", use_container_width=True):
            try:
                parsed_rec = json.loads(sample_json_text)
                recs_to_test = [parsed_rec] if isinstance(parsed_rec, dict) else parsed_rec
                s_sum, s_clean, s_quar = engine.process_batch("orders", recs_to_test)
                if s_quar:
                    st.error(f"✕ Record Intercepted & Quarantined! Found {len(s_quar[0].violations)} violation(s).")
                    st.json([v.model_dump() for v in s_quar[0].violations])
                else:
                    st.success("✓ Record Passed 100% of Expectation Rules!")
            except Exception as e:
                st.error(f"JSON Parsing Error: {str(e)}")

    with col_ing_res:
        st.markdown("#### 📋 **Gatekeeper Evaluation Matrix**")
        latest = simulator.latest_summary
        if latest:
            sum_data = [
                {"Metric": "Batch Identifier", "Value": str(latest.batch_id)},
                {"Metric": "Dataset", "Value": str(latest.dataset_name)},
                {"Metric": "Total Records Processed", "Value": str(latest.total_records)},
                {"Metric": "Clean Records (Promoted to DW)", "Value": f"{latest.passed_records} ({latest.pass_rate}%)"},
                {"Metric": "Quarantined Records (Isolated)", "Value": f"{latest.quarantined_records} ({latest.error_rate * 100:.2f}%)"},
                {"Metric": "Schema Drift Status", "Value": "⚠️ DETECTED" if latest.schema_drift.detected else "✅ NONE"},
                {"Metric": "SLA Compliance Status", "Value": "✕ BREACHED" if latest.sla_breached else "✓ COMPLIANT"},
                {"Metric": "Execution Latency", "Value": f"{latest.processing_duration_ms} ms"},
            ]
            df_sum = pd.DataFrame(sum_data)
            df_sum["Metric"] = df_sum["Metric"].astype(str)
            df_sum["Value"] = df_sum["Value"].astype(str)
            st.dataframe(df_sum, use_container_width=True, hide_index=True)

            st.markdown("##### **Quality Dimension Scores**")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.write(f"• **Completeness:** `{latest.health_score.completeness}%`")
                st.progress(latest.health_score.completeness / 100.0)
                st.write(f"• **Validity:** `{latest.health_score.validity}%`")
                st.progress(latest.health_score.validity / 100.0)
                st.write(f"• **Uniqueness:** `{latest.health_score.uniqueness}%`")
                st.progress(latest.health_score.uniqueness / 100.0)
            with d_col2:
                st.write(f"• **Timeliness:** `{latest.health_score.timeliness}%`")
                st.progress(latest.health_score.timeliness / 100.0)
                st.write(f"• **Consistency:** `{latest.health_score.consistency}%`")
                st.progress(latest.health_score.consistency / 100.0)

# ==============================================================================
# TAB 3: QUARANTINE & REMEDIATION CENTER
# ==============================================================================
with tabs[2]:
    st.subheader("🛑 Quarantine Review & Human-in-the-Loop Remediation")
    st.markdown("Inspect isolated bad records, audit root causes, and execute remediation workflows (Approve & Replay, Patch, or Drop).")

    q_filter_col1, q_filter_col2, q_filter_col3 = st.columns([1, 1, 2])
    with q_filter_col1:
        q_status_filter = st.selectbox("Status Filter", options=["All", "QUARANTINED", "RECONCILED", "DROPPED"])
    with q_filter_col2:
        q_sev_filter = st.selectbox("Severity Filter", options=["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
    with q_filter_col3:
        search_query = st.text_input("🔍 Search by Quarantine ID or Batch ID", "")

    all_q_records = simulator.get_quarantine_records()
    
    filtered_q = []
    for r in all_q_records:
        if q_status_filter != "All" and r["status"] != q_status_filter:
            continue
        if q_sev_filter != "All" and r["severity"] != q_sev_filter:
            continue
        if search_query and (search_query.lower() not in r["quarantine_id"].lower() and search_query.lower() not in r["batch_id"].lower()):
            continue
        filtered_q.append(r)

    st.markdown(f"Displaying **{len(filtered_q)}** quarantine record(s)")

    if filtered_q:
        df_q = pd.DataFrame([
            {
                "Quarantine ID": str(r["quarantine_id"]),
                "Batch ID": str(r["batch_id"]),
                "Entity Type": str(r["entity_type"]),
                "Severity": str(r["severity"]),
                "Status": str(r["status"]),
                "Violations Count": int(len(r["violations"])),
                "Quarantined At": (
                    r["quarantined_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(r["quarantined_at"], datetime)
                    else str(r["quarantined_at"])
                ),
            }
            for r in filtered_q
        ])
        st.dataframe(df_q, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🔬 **Record Root-Cause Inspector & Remediation**")

        q_ids = [r["quarantine_id"] for r in filtered_q]
        selected_qid = st.selectbox("Select Quarantine ID to Inspect:", options=q_ids)
        target_rec = next((r for r in filtered_q if r["quarantine_id"] == selected_qid), None)

        if target_rec:
            col_insp_left, col_insp_right = st.columns(2)
            with col_insp_left:
                st.markdown("##### **📦 Raw Intercepted Payload**")
                st.json(target_rec["raw_payload"])

            with col_insp_right:
                st.markdown("##### **⚠️ Rule Violations Breakdown**")
                for v in target_rec["violations"]:
                    safe_html(f"""<div style="background:rgba(244,63,94,0.08); border:1px solid #f43f5e; border-radius:6px; padding:10px; margin-bottom:8px;"><div style="font-weight:700; color:#f43f5e;">Rule: {v.get('rule_name')}</div><div style="font-size:0.85rem; color:#cbd5e1;">Column: <code>{v.get('column')}</code> | Type: <code>{v.get('rule_type')}</code></div><div style="font-size:0.85rem; color:#fda4af; margin-top:4px;">{v.get('message')}</div></div>""")

            if target_rec["status"] == "QUARANTINED":
                st.markdown("##### **⚡ Remediation Actions**")
                act_c1, act_c2, act_c3 = st.columns([1.2, 1.2, 2])
                with act_c1:
                    if st.button("✅ Approve & Replay to Clean DW", use_container_width=True):
                        simulator.resolve_quarantine_record(
                            selected_qid, "RECONCILE", notes="Approved by Senior Data Engineer after verification"
                        )
                        st.success(f"Record {selected_qid} approved and queued for replay!")
                        st.rerun()
                with act_c2:
                    if st.button("🗑️ Drop & Discard Record", use_container_width=True):
                        simulator.resolve_quarantine_record(
                            selected_qid, "DROP", notes="Unrecoverable corruption discarded"
                        )
                        st.warning(f"Record {selected_qid} marked as DROPPED.")
                        st.rerun()

# ==============================================================================
# TAB 4: SCHEMA DRIFT & CONTRACTS
# ==============================================================================
with tabs[3]:
    st.subheader("🧬 Schema Drift Monitoring & Contract Governance")
    st.markdown("Track schema mutations, unplanned column additions, and type divergences across ingress endpoints.")

    col_c_spec, col_c_res = st.columns(2)
    with col_c_spec:
        st.markdown("#### 📜 **Expected Contract Schema (`orders`)**")
        contract_spec = {
            "order_id": "str (Required UUID/Prefix ORD-)",
            "customer_id": "str (Required UUID/Prefix CUST-)",
            "total_amount": "float (Positive Decimal > 0.0)",
            "discount_amount": "float (Decimal >= 0.0 and <= total_amount)",
            "currency": "str (ISO Currency: USD, EUR, GBP, CAD, AUD, JPY)",
            "status": "str (Enum: PENDING, PROCESSING, COMPLETED, CANCELLED, REFUNDED)",
            "order_timestamp": "str (ISO-8601 UTC Datetime)",
            "items_count": "int (Positive Integer >= 1)",
            "shipping_country": "str (ISO 3166-1 Alpha-2)",
        }
        st.json(contract_spec)

    with col_c_res:
        st.markdown("#### ⚡ **Runtime Schema Drift Evaluation**")
        latest = simulator.latest_summary
        if latest:
            sd = latest.schema_drift
            st.metric("Drift Score (0.0 to 1.0)", f"{sd.drift_score:.3f}")
            st.write(f"**Drift Detected:** `{'⚠️ YES' if sd.detected else '✅ NO'}`")
            st.write(f"**Diagnostic Summary:** {sd.summary}")

            if sd.missing_columns:
                st.error(f"Missing Required Columns: {', '.join(sd.missing_columns)}")
            if sd.unexpected_columns:
                st.warning(f"Unexpected Columns: {', '.join(sd.unexpected_columns)}")
            if sd.type_mismatches:
                st.error(f"Type Mismatches: {sd.type_mismatches}")

# ==============================================================================
# TAB 5: DATA DOCS & HEALTH CERTIFICATES
# ==============================================================================
with tabs[4]:
    st.subheader("📜 Automated Data Quality Certificates & Data Docs")
    st.markdown("Compile self-contained, auditable HTML certificates for batch quality assurance and regulatory governance.")

    latest = simulator.latest_summary
    if latest:
        reporter = DataDocsReporter()
        html_doc = reporter.generate_html(latest)

        st.download_button(
            label="📥 Download Data Quality Certificate (HTML)",
            data=html_doc,
            file_name=f"data_quality_certificate_{latest.batch_id}.html",
            mime="text/html",
        )

        st.markdown("##### **Live Embedded Certificate Preview:**")
        try:
            st.components.v1.html(html_doc, height=620, scrolling=True)
        except Exception:
            st.markdown(html_doc, unsafe_allow_html=True)

# ==============================================================================
# TAB 6: INCIDENT & ALERT CENTER
# ==============================================================================
with tabs[5]:
    st.subheader("🚨 Real-Time Incident & Alerting Center")
    st.markdown("Automated dispatch of SLA breach incidents to Slack, PagerDuty, and Webhook receivers.")

    col_al_left, col_al_right = st.columns([1.1, 1.9])
    with col_al_left:
        st.markdown("#### 🔔 **Test Alert Dispatcher**")
        test_sev = st.selectbox("Severity Level", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        test_custom_msg = st.text_area("Custom Alert Note", "SLA violation detected on daily ingress pipeline.")

        if st.button("📤 Send Webhook / Slack Notification", use_container_width=True):
            dispatcher = AlertDispatcher(webhook_url=settings.slack_webhook_url)
            summary = simulator.latest_summary
            if summary:
                dispatcher.notify_batch_evaluation(summary)
                st.success("Alert notification dispatched to webhook receiver!")

    with col_al_right:
        st.markdown("#### 📜 **Remediation Audit Trail**")
        if simulator.audit_log:
            df_audit = pd.DataFrame([
                {
                    "Quarantine ID": str(a.get("quarantine_id", "")),
                    "Action": str(a.get("action", "")),
                    "Actor": str(a.get("actor", "")),
                    "Notes": str(a.get("notes", "")),
                    "Timestamp": (
                        a.get("timestamp").strftime("%Y-%m-%d %H:%M:%S")
                        if isinstance(a.get("timestamp"), datetime)
                        else str(a.get("timestamp", ""))
                    ),
                }
                for a in simulator.audit_log
            ])
            df_audit["Quarantine ID"] = df_audit["Quarantine ID"].astype(str)
            df_audit["Action"] = df_audit["Action"].astype(str)
            df_audit["Actor"] = df_audit["Actor"].astype(str)
            df_audit["Notes"] = df_audit["Notes"].astype(str)
            df_audit["Timestamp"] = df_audit["Timestamp"].astype(str)
            st.dataframe(df_audit, use_container_width=True, hide_index=True)
        else:
            st.info("Audit log is currently empty. Actions executed in the Quarantine tab will be logged here.")
