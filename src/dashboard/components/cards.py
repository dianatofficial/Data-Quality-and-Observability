import textwrap
import streamlit as st


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

    card_html = f'<div class="obs-card" style="border-left: 4px solid {color};"><div class="obs-card-label"><span>{icon}</span> {title}</div><div style="display: flex; align-items: baseline; justify-content: space-between;"><span class="obs-card-value">{value}</span>{delta_html}</div>{sub_html}</div>'
    st.markdown(card_html, unsafe_allow_html=True)


def render_sla_badge(sla_passed: bool) -> str:
    """Renders an SLA status badge."""
    if sla_passed:
        return '<span class="badge-pass"><span style="color:#10b981; margin-right:4px;">●</span> SLA COMPLIANT</span>'
    return '<span class="badge-breach"><span style="color:#f43f5e; margin-right:4px;">●</span> SLA BREACHED</span>'


def render_severity_chip(severity: str) -> str:
    """Returns HTML for color-coded severity tags."""
    sev_upper = severity.upper()
    if sev_upper == "CRITICAL":
        return '<span class="badge-sev-critical">CRITICAL</span>'
    elif sev_upper == "HIGH":
        return '<span class="badge-sev-high">HIGH</span>'
    elif sev_upper == "MEDIUM":
        return '<span class="badge-sev-medium">MEDIUM</span>'
    return '<span class="badge-sev-low">LOW</span>'
