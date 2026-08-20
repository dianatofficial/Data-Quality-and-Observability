from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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

    # Health score line + area
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

    # Quarantined count bars
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
