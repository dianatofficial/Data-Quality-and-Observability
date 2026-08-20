import streamlit as st


def render_kpi_card(
    title: str,
    value: str | int | float,
    delta: str | None = None,
    color: str = "#3b82f6",
    help_text: str | None = None,
) -> None:
    """Renders a stylized KPI card in Streamlit."""
    delta_html = ""
    if delta:
        delta_color = "#10b981" if not delta.startswith("-") else "#ef4444"
        delta_html = f'<span style="color: {delta_color}; font-size: 0.85rem; font-weight: 600; margin-left: 8px;">{delta}</span>'

    card_html = f"""
    <div style="
        background: #161f30;
        border: 1px solid #2d3748;
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
    ">
        <div style="font-size: 0.8rem; font-weight: 600; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.05em;">
            {title}
        </div>
        <div style="display: flex; align-items: baseline; margin-top: 6px;">
            <span style="font-size: 1.8rem; font-weight: 700; color: #f7fafc;">{value}</span>
            {delta_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_sla_badge(sla_passed: bool) -> str:
    if sla_passed:
        return '<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #059669; padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">✓ SLA COMPLIANT</span>'
    return '<span style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #dc2626; padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">✕ SLA BREACHED</span>'
