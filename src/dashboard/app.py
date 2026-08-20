import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import streamlit as st

from config.settings import get_settings
from src.alerts.notifier import AlertDispatcher
from src.core.engine import GatekeeperEngine
from src.core.models import ValidationSeverity, ValidationStatus
from src.core.reporter import DataDocsReporter
from src.dashboard.components.cards import render_kpi_card, render_sla_badge
from src.dashboard.components.charts import (
    render_dimensions_radar,
    render_health_gauge,
    render_trend_chart,
    render_violations_bar,
)
from src.dashboard.simulator import LiveSimulationEngine
from src.storage.database import DatabaseManager
from src.storage.repositories import DataWarehouseRepository, QuarantineRepository

# Streamlit Page Config
st.set_page_config(
    page_title="Data Quality Gatekeeper & Observability",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling Injection
CSS_PATH = Path(__file__).parent / "styles.css"
if CSS_PATH.exists():
    st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# Initialize Session State
@st.cache_resource
def get_simulator() -> LiveSimulationEngine:
    return LiveSimulationEngine()


@st.cache_resource
def get_engine() -> GatekeeperEngine:
    return GatekeeperEngine()


settings = get_settings()
simulator = get_simulator()
engine = get_engine()

# Sidebar: Environment & Mode Selector
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Python-Dark.svg",
        width=48,
    )
    st.title("Gatekeeper Engine")
    st.caption("Automated Data Quality & Observability Platform")

    st.markdown("---")
    mode = st.radio(
        "Execution Mode",
        options=["In-Memory Simulation (Cloud Demo)", "Connected Database"],
        index=0,
        help="Switch between zero-dependency cloud preview simulator and real PostgreSQL/SQLite storage.",
    )

    st.markdown("---")
    st.markdown("### ⚙️ SLA Thresholds")
    st.write(f"• **Min Health Score:** `{settings.sla_min_health_score}%`")
    st.write(f"• **Max Error Rate:** `{settings.sla_max_error_rate * 100}%`")
    st.write(f"• **Auto-Quarantine:** `{'Enabled' if settings.auto_quarantine_enabled else 'Disabled'}`")

    st.markdown("---")
    if st.button("🔄 Trigger Synthetic Ingestion Stream", use_container_width=True):
        summary = simulator.run_simulation_batch(batch_type="mixed", total_records=150)
        st.toast(f"Ingested Batch `{summary.batch_id}`: Health Score {summary.health_score.overall_score}%", icon="🛡️")

# Main Header
col_header_left, col_header_right = st.columns([3, 1])
with col_header_left:
    st.title("🛡️ Data Quality Gatekeeper & Observability")
    st.markdown(
        "Pre-Ingestion Contract Validation &bull; Real-time Quarantine &bull; Zero Data Drift Protocol"
    )

with col_header_right:
    latest = simulator.latest_summary
    if latest:
        badge_html = render_sla_badge(not latest.sla_breached)
        st.markdown(
            f"<div style='text-align: right; padding-top: 10px;'>Status:<br>{badge_html}</div>",
            unsafe_allow_html=True,
        )

# Navigation Tabs
tabs = st.tabs([
    "📊 Executive Observability",
    "⚡ Live Gatekeeper Validator",
    "🛑 Quarantine & Reconciliation",
    "🧬 Schema Drift Explorer",
    "📜 Data Docs & Certificates",
    "🚨 Incident & Alert Center",
])

# ---------------------------------------------------------
# TAB 1: EXECUTIVE OBSERVABILITY
# ---------------------------------------------------------
with tabs[0]:
    st.subheader("Enterprise Data Quality Health Metrics")
    latest = simulator.latest_summary
    history = simulator.batch_history

    if latest:
        # Top KPI Cards Row
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        with kpi1:
            render_kpi_card(
                "Health Score",
                f"{latest.health_score.overall_score}%",
                color="#10b981" if latest.health_score.overall_score >= 95 else "#ef4444",
            )
        with kpi2:
            render_kpi_card("Pass Rate", f"{latest.pass_rate}%", color="#3b82f6")
        with kpi3:
            render_kpi_card("Total Evaluated", f"{latest.total_records:,}", color="#8b5cf6")
        with kpi4:
            render_kpi_card(
                "Quarantined",
                f"{latest.quarantined_records:,}",
                color="#ef4444" if latest.quarantined_records > 0 else "#10b981",
            )
        with kpi5:
            render_kpi_card("Gate Latency", f"{latest.processing_duration_ms} ms", color="#06b6d4")

        st.markdown("---")

        # Visual Analytics Row
        col_g, col_r, col_v = st.columns([1.2, 1.4, 1.4])
        with col_g:
            st.markdown("##### 🎯 Overall Health Gauge")
            st.plotly_chart(render_health_gauge(latest.health_score.overall_score), use_container_width=True)

        with col_r:
            st.markdown("##### 🌐 5 Quality Dimensions")
            dims = {
                "Completeness": latest.health_score.completeness,
                "Validity": latest.health_score.validity,
                "Uniqueness": latest.health_score.uniqueness,
                "Timeliness": latest.health_score.timeliness,
                "Consistency": latest.health_score.consistency,
            }
            st.plotly_chart(render_dimensions_radar(dims), use_container_width=True)

        with col_v:
            st.markdown("##### ⚠️ Rule Violations Distribution")
            st.plotly_chart(render_violations_bar(latest.violations_by_type), use_container_width=True)

        st.markdown("---")
        st.markdown("##### 📈 Historical Quality Trend & Quarantine Influx")
        st.plotly_chart(render_trend_chart(history), use_container_width=True)

# ---------------------------------------------------------
# TAB 2: LIVE GATEKEEPER VALIDATOR
# ---------------------------------------------------------
with tabs[1]:
    st.subheader("Real-Time Pre-Ingestion Data Quality Gate")
    st.markdown("Execute validation suites against live batches or custom JSON payloads before entering production storage.")

    col_ctrl1, col_ctrl2 = st.columns([1, 2])
    with col_ctrl1:
        st.markdown("##### 🛠 Ingest Test Batch")
        batch_preset = st.selectbox(
            "Batch Anomaly Profile",
            options=["Mixed / Corrupted (20% Bad Records)", "Clean Batch (100% Valid)", "Schema Drifted (Structural Change)"],
        )
        record_count = st.slider("Record Volume", min_value=10, max_value=500, value=100, step=10)

        if st.button("🚀 Run Gatekeeper Validation", type="primary", use_container_width=True):
            b_type = "mixed"
            if "Clean" in batch_preset:
                b_type = "clean"
            elif "Drifted" in batch_preset:
                b_type = "drifted"

            summary = simulator.run_simulation_batch(batch_type=b_type, total_records=record_count)
            st.success(f"Processed Batch `{summary.batch_id}` in {summary.processing_duration_ms}ms!")

    with col_ctrl2:
        st.markdown("##### 📋 Latest Batch Execution Summary")
        if simulator.latest_summary:
            ls = simulator.latest_summary
            sum_df = pd.DataFrame([
                {"Metric": "Batch ID", "Value": ls.batch_id},
                {"Metric": "Dataset", "Value": ls.dataset_name},
                {"Metric": "Total Records", "Value": ls.total_records},
                {"Metric": "Passed / Clean Records", "Value": f"{ls.passed_records} ({ls.pass_rate}%)"},
                {"Metric": "Quarantined Records", "Value": f"{ls.quarantined_records} ({ls.error_rate * 100:.2f}%)"},
                {"Metric": "Schema Drift Detected", "Value": "YES ⚠️" if ls.schema_drift.detected else "NO ✅"},
                {"Metric": "SLA Status", "Value": "BREACHED ✕" if ls.sla_breached else "COMPLIANT ✓"},
            ])
            st.dataframe(sum_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# TAB 3: QUARANTINE & RECONCILIATION
# ---------------------------------------------------------
with tabs[2]:
    st.subheader("Quarantine Record Review & Remediation Center")
    st.markdown("Inspect isolated bad records, audit root causes, and execute reconciliation workflows (Replay, Patch, or Drop).")

    q_filter = st.selectbox("Status Filter", options=["All", "QUARANTINED", "RECONCILED", "DROPPED"])
    status_arg = None if q_filter == "All" else q_filter
    q_records = simulator.get_quarantine_records(status=status_arg)

    st.write(f"Showing **{len(q_records)}** quarantined records")

    if q_records:
        df_q = pd.DataFrame([
            {
                "Quarantine ID": r["quarantine_id"],
                "Batch ID": r["batch_id"],
                "Entity Type": r["entity_type"],
                "Severity": r["severity"],
                "Status": r["status"],
                "Quarantined At": r["quarantined_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(r["quarantined_at"], datetime) else str(r["quarantined_at"]),
                "Violations Count": len(r["violations"]),
            }
            for r in q_records
        ])
        st.dataframe(df_q, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("##### 🔍 Inspect & Reconcile Record")
        selected_qid = st.selectbox("Select Quarantine ID to Inspect", options=[r["quarantine_id"] for r in q_records])
        selected_rec = next((r for r in q_records if r["quarantine_id"] == selected_qid), None)

        if selected_rec:
            col_raw, col_vio = st.columns(2)
            with col_raw:
                st.markdown("**Raw Intercepted Payload:**")
                st.json(selected_rec["raw_payload"])

            with col_vio:
                st.markdown("**Rule Violations Detected:**")
                st.json(selected_rec["violations"])

            if selected_rec["status"] == "QUARANTINED":
                col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
                with col_act1:
                    if st.button("✅ Approve & Replay to Clean Warehouse", use_container_width=True):
                        simulator.resolve_quarantine_record(
                            selected_qid, "RECONCILE", notes="Manually reviewed and approved by Data Engineer"
                        )
                        st.success(f"Record `{selected_qid}` reconciled and queued for replay!")
                        st.rerun()
                with col_act2:
                    if st.button("🗑️ Drop Record", use_container_width=True):
                        simulator.resolve_quarantine_record(
                            selected_qid, "DROP", notes="Unrecoverable anomaly discarded"
                        )
                        st.warning(f"Record `{selected_qid}` marked as DROPPED.")
                        st.rerun()

# ---------------------------------------------------------
# TAB 4: SCHEMA DRIFT EXPLORER
# ---------------------------------------------------------
with tabs[3]:
    st.subheader("Schema Contract & Drift Governance")
    st.markdown("Continuous monitoring of structural changes, column additions, deletions, and type divergences.")

    col_sd1, col_sd2 = st.columns(2)
    with col_sd1:
        st.markdown("##### 📜 Expected Production Contract (`orders`)")
        contract_spec = {
            "order_id": "str (UUID / Prefix ORD-)",
            "customer_id": "str (UUID / Prefix CUST-)",
            "total_amount": "float (> 0.0, <= 1000000.0)",
            "discount_amount": "float (>= 0.0, <= total_amount)",
            "currency": "str (USD, EUR, GBP, CAD, AUD, JPY)",
            "status": "str (State Machine allowed states)",
            "order_timestamp": "str (ISO-8601 Datetime)",
        }
        st.json(contract_spec)

    with col_sd2:
        st.markdown("##### ⚡ Latest Drift Evaluation Result")
        latest = simulator.latest_summary
        if latest:
            sd = latest.schema_drift
            st.metric("Drift Score (0.0 to 1.0)", sd.drift_score)
            st.write(f"**Drift Detected:** `{'⚠️ YES' if sd.detected else '✅ NO'}`")
            st.write(f"**Status:** {sd.summary}")
            if sd.missing_columns:
                st.error(f"Missing Columns: {sd.missing_columns}")
            if sd.unexpected_columns:
                st.warning(f"Unexpected Columns: {sd.unexpected_columns}")
            if sd.type_mismatches:
                st.error(f"Type Mismatches: {sd.type_mismatches}")

# ---------------------------------------------------------
# TAB 5: DATA DOCS & HTML CERTIFICATES
# ---------------------------------------------------------
with tabs[4]:
    st.subheader("Automated Data Quality Documentation & Certificates")
    st.markdown("Production-grade HTML documentation automatically compiled per batch for governance transparency.")

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

        st.markdown("##### Live Certificate Preview:")
        st.components.v1.html(html_doc, height=650, scrolling=True)

# ---------------------------------------------------------
# TAB 6: INCIDENT & ALERT CENTER
# ---------------------------------------------------------
with tabs[5]:
    st.subheader("SLA Breach Alerting & Incident Log")
    st.markdown("Real-time notifications sent to engineering response teams upon SLA degradation.")

    col_alert_test, col_alert_feed = st.columns([1, 2])
    with col_alert_test:
        st.markdown("##### 🔔 Alert Dispatcher Test")
        test_sev = st.selectbox("Alert Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        test_msg = st.text_area("Alert Message", "SLA violation detected on daily ingest batch.")

        if st.button("📤 Send Test Slack/Webhook Alert", use_container_width=True):
            dispatcher = AlertDispatcher(webhook_url=settings.slack_webhook_url)
            summary = simulator.latest_summary
            if summary:
                dispatcher.notify_batch_evaluation(summary)
                st.success("Alert successfully sent to Slack / Webhook Dispatcher!")

    with col_alert_feed:
        st.markdown("##### 📜 Recent Remediation Audit Trail")
        if simulator.audit_log:
            df_audit = pd.DataFrame(simulator.audit_log)
            st.dataframe(df_audit, use_container_width=True)
        else:
            st.info("Audit log is currently empty. Actions taken in the Quarantine tab will appear here.")
